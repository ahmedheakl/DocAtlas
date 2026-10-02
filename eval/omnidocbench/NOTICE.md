# Third-party notice

The code in this folder is a trimmed copy of the end-to-end evaluation of
[OmniDocBench](https://github.com/opendatalab/OmniDocBench) (v1.5 code base),
which is distributed under the Apache License 2.0 (see `LICENSE` in this folder).
`metrics/table_metric.py` (TEDS) is Copyright 2020 IBM, Apache License 2.0.

Changes made for DocAtlas:

- Kept only what the end-to-end Markdown evaluation needs (text edit distance,
  table TEDS, reading-order edit distance). Removed the detection, single-module
  recognition and md2md datasets, the CDM, BLEU and METEOR metrics, the
  model-inference tools and the demo data.
- `metrics/cal_metric.py`, `task/end2end_run_eval.py`: results are written to a
  configurable folder (`utils/result_dir.py`, new file) instead of `./result`.
- `dataset/end2end_dataset.py`: `RecognitionEnd2EndTableDataset` no longer inherits
  from the removed `RecognitionTableDataset`; unused imports dropped.
- `utils/match_quick.py`, `utils/table_utils.py`: unused imports and plotting helpers dropped.

The matching and scoring logic is unchanged.
