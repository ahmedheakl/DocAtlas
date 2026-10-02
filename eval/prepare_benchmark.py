#!/usr/bin/env python
"""Download DocAtlas-Bench from the Hugging Face Hub.

Writes:
  <out>/DocAtlas-Bench.json     ground truth used by run_eval.py
  <out>/images/<page id>.jpg    page images to run your model on (original JPEG bytes)

Usage:
  python prepare_benchmark.py --out data
  python prepare_benchmark.py --out data --skip-images      # ground truth only
"""
import argparse
import os

REPO_ID = "ahmedheakl/DocAtlas-Bench"
GT_FILE = "DocAtlas-Bench.json"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data", help="output folder (default: data)")
    ap.add_argument("--repo", default=REPO_ID, help=f"dataset repo (default: {REPO_ID})")
    ap.add_argument("--skip-images", action="store_true", help="only download the ground-truth JSON")
    ap.add_argument("--languages", nargs="*", default=None, metavar="CODE",
                    help="only export pages in these language codes, e.g. --languages ar he fa ur")
    return ap.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    from huggingface_hub import hf_hub_download

    gt_path = hf_hub_download(args.repo, GT_FILE, repo_type="dataset", local_dir=args.out)
    print(f"ground truth: {gt_path}")
    if args.skip_images:
        return

    from datasets import Image, load_dataset
    from tqdm import tqdm

    image_dir = os.path.join(args.out, "images")
    os.makedirs(image_dir, exist_ok=True)
    wanted = set(args.languages) if args.languages else None

    # decode=False keeps the original JPEG bytes instead of re-encoding them.
    pages = load_dataset(args.repo, split="test", streaming=True).select_columns(["id", "language", "image"])
    pages = pages.cast_column("image", Image(decode=False))

    written = 0
    for page in tqdm(pages, desc="exporting images", unit="page"):
        if wanted is not None and page["language"] not in wanted:
            continue
        path = os.path.join(image_dir, page["id"] + ".jpg")
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(page["image"]["bytes"])
        written += 1
    print(f"{written} page images in {image_dir}")


if __name__ == "__main__":
    main()
