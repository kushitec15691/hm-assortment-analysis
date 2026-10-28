"""
H&M Assortment Performance Analysis – build summary tables.

Usage:
    pip install duckdb
    python build_tables.py --data path/to/kaggle_folder --out output

Reads articles.csv, customers.csv and transactions_train.csv from the H&M
Personalized Fashion Recommendations dataset (Kaggle) and writes six small CSV
files to --out, ready for Power BI or Excel. Runs on a normal laptop
(DuckDB streams the 31M-row file; expect 2–10 minutes).
"""
import argparse
import pathlib
import time

import duckdb

HERE = pathlib.Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder with the three Kaggle CSV files")
    ap.add_argument("--out", default="output", help="folder for the summary CSV files")
    args = ap.parse_args()

    data = pathlib.Path(args.data).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for f in ("articles.csv", "customers.csv", "transactions_train.csv"):
        if not (data / f).exists():
            raise SystemExit(f"Missing {data / f} – download it from Kaggle first (see README).")

    sql = (HERE / "sql" / "build_tables.sql").read_text(encoding="utf-8")
    sql = sql.replace("{DATA}", data.as_posix()).replace("{OUT}", out.as_posix())

    con = duckdb.connect(str(out / "hm.duckdb"))
    start = time.time()
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        first = next(l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--"))
        print(f"[{time.time() - start:6.1f}s] {first[:70]}")
        con.execute(stmt)

    print("\nRows written:")
    for f in sorted(out.glob("*.csv")):
        n = con.execute(f"SELECT count(*) FROM read_csv_auto('{f.as_posix()}')").fetchone()[0]
        print(f"  {f.name:24s} {n:>10,}")

    # Headline numbers for the README / LinkedIn post
    print("\nHeadline numbers:")
    for label, q in [
        ("Items sold", "SELECT count(*) FROM fact"),
        ("Online share of units", "SELECT round(avg(CASE WHEN channel='Online' THEN 1 ELSE 0 END),3) FROM fact"),
        ("Products (product_code)", "SELECT count(DISTINCT product_code) FROM fact"),
        ("Customers", "SELECT count(DISTINCT customer_id) FROM fact"),
    ]:
        print(f"  {label:26s} {con.execute(q).fetchone()[0]}")
    con.close()
    print(f"\nDone in {time.time() - start:.0f}s. Open the CSV files in {out} with Power BI.")


if __name__ == "__main__":
    main()
