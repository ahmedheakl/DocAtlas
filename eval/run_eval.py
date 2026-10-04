#!/usr/bin/env python
"""End-to-end evaluation on DocAtlas-Bench.

Scores a folder of Markdown predictions (one ``<page id>.md`` per benchmark page)
against the benchmark ground truth and writes:

  <out>/<name>_quick_match_metric_result.json   aggregate scores (OmniDocBench layout)
  <out>/<name>_quick_match_*_result.json        per-element matches with their scores
  <out>/<name>_quick_match_summary.json         DocAtlas summary (overall / per language / ...)

Usage:
  python run_eval.py --gt data/DocAtlas-Bench.json --pred predictions/my_model
  python run_eval.py --gt data/DocAtlas-Bench.json --pred predictions/my_model --workers 16   # faster
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "omnidocbench"))

from registry.registry import DATASET_REGISTRY, EVAL_TASK_REGISTRY, METRIC_REGISTRY  # noqa: E402
import dataset  # noqa: E402,F401  (registers the end-to-end dataset)
import metrics  # noqa: E402,F401  (registers Edit_dist / TEDS)
import task  # noqa: E402,F401  (registers end2end_eval)
from metrics.show_result import get_full_labels_results, get_page_split, show_result  # noqa: E402
from utils.result_dir import result_path, set_result_dir  # noqa: E402

METRICS = {
    "text_block": {"metric": ["Edit_dist"]},
    "display_formula": {"metric": ["Edit_dist"]},
    "table": {"metric": ["TEDS", "Edit_dist"]},
    "reading_order": {"metric": ["Edit_dist"]},
}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gt", required=True, help="ground-truth JSON (DocAtlas-Bench.json)")
    ap.add_argument("--pred", required=True, help="folder with one <page id>.md per page")
    ap.add_argument("--out", default="results", help="output folder (default: results)")
    ap.add_argument("--name", default=None, help="run name (default: name of the prediction folder)")
    ap.add_argument("--match", default="quick_match", choices=["quick_match", "simple_match"],
                    help="GT/prediction matching strategy (default: quick_match)")
    ap.add_argument("--filter", action="append", default=[], metavar="KEY=VALUE",
                    help="only evaluate pages whose page attribute KEY equals VALUE, "
                         "e.g. --filter language=arabic (repeatable)")
    ap.add_argument("--workers", type=int, default=1,
                    help="score the pages in this many parallel processes (default: 1)")
    return ap.parse_args()


def _number(x):
    return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))


def _mean(values):
    values = [v for v in values if _number(v)]
    return sum(values) / len(values) if values else None


def _overall(text_edit, table_teds):
    """Mean of text accuracy and table TEDS, both on a 0-100 scale."""
    if text_edit is None or table_teds is None:
        return None
    return ((1.0 - text_edit) * 100.0 + table_teds) / 2.0


def _page_breakdown(result, prefix):
    """Page-level scores for one page attribute (e.g. 'data_source: ') as computed by the harness."""
    text = result["text_block"]["page"].get("Edit_dist", {})
    teds = result["table"]["page"].get("TEDS", {})
    order = result["reading_order"]["page"].get("Edit_dist", {})
    out = {}
    for key in sorted(set(text) | set(teds) | set(order)):
        if not key.startswith(prefix):
            continue
        t = text.get(key)
        tb = teds.get(key)
        out[key[len(prefix):]] = {
            "text_edit": t if _number(t) else None,
            "table_teds": tb * 100.0 if _number(tb) else None,
            "reading_order_edit": order.get(key) if _number(order.get(key)) else None,
        }
    return out


def build_summary(result, table_samples, pages, pages_with_pred, name, args):
    page_language = {os.path.basename(p["page_info"]["image_path"]): p["page_info"]["page_attribute"].get("language")
                     for p in pages}

    # Text: element-level mean per language (the harness' `group` split on the text_language attribute).
    per_language = defaultdict(dict)
    text_group = result["text_block"]["group"].get("Edit_dist", {})
    text_count = result["text_block"]["group"].get("sample_count", {})
    for key, value in text_group.items():
        if key.startswith("text_language: text_") and _number(value):
            lang = key[len("text_language: text_"):]
            per_language[lang]["text_edit"] = value
            per_language[lang]["text_elements"] = text_count.get(key)

    # Tables: element-level mean TEDS per page language.
    teds_by_lang = defaultdict(list)
    for sample in table_samples:
        score = (sample.get("metric") or {}).get("TEDS")
        lang = page_language.get(sample.get("img_id"))
        if lang is not None and _number(score):
            teds_by_lang[lang].append(score)
    for lang, scores in teds_by_lang.items():
        per_language[lang]["table_teds"] = 100.0 * sum(scores) / len(scores)
        per_language[lang]["tables"] = len(scores)

    for lang, row in per_language.items():
        row.setdefault("text_edit", None)
        row.setdefault("table_teds", None)
        row["overall"] = _overall(row["text_edit"], row["table_teds"])

    macro_text = _mean(r["text_edit"] for r in per_language.values())
    macro_teds = _mean(r["table_teds"] for r in per_language.values())

    text_all = result["text_block"]["all"].get("Edit_dist", {})
    table_all = result["table"]["all"]
    order_all = result["reading_order"]["all"].get("Edit_dist", {})
    page_text = text_all.get("ALL_page_avg") if _number(text_all.get("ALL_page_avg")) else None
    page_teds = table_all["TEDS"]["all"] * 100.0 if _number(table_all.get("TEDS", {}).get("all")) else None
    teds_struct = table_all.get("TEDS_structure_only", {}).get("all")
    reading_order = order_all.get("ALL_page_avg") if _number(order_all.get("ALL_page_avg")) else None

    return {
        "name": name,
        "ground_truth": os.path.abspath(args.gt),
        "predictions": os.path.abspath(args.pred),
        "match_method": args.match,
        "filter": dict(f.split("=", 1) for f in args.filter),
        "pages": len(pages),
        "pages_with_prediction": pages_with_pred,
        "language_macro": {
            "text_edit": macro_text,
            "table_teds": macro_teds,
            "reading_order_edit": reading_order,
            "overall": _overall(macro_text, macro_teds),
            "languages_with_text": sum(1 for r in per_language.values() if r["text_edit"] is not None),
            "languages_with_tables": sum(1 for r in per_language.values() if r["table_teds"] is not None),
        },
        "page_average": {
            "text_edit": page_text,
            "table_teds": page_teds,
            "table_teds_structure_only": teds_struct * 100.0 if _number(teds_struct) else None,
            "reading_order_edit": reading_order,
            "overall": _overall(page_text, page_teds),
        },
        "per_language": {k: per_language[k] for k in sorted(per_language)},
        "per_data_source": _page_breakdown(result, "data_source: "),
        "per_layout": _page_breakdown(result, "layout: "),
    }


def _page_of(sample):
    """Image name of the page a result sample belongs to (same rule as the harness)."""
    img_id = sample["img_id"]
    return img_id if img_id.endswith((".jpg", ".png")) else "_".join(img_id.split("_")[:-1])


def score_in_parallel(args, pages, has_prediction, name, save_name):
    """Score the pages in ``args.workers`` processes and merge the results.

    Every page is matched and scored on its own, so page shards can be scored by separate
    run_eval.py processes; the aggregate scores are then computed here from the merged per-element
    results with the same harness code as in a single-process run, and written to the same files.
    Returns the scored table samples.
    """
    scored_pages = [p for p in pages if has_prediction(os.path.basename(p["page_info"]["image_path"]))]
    workers = min(args.workers, len(scored_pages))
    os.makedirs(args.out, exist_ok=True)
    merged = {element: [] for element in METRICS}
    per_table = {}
    with tempfile.TemporaryDirectory(dir=args.out, prefix=".shards_") as tmp:
        shards = []
        for i in range(workers):
            gt_path = os.path.join(tmp, f"gt_{i:03d}.json")
            with open(gt_path, "w", encoding="utf-8") as f:
                json.dump(scored_pages[i::workers], f, ensure_ascii=False)
            log_path = os.path.join(tmp, f"shard_{i:03d}.log")
            with open(log_path, "w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), "--gt", gt_path, "--pred", args.pred,
                     "--out", os.path.join(tmp, f"{i:03d}"), "--name", name, "--match", args.match],
                    stdout=log, stderr=subprocess.STDOUT)
            shards.append((process, log_path))

        print(f"scoring {len(scored_pages)} pages in {workers} processes ...", flush=True)
        while True:
            running = sum(process.poll() is None for process, _ in shards)
            print(f"\r  {workers - running}/{workers} processes finished", end="", flush=True)
            if not running:
                break
            time.sleep(2)
        print()
        failed = [log_path for process, log_path in shards if process.returncode != 0]
        if failed:
            with open(failed[0], encoding="utf-8", errors="replace") as f:
                tail = "".join(f.readlines()[-30:])
            sys.exit(f"{len(failed)} of {workers} scoring processes failed. End of the first log:\n{tail}")

        for i in range(workers):
            for element in METRICS:
                with open(os.path.join(tmp, f"{i:03d}", f"{save_name}_{element}_result.json"), encoding="utf-8") as f:
                    merged[element].extend(json.load(f))
            with open(os.path.join(tmp, f"{i:03d}", f"{save_name}_table_per_table_TEDS.json"), encoding="utf-8") as f:
                per_table.update(json.load(f))

    # Same sample order as a single-process run: pages in ground-truth order, and the display formulas
    # that were scored as text (their img_id carries an index suffix) after the text blocks.
    position = {os.path.basename(p["page_info"]["image_path"]): i for i, p in enumerate(pages)}
    for samples in merged.values():
        samples.sort(key=lambda s: (_page_of(s) != s["img_id"], position[_page_of(s)]))

    page_info = {os.path.basename(p["page_info"]["image_path"]): p["page_info"]["page_attribute"] for p in pages}
    result_all = {}
    for element, config in METRICS.items():
        # the container the harness aggregates over in a single-process run
        samples = DATASET_REGISTRY.get("recogition_end2end_base_dataset")(merged[element])
        result = {}
        for metric in config["metric"]:
            if metric == "TEDS":  # computed per table by the worker processes; only averaged here
                scores = {key: [s["metric"][key] for s in merged[element]] for key in ("TEDS", "TEDS_structure_only")}
                result.update({key: {"all": sum(v) / len(v)} if v else {} for key, v in scores.items()})
                with open(result_path(f"{save_name}_{element}_per_table_TEDS.json"), "w", encoding="utf-8") as f:
                    json.dump(per_table, f, indent=4, ensure_ascii=False)
            else:
                samples, metric_result = METRIC_REGISTRY.get(metric)(samples).evaluate([], f"{save_name}_{element}")
                result.update(metric_result)
        if result:
            print(f"【{element}】")
            show_result(result)
        result_all[element] = {
            "all": result,
            "group": get_full_labels_results(samples),
            "page": get_page_split(samples, page_info),
        }
        with open(result_path(f"{save_name}_{element}_result.json"), "w", encoding="utf-8") as f:
            json.dump(merged[element], f, indent=4, ensure_ascii=False)
    with open(result_path(f"{save_name}_metric_result.json"), "w", encoding="utf-8") as f:
        json.dump(result_all, f, indent=4, ensure_ascii=False)
    return merged["table"]


def fmt(value, digits):
    return "n/a" if value is None else f"{value:.{digits}f}"


def print_summary(summary):
    print("\n" + "=" * 78)
    print(f"DocAtlas-Bench summary: {summary['name']}  "
          f"({summary['pages_with_prediction']}/{summary['pages']} pages with a prediction)")
    print("=" * 78)
    header = f"{'aggregation':<26}{'Text Edit↓':>12}{'Table TEDS↑':>13}{'Read Order↓':>13}{'Overall↑':>11}"
    print(header)
    print("-" * len(header))
    for label, key in (("macro over languages", "language_macro"), ("average over pages", "page_average")):
        row = summary[key]
        print(f"{label:<26}{fmt(row['text_edit'], 3):>12}{fmt(row['table_teds'], 2):>13}"
              f"{fmt(row['reading_order_edit'], 3):>13}{fmt(row['overall'], 2):>11}")
    macro = summary["language_macro"]
    print(f"\nlanguages: {macro['languages_with_text']} with text, {macro['languages_with_tables']} with tables. "
          "Overall = mean(100 x (1 - Text Edit), Table TEDS).")


def main():
    args = parse_args()
    if not os.path.isfile(args.gt):
        sys.exit(f"ground-truth file not found: {args.gt}")
    if not os.path.isdir(args.pred):
        sys.exit(f"prediction folder not found: {args.pred}")

    name = args.name or os.path.basename(os.path.normpath(args.pred))
    save_name = f"{name}_{args.match}"
    set_result_dir(args.out)

    page_filter = {}
    for item in args.filter:
        if "=" not in item:
            sys.exit(f"--filter expects KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        page_filter[key] = value

    with open(args.gt, encoding="utf-8") as f:
        pages = json.load(f)
    if page_filter:
        pages = [p for p in pages
                 if all(p["page_info"]["page_attribute"].get(k) == v for k, v in page_filter.items())]
        if not pages:
            sys.exit(f"no page matches the filter {page_filter}")

    # The harness looks a prediction up under these names, in this order.
    def has_prediction(image_name):
        stem = image_name[:-4]
        candidates = (stem + ".md", stem.replace(".pdf", "") + ".mmd", stem.replace(".pdf", "") + ".md", image_name + ".md")
        return any(os.path.exists(os.path.join(args.pred, c)) for c in candidates)

    pages_with_pred = sum(has_prediction(os.path.basename(p["page_info"]["image_path"])) for p in pages)
    if pages_with_pred == 0:
        sys.exit(f"no prediction in {args.pred} matches a benchmark page id "
                 f"(expected files such as {os.path.basename(pages[0]['page_info']['image_path'])[:-4]}.md)")
    if pages_with_pred < len(pages):
        print(f"WARNING: {len(pages) - pages_with_pred} of {len(pages)} pages have no prediction; "
              "they are skipped, not scored as errors.", file=sys.stderr)

    if args.workers > 1 and pages_with_pred > 1:
        table_samples = score_in_parallel(args, pages, has_prediction, name, save_name)
    else:
        cfg = {
            "metrics": METRICS,
            "dataset": {
                "dataset_name": "end2end_dataset",
                "ground_truth": {"data_path": args.gt},
                "prediction": {"data_path": args.pred},
                "match_method": args.match,
            },
        }
        if page_filter:
            cfg["dataset"]["filter"] = page_filter

        val_dataset = DATASET_REGISTRY.get("end2end_dataset")(cfg)
        EVAL_TASK_REGISTRY.get("end2end_eval")(val_dataset, METRICS, args.gt, save_name)
        table_samples = val_dataset.samples["table"].samples

    with open(result_path(f"{save_name}_metric_result.json"), encoding="utf-8") as f:
        result = json.load(f)
    summary = build_summary(result, table_samples, pages, pages_with_pred, name, args)
    summary_path = result_path(f"{save_name}_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print_summary(summary)
    print(f"\nsummary written to {summary_path}")


if __name__ == "__main__":
    main()
