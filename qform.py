import discord
import json
import re
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

            # --- Regional form lookup logic ---
            # Load formsen.json and poke_lookup (api.json) from bot or disk
            with open("data/forms/formsen.json", encoding="utf-8") as f:
                formsen = json.load(f)
            poke_lookup = bot.poke_lookup  # or load from api.json if not already loaded

            # Find all form keys containing the form_query (case-insensitive, fuzzy)
            form_query_lower = form_query.lower()
            regional_forms = [(k, v) for k, v in formsen.items() if form_query_lower in v.lower()]
            regional_form_ids = [int(k.split("_")[1]) for k, v in regional_forms]

            # Cross-reference with poke_lookup
            form_id = None
            form_name = None
            for entry in poke_lookup:
                if f"({mon_id})" in entry["pokedex"]:
                    m = re.search(r"\((\d+)\)", entry["form"])
                    if m and int(m.group(1)) in regional_form_ids:
                        form_id = int(m.group(1))
                        form_name = entry["form"]
                        break

            if not form_id:
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
                quest_info = json.loads(quest_json)[0]["info"]
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