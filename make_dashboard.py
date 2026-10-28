"""
H&M Assortment Performance Analysis - build the dashboard automatically.

Usage (after build_tables.py has created the output folder):
    python -m pip install plotly pandas
    python make_dashboard.py --out output

Creates output/dashboard.html: one interactive page with KPIs, seven charts
and the key findings. Open it in any browser; take screenshots for GitHub.
"""
import argparse
import pathlib

import pandas as pd
import plotly.express as px
import plotly.io as pio

PALETTE = {"Online": "#0B6E4F", "Store": "#C8102E"}
GROUPS = {"Ladieswear": "#0B6E4F", "Divided": "#E07A1F", "Menswear": "#3A6EA5",
          "Sport": "#8E5AA8", "Baby/Children": "#C8102E"}
COLOURS = {"Black": "#1A1A1A", "White": "#E6E6E6", "Off White": "#EFE9DD", "Dark Blue": "#1F3A68",
           "Blue": "#3A6EA5", "Light Blue": "#9CC3E6", "Grey": "#8C8C8C", "Dark Grey": "#4D4D4D",
           "Light Grey": "#C8C8C8", "Light Pink": "#F4B8C4", "Pink": "#E5739B", "Beige": "#D8C3A0",
           "Light Beige": "#E8DAC0", "Dark Beige": "#B39B73", "Red": "#C8102E", "Dark Red": "#7A0E1E",
           "Green": "#3C8D4F", "Dark Green": "#1F4D2B", "Khaki green": "#7A7B4A", "Yellow": "#E8C547",
           "Light Orange": "#F2B57A", "Orange": "#E07A1F", "Brown": "#7A4E2D", "Other": "#B0B0B0"}
SEQ = ["#0B6E4F", "#2E8B6E", "#7FB8A4", "#C9E3D9"]
Y1, Y2 = "Y1 (Sep 2018–Sep 2019)", "Y2 (Sep 2019–Sep 2020)"


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def style(fig, title: str, height: int = 420):
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=17)),
        template="plotly_white", height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", y=-0.15),
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", size=12),
    )
    return fig


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output", help="folder with the CSV files from build_tables.py")
    out = pathlib.Path(ap.parse_args().out)

    weekly = pd.read_csv(out / "weekly_sales.csv", parse_dates=["week"])
    growth = pd.read_csv(out / "group_growth.csv")
    bands = pd.read_csv(out / "price_band_mix.csv")
    life = pd.read_csv(out / "product_lifecycle.csv")
    cust = pd.read_csv(out / "customer_mix.csv")
    colour = pd.read_csv(out / "colour_season.csv")

    # ---------- KPIs ----------
    by_p = weekly.groupby("period")[["units", "sales_value"]].sum()
    units_g = by_p.loc[Y2, "units"] / by_p.loc[Y1, "units"] - 1
    value_g = by_p.loc[Y2, "sales_value"] / by_p.loc[Y1, "sales_value"] - 1
    ch = weekly.groupby(["period", "channel"])["sales_value"].sum().unstack()
    online_share_y2 = ch.loc[Y2, "Online"] / ch.loc[Y2].sum()
    store_g = ch.loc[Y2, "Store"] / ch.loc[Y1, "Store"] - 1
    online_g = ch.loc[Y2, "Online"] / ch.loc[Y1, "Online"] - 1
    # (label, value, sub-text, tone)  tone: up / down / neutral
    kpis = [
        ("Items sold", f"{weekly['units'].sum() / 1e6:.1f}M", "Sep 2018 – Sep 2020", "neutral"),
        ("New products tracked", f"{life['product_code'].nunique() / 1e3:.1f}K", "launched within the period", "neutral"),
        ("Online share of sales", f"{online_share_y2 * 100:.0f}%", "of sales value in Y2", "neutral"),
        ("Avg price per item", pct((1 + value_g) / (1 + units_g) - 1), "Y2 vs Y1", (1 + value_g) / (1 + units_g) - 1),
        ("Units", pct(units_g), "Y2 vs Y1", units_g),
        ("Sales value", pct(value_g), "Y2 vs Y1", value_g),
        ("Store sales", pct(store_g), "Y2 vs Y1", store_g),
        ("Online sales", pct(online_g), "Y2 vs Y1", online_g),
    ]
    kpis = [(k, v, sub, t if isinstance(t, str) else ("up" if t > 0 else "down")) for k, v, sub, t in kpis]

    figs = []

    # 1. Weekly sales by channel
    w = weekly.groupby(["week", "channel"], as_index=False)["sales_value"].sum()
    weeks = sorted(w["week"].unique())
    w = w[(w["week"] > weeks[0]) & (w["week"] < weeks[-1])]  # drop partial first/last week
    figs.append(style(px.line(w, x="week", y="sales_value", color="channel",
                              color_discrete_map=PALETTE,
                              labels={"sales_value": "Sales value (normalised)", "week": ""}),
                      f"Stores fell {abs(store_g) * 100:.0f}% vs online {abs(online_g) * 100:.0f}% – weekly sales by channel"))

    # 2. Index group mix
    ig = growth.groupby("index_group_name")[["sales_y1", "sales_y2"]].sum().reset_index()
    ig = ig.melt(id_vars="index_group_name", var_name="year", value_name="sales_value")
    ig["year"] = ig["year"].map({"sales_y1": "Y1", "sales_y2": "Y2"})
    figs.append(style(px.bar(ig, y="index_group_name", x="sales_value", color="year", barmode="group",
                             orientation="h", color_discrete_sequence=["#9AA5A0", "#0B6E4F"],
                             labels={"index_group_name": "", "sales_value": "Sales value"}),
                      "Top-down: sales by index group, Y1 vs Y2"))

    # 3. Bottom-up: growth vs share (bubble)
    g = growth.dropna(subset=["growth_y2_vs_y1", "share_of_total_y2"])
    g = g[g["share_of_total_y2"] >= 0.005].copy()
    g["label"] = g["index_group_name"] + " · " + g["garment_group_name"]
    g["Growth"] = g["growth_y2_vs_y1"] * 100
    g["Share of sales (%)"] = g["share_of_total_y2"] * 100
    fig = px.scatter(g, x="Share of sales (%)", y="Growth", size="sales_y2", color="index_group_name",
                     hover_name="label", size_max=45, color_discrete_map=GROUPS,
                     labels={"Growth": "Growth Y2 vs Y1 (%)", "index_group_name": "Index group"})
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    for _, r in pd.concat([g.nlargest(3, "Growth"), g.nsmallest(3, "Growth"), g.nlargest(2, "sales_y2")]).drop_duplicates("label").iterrows():
        fig.add_annotation(x=r["Share of sales (%)"], y=r["Growth"], text=r["garment_group_name"],
                           showarrow=False, yshift=14, font=dict(size=10))
    figs.append(style(fig, "Bottom-up: which garment groups grew – size = sales, above the line = growth", 480))

    # 4. Biggest movers (sales value change)
    g2 = growth.copy()
    g2["change"] = g2["sales_y2"].fillna(0) - g2["sales_y1"].fillna(0)
    g2["label"] = g2["index_group_name"] + " · " + g2["garment_group_name"]
    movers = pd.concat([g2.nsmallest(8, "change"), g2.nlargest(6, "change")]).sort_values("change")
    movers["direction"] = movers["change"].apply(lambda v: "Growth" if v > 0 else "Decline")
    figs.append(style(px.bar(movers, x="change", y="label", orientation="h", color="direction",
                             color_discrete_map={"Growth": "#0B6E4F", "Decline": "#C8102E"},
                             labels={"change": "Change in sales value", "label": ""}),
                      "Comfort wins, occasion loses – biggest movers in sales value", 480))

    # 5. Price band mix by channel and year
    b = bands.groupby(["channel", "period", "price_band"], as_index=False)["sales_value"].sum()
    b["share"] = b["sales_value"] / b.groupby(["channel", "period"])["sales_value"].transform("sum") * 100
    b["column"] = b["channel"] + " " + b["period"].str[:2]
    figs.append(style(px.bar(b, x="column", y="share", color="price_band", text=b["share"].round(0),
                             color_discrete_sequence=SEQ[::-1],
                             labels={"share": "% of sales value", "column": "", "price_band": "Price band"}),
                      "Premium holds, entry price weakens – price band mix (bands = quartiles within each garment group)"))

    # 6. Customer age mix
    c = cust[cust["age_band"] != "Unknown"].groupby(["age_band", "index_group_name"], as_index=False)["units"].sum()
    c["share"] = c["units"] / c.groupby("index_group_name")["units"].transform("sum") * 100
    pivot = c.pivot(index="age_band", columns="index_group_name", values="share").round(1)
    figs.append(style(px.imshow(pivot, text_auto=True, color_continuous_scale="Greens", aspect="auto",
                                labels={"color": "% of units", "x": "", "y": "Age band"}),
                      "Who buys what – share of units by customer age band within each index group"))

    # 7. Fast vs slow movers after launch
    l = life.groupby("garment_group_name", as_index=False)["weekly_rate_first_8w"].median()
    l = l.sort_values("weekly_rate_first_8w")
    figs.append(style(px.bar(l, x="weekly_rate_first_8w", y="garment_group_name", orientation="h",
                             color_discrete_sequence=["#0B6E4F"],
                             labels={"weekly_rate_first_8w": "Median units per week, first 8 weeks after launch",
                                     "garment_group_name": ""}),
                      "Rate of sale after launch – median product per garment group", 520))

    # 8. Top colours by season
    top = colour.groupby(["season", "colour_group_name"], as_index=False)["units"].sum()
    top["rank"] = top.groupby("season")["units"].rank(ascending=False)
    top = top[top["rank"] <= 6]
    order = ["Spring", "Summer", "Autumn", "Winter"]
    figs.append(style(px.bar(top, x="season", y="units", color="colour_group_name", barmode="group",
                             category_orders={"season": order}, color_discrete_map=COLOURS,
                             labels={"units": "Units", "season": "", "colour_group_name": "Colour"}),
                      "What customers want, when – top 6 colours per season"))

    findings = (out.parent / "README.md")
    findings_html = ""
    if findings.exists():
        txt = findings.read_text(encoding="utf-8")
        if "## Key findings" in txt:
            block = txt.split("## Key findings", 1)[1].split("\n## ", 1)[0]
            import html, re
            items = re.findall(r"^\d\.\s+(.*)$", block, flags=re.M)
            def md(s):
                s = html.escape(s)
                s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
                return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
            findings_html = "<ol>" + "".join(f"<li>{md(i)}</li>" for i in items) + "</ol>"

    arrow = {"up": "&#9650;", "down": "&#9660;", "neutral": ""}
    kpi_html = "".join(
        f'<div class="kpi {t}"><div class="l">{k}</div>'
        f'<div class="v">{('<span class="ar">' + arrow[t] + '</span>') if arrow[t] else ""}{v}</div><div class="s">{sub}</div></div>'
        for k, v, sub, t in kpis)
    charts = "".join(f'<div class="card">{pio.to_html(f, full_html=False, include_plotlyjs=(i == 0))}</div>'
                     for i, f in enumerate(figs))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>H&amp;M Assortment Performance</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#F4F6F5;color:#1D2B26;font-family:'Inter','Segoe UI',Arial,sans-serif}}
header{{background:linear-gradient(120deg,#0B3D2E,#0B6E4F);color:#fff;padding:30px 16px 60px}}
header h1{{margin:0 0 6px;font-size:28px;font-weight:800;letter-spacing:-.01em}} header p{{margin:0;opacity:.9}}
main{{max-width:1200px;margin:0 auto;padding:0 16px 24px}} .hin{{max-width:1168px;margin:0 auto}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:-34px 0 22px;position:relative}}
@media (max-width:820px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
.kpi{{background:#fff;border-radius:14px;padding:18px 20px 16px;box-shadow:0 4px 14px rgba(11,40,30,.08);border-top:4px solid #0B6E4F}}
.kpi.down{{border-top-color:#C8102E}} .kpi.up{{border-top-color:#1F9D55}}
.kpi .l{{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#6B7B75}}
.kpi .v{{font-size:34px;font-weight:800;line-height:1.15;margin-top:8px;color:#0B3D2E;font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
.kpi.down .v{{color:#C8102E}} .kpi.up .v{{color:#1F9D55}}
.kpi .ar{{font-size:18px;margin-right:8px;vertical-align:middle;position:relative;top:-3px}}
.kpi .s{{font-size:12px;color:#8A9893;margin-top:4px}}
.card{{background:#fff;border-radius:10px;padding:8px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.findings{{background:#fff;border-radius:10px;padding:8px 24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);line-height:1.5}}
footer{{color:#5B6B65;font-size:12px;padding:8px 16px 32px;max-width:1200px;margin:0 auto}}
</style></head><body>
<header><div class="hin"><h1>H&amp;M Assortment Performance Analysis</h1>
<p>31.8M real H&amp;M transactions · Sep 2018 – Sep 2020 · top-down and bottom-up · by Kushmi Chandrasena</p></div></header>
<main><div class="kpis">{kpi_html}</div>
{f'<div class="findings"><h2>Key findings</h2>{findings_html}</div>' if findings_html else ''}
{charts}</main>
<footer>Data: H&amp;M Personalized Fashion Recommendations (Kaggle). Prices are normalised in the source data, so values show relative sales value, not SEK.
sales_channel_id 2 is treated as online. Y2 includes the Covid-19 spring of 2020. Built with SQL (DuckDB), Python and Plotly.</footer>
</body></html>"""
    target = out / "dashboard.html"
    target.write_text(page, encoding="utf-8")
    print(f"Dashboard written to {target.resolve()} – open it in your browser.")


if __name__ == "__main__":
    main()
