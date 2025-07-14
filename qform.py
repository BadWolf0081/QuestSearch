import discord
import json
import re
import difflib
import logging
from discord.ext import commands

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)

async def setup(bot):
    async def qform(ctx, areaname="", pokemon_name="", form_query=""):
        """
        Usage: !qform <area> <pokemon name> [form]
        Example: !qform Greatermoncton meowth galarian
        """
        try:
            print(f"[QFORM DEBUG] area='{areaname}', pokemon_name='{pokemon_name}', form_query='{form_query}'")
            if not areaname or not pokemon_name:
                await ctx.send("Usage: !qform <area> <pokemon name> [form]")
                return

            area = bot.get_area(areaname)
            print(f"[QFORM DEBUG] Area lookup: {area}")
            if area[1] == bot.locale['unknown']:
                await ctx.send(f"Unknown area: {areaname}")
                return

            # --- Load formsen.json for form name/id mapping ---
            with open("data/forms/formsen.json", encoding="utf-8") as f:
                formsen = json.load(f)
            # --- Load index.json for icon existence check ---
            with open("data/forms/index.json", encoding="utf-8") as f:
                icon_index = json.load(f)

            # --- 1. Fuzzy form name lookup: find all matching form IDs ---
            def get_form_ids_by_name(form_query, formsen):
                form_map = {int(k.replace("form_", "")): v for k, v in formsen.items() if k.startswith("form_")}
                matches = [fid for fid, name in form_map.items() if name.lower() == form_query.lower()]
                if matches:
                    return matches
                close = difflib.get_close_matches(form_query.lower(), [v.lower() for v in form_map.values()], n=5, cutoff=0.7)
                if close:
                    return [fid for fid, name in form_map.items() if name.lower() in close]
                return []

            # --- 2. Fuzzy Pokémon name lookup using qs.py logic ---
            pokemon_entry = bot.fuzzy_find_pokemon(pokemon_name)
            if not pokemon_entry:
                await ctx.send(f"Could not find Pokémon: {pokemon_name}")
                return
            match = re.search(r"(\d+)", pokemon_entry["pokedex"])
            if match:
                pokedex_id = int(match.group(1))
            else:
                await ctx.send(f"Could not extract Pokédex number for {pokemon_name}")
                return

            # --- Robust per-mon form lookup ---
            form_id_for_mon = None
            form_name = None

            # Load the language-specific forms file (e.g., en.json)
            form_lang = bot.config['language']
            if not form_lang in ["en", "de", "fr", "es"]:
                form_lang = "en"
            with open(f"data/forms/{form_lang}.json", encoding="utf-8") as f:
                forms_lang = json.load(f)

            # Use the bot's robust lookup function
            if hasattr(bot, "lookup_form_id_for_mon"):
                result = bot.lookup_form_id_for_mon(pokedex_id, form_query)
                if result:
                    form_id_for_mon, form_name = result
                    logging.info(f"[QFORM] lookup_form_id_for_mon found: fid={form_id_for_mon}, fname='{form_name}'")
            else:
                # fallback to old logic if needed
                if str(pokedex_id) in forms_lang:
                    for fid, fname in forms_lang[str(pokedex_id)].items():
                        if fname.strip().lower() == form_query.strip().lower():
                            form_id_for_mon = fid
                            form_name = fname
                            break
                    # Fuzzy match if not exact
                    if not form_id_for_mon and form_query:
                        all_names = [fname.strip().lower() for fname in forms_lang[str(pokedex_id)].values()]
                        close = difflib.get_close_matches(form_query.strip().lower(), all_names, n=1, cutoff=0.7)
                        if close:
                            for fid, fname in forms_lang[str(pokedex_id)].items():
                                if fname.strip().lower() == close[0]:
                                    form_id_for_mon = fid
                                    form_name = fname
                                    break

            logging.debug(f"[QFORM] Final form_id_for_mon={form_id_for_mon}, form_name={form_name}")

            # After parsing arguments, before any form logic:
            form_query_clean = form_query.strip().lower() if form_query else ""
            use_no_form = not form_query

            if form_id_for_mon is not None:
                if int(form_id_for_mon) == 0:
                    icon_filename = f"{pokedex_id}.png"
                else:
                    icon_filename = f"{pokedex_id}_f{form_id_for_mon}.png"
                print(f"[QFORM DEBUG] Using icon_filename: {icon_filename}")
                if not search_icon_index(icon_index, icon_filename):
                    # fallback to base icon
                    fallback_icon_filename = f"{pokedex_id}.png"
                    print(f"[QFORM DEBUG] Fallback to icon_filename: {fallback_icon_filename}")
                    if search_icon_index(icon_index, fallback_icon_filename):
                        icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{fallback_icon_filename}"
                    else:
                        await ctx.send(f"No valid icon found for {pokemon_name} with form '{form_query}'")
                        return
                else:
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"
                found_form_id = int(form_id_for_mon)
                use_costume = False
                costume_id_for_match = None
            else:
                # --- Handle form logic ---
                form_query_clean = form_query.strip().lower() if form_query else ""
                use_no_form = not form_query
                form_id_for_mon = None
                form_name = None

                # 1. Build a list of all possible form IDs for this Pokémon from formsen.json
                form_ids = []
                form_map = {}
                for k, v in formsen.items():
                    if k.startswith("form_"):
                        fid = int(k.replace("form_", ""))
                        # Only include forms that have an icon for this Pokémon
                        icon_filename = f"{pokedex_id}_f{fid}.png"
                        if search_icon_index(icon_index, icon_filename):
                            form_ids.append(fid)
                            form_map[fid] = v

                # 2. Try exact match
                for fid, fname in form_map.items():
                    if fname.strip().lower() == form_query_clean:
                        form_id_for_mon = fid
                        form_name = fname
                        break

                # 3. Try fuzzy match if not exact
                if form_id_for_mon is None and form_query:
                    all_names = [fname.strip().lower() for fname in form_map.values()]
                    close = difflib.get_close_matches(form_query_clean, all_names, n=1, cutoff=0.7)
                    if close:
                        for fid, fname in form_map.items():
                            if fname.strip().lower() == close[0]:
                                form_id_for_mon = fid
                                form_name = fname
                                break

                # 4. If still not found, show available forms
                if form_id_for_mon is None and not use_no_form:
                    available_forms = [fname for fname in form_map.values()]
                    forms_list = "\n".join(f"- {fname}" for fname in available_forms)
                    await ctx.send(
                        embed=discord.Embed(
                            title=f"No valid form found for {pokemon_name.title()} with form '{form_query}'",
                            description=f"Available forms for {pokemon_name.title()}:\n{forms_list}",
                            color=discord.Color.orange()
                        )
                    )
                    return

            if form_id_for_mon:
                icon_filename = f"{pokedex_id}_f{form_id_for_mon}.png"
                print(f"[QFORM DEBUG] Using icon_filename: {icon_filename}")
                if not search_icon_index(icon_index, icon_filename):
                    # fallback to base icon
                    fallback_icon_filename = f"{pokedex_id}.png"
                    print(f"[QFORM DEBUG] Fallback to icon_filename: {fallback_icon_filename}")
                    if search_icon_index(icon_index, fallback_icon_filename):
                        icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{fallback_icon_filename}"
                    else:
                        await ctx.send(f"No valid icon found for {pokemon_name} with form '{form_query}'")
                        return
                else:
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"
                found_form_id = int(form_id_for_mon)
                use_costume = False
                costume_id_for_match = None
            else:
                # --- Handle form logic ---
                form_query_clean = form_query.strip().lower() if form_query else ""
                use_no_form = not form_query
                form_id_for_mon = None
                form_name = None
                icon_url = None
                found_form_id = None
                use_costume = False
                costume_id_for_match = None

                if str(pokedex_id) in forms_lang and not use_no_form:
                    # Always search values for the form name (case-insensitive, strip whitespace)
                    for fid, fname in forms_lang[str(pokedex_id)].items():
                        if fname.strip().lower() == form_query_clean:
                            form_id_for_mon = fid
                            form_name = fname
                            break
                    # Fuzzy match if not exact
                    if not form_id_for_mon and form_query:
                        all_names = [fname.lower() for fname in forms_lang[str(pokedex_id)].values()]
                        close = difflib.get_close_matches(form_query_clean, all_names, n=1, cutoff=0.7)
                        if close:
                            for fid, fname in forms_lang[str(pokedex_id)].items():
                                if fname.lower() == close[0]:
                                    form_id_for_mon = fid
                                    form_name = fname
                                    break

                if use_no_form:
                    icon_filename = f"{pokedex_id}.png"
                    if not search_icon_index(icon_index, icon_filename):
                        await ctx.send(f"No valid icon found for {pokemon_name} (no form)")
                        return
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"
                    form_name = "No Form"
                    found_form_id = 0
                elif form_id_for_mon is not None:
                    icon_filename = f"{pokedex_id}_f{form_id_for_mon}.png"
                    if not search_icon_index(icon_index, icon_filename):
                        await ctx.send(f"No valid icon found for {pokemon_name} (form: {form_name})")
                        return
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"
                    found_form_id = int(form_id_for_mon)
                else:
                    # Use form logic as before
                    form_ids = get_form_ids_by_name(form_query, formsen)
                    print(f"[QFORM DEBUG] form_ids found for '{form_query}': {form_ids}")
                    if not form_ids:
                        # Try costume match if no form match
                        costume_ids = []
                        costume_map = {int(k.replace("costume_", "")): v for k, v in formsen.items() if k.startswith("costume_")}
                        matches = [cid for cid, name in costume_map.items() if name.lower() == form_query.lower()]
                        if matches:
                            costume_ids = matches
                        else:
                            close = difflib.get_close_matches(form_query.lower(), [v.lower() for v in costume_map.values()], n=5, cutoff=0.7)
                            if close:
                                costume_ids = [cid for cid, name in costume_map.items() if name.lower() in close]
                        if costume_ids:
                            found_costume_id = costume_ids[0]
                            icon_filename = f"{pokedex_id}_c{found_costume_id}.png"
                            if not search_icon_index(icon_index, icon_filename):
                                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{pokedex_id}_c{found_costume_id}.png"
                                found_form_id = None
                                form_name = form_query.title()
                                # No icon found, but still show embed with icon
                            else:
                                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{pokedex_id}_c{found_costume_id}.png"
                                found_form_id = None
                                form_name = form_query.title()
                            # Set a flag to use costume_id for quest matching
                            use_costume = True
                            costume_id_for_match = found_costume_id
                        else:
                            await ctx.send(
                                embed=discord.Embed(
                                    title=f"{pokemon_name.title()} ({form_query.title()}) Quests - {area[1]}",
                                    description=f"Could not find any form or costume matching '{form_query}'",
                                    color=discord.Color.red()
                                )
                            )
                            return
                    else:
                        use_costume = False
                        costume_id_for_match = None
                        found_form_id = None
                        icon_filename = None
                        # Try all form IDs until we find one with an icon
                        for fid in form_ids:
                            test_icon_filename = f"{pokedex_id}_f{fid}.png"
                            print(f"[QFORM DEBUG] Checking icon_filename: {test_icon_filename}")
                            if search_icon_index(icon_index, test_icon_filename):
                                found_form_id = fid
                                icon_filename = test_icon_filename
                                break
                        
                        if found_form_id is not None:
                            form_name = formsen.get(f"form_{found_form_id}", form_query.title())
                            icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"
                        else:
                            # Try fallback: check for just {pokedex_id}.png (some forms use base icon)
                            fallback_icon_filename = f"{pokedex_id}.png"
                            print(f"[QFORM DEBUG] Fallback to icon_filename: {fallback_icon_filename}")
                            if search_icon_index(icon_index, fallback_icon_filename):
                                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{fallback_icon_filename}"
                                form_name = None
                                found_form_id = None
                            else:
                                # No valid icon found for any form, so list available forms for this Pokémon
                                # Get all form IDs for this Pokémon from the language file
                                available_forms = []
                                if str(pokedex_id) in forms_lang:
                                    for fid, fname in forms_lang[str(pokedex_id)].items():
                                        available_forms.append(fname)
                                if available_forms:
                                    forms_list = "\n".join(f"- {fname}" for fname in available_forms)
                                    await ctx.send(
                                        embed=discord.Embed(
                                            title=f"No valid icon found for {pokemon_name} with form '{form_query}'",
                                            description=f"Available forms for {pokemon_name.title()}:\n{forms_list}",
                                            color=discord.Color.orange()
                                        )
                                    )
                                else:
                                    await ctx.send(f"No valid icon or forms found for {pokemon_name} with form '{form_query}'")
                                return

            print(f"[QFORM] Area: {area[1]}, Pokémon: {pokemon_name}, Form: {form_name} (id={found_form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(bot.config, area, pokedex_id)
            found = False
            entries = []

            for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                try:
                    quest_json_str = quest_json.strip()
                    if quest_json_str.startswith("["):
                        end_idx = quest_json_str.find("]") + 1
                        quest_json_str = quest_json_str[:end_idx]
                    elif quest_json_str.startswith("{"):
                        end_idx = quest_json_str.find("}") + 1
                        quest_json_str = quest_json_str[:end_idx]
                    quest_list = json.loads(quest_json_str)
                except Exception as err:
                    print(f"[QFORM ERROR] Could not parse quest_json: {quest_json} ({err})")
                    continue
                if not quest_list or not isinstance(quest_list, list):
                    continue
                first = quest_list[0]
                if not isinstance(first, dict) or "info" not in first:
                    continue
                quest_info = first["info"]
                q_form_id = quest_info.get("form_id", 0)
                q_costume_id = quest_info.get("costume_id", 0)
                logging.debug(f"[QFORM] Quest: stop='{stop_name}', q_form_id={q_form_id}, q_costume_id={q_costume_id}")

                if use_no_form:
                    if not q_form_id or int(q_form_id) == 0:
                        logging.info(f"[QFORM] Matched NO FORM at stop '{stop_name}'")
                        found = True
                        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        stop_name_short = stop_name[:30]
                        entries.append(f"[{stop_name_short}]({map_url})")
                elif form_id_for_mon:
                    if q_form_id is not None and int(q_form_id) == int(found_form_id):
                        logging.info(f"[QFORM] Matched FORM {found_form_id} at stop '{stop_name}'")
                        found = True
                        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        stop_name_short = stop_name[:30]
                        entries.append(f"[{stop_name_short}]({map_url})")
                elif use_costume:
                    if int(q_costume_id) == int(costume_id_for_match):
                        found = True
                        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        stop_name_short = stop_name[:30]
                        entries.append(f"[{stop_name_short}]({map_url})")
                else:
                    if int(q_form_id) == int(found_form_id):
                        found = True
                        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        stop_name_short = stop_name[:30]
                        entries.append(f"[{stop_name_short}]({map_url})")
            if found:
                embed = discord.Embed(
                    title=f"{pokemon_name.title()} ({form_name}) Quests - {area[1]}",
                    description="\n".join(entries) if entries else "No quests found.",
                    color=discord.Color.blue()
                )
                if icon_url:
                    embed.set_thumbnail(url=icon_url)

                # Set the placeholder image first
                placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
                embed.set_image(url=placeholder_img)

                msg = await ctx.send(embed=embed)

                # Now generate and update with the static map if possible
                if getattr(bot, "static_map", None) is not None and entries:
                    try:
                        lat_list = []
                        lon_list = []
                        mons = []
                        # You may need to build mons as (id, lat, lon) tuples
                        for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                            # Only add those that matched
                            if stop_name[:30] in [e.split(']')[0][1:] for e in entries]:
                                if use_costume:
                                    mons.append((f"{pokedex_id}_c{costume_id_for_match}", lat, lon))
                                elif found_form_id:
                                    # Check if this form is "Normal"
                                    normal_names = ["normal"]
                                    # Try to get the form name for this form ID
                                    form_name_for_map = None
                                    if str(pokedex_id) in forms_lang and str(found_form_id) in forms_lang[str(pokedex_id)]:
                                        form_name_for_map = forms_lang[str(pokedex_id)][str(found_form_id)].strip().lower()
                                    elif f"form_{found_form_id}" in formsen:
                                        form_name_for_map = formsen[f"form_{found_form_id}"].strip().lower()
                                    if form_name_for_map in normal_names:
                                        mons.append((str(pokedex_id), lat, lon))
                                    else:
                                        mons.append((f"{pokedex_id}_f{found_form_id}", lat, lon))
                                else:
                                    mons.append((pokedex_id, lat, lon))
                                lat_list.append(lat)
                                lon_list.append(lon)
                        # Call the static map generator
                        print(f"[QFORM DEBUG] Calling static_map.quest with {len(lat_list)} locations")
                        static_map_url = await bot.static_map.quest(lat_list, lon_list, [], mons, bot.custom_emotes)
                        print(f"[QFORM DEBUG] static_map_url: {static_map_url}")
                        if static_map_url:
                            embed.set_image(url=static_map_url)
                            await msg.edit(embed=embed)
                    except Exception as e:
                        print(f"[QFORM ERROR] Static map failed: {e}")
                print(f"[QFORM] Sent {len(entries)} results for {pokemon_name} ({form_name})")
            else:
                # No quests found for the requested form, but maybe other forms exist in the data
                # Collect all unique form_ids from the quest data for this Pokémon
                available_form_ids = set()
                for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                    try:
                        quest_json_str = quest_json.strip()
                        if quest_json_str.startswith("["):
                            end_idx = quest_json_str.find("]") + 1
                            quest_json_str = quest_json_str[:end_idx]
                        elif quest_json_str.startswith("{"):
                            end_idx = quest_json_str.find("}") + 1
                            quest_json_str = quest_json_str[:end_idx]
                        quest_list = json.loads(quest_json_str)
                    except Exception:
                        continue
                    if not quest_list or not isinstance(quest_list, list):
                        continue
                    first = quest_list[0]
                    if not isinstance(first, dict) or "info" not in first:
                        continue
                    quest_info = first["info"]
                    q_form_id = quest_info.get("form_id", 0)
                    if q_form_id is not None:
                        available_form_ids.add(int(q_form_id))

                # Build a list of (form_id, form_name) tuples, using all available sources
                available_forms = []
                for fid in sorted(available_form_ids):
                    fname = None
                    if str(pokedex_id) in forms_lang:
                        fname = forms_lang[str(pokedex_id)].get(str(fid))
                    if not fname:
                        fname = formsen.get(f"form_{fid}")
                    if not fname:
                        fname = f"Form {fid}"
                    available_forms.append((fid, fname))

                if available_forms:
                    forms_list = "\n".join(f"- {fname} (ID: {fid})" for fid, fname in available_forms)
                    await ctx.send(
                        embed=discord.Embed(
                            title=f"No quests found for {pokemon_name.title()} with form '{form_name}' in {area[1]}",
                            description=f"However, quests are available for these forms:\n{forms_list}",
                            color=discord.Color.orange()
                        )
                    )
                else:
                    embed = discord.Embed(
                        title=f"{pokemon_name.title()} ({form_name}) Quests - {area[1]}",
                        description=f"No quests found for {pokemon_name} with form '{form_name}' in {area[1]}",
                        color=discord.Color.blue()
                    )
                    if icon_url:
                        embed.set_thumbnail(url=icon_url)
                    await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")

    bot.command(name="qform")(qform)  # <-- Add this line to register the command

def search_icon_index(obj, filename):
    if isinstance(obj, list):
        return filename in obj
    elif isinstance(obj, dict):
        for v in obj.values():
            if search_icon_index(v, filename):
                return True
    return False