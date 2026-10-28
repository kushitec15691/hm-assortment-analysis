# How to build the project (step by step, for Kushmi)

Time needed: about 3–4 evenings. Keep this file private (don't upload it to GitHub).

## Evening 1 – get the data and run the script (1–2 hours)
1. Go to kaggle.com, create a free account (or sign in with Google).
2. Search for **"H&M Personalized Fashion Recommendations"** → open the competition → **Data** tab → click **"Join competition" / "I understand and accept"** (needed to download).
3. Download only these three files (skip the 30 GB images folder):
   - `articles.csv` (~35 MB)
   - `customers.csv` (~200 MB)
   - `transactions_train.csv` (~3.5 GB – takes a while)
   Put them in one folder, e.g. `C:\hm_data` (Windows) or `~/hm_data` (Mac).
4. Unzip this project folder somewhere, e.g. `C:\hm-assortment-analysis`.
5. Open a terminal:
   - Windows: Start → type `cmd` → Enter. Mac: open Terminal.
6. Check Python: type `python --version`. If it says "not found", install Python 3.12 from python.org (Windows: tick **"Add Python to PATH"** during install), then open a new terminal.
7. Install DuckDB: `pip install duckdb`
8. Go to the project folder and run:
   ```
   cd C:\hm-assortment-analysis
   python build_tables.py --data C:\hm_data --out output
   ```
   (Mac: `cd ~/hm-assortment-analysis` and `python3 build_tables.py --data ~/hm_data --out output`)
9. Wait 2–10 minutes. At the end you'll see six CSV files and some headline numbers. **Copy the headline numbers and send them to Claude.**

If you get an error, copy the full red text and send it to Claude.

## Evening 2 – Power BI dashboard (2–3 hours)
Open Power BI Desktop → **Get data → Text/CSV** → load all six files from `output/`. Build three pages:

**Page 1 – Overview (top-down)**
- Cards: total units, total sales value, online share, number of products.
- Line chart: `weekly_sales` – week on the axis, sales_value as value, channel as legend.
- Stacked bar: sales_value by index_group_name.
- Slicers: period, channel, index_group_name.

**Page 2 – Groups & price (bottom-up)**
- Table from `group_growth`: garment group, share_of_total_y2, growth_y2_vs_y1, avg_price_y1, avg_price_y2. Conditional formatting: green for growth, red for decline.
- Scatter chart: x = share_of_total_y2, y = growth_y2_vs_y1, details = garment_group_name ("where to invest vs where to fix").
- 100% stacked column from `price_band_mix`: garment group on the axis, price_band as legend, units as value.

**Page 3 – Products & customers**
- Table from `product_lifecycle`: top and bottom products by weekly_rate_first_8w per garment group (filter speed_quintile = 5 and = 1).
- Matrix from `customer_mix`: age_band as rows, index_group_name as columns, units as values.
- Bar chart from `colour_season`: top colours per season (filter on a garment group).

Use one colour theme, clear titles that state the insight (e.g. "Online grew while stores fell in spring 2020"), and no more than 4–5 visuals per page.

## Evening 3 – findings and GitHub (1–2 hours)
1. Send Claude screenshots of the three pages; together we'll write 3–5 findings for the README (each: number → so what → suggested action).
2. Create a GitHub repository `hm-assortment-analysis`, upload `README.md`, `build_tables.py`, the `sql` folder and the screenshots. **Don't upload the Kaggle data or the output folder.**
3. Add the repository to your LinkedIn **Featured** section and your portfolio site.
4. Claude adds the project to your CV.

## Evening 4 (optional) – LinkedIn post
A short post: what you analysed, one chart, two findings, and the link. It shows H&M recruiters the work directly.

## Talking about it in the interview
"I wanted to understand assortment controlling from the data side, so I analysed 31 million of H&M's own public transactions. I looked at the mix top-down and bottom-up, price bands, rate of sale after launch and channel shifts. For example, [your best finding]. It showed me how much quantity, timing and price drive the result – which is exactly what this role optimises."
