import discord
import json
import re
import difflib
import logging
import ast
from discord.ext import commands

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)

def search_icon_index(obj, filename):
    if isinstance(obj, list):
        return filename in obj
    elif isinstance(obj, dict):
        for v in obj.values():
            if search_icon_index(v, filename):
                return True
    return False

async def setup(bot):
    @bot.command(name="qform")
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

            # Load mon_names/en.txt for name->id mapping
            with open("data/mon_names/en.txt", encoding="utf-8") as f:
                mon_names = ast.literal_eval(f.read())

            # Fuzzy Pokémon name lookup
            def fuzzy_mon_lookup(query, mon_names):
                names = list(mon_names.keys())
                match = difflib.get_close_matches(query.lower(), [n.lower() for n in names], n=1, cutoff=0.7)
                if match:
                    for n in names:
                        if n.lower() == match[0]:
                            return n, mon_names[n]
                # fallback: try substring match
                for n in names:
                    if query.lower() in n.lower():
                        return n, mon_names[n]
                return None, None

            mon_name_found, pokedex_id = fuzzy_mon_lookup(pokemon_name, mon_names)
            if not pokedex_id:
                await ctx.send(f"Could not find Pokémon: {pokemon_name}")
                return

            print(f"[QFORM DEBUG] Found: {mon_name_found} (ID: {pokedex_id})")

            # Load formsen.json for form name/id mapping
            with open("data/forms/formsen.json", encoding="utf-8") as f:
                formsen = json.load(f)
            # Load index.json for icon existence check
            with open("data/forms/index.json", encoding="utf-8") as f:
                icon_index = json.load(f)

            # Query for quests with this Pokémon (all forms)
            quests = await bot.get_data(bot.config, area, pokedex_id)
            found = False
            entries = []
            forms_with_quests = {}

            for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                try:
                    quest_list = json.loads(quest_json)
                except Exception as err:
                    continue
                if not quest_list or not isinstance(quest_list, list):
                    continue
                first = quest_list[0]
                if not isinstance(first, dict) or "info" not in first:
                    continue
                quest_info = first["info"]
                q_form_id = int(quest_info.get("form_id", 0))
                # Track which forms have quests
                if q_form_id not in forms_with_quests:
                    forms_with_quests[q_form_id] = []
                forms_with_quests[q_form_id].append((stop_name, lat, lon, stop_id))

            # Now build the mapping of form_id <-> form_name for only available forms
            form_id_to_name = {}
            form_name_to_id = {}
            for fid in forms_with_quests.keys():
                form_name = formsen.get(f"form_{fid}", f"Form {fid}")
                form_id_to_name[fid] = form_name
                form_name_to_id[form_name.lower()] = fid

            # Fuzzy form name lookup (if requested)
            form_id_for_mon = None
            form_name = None
            if form_query:
                # Try exact match among available forms
                if form_query.lower() in form_name_to_id:
                    form_id_for_mon = form_name_to_id[form_query.lower()]
                    form_name = form_id_to_name[form_id_for_mon]
                else:
                    # Fuzzy match among available forms
                    close = difflib.get_close_matches(form_query.lower(), list(form_name_to_id.keys()), n=1, cutoff=0.7)
                    if close:
                        form_id_for_mon = form_name_to_id[close[0]]
                        form_name = form_id_to_name[form_id_for_mon]
                # Only show this form's quests if available
                if form_id_for_mon is not None and form_id_for_mon in forms_with_quests:
                    for stop_name, lat, lon, stop_id in forms_with_quests[form_id_for_mon]:
                        entries.append(f"[{stop_name}]({bot.get_map_url(lat, lon, stop_id)})")
                    found = True
                else:
                    # Form not found or no quests for this form, show available forms (but do NOT show all results)
                    available_forms = [f"{form_id_to_name[fid]} (ID: {fid})" for fid in forms_with_quests.keys()]
                    if available_forms:
                        embed = discord.Embed(
                            title=f"Available forms for {mon_name_found.title()} in {area[1]}",
                            description="\n".join(f"• {form_id_to_name[fid]} (ID: {fid})" for fid in forms_with_quests.keys()),
                            color=discord.Color.orange()
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(
                            f"No quests found for {mon_name_found} in {area[1]}.\nNo forms with quests available."
                        )
                    return
            else:
                # No form specified, check if base form (0) has quests
                if 0 in forms_with_quests:
                    # Show only base form quests
                    for stop_name, lat, lon, stop_id in forms_with_quests[0]:
                        entries.append(f"[{stop_name}]({bot.get_map_url(lat, lon, stop_id)})")
                    found = True
                else:
                    # No base form quests, show available forms as a list
                    available_forms = [f"{form_id_to_name[fid]} (ID: {fid})" for fid in forms_with_quests.keys()]
                    if available_forms:
                        embed = discord.Embed(
                            title=f"Available forms for {mon_name_found.title()} in {area[1]}",
                            description="\n".join(f"• {form_id_to_name[fid]} (ID: {fid})" for fid in forms_with_quests.keys()),
                            color=discord.Color.orange()
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(
                            f"No quests found for {mon_name_found} in {area[1]}.\nNo forms with quests available."
                        )
                    return

            # Compose icon filename for the requested form (or default)
            def is_normal_form(fid):
                return (fid == 0) or (form_id_to_name.get(fid, "").lower() == "normal")

            icon_form_id = form_id_for_mon if form_id_for_mon is not None else 0
            if is_normal_form(icon_form_id):
                icon_filename = f"{pokedex_id}.png"
            else:
                icon_filename = f"{pokedex_id}_f{icon_form_id}.png"
            print(f"[QFORM DEBUG] Using icon_filename: {icon_filename}")

            # Check if icon exists
            if not search_icon_index(icon_index, icon_filename):
                icon_url = None
            else:
                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"

            if found:
                embed = discord.Embed(
                    title=f"{mon_name_found.title()} ({form_name if form_name else 'All Forms'}) Quests - {area[1]}",
                    description="\n".join(entries) if entries else "No quests found.",
                    color=discord.Color.blue()
                )
                if icon_url:
                    embed.set_thumbnail(url=icon_url)
                placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
                embed.set_image(url=placeholder_img)
                msg = await ctx.send(embed=embed)

                # --- Static map support ---
                if getattr(bot, "static_map", None) and bot.config.get("use_static"):
                    lat_list = []
                    lon_list = []
                    mons_list = []
                    # For each quest entry, collect lat/lon and mon_id (with form if possible)
                    def is_normal_form(fid):
                        # Treat as Normal if form name is "Normal" or fid == 0
                        return (fid == 0) or (form_id_to_name.get(fid, "").lower() == "normal")

                    if form_id_for_mon is not None:
                        # Only one form requested
                        for stop_name, lat, lon, stop_id in forms_with_quests.get(form_id_for_mon, []):
                            lat_list.append(lat)
                            lon_list.append(lon)
                            if is_normal_form(form_id_for_mon):
                                mons_list.append((str(pokedex_id), lat, lon))
                            else:
                                mons_list.append((f"{pokedex_id}_f{form_id_for_mon}", lat, lon))
                    else:
                        # All forms
                        for fid, stops in forms_with_quests.items():
                            for stop_name, lat, lon, stop_id in stops:
                                lat_list.append(lat)
                                lon_list.append(lon)
                                if is_normal_form(fid):
                                    mons_list.append((str(pokedex_id), lat, lon))
                                else:
                                    mons_list.append((f"{pokedex_id}_f{fid}", lat, lon))
                    if lat_list and lon_list and mons_list:
                        image = await bot.static_map.quest(
                            lat_list, lon_list, [], [(mon_id, lat, lon) for mon_id, lat, lon in mons_list], bot.custom_emotes
                        )
                        if image:
                            embed.set_image(url=image)
                            await msg.edit(embed=embed)
            else:
                await ctx.send(f"No quests found for {mon_name_found} ({form_name if form_name else 'All Forms'}) in {area[1]}.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")