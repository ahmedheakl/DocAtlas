#!/usr/bin/env python
"""MinerU2.5 page-to-Markdown inference; the model is served by vLLM.

Runs the MinerU command line client with its `vlm-http-client` backend, i.e. the two-step
extraction of MinerU2.5 (layout detection on the whole page, then recognition of every block)
followed by MinerU's own conversion to Markdown:

    mineru -p <images> -o <raw> -b vlm-http-client -u http://localhost:8000

Setup:

  pip install "mineru==2.7.6"              # the client
  pip install mineru-vl-utils              # in the vLLM environment: logits processor used by the server
  ./serve_vllm.sh mineru2.5 8000

  python run_inference_mineru.py --images data/images --out predictions/mineru2.5 \\
      --base-url http://localhost:8000/v1

Writes one ``<page id>.md`` per image, which is the layout run_eval.py expects; MinerU's own outputs
(layout JSON, page renders) are kept in --raw. Re-running only processes the pages that are not done.
"""
import argparse
import os
import shutil
import subprocess
import sys

IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--raw", default=None, help="folder for MinerU's own outputs (default: <out>_raw)")
    ap.add_argument("--base-url", default="http://localhost:8000/v1", help="server URL, with or without /v1")
    ap.add_argument("--mineru-bin", default="mineru", help="the MinerU command line client (default: mineru)")
    ap.add_argument("--clients", type=int, default=8, help="MinerU clients to run side by side (default: 8)")
    args = ap.parse_args()

    raw = args.raw or os.path.normpath(args.out) + "_raw"
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(raw, exist_ok=True)
    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run", flush=True)
    if not todo:
        return

    # MinerU takes a folder and works through it one file at a time: give it folders that only hold
    # the pages still to do, and run several clients side by side
    todo_dir = os.path.join(raw, "_todo")
    shutil.rmtree(todo_dir, ignore_errors=True)
    shards = min(args.clients, len(todo))
    for index, name in enumerate(todo):
        shard_dir = os.path.join(todo_dir, str(index % shards))
        os.makedirs(shard_dir, exist_ok=True)
        os.symlink(os.path.abspath(os.path.join(args.images, name)), os.path.join(shard_dir, name))

    url = args.base_url.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    # keep each client to a few CPU threads
    env = dict(os.environ)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env.setdefault(var, "4")
    try:
        procs = [subprocess.Popen([args.mineru_bin, "-p", os.path.join(todo_dir, str(i)), "-o", raw,
                                   "-b", "vlm-http-client", "-u", url], env=env) for i in range(shards)]
    except FileNotFoundError:
        sys.exit(f"cannot run {args.mineru_bin!r}: install the MinerU client (pip install mineru==2.7.6) "
                 "or pass its path with --mineru-bin")
    rc = max(p.wait() for p in procs)
    shutil.rmtree(todo_dir, ignore_errors=True)

    missing = []
    for name in todo:
        stem = os.path.splitext(name)[0]
        source = os.path.join(raw, stem, "vlm", stem + ".md")
        if os.path.exists(source):
            shutil.copyfile(source, os.path.join(args.out, stem + ".md.tmp"))
            os.replace(os.path.join(args.out, stem + ".md.tmp"), os.path.join(args.out, stem + ".md"))
        else:
            missing.append(name)
    if missing or rc != 0:
        print(f"mineru exited {rc}; {len(missing)} pages have no Markdown output; re-run to retry them")
        sys.exit(1)
    print(f"predictions written to {args.out}")


if __name__ == "__main__":
    main()
