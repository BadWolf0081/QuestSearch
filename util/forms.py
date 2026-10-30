import asyncio
import json
import time

import requests

FORMS_CACHE_SECONDS = 3600
_forms_cache = {"data": None, "time": 0.0}

def _fetch_forms(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

async def load_forms(url):
    """Return translation data from the configured URL (cached), falling back to the local file."""
    if url:
        now = time.time()
        if _forms_cache["data"] is not None and now - _forms_cache["time"] < FORMS_CACHE_SECONDS:
            return _forms_cache["data"]
        try:
            data = await asyncio.to_thread(_fetch_forms, url)
            _forms_cache["data"] = data
            _forms_cache["time"] = now
            return data
        except Exception as err:
            print(f"[FORMS] Could not load forms_url, using fallback: {err}")
            if _forms_cache["data"] is not None:
                return _forms_cache["data"]
    with open("data/forms/formsen.json", encoding="utf-8") as f:
        return json.load(f)
