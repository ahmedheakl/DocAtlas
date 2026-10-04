#!/usr/bin/env python
"""PaddleOCR-VL page-to-Markdown inference; the recognition model is served by vLLM.

Runs the PaddleOCR pipeline, version "v1": PP-DocLayoutV2 layout detection and reading order (run
locally by PaddlePaddle, on the CPU if no GPU build is installed), recognition of every block with
PaddleOCR-VL-0.9B (the vLLM server), and PaddleOCR's own conversion of the page to Markdown:

    PaddleOCRVL(pipeline_version="v1", vl_rec_backend="vllm-server", vl_rec_server_url=...)

Setup:

  pip install paddlepaddle "paddleocr[doc-parser]"
  ./serve_vllm.sh paddleocr-vl 8000        # serves the model as "PaddleOCR-VL-0.9B"

  python run_inference_paddleocr_vl.py --images data/images --out predictions/paddleocr-vl \\
      --base-url http://localhost:8000/v1

Writes one ``<page id>.md`` per image, which is the layout run_eval.py expects. With --raw, the
pipeline's JSON output is kept as well. Re-running skips pages that are already done. The layout
stage is the slow part on a CPU: start several clients side by side with --shard 0/8 ... 7/8.
"""
import argparse
import os
import sys

# keep each client to a few CPU threads, so that several of them can run side by side
for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "4")

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--raw", default=None, help="optional folder for the pipeline's JSON outputs")
    ap.add_argument("--model", default="PaddleOCR-VL-0.9B", help="model name as known to the server")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--workers", type=int, default=16, help="concurrent recognition requests (default: 16)")
    ap.add_argument("--shard", default=None, metavar="I/N",
                    help="only run every N-th page starting at I (for several clients in parallel)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.raw:
        os.makedirs(args.raw, exist_ok=True)
    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    if args.shard:
        index, count = (int(x) for x in args.shard.split("/"))
        images = images[index::count]
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run", flush=True)
    if not todo:
        return

    from paddleocr import PaddleOCRVL

    pipeline = PaddleOCRVL(pipeline_version="v1", vl_rec_backend="vllm-server", vl_rec_server_url=args.base_url,
                           vl_rec_api_model_name=args.model, vl_rec_max_concurrency=args.workers)
    failures = []
    for index, name in enumerate(todo, 1):
        stem = os.path.splitext(name)[0]
        try:
            result = list(pipeline.predict(os.path.join(args.images, name)))[0]
            markdown = result.markdown["markdown_texts"]
            if args.raw:
                result.save_to_json(save_path=args.raw)
            tmp = os.path.join(args.out, stem + ".md.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(markdown)
            os.replace(tmp, os.path.join(args.out, stem + ".md"))
        except Exception as error:  # leave no prediction behind so the page is retried on the next run
            failures.append((name, f"{type(error).__name__}: {error}"))
        if index % 25 == 0 or index == len(todo):
            print(f"  {index}/{len(todo)} pages", flush=True)

    if failures:
        print(f"{len(failures)} pages failed and have no prediction; re-run to retry them. First error:")
        print(f"  {failures[0][0]}: {failures[0][1]}")
        sys.exit(1)
    print(f"predictions written to {args.out}")


if __name__ == "__main__":
    main()
