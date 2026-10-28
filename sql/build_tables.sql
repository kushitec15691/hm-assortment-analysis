-- H&M Assortment Performance Analysis
-- Builds small summary tables from the H&M Kaggle dataset (2018-09-20 to 2020-09-22).
-- Engine: DuckDB. Paths are set by build_tables.py (variables replaced at run time).

CREATE OR REPLACE VIEW articles AS
SELECT * FROM read_csv_auto('{DATA}/articles.csv', header=true, all_varchar=true);

CREATE OR REPLACE VIEW customers AS
SELECT customer_id, TRY_CAST(age AS INTEGER) AS age, club_member_status
FROM read_csv_auto('{DATA}/customers.csv', header=true, all_varchar=true);

CREATE OR REPLACE VIEW tx AS
SELECT CAST(t_dat AS DATE) AS t_dat,
       customer_id,
       article_id,
       CAST(price AS DOUBLE) AS price,
       CASE WHEN CAST(sales_channel_id AS INTEGER) = 2 THEN 'Online' ELSE 'Store' END AS channel
FROM read_csv_auto('{DATA}/transactions_train.csv', header=true, all_varchar=true);

-- Enriched fact table (one row per item sold), persisted once for speed
CREATE OR REPLACE TABLE fact AS
SELECT t.t_dat,
       date_trunc('week', t.t_dat)                        AS week,
       year(t.t_dat)                                      AS yr,
       CASE WHEN t.t_dat >= DATE '2019-09-23' THEN 'Y2 (Sep 2019–Sep 2020)'
            ELSE 'Y1 (Sep 2018–Sep 2019)' END             AS period,
       t.channel, t.price, t.customer_id, t.article_id,
       a.product_code, a.prod_name, a.product_type_name, a.product_group_name,
       a.department_name, a.index_name, a.index_group_name, a.section_name, a.garment_group_name,
       a.colour_group_name
FROM tx t LEFT JOIN articles a ON t.article_id = a.article_id;

-- Price bands per garment group (quartiles of the normalised price within each garment group)
CREATE OR REPLACE TABLE price_bands AS
SELECT garment_group_name,
       quantile_cont(price, 0.25) AS p25,
       quantile_cont(price, 0.50) AS p50,
       quantile_cont(price, 0.75) AS p75
FROM fact GROUP BY garment_group_name;

-- 1. Weekly sales by group and channel (trend, seasonality, channel mix)
COPY (
  SELECT week, period, channel, index_group_name, garment_group_name,
         count(*) AS units, round(sum(price), 4) AS sales_value,
         count(DISTINCT customer_id) AS customers
  FROM fact GROUP BY ALL ORDER BY week
) TO '{OUT}/weekly_sales.csv' (HEADER);

-- 2. Top-down vs bottom-up: each group's share of total and growth Y2 vs Y1
COPY (
  WITH g AS (
    SELECT index_group_name, garment_group_name, period,
           sum(price) AS sales_value, count(*) AS units
    FROM fact GROUP BY ALL
  ), p AS (
    SELECT index_group_name, garment_group_name,
           round(sum(CASE WHEN period LIKE 'Y1%' THEN sales_value END), 4) AS sales_y1,
           round(sum(CASE WHEN period LIKE 'Y2%' THEN sales_value END), 4) AS sales_y2,
           sum(CASE WHEN period LIKE 'Y1%' THEN units END) AS units_y1,
           sum(CASE WHEN period LIKE 'Y2%' THEN units END) AS units_y2
    FROM g GROUP BY ALL
  )
  SELECT *,
         round(sales_y2 / sum(sales_y2) OVER (), 4)         AS share_of_total_y2,
         round(sales_y2 / NULLIF(sales_y1, 0) - 1, 4)        AS growth_y2_vs_y1,
         round(sales_y2 / NULLIF(units_y2, 0), 6)            AS avg_price_y2,
         round(sales_y1 / NULLIF(units_y1, 0), 6)            AS avg_price_y1
  FROM p ORDER BY sales_y2 DESC
) TO '{OUT}/group_growth.csv' (HEADER);

-- 3. Price band mix: where volume and value sit within each garment group
COPY (
  SELECT f.garment_group_name, f.channel, f.period,
         CASE WHEN f.price <= b.p25 THEN '1 Entry'
              WHEN f.price <= b.p50 THEN '2 Core low'
              WHEN f.price <= b.p75 THEN '3 Core high'
              ELSE '4 Premium' END AS price_band,
         count(*) AS units, round(sum(f.price), 4) AS sales_value
  FROM fact f JOIN price_bands b USING (garment_group_name)
  GROUP BY ALL ORDER BY 1, 4
) TO '{OUT}/price_band_mix.csv' (HEADER);

-- 4. Product lifecycle: rate of sale in the first 8 weeks after launch (fast vs slow movers)
COPY (
  WITH first_sale AS (
    SELECT product_code, min(t_dat) AS launch_date FROM fact GROUP BY product_code
  ), w AS (
    SELECT f.product_code, any_value(f.prod_name) AS prod_name,
           any_value(f.garment_group_name) AS garment_group_name,
           any_value(f.index_group_name) AS index_group_name,
           fs.launch_date,
           count(*) FILTER (WHERE f.t_dat < fs.launch_date + INTERVAL 56 DAY) AS units_first_8w,
           count(*) AS units_total,
           round(sum(f.price), 4) AS sales_total,
           max(f.t_dat) AS last_sale
    FROM fact f JOIN first_sale fs USING (product_code)
    GROUP BY f.product_code, fs.launch_date
  )
  SELECT *,
         round(units_first_8w / 8.0, 2) AS weekly_rate_first_8w,
         ntile(5) OVER (PARTITION BY garment_group_name ORDER BY units_first_8w) AS speed_quintile
  FROM w
  WHERE launch_date >= DATE '2018-10-01'   -- skip products already on sale when data starts
    AND launch_date <= DATE '2020-07-28'   -- need 8 full weeks of data after launch
) TO '{OUT}/product_lifecycle.csv' (HEADER);

-- 5. Customer mix: age bands by department and channel
COPY (
  SELECT f.index_group_name, f.garment_group_name, f.channel, f.period,
         CASE WHEN c.age IS NULL THEN 'Unknown'
              WHEN c.age < 25 THEN '16–24' WHEN c.age < 35 THEN '25–34'
              WHEN c.age < 45 THEN '35–44' WHEN c.age < 55 THEN '45–54'
              ELSE '55+' END AS age_band,
         count(*) AS units, round(sum(f.price), 4) AS sales_value,
         count(DISTINCT f.customer_id) AS customers
  FROM fact f LEFT JOIN customers c USING (customer_id)
  GROUP BY ALL
) TO '{OUT}/customer_mix.csv' (HEADER);

-- 6. Colour mix by season (what customers want, when)
COPY (
  SELECT garment_group_name, colour_group_name,
         CASE WHEN month(t_dat) IN (3,4,5) THEN 'Spring' WHEN month(t_dat) IN (6,7,8) THEN 'Summer'
              WHEN month(t_dat) IN (9,10,11) THEN 'Autumn' ELSE 'Winter' END AS season,
         period, count(*) AS units
  FROM fact GROUP BY ALL
) TO '{OUT}/colour_season.csv' (HEADER);
