"""Output-directory helper (added for DocAtlas; upstream OmniDocBench always writes to ./result)."""
import os

_RESULT_DIR = "./result"


def set_result_dir(path):
    global _RESULT_DIR
    _RESULT_DIR = path


def result_path(name):
    os.makedirs(_RESULT_DIR, exist_ok=True)
    return os.path.join(_RESULT_DIR, name)
