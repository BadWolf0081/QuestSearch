import discord
import json
import re
import difflib
from discord.ext import commands

async def setup(bot):
    async def qform(ctx, areaname="", pokemon_name="", form_query=""):
        """
        Usage: !qform <area> <pokemon name> <form>
        Example: !qform Greatermoncton meowth galarian
        """
        try:
            print(f"[QFORM DEBUG] area='{areaname}', pokemon_name='{pokemon_name}', form_query='{form_query}'")
            if not areaname or not pokemon_name or not form_query:
                await ctx.send("Usage: !qform <area> <pokemon name> <form>")
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
                # Lowercase all values for fuzzy matching
                form_map = {int(k.replace("form_", "")): v for k, v in formsen.items() if k.startswith("form_")}
                # Exact match
                matches = [fid for fid, name in form_map.items() if name.lower() == form_query.lower()]
                if matches:
                    return matches
                # Fuzzy match
                close = difflib.get_close_matches(form_query.lower(), [v.lower() for v in form_map.values()], n=5, cutoff=0.7)
                if close:
                    return [fid for fid, name in form_map.items() if name.lower() in close]
                return []

            form_ids = get_form_ids_by_name(form_query, formsen)
            if not form_ids:
                await ctx.send(f"Could not find any form matching '{form_query}'")
                return

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

            # --- 3. Check for icon existence in index.json ---
            def search_icon_index(obj, filename):
                if isinstance(obj, list):
                    return filename in obj
                elif isinstance(obj, dict):
                    for v in obj.values():
                        if search_icon_index(v, filename):
                            return True
                return False

            found_form_id = None
            for form_id in form_ids:
                icon_filename = f"{pokedex_id}_f{form_id}.png"
                if search_icon_index(icon_index, icon_filename):
                    found_form_id = form_id
                    break

            if not found_form_id:
                await ctx.send(f"No valid icon found for {pokemon_name} with form '{form_query}'")
                return

            # Now you have: pokedex_id, found_form_id, and can proceed as before
            form_name = formsen.get(f"form_{found_form_id}", form_query.title())

            print(f"[QFORM] Area: {area[1]}, Pokémon: {pokemon_name}, Form: {form_name} (id={found_form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(area, pokedex_id)
            found = False
            entries = []
            filecode = f"{pokedex_id}_f{found_form_id}"
            icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"

            for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                try:
                    # Defensive: only parse up to the first valid JSON array/object
                    quest_json_str = quest_json.strip()
                    if quest_json_str.startswith("["):
                        # Try to find the matching closing bracket for the array
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
                    continue  # skip empty or malformed quest entries
                first = quest_list[0]
                if not isinstance(first, dict) or "info" not in first:
                    continue  # skip malformed quest entries
                quest_info = first["info"]
                q_form_id = quest_info.get("form_id", 0)
                if int(q_form_id) == int(found_form_id):
                    found = True
                    # Google Maps link
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    # Truncate stop name if too long
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
                await ctx.send(embed=embed)
                print(f"[QFORM] Sent {len(entries)} results for {pokemon_name} ({form_name})")
            else:
                await ctx.send(f"No quests found for {pokemon_name} with form '{form_name}' in {area[1]}")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")

    bot.command(name="qform")(qform)  # <-- Add this line to register the command