#!/usr/bin/env python
"""Compare DocAtlas-Bench runs side by side.

Reads the ``*_summary.json`` files written by run_eval.py and prints one row per run.

Usage:
  python summarize.py results/                       # every run in a folder
  python summarize.py results/a_quick_match_summary.json results/b_quick_match_summary.json
  python summarize.py results/ --by language         # per-language breakdown
  python summarize.py results/ --csv leaderboard.csv
"""
import argparse
import csv
import glob
import json
import os
import sys

BREAKDOWNS = {"language": "per_language", "data_source": "per_data_source", "layout": "per_layout"}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="summary JSON files, or folders containing them")
    ap.add_argument("--aggregation", default="language_macro", choices=["language_macro", "page_average"],
                    help="headline aggregation (default: language_macro)")
    ap.add_argument("--by", choices=sorted(BREAKDOWNS), help="print a breakdown instead of the headline table")
    ap.add_argument("--metric", default="overall", choices=["overall", "text_edit", "table_teds"],
                    help="metric shown in a --by breakdown (default: overall; for data_source/layout, "
                         "overall is derived from text_edit and table_teds)")
    ap.add_argument("--csv", help="also write the table to this CSV file")
    return ap.parse_args()


def load(paths):
    files = []
    for path in paths:
        if os.path.isdir(path):
            files.extend(sorted(glob.glob(os.path.join(path, "*_summary.json"))))
        else:
            files.append(path)
    if not files:
        sys.exit("no *_summary.json found")
    runs = []
    for file in files:
        with open(file, encoding="utf-8") as f:
            runs.append(json.load(f))
    return runs


def fmt(value, digits):
    return "n/a" if value is None else f"{value:.{digits}f}"


def overall(row):
    if row.get("overall") is not None:
        return row["overall"]
    if row.get("text_edit") is None or row.get("table_teds") is None:
        return None
    return ((1.0 - row["text_edit"]) * 100.0 + row["table_teds"]) / 2.0


def print_table(header, rows):
    widths = [max(len(str(c)) for c in col) for col in zip(header, *rows)]
    line = "  ".join(f"{h:<{w}}" if i == 0 else f"{h:>{w}}" for i, (h, w) in enumerate(zip(header, widths)))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(f"{c:<{w}}" if i == 0 else f"{c:>{w}}" for i, (c, w) in enumerate(zip(row, widths))))


def main():
    args = parse_args()
    runs = load(args.paths)

    if args.by:
        key = BREAKDOWNS[args.by]
        digits = 3 if args.metric == "text_edit" else 2
        groups = sorted({g for run in runs for g in run.get(key, {})})
        header = [args.by] + [run["name"] for run in runs]
        rows = []
        for group in groups:
            row = [group]
            for run in runs:
                cell = run.get(key, {}).get(group)
                value = None if cell is None else (overall(cell) if args.metric == "overall" else cell.get(args.metric))
                row.append(fmt(value, digits))
            rows.append(row)
        print(f"{args.metric} by {args.by}")
    else:
        header = ["run", "pages", "Text Edit↓", "Table TEDS↑", "Read Order↓", "Overall↑"]
        rows = []
        ranked = sorted(runs, key=lambda r: -(r[args.aggregation]["overall"] or float("-inf")))
        for run in ranked:
            agg = run[args.aggregation]
            rows.append([run["name"], f"{run['pages_with_prediction']}/{run['pages']}",
                         fmt(agg["text_edit"], 3), fmt(agg["table_teds"], 2),
                         fmt(agg["reading_order_edit"], 3), fmt(agg["overall"], 2)])
        print(f"aggregation: {args.aggregation}")

    print_table(header, rows)
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"\nwritten to {args.csv}")


if __name__ == "__main__":
    main()
