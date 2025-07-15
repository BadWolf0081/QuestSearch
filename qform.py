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

            # --- Load mon_names/en.txt for name->id mapping ---
            with open("data/mon_names/en.txt", encoding="utf-8") as f:
                mon_names = ast.literal_eval(f.read())

            # --- Fuzzy Pokémon name lookup using mon_names/en.txt ---
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

            # --- Robust per-mon form lookup ---
            form_id_for_mon = None
            form_name = None

            # Load the language-specific forms file (e.g., en.json)
            form_lang = bot.config['language']
            if not form_lang in ["en", "de", "fr", "es"]:
                form_lang = "en"
            with open(f"data/forms/{form_lang}.json", encoding="utf-8") as f:
                forms_lang = json.load(f)

            # Find all possible form IDs for this Pokémon from formsen.json
            form_ids = []
            form_map = {}
            for k, v in formsen.items():
                if k.startswith("form_"):
                    fid = int(k.replace("form_", ""))
                    form_map[v.lower()] = fid
                    form_ids.append(fid)

            # Try to match form_query to a form ID
            form_id_for_mon = None
            if form_query:
                # Try exact match
                for fname, fid in form_map.items():
                    if fname == form_query.lower():
                        form_id_for_mon = fid
                        form_name = fname
                        break
                # Try fuzzy match
                if not form_id_for_mon:
                    close = difflib.get_close_matches(form_query.lower(), list(form_map.keys()), n=1, cutoff=0.7)
                    if close:
                        form_id_for_mon = form_map[close[0]]
                        form_name = close[0]
            else:
                form_id_for_mon = 0  # Default form

            # Compose icon filename
            icon_filename = f"{pokedex_id}_f{form_id_for_mon}.png" if form_id_for_mon else f"{pokedex_id}.png"
            print(f"[QFORM DEBUG] Using icon_filename: {icon_filename}")

            # Check if icon exists
            def search_icon_index(obj, filename):
                if isinstance(obj, list):
                    return filename in obj
                elif isinstance(obj, dict):
                    for v in obj.values():
                        if search_icon_index(v, filename):
                            return True
                return False

            if not search_icon_index(icon_index, icon_filename):
                icon_url = None
            else:
                icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{icon_filename}"

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(bot.config, area, pokedex_id)
            found = False
            entries = []

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
                q_form_id = quest_info.get("form_id", 0)
                if (form_id_for_mon is None or int(q_form_id) == int(form_id_for_mon)):
                    entries.append(f"[{stop_name}]({bot.get_map_url(lat, lon, stop_id)})")
                    found = True

            if found:
                embed = discord.Embed(
                    title=f"{mon_name_found.title()} ({form_name if form_name else 'Normal'}) Quests - {area[1]}",
                    description="\n".join(entries) if entries else "No quests found.",
                    color=discord.Color.blue()
                )
                if icon_url:
                    embed.set_thumbnail(url=icon_url)
                placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
                embed.set_image(url=placeholder_img)
                msg = await ctx.send(embed=embed)
                # Optionally: add static map logic here
                print(f"[QFORM] Sent {len(entries)} results for {mon_name_found} ({form_name})")
            else:
                await ctx.send(f"No quests found for {mon_name_found} ({form_name if form_name else 'Normal'}) in {area[1]}.")

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            print(f"[QFORM ERROR] {str(e)}")

    bot.command(name="qform")(qform)