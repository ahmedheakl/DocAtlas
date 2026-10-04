#!/usr/bin/env python
"""Chandra page-to-Markdown inference through a vLLM OpenAI-compatible server.

Drives the code of the Chandra repository the way its own command line does
(`chandra <input> <output> --method vllm`):

  * image loading     chandra.input.load_file (small pages are upscaled)
  * prompt            prompt type "ocr_layout" (HTML layout blocks with bounding boxes)
  * decoding          the repository's vLLM client: temperature 0, top_p 0.1, and its retries at a
                      higher temperature when the output ends in a repetition loop
  * output            chandra.output.parse_markdown with the command line defaults (page headers and
                      footers dropped, tables kept as HTML)

Setup (the original `datalab-to/chandra` checkpoint; later revisions of the repository target its
successor):

  git clone https://github.com/datalab-to/chandra && git -C chandra checkout a6928a2
  pip install beautifulsoup4 click filetype markdownify==1.1.0 openai pillow pydantic \\
      pydantic-settings pypdfium2 python-dotenv six
  ./serve_vllm.sh chandra 8000

  python run_inference_chandra.py --images data/images --out predictions/chandra \\
      --chandra-repo chandra --base-url http://localhost:8000/v1

Writes one ``<page id>.md`` per image, which is the layout run_eval.py expects. With --raw, the
model's HTML output is kept as well. Re-running skips pages that are already done.
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--raw", default=None, help="optional folder for the raw model outputs")
    ap.add_argument("--chandra-repo", default=os.environ.get("CHANDRA_REPO"),
                    help="path to a clone of https://github.com/datalab-to/chandra "
                         "(default: $CHANDRA_REPO; not needed if the package is installed)")
    ap.add_argument("--model", default="chandra", help="model name as known to the server")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--workers", type=int, default=32, help="concurrent requests (default: 32)")
    return ap.parse_args()


def main():
    args = parse_args()
    # chandra reads its settings from the environment when it is imported
    os.environ["VLLM_API_BASE"] = args.base_url
    os.environ["VLLM_MODEL_NAME"] = args.model
    if args.chandra_repo:
        sys.path.insert(0, os.path.abspath(args.chandra_repo))
    try:
        from chandra.input import load_file
        from chandra.model import InferenceManager
        from chandra.model.schema import BatchInputItem
    except ImportError as error:
        sys.exit(f"cannot import chandra ({error}): clone https://github.com/datalab-to/chandra "
                 "and pass its path with --chandra-repo")

    manager = InferenceManager(method="vllm")
    os.makedirs(args.out, exist_ok=True)
    if args.raw:
        os.makedirs(args.raw, exist_ok=True)

    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run")

    def run(name):
        stem = os.path.splitext(name)[0]
        try:
            image = load_file(os.path.join(args.images, name), {})[0]
            result = manager.generate([BatchInputItem(image=image, prompt_type="ocr_layout")],
                                      include_images=True, include_headers_footers=False)[0]
            if result.error:  # the request failed even after the client's own retries
                return name, "request failed (see the 'Error during VLLM generation' lines above)"
            if args.raw:
                with open(os.path.join(args.raw, stem + ".html"), "w", encoding="utf-8") as f:
                    f.write(result.raw)
            tmp = os.path.join(args.out, stem + ".md.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            os.replace(tmp, os.path.join(args.out, stem + ".md"))
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
