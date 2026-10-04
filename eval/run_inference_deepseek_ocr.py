#!/usr/bin/env python
"""DeepSeek-OCR page-to-Markdown inference through a vLLM OpenAI-compatible server.

Follows the benchmark script of the DeepSeek-OCR repository
(DeepSeek-OCR-vllm/run_dpsk_ocr_eval_batch.py):

  * prompt            "<image>\\n<|grounding|>Convert the document to markdown."
  * resolution mode   Gundam (base 1024, crops 640), the default of vLLM's DeepSeek-OCR processor
  * decoding          greedy, no-repeat n-gram logits processor (n-gram 40, window 90,
                      <td> / </td> whitelisted), special tokens kept
  * post-processing   drop every <|ref|>..<|/ref|><|det|>..<|/det|> grounding tag, clean formulas,
                      collapse blank lines, drop <center> tags

Start the server with `./serve_vllm.sh deepseek-ocr 8000`, then:

  python run_inference_deepseek_ocr.py --images data/images --out predictions/deepseek-ocr \\
      --base-url http://localhost:8000/v1

Writes one ``<page id>.md`` per image, which is the layout run_eval.py expects. With --raw, the
model output before post-processing (with grounding tags) is kept as well. Re-running skips pages
that are already done.
"""
import argparse
import base64
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from tqdm import tqdm

PROMPT = "<image>\n<|grounding|>Convert the document to markdown."
EOS = "<｜end▁of▁sentence｜>"
TD_TOKEN_IDS = [128821, 128822]  # <td>, </td>: exempt from the no-repeat n-gram processor
IMAGE_EXTS = (".jpg", ".jpeg", ".png")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


# --- post-processing, as in run_dpsk_ocr_eval_batch.py --------------------------------------------
def clean_formula(text):
    formula_pattern = r'\\\[(.*?)\\\]'

    def process_formula(match):
        formula = match.group(1)
        formula = re.sub(r'\\quad\s*\([^)]*\)', '', formula)
        formula = formula.strip()
        return r'\[' + formula + r'\]'

    return re.sub(formula_pattern, process_formula, text)


def postprocess(content):
    content = content.replace(EOS, "")
    content = clean_formula(content)
    grounding_tags = re.findall(r'(<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>)', content, re.DOTALL)
    for tag in grounding_tags:
        content = (content.replace(tag, '').replace('\n\n\n\n', '\n\n').replace('\n\n\n', '\n\n')
                   .replace('<center>', '').replace('</center>', ''))
    return content
# --------------------------------------------------------------------------------------------------


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--raw", default=None, help="optional folder for the raw model outputs")
    ap.add_argument("--model", default="deepseek-ocr", help="model name as known to the server")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--api-key", default="EMPTY")
    ap.add_argument("--prompt", default=PROMPT)
    ap.add_argument("--ngram-size", type=int, default=40)
    ap.add_argument("--window-size", type=int, default=90)
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="default: no limit, i.e. generate until the end-of-sequence token or until "
                         "the model's 8192-token context is full")
    ap.add_argument("--workers", type=int, default=32, help="concurrent requests (default: 32)")
    return ap.parse_args()


def main():
    args = parse_args()
    client = OpenAI(api_key=args.api_key, base_url=args.base_url, timeout=1800)
    os.makedirs(args.out, exist_ok=True)
    if args.raw:
        os.makedirs(args.raw, exist_ok=True)

    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run")

    def run(name):
        stem, ext = os.path.splitext(name)
        with open(os.path.join(args.images, name), "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        limits = {"max_tokens": args.max_tokens} if args.max_tokens else {}
        try:
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{MIME[ext.lower()]};base64,{encoded}"}},
                    {"type": "text", "text": args.prompt},
                ]}],
                temperature=0.0,
                extra_body={
                    "skip_special_tokens": False,
                    "vllm_xargs": {"ngram_size": args.ngram_size, "window_size": args.window_size,
                                   "whitelist_token_ids": TD_TOKEN_IDS},
                },
                **limits,
            )
            raw = response.choices[0].message.content or ""
        except Exception as error:  # leave no file behind so the page is retried on the next run
            return name, str(error)
        if args.raw:
            with open(os.path.join(args.raw, stem + ".txt"), "w", encoding="utf-8") as f:
                f.write(raw)
        with open(os.path.join(args.out, stem + ".md"), "w", encoding="utf-8") as f:
            f.write(postprocess(raw))
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
