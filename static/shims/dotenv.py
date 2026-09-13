"""Browser-side stand-in for `python-dotenv`.

`data_loader.py` calls `load_dotenv(find_dotenv())` at import time. There is no
`.env` in a static deployment, so both calls are no-ops.
"""


def find_dotenv(*args, **kwargs):
    return ""


def load_dotenv(*args, **kwargs):
    return False


def dotenv_values(*args, **kwargs):
    return {}
