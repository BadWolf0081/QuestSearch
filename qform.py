import discord
import json
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
            form_id, form_name = bot.lookup_form_id_for_mon(
                mon_id=mon_id,
                form_query=form_query
            )
            if not form_name:
                await ctx.send(f"Could not find form '{form_query}' for {mon['name']}")
                return

            print(f"[QFORM] Area: {area[1]}, Pokémon: {mon['name']}, Form: {form_name} (id={form_id})")

            # Query for quests with this Pokémon and form
            quests = await bot.get_data(area, mon_id)
            found = False
            for quest_json, quest_template, lat, lon, stop_name, stop_id in quests:
                quest_info = json.loads(quest_json)[0]["info"]
                q_form_id = quest_info.get("form_id", 0)
                if int(q_form_id) == int(form_id):
                    found = True
                    filecode = bot.get_api_filecode(
                        mon_id,
                        form_id=form_id
                    )
                    icon_url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png" if filecode else ""
                    reply = f"**{mon['name']}** ({form_name}) at **{stop_name}**"
                    if icon_url:
                        embed = discord.Embed(description=reply)
                        embed.set_image(url=icon_url)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(reply)
                    print(f"[QFORM] Sent: {reply} | Icon: {icon_url}")
            if not found:
                await ctx.send(f"No quests found for {mon['name']} ({form_name}) in {area[1]}")
        except Exception as e:
            print(f"[QFORM ERROR] {e}")
            await ctx.send("Error processing your request.")

    bot.add_command(commands.Command(qform, name="qform"))