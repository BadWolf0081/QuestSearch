import difflib
import re
import json

def fuzzy_find_pokemon(query, poke_lookup):
    names = [p["name"] for p in poke_lookup]
    match = difflib.get_close_matches(query, names, n=1, cutoff=0.6)
    if match:
        for p in poke_lookup:
            if p["name"] == match[0]:
                return p
    return None

def fuzzy_find_variant(pokemon, query, variant_type, poke_lookup):
    # variant_type: "form" or "costume" or "filecode"
    variants = []
    for p in poke_lookup:
        if p["name"] == pokemon["name"]:
            if variant_type == "form" and p["form"]:
                variants.append(p["form"])
            elif variant_type == "costume" and p["costume"]:
                variants.append(p["costume"])
            elif variant_type == "filecode" and p["filecode"]:
                variants.append(p["filecode"])
    match = difflib.get_close_matches(query, variants, n=1, cutoff=0.6)
    if match:
        for p in poke_lookup:
            if p["name"] == pokemon["name"] and (p[variant_type] == match[0]):
                return p
    return None

def fuzzy_lookup_form_id(query, forms_data):
    # Find best match for form name, return (form_id, form_name)
    form_keys = [k for k in forms_data if k.startswith("form_")]
    form_names = [forms_data[k].lower() for k in form_keys]
    match = difflib.get_close_matches(query.lower(), form_names, n=1, cutoff=0.6)
    if match:
        for k in form_keys:
            if forms_data[k].lower() == match[0]:
                return int(k.split("_")[1]), forms_data[k]
    return None, None

def fuzzy_lookup_costume_id(query, forms_data):
    # Find best match for costume name, return (costume_id, costume_name)
    costume_keys = [k for k in forms_data if k.startswith("costume_")]
    costume_names = [forms_data[k].lower() for k in costume_keys]
    match = difflib.get_close_matches(query.lower(), costume_names, n=1, cutoff=0.6)
    if match:
        for k in costume_keys:
            if forms_data[k].lower() == match[0]:
                return int(k.split("_")[1]), forms_data[k]
    return None, None

def get_api_filecode(pokedex_id, poke_lookup, form_id=None, costume_id=None, shiny=False, mega_id=None):
    print(f"[API FILECODE] Looking up: pokedex_id={pokedex_id}, form_id={form_id}, costume_id={costume_id}, shiny={shiny}, mega_id={mega_id}")
    candidates = []
    for entry in poke_lookup:
        if f"({pokedex_id})" not in entry["pokedex"]:
            continue
        if form_id and f"({form_id})" not in entry["form"]:
            continue
        if costume_id and f"({costume_id})" not in entry["costume"]:
            continue
        if mega_id is not None and str(mega_id) != entry.get("mega", "0"):
            continue
        filecode = entry["filecode"]
        if not filecode:
            continue
        candidates.append(filecode)
    # Prefer shiny if available
    if shiny:
        shiny_candidates = [c for c in candidates if c.endswith("_s")]
        if shiny_candidates:
            print(f"[API FILECODE] Returning shiny filecode: {shiny_candidates[0]}")
            return shiny_candidates[0]
    if candidates:
        print(f"[API FILECODE] Returning filecode: {candidates[0]}")
        return candidates[0]
    print(f"[API FILECODE] No candidates found for pokedex_id={pokedex_id}, form_id={form_id}, costume_id={costume_id}, shiny={shiny}, mega_id={mega_id}")
    return None

def lookup_form_id_for_mon(mon_id, form_query, poke_lookup):
    """Find the correct form_id for a given Pokémon ID and form name (case-insensitive, fuzzy)."""
    candidates = [entry for entry in poke_lookup if f"({mon_id})" in entry["pokedex"]]
    form_map = {}
    for entry in candidates:
        form_field = entry["form"]
        if form_field:
            form_base = form_field.split(" (")[0].strip().lower()
            form_map[form_base] = entry
            if "_" in form_base:
                _, form_only = form_base.split("_", 1)
                form_map[form_only] = entry
    print(f"[LOOKUP DEBUG] Candidates for mon_id={mon_id}: {list(form_map.keys())}")
    form_query_clean = form_query.strip().lower() if form_query else ""
    if form_query_clean in form_map:
        entry = form_map[form_query_clean]
        m = re.search(r"\((\d+)\)", entry["form"])
        if m:
            return int(m.group(1)), entry["form"]
    match = difflib.get_close_matches(form_query_clean, form_map.keys(), n=1, cutoff=0.7)
    if match:
        entry = form_map[match[0]]
        m = re.search(r"\((\d+)\)", entry["form"])
        if m:
            return int(m.group(1)), entry["form"]
    return None

def lookup_costume_id_for_mon(mon_id, costume_query, poke_lookup):
    """Find the correct costume_id for a given Pokémon ID and costume name (case-insensitive, fuzzy)."""
    candidates = [entry for entry in poke_lookup if f"({mon_id})" in entry["pokedex"]]
    costume_names = [entry["costume"] for entry in candidates if entry["costume"]]
    match = difflib.get_close_matches(costume_query.lower(), [c.lower() for c in costume_names], n=1, cutoff=0.6)
    if match:
        for entry in candidates:
            if entry["costume"].lower() == match[0]:
                m = re.search(r"\((\d+)\)", entry["costume"])
                if m:
                    return int(m.group(1)), entry["costume"]
    return 0, None  # fallback to default costume