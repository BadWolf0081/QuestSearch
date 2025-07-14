import discord
import json
import re
import difflib
from discord.ext import commands

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

            if str(pokedex_id) in forms_lang:
                # Try to match the form name for this Pokémon
                for fid, fname in forms_lang[str(pokedex_id)].items():
                    if fname.lower() == form_query.strip().lower():
                        form_id_for_mon = fid
                        form_name = fname
                        break
                # Fuzzy match if not exact
                if not form_id_for_mon:
                    import difflib
                    all_names = [fname.lower() for fname in forms_lang[str(pokedex_id)].values()]
                    close = difflib.get_close_matches(form_query.strip().lower(), all_names, n=1, cutoff=0.7)
                    if close:
                        for fid, fname in forms_lang[str(pokedex_id)].items():
                            if fname.lower() == close[0]:
                                form_id_for_mon = fid
                                form_name = fname
                                break

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
                use_normal = not form_query or form_query.strip().lower() == "normal"
                found_form_id = None
                form_name = "Normal"
                icon_url = None

                def search_icon_index(obj, filename):
                    if isinstance(obj, list):
                        return filename in obj
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            if search_icon_index(v, filename):
                                return True
                    return False

                if use_normal:
                    # Only use base icon and only match quests with no form_id or form_id==0
                    icon_filename = f"{pokedex_id}.png"
                    if not search_icon_index(icon_index, icon_filename):
                        await ctx.send(f"No valid icon found for {pokemon_name} (Normal form)")
                        return
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{pokedex_id}.png"
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
                            await ctx.send(f"Could not find any form or costume matching '{form_query}'")
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
                                form_name = "Normal"
                                found_form_id = None
                            else:
                                await ctx.send(f"No valid icon found for {pokemon_name} with form '{form_query}'")
                                return

            print(f"[QFORM] Area: {area[1]}, Pokémon: {pokemon_name}, Form: {form_name} (id={found_form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(area, pokedex_id)
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
                if use_normal:
                    # Only match if form_id is missing or 0
                    if not q_form_id or int(q_form_id) == 0:
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

                # Set the same placeholder image as !quest
                placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
                embed.set_image(url=placeholder_img)

                static_map_url = None
                if getattr(bot, "static_map", None) is not None and entries:
                    # ...existing static map logic...
                    pass
                await ctx.send(embed=embed)
                print(f"[QFORM] Sent {len(entries)} results for {pokemon_name} ({form_name})")
            else:
                # Always show the icon even if no quests found
                embed = discord.Embed(
                    title=f"{pokemon_name.title()} ({form_name}) Quests - {area[1]}",
                    description=f"No quests found for {pokemon_name} with form '{form_name}' in {area[1]}",
                    color=discord.Color.blue()
                )
                if icon_url:
                    embed.set_thumbnail(url=icon_url)
                placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
                embed.set_image(url=placeholder_img)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")

    bot.command(name="qform")(qform)  # <-- Add this line to register the command