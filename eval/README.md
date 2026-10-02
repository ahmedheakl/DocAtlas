# DocAtlas-Bench evaluation

Minimal end-to-end evaluation for [DocAtlas-Bench](https://huggingface.co/datasets/ahmedheakl/DocAtlas-Bench):
your model converts each page image to Markdown, and the Markdown is scored against the ground truth for
text, tables and reading order.

## Setup

```bash
pip install -r requirements.txt        # or requirements-lock.txt for the exact versions we evaluated with
```

## 1. Get the benchmark

```bash
python prepare_benchmark.py --out data
```

This writes `data/DocAtlas-Bench.json` (ground truth) and `data/images/<page id>.jpg` (5,575 pages, ~3.2 GB).
Add `--skip-images` for the ground truth only, or `--languages ar he` to export a subset of images.

## 2. Run your model

Produce one Markdown file per page, named after the image: `predictions/<model>/<page id>.md`.
Write tables as HTML (`<table>…</table>`); Markdown pipe tables are converted automatically, LaTeX tables get no credit.

`run_inference.py` does this for any OpenAI-compatible endpoint (hosted APIs, or a local server such as vLLM):

```bash
python run_inference.py --images data/images --out predictions/my_model \
    --model my_model --base-url http://localhost:8000/v1 --api-key EMPTY
```

## 3. Score

```bash
python run_eval.py --gt data/DocAtlas-Bench.json --pred predictions/my_model --out results
python summarize.py results/                  # compare runs
python summarize.py results/ --by language    # or: --by data_source, --by layout
```

The full benchmark takes about 15 minutes on one CPU core.

## What is reported

| Metric | Meaning |
|---|---|
| Text Edit ↓ | normalized edit distance between ground-truth text blocks and the matched predicted text |
| Table TEDS ↑ | tree-edit-distance similarity between ground-truth and predicted HTML tables (0–100) |
| Read Order ↓ | edit distance between the ground-truth and predicted order of the matched text blocks |
| Overall ↑ | mean of text accuracy `100 × (1 − Text Edit)` and Table TEDS |

Two aggregations are printed:

- **macro over languages**: each score is computed per language, then averaged over languages.
- **average over pages**: scores averaged over all pages.

Notes:

- Scored ground-truth elements are `text_block` and `table`. `section_header` elements are in the annotations but are not scored.
- Pages without a prediction file are skipped (a warning is printed), so evaluate all pages when comparing models.
- Use `--filter KEY=VALUE` to score a subset, e.g. `--filter language=arabic` or `--filter data_source=newspaper`
  (keys and values are the page attributes in the ground-truth JSON).

## Output files

`run_eval.py` writes to `--out`:

- `<name>_quick_match_summary.json`: the numbers above, plus per-language, per-document-type and per-layout breakdowns.
- `<name>_quick_match_metric_result.json`: all aggregate scores.
- `<name>_quick_match_{text_block,table,reading_order}_result.json`: every matched ground-truth/prediction pair with its score.

## Credits

The matching and scoring code in `omnidocbench/` is adapted from
[OmniDocBench](https://github.com/opendatalab/OmniDocBench) (Apache-2.0); see `omnidocbench/NOTICE.md`.
