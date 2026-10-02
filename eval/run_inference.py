#!/usr/bin/env python
"""Page-to-Markdown inference through any OpenAI-compatible endpoint.

Works with hosted APIs and with local servers such as vLLM
(``vllm serve <model> --port 8000``). Writes one ``<page id>.md`` per image,
which is the layout run_eval.py expects. Re-running skips pages already done.

Usage:
  export OPENAI_API_KEY=...
  python run_inference.py --images data/images --out predictions/gpt-4o --model gpt-4o

  # local vLLM server
  python run_inference.py --images data/images --out predictions/my_model \
      --model my_model --base-url http://localhost:8000/v1 --api-key EMPTY
"""
import argparse
import base64
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI
from tqdm import tqdm

# Prompt used for general-purpose VLMs (same as OmniDocBench).
PROMPT = r"""You are an AI assistant specialized in converting PDF images to Markdown format. Please follow these instructions for the conversion:

1. Text Processing:
- Accurately recognize all text content in the PDF image without guessing or inferring.
- Convert the recognized text into Markdown format.
- Maintain the original document structure, including headings, paragraphs, lists, etc.

2. Mathematical Formula Processing:
- Convert all mathematical formulas to LaTeX format.
- Enclose inline formulas with \( \). For example: This is an inline formula \( E = mc^2 \)
- Enclose block formulas with \[ \]. For example: \[ \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \]

3. Table Processing:
- Convert tables to HTML format.
- Wrap the entire table with <table> and </table>.

4. Figure Handling:
- Ignore figures content in the PDF image. Do not attempt to describe or convert images.

5. Output Format:
- Ensure the output Markdown document has a clear structure with appropriate line breaks between elements.
- For complex layouts, try to maintain the original document's structure and format as closely as possible.

Please strictly follow these guidelines to ensure accuracy and consistency in the conversion. Your task is to accurately convert the content of the PDF image into Markdown format without adding any extra explanations or comments."""

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="folder with the benchmark page images")
    ap.add_argument("--out", required=True, help="folder for the Markdown predictions")
    ap.add_argument("--model", required=True, help="model name as known to the endpoint")
    ap.add_argument("--base-url", default=None, help="endpoint URL (default: the OpenAI API)")
    ap.add_argument("--api-key", default=None, help="API key (default: $OPENAI_API_KEY)")
    ap.add_argument("--prompt-file", default=None, help="text file with a custom prompt")
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--workers", type=int, default=8, help="concurrent requests (default: 8)")
    return ap.parse_args()


def main():
    args = parse_args()
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("no API key: pass --api-key or set OPENAI_API_KEY (use any value, e.g. EMPTY, for a local server)")
    client = OpenAI(api_key=api_key, base_url=args.base_url)

    prompt = PROMPT
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()

    os.makedirs(args.out, exist_ok=True)
    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith(IMAGE_EXTS))
    if not images:
        sys.exit(f"no images found in {args.images}")
    todo = [f for f in images if not os.path.exists(os.path.join(args.out, os.path.splitext(f)[0] + ".md"))]
    print(f"{len(images)} images, {len(images) - len(todo)} already done, {len(todo)} to run")

    def run(name):
        with open(os.path.join(args.images, name), "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        mime = MIME[os.path.splitext(name)[1].lower()]
        try:
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                    {"type": "text", "text": prompt},
                ]}],
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            text = response.choices[0].message.content or ""
        except Exception as error:  # leave no file behind so the page is retried on the next run
            return name, str(error)
        with open(os.path.join(args.out, os.path.splitext(name)[0] + ".md"), "w", encoding="utf-8") as f:
            f.write(text)
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
