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

            # --- Handle form logic ---
            use_normal = not form_query or form_query.strip().lower() == "normal"
            found_form_id = None
            form_name = "Normal"
            icon_url = None

            if use_normal:
                # Only use base icon and only match quests with no form_id or form_id==0
                icon_filename = f"{pokedex_id}.png"
                def search_icon_index(obj, filename):
                    if isinstance(obj, list):
                        return filename in obj
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            if search_icon_index(v, filename):
                                return True
                    return False
                if not search_icon_index(icon_index, icon_filename):
                    await ctx.send(f"No valid icon found for {pokemon_name} (Normal form)")
                    return
                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{pokedex_id}.png"
            else:
                # Use form logic as before
                form_ids = get_form_ids_by_name(form_query, formsen)
                if not form_ids:
                    await ctx.send(f"Could not find any form matching '{form_query}'")
                    return
                def search_icon_index(obj, filename):
                    if isinstance(obj, list):
                        return filename in obj
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            if search_icon_index(v, filename):
                                return True
                    return False
                for form_id in form_ids:
                    icon_filename = f"{pokedex_id}_f{form_id}.png"
                    if search_icon_index(icon_index, icon_filename):
                        found_form_id = form_id
                        break
                if not found_form_id:
                    await ctx.send(f"No valid icon found for {pokemon_name} with form '{form_query}'")
                    return
                form_name = formsen.get(f"form_{found_form_id}", form_query.title())
                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{pokedex_id}_f{found_form_id}.png"

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

                # --- Static map logic (like !q) ---
                static_map_url = None
                if getattr(bot, "static_map", None) is not None and entries:
                    # Gather all coordinates for the found quests
                    lat_list = []
                    lon_list = []
                    mons = []
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
                        if use_normal:
                            if not q_form_id or int(q_form_id) == 0:
                                lat_list.append(lat)
                                lon_list.append(lon)
                                mons.append((pokedex_id, lat, lon))  # base icon
                        else:
                            if int(q_form_id) == int(found_form_id):
                                lat_list.append(lat)
                                lon_list.append(lon)
                                # Use the correct icon filename for forms
                                mons.append((f"{pokedex_id}_f{found_form_id}", lat, lon))

                    if mons and isinstance(lat_list, list) and isinstance(lon_list, list):
                        msg = await ctx.send(embed=embed)
                        try:
                            import asyncio
                            await asyncio.sleep(1)
                            static_map_url = await bot.static_map.quest(
                                lat_list, lon_list, 0, mons, bot.custom_emotes
                            )
                            if static_map_url:
                                embed.set_image(url=static_map_url)
                                await msg.edit(embed=embed)
                        except Exception as e:
                            print(f"[QFORM ERROR] Static map failed: {e}")
                        print(f"[QFORM] Sent {len(entries)} results for {pokemon_name} ({form_name}) with map")
                        return
                # If not using static map, just send the embed
                await ctx.send(embed=embed)
                print(f"[QFORM] Sent {len(entries)} results for {pokemon_name} ({form_name})")
            else:
                await ctx.send(f"No quests found for {pokemon_name} with form '{form_name}' in {area[1]}")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")

    bot.command(name="qform")(qform)  # <-- Add this line to register the command