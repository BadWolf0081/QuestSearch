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

            # --- Find pokedex number for the pokemon ---
            # Use mon_names/en.txt for name->dex lookup
            import ast
            with open(f"data/mon_names/{bot.config['language']}.txt", encoding="utf-8") as f:
                mon_names = ast.literal_eval(f.read())

            def get_pokedex_id_from_name(name, names_dict):
                # Try exact match
                for mon_name, dex in names_dict.items():
                    if mon_name.lower() == name.lower():
                        return int(dex)
                # Fuzzy match
                matches = difflib.get_close_matches(name.lower(), [n.lower() for n in names_dict.keys()], n=1, cutoff=0.7)
                if matches:
                    return int(names_dict[matches[0]])
                return None

            pokedex_id = get_pokedex_id_from_name(pokemon_name, mon_names)
            if pokedex_id is None:
                await ctx.send(f"Could not find Pokémon: {pokemon_name}")
                return

            # --- Find form id for the given form_query and pokedex_id ---
            def get_form_id_for_query(pokedex_id, form_query, forms_dict):
                forms_for_mon = forms_dict.get(str(pokedex_id), {})
                # Try exact match
                for form_id, form_name in forms_for_mon.items():
                    if form_name.lower() == form_query.lower():
                        return int(form_id), form_name
                # Fuzzy match
                matches = difflib.get_close_matches(form_query.lower(), [v.lower() for v in forms_for_mon.values()], n=1, cutoff=0.7)
                if matches:
                    for form_id, form_name in forms_for_mon.items():
                        if form_name.lower() == matches[0]:
                            return int(form_id), form_name
                return None, None

            form_id, form_name = get_form_id_for_query(pokedex_id, form_query, bot.forms)
            if form_id is None:
                await ctx.send(f"Could not find form '{form_query}' for {pokemon_name}")
                return

            # --- Check if the icon file exists in index.json (valid form for this Pokémon) ---
            icon_filename = f"{pokedex_id}_f{form_id}.png"
            valid_form = False

            def search_icon_index(obj, filename):
                """Recursively search for filename in any list value in obj."""
                if isinstance(obj, list):
                    return filename in obj
                elif isinstance(obj, dict):
                    for v in obj.values():
                        if search_icon_index(v, filename):
                            return True
                return False

            if search_icon_index(icon_index, icon_filename):
                valid_form = True

            if not valid_form:
                await ctx.send(f"Form '{form_query}' is not valid for {pokemon_name}")
                return

            print(f"[QFORM] Area: {area[1]}, Pokémon: {pokemon_name}, Form: {form_name} (id={form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(area, pokedex_id)
            found = False
            entries = []
            filecode = f"{pokedex_id}_f{form_id}"
            icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"

            for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                quest_list = json.loads(quest_json)
                if not quest_list or not isinstance(quest_list, list):
                    continue  # skip empty or malformed quest entries
                first = quest_list[0]
                if not isinstance(first, dict) or "info" not in first:
                    continue  # skip malformed quest entries
                quest_info = first["info"]
                q_form_id = quest_info.get("form_id", 0)
                if int(q_form_id) == int(form_id):
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
                await ctx.send(f"No quests found for {pokemon_name} ({form_name}) in {area[1]}")
        except Exception as e:
            print(f"[QFORM ERROR] {e}")
            await ctx.send("Error processing your request.")

    bot.add_command(commands.Command(qform, name="qform"))