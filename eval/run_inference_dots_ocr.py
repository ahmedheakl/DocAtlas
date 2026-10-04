#!/usr/bin/env python
"""dots.ocr page-to-Markdown inference through a vLLM OpenAI-compatible server.

Drives the parser of the dots.ocr repository (dots_ocr.DotsOCRParser) the way its OmniDocBench
recipe does (tools/eval_omnidocbench.md):

  * prompt mode       prompt_layout_all_en (layout JSON with bbox / category / text per element)
  * pre-processing    fitz_preprocess (page re-rendered at 200 dpi), then the model's smart resize
  * decoding          temperature 0.1, top_p 1.0, max_completion_tokens 16384 (parser defaults)
  * output            the parser's "_nohf" Markdown (page headers / footers dropped), or the
                      cleaned raw text when the model's JSON cannot be parsed

Setup:

  git clone https://github.com/rednote-hilab/dots.ocr
  pip install PyMuPDF
  ./serve_vllm.sh dots-ocr 8000

  python run_inference_dots_ocr.py --images data/images --out predictions/dots-ocr \\
      --dots-ocr-repo dots.ocr --base-url http://localhost:8000/v1

Writes one ``<page id>.md`` per image, which is the layout run_eval.py expects, and keeps the
parser's own outputs (layout JSON, Markdown with headers / footers) in --raw. Re-running skips
pages that are already done.
"""
import argparse
import contextlib
import io
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from tqdm import tqdm

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--raw", default=None,
                    help="folder for the parser's own outputs (default: <out>_raw)")
    ap.add_argument("--dots-ocr-repo", default=os.environ.get("DOTS_OCR_REPO"),
                    help="path to a clone of https://github.com/rednote-hilab/dots.ocr "
                         "(default: $DOTS_OCR_REPO; not needed if dots_ocr is installed)")
    ap.add_argument("--model", default="dots-ocr", help="model name as known to the server")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--top-p", type=float, default=1.0)
    ap.add_argument("--max-completion-tokens", type=int, default=16384)
    ap.add_argument("--no-fitz-preprocess", action="store_true")
    ap.add_argument("--workers", type=int, default=32, help="concurrent requests (default: 32)")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.dots_ocr_repo:
        sys.path.insert(0, os.path.abspath(args.dots_ocr_repo))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from dots_ocr import DotsOCRParser
    except ImportError as error:
        sys.exit(f"cannot import dots_ocr ({error}): clone https://github.com/rednote-hilab/dots.ocr "
                 "and pass its path with --dots-ocr-repo")

    raw = args.raw or os.path.normpath(args.out) + "_raw"
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    url = urlparse(args.base_url)
    with contextlib.redirect_stdout(io.StringIO()):
        parser = DotsOCRParser(protocol=url.scheme, ip=url.hostname, port=url.port, model_name=args.model,
                               temperature=args.temperature, top_p=args.top_p,
                               max_completion_tokens=args.max_completion_tokens,
                               num_thread=args.workers, output_dir=raw)

    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run")

    def run(name):
        stem = os.path.splitext(name)[0]
        try:
            # the parser prints one line per page; keep the log readable
            with contextlib.redirect_stdout(io.StringIO()):
                result = parser.parse_file(os.path.join(args.images, name), output_dir=raw,
                                           prompt_mode="prompt_layout_all_en",
                                           fitz_preprocess=not args.no_fitz_preprocess)[0]
            source = result.get("md_content_nohf_path") or result["md_content_path"]
            tmp = os.path.join(args.out, stem + ".md.tmp")
            shutil.copyfile(source, tmp)
            os.replace(tmp, os.path.join(args.out, stem + ".md"))
            # the annotated page image is only a visualisation; drop it to save space
            layout_image = result.get("layout_image_path")
            if layout_image and os.path.exists(layout_image):
                os.remove(layout_image)
        except Exception as error:  # leave no prediction behind so the page is retried on the next run
            return name, f"{type(error).__name__}: {error}"
        return name, None

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for name, error in tqdm(pool.map(run, todo), total=len(todo), desc="inference", unit="page"):
            if error:
                failures.append((name, error))

    if failures:
        print(f"{len(failures)} pages failed and have no prediction; re-run to retry them. First error:")
        print(f"  {failures[0][0]}: {failures[0][1]}")
        sys.exit(1)
    print(f"predictions written to {args.out}")


if __name__ == "__main__":
    main()
