import re
import unicodedata

from util.forms import load_forms

# Words handled by dedicated !quest branches; never loosely matched to an item.
RESERVED_WORDS = ("mega", "showcase", "station", "power", "lure", "route", "giovan", "sierra",
                  "arlo", "cliff", "kecleon", "coin", "star", "dust")

def _ascii(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()

def normalize(text):
    return re.sub(r"[^a-z0-9]", "", _ascii(text))

def _tokens(text):
    return re.findall(r"[a-z0-9]+", _ascii(text))

async def get_item_index(bot):
    """Return [(item_id, name)] from the translation data plus the bundled item list."""
    forms = await load_forms(bot.config.get("forms_url"))
    index = []
    for key, name in forms.items():
        match = re.fullmatch(r"item_(\d+)", key)
        if match and int(match.group(1)) > 0 and isinstance(name, str):
            index.append((match.group(1), name))
    index.extend((item_id, item["name"]) for item_id, item in bot.items.items())
    return index

def find_item(query, index, loose=True):
    """Find (item_id, name) for a query: exact name first, then all query words within a name."""
    query_norm = normalize(query)
    if not query_norm:
        return None
    for item_id, name in index:
        if normalize(name) == query_norm:
            return item_id, name
    words = _tokens(query)
    if not loose or not words:
        return None
    if len(words) == 1 and (len(words[0]) < 4 or words[0].startswith(RESERVED_WORDS)):
        return None
    candidates = [(item_id, name) for item_id, name in index if set(words) <= set(_tokens(name))]
    if not candidates:
        return None
    return min(candidates, key=lambda c: (len(c[1]), int(c[0])))
