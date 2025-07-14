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

            mon = bot.fuzzy_find_pokemon(pokemon_name)
            print(f"[QFORM DEBUG] Fuzzy pokemon: {mon}")
            if not mon:
                await ctx.send(f"Could not find Pokémon: {pokemon_name}")
                return

            mon_id = int(mon['pokedex'].split('(')[-1].replace(')', '').strip())

            def find_form_id_for_mon(mon_id, form_query, formsen, poke_lookup):
                # 1. Fuzzy match form_query to formsen values (case-insensitive, partial match)
                form_names = [v.lower() for k, v in formsen.items() if k.startswith("form_")]
                matches = difflib.get_close_matches(form_query.lower(), form_names, n=5, cutoff=0.6)
                if not matches:
                    # Try substring match as fallback
                    matches = [v for k, v in formsen.items() if k.startswith("form_") and form_query.lower() in v.lower()]
                if not matches:
                    return None, None

                # 2. Collect all form IDs that match
                matched_form_ids = []
                for k, v in formsen.items():
                    if k.startswith("form_") and v.lower() in matches:
                        try:
                            matched_form_ids.append(int(k.split("_")[1]))
                        except Exception:
                            continue

                # 3. For each matching form ID, check if it exists for this Pokémon in poke_lookup
                for entry in poke_lookup:
                    if f"({mon_id})" in entry["pokedex"]:
                        m = re.search(r"\((\d+)\)", entry["form"])
                        if m and int(m.group(1)) in matched_form_ids:
                            return int(m.group(1)), entry["form"]
                return None, None

            # --- Regional form lookup logic ---
            # Load formsen.json and poke_lookup (api.json) from bot or disk
            with open("data/forms/formsen.json", encoding="utf-8") as f:
                formsen = json.load(f)
            poke_lookup = bot.poke_lookup  # or load from api.json if not already loaded

            # --- Load index.json for icon existence check ---
            with open("data/forms/index.json", encoding="utf-8") as f:
                icon_index = json.load(f)

            form_id, form_name = find_form_id_for_mon(mon_id, form_query, formsen, poke_lookup)

            # Check if the icon file exists in index.json (valid form for this Pokémon)
            valid_form = False
            if form_id is not None:
                icon_filename = f"{mon_id}_f{form_id}.png"
                # icon_index is a dict of lists, search all lists for the filename
                for file_list in icon_index.values():
                    if icon_filename in file_list:
                        valid_form = True
                        break

            if not form_id or not valid_form:
                await ctx.send(f"Could not find form '{form_query}' for {mon['name']}")
                return

            print(f"[QFORM] Area: {area[1]}, Pokémon: {mon['name']}, Form: {form_name} (id={form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(area, mon_id)
            found = False
            entries = []
            filecode = bot.get_api_filecode(mon_id, form_id=form_id)
            icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png" if filecode else ""

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
                    title=f"{mon['name']} ({form_name}) Quests - {area[1]}",
                    description="\n".join(entries) if entries else "No quests found.",
                    color=discord.Color.blue()
                )
                if icon_url:
                    embed.set_thumbnail(url=icon_url)
                await ctx.send(embed=embed)
                print(f"[QFORM] Sent {len(entries)} results for {mon['name']} ({form_name})")
            else:
                await ctx.send(f"No quests found for {mon['name']} ({form_name}) in {area[1]}")
        except Exception as e:
            print(f"[QFORM ERROR] {e}")
            await ctx.send("Error processing your request.")

    bot.add_command(commands.Command(qform, name="qform"))