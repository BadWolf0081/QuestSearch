import discord
import json
import asyncio
import aiomysql

from datetime import datetime, date
import matplotlib.pyplot as plt
import pyshorteners
from discord.ext import commands
from util.mondetails import details
import util.config
import util.maps

extensions = []

activity = discord.Activity(type=discord.ActivityType.watching, name="Quest Bot: Online")
intents = discord.Intents.default()
intents.message_content = True
config = util.config.create_config("config/config.ini")
bot = commands.Bot(command_prefix=config['prefix'], case_insensitive=1, intents=intents, activity=activity, status=discord.Status.online)
bot.max_moves_in_list = 340
bot.config = config
short = pyshorteners.Shortener().tinyurl.short

if bot.config['use_map']:
    bot.map_url = util.maps.map_url(config['map'], config['map_url'])

### LANG FILES

dts_lang = bot.config['language']
if not bot.config['language'] in ["en", "de", "fr", "es", "pl"]:
    dts_lang = "en"

with open(f"data/dts/{dts_lang}.json", encoding="utf-8") as f:
    bot.locale = json.load(f)

move_lang = bot.config['language']
if not bot.config['language'] in ["en", "de", "fr", "es"]:
    move_lang = "en"

with open(f"data/moves/{move_lang}.json", encoding="utf-8") as f:
    bot.moves = json.load(f)

form_lang = bot.config['language']
if not bot.config['language'] in ["en", "de", "fr", "es"]:
    form_lang = "en"

with open(f"data/forms/{form_lang}.json", encoding="utf-8") as f:
    bot.forms = json.load(f)

item_lang = bot.config['language']
if not bot.config['language'] in ["en", "de", "fr", "es"]:
    item_lang = "en"

with open(f"data/items/{item_lang}.json", encoding="utf-8") as f:
    bot.items = json.load(f)

### LANG FILES STOP

with open("config/geofence.json", encoding="utf-8") as f:
    bot.geofences = json.load(f)
    
with open("config/emotes.json", encoding="utf-8") as f:
    bot.custom_emotes = json.load(f)

async def get_data(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT quest_rewards, quest_template, lat, lon, name, id FROM rdmdb.pokestop WHERE quest_type IS NOT NULL AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY quest_item_id ASC, quest_pokemon_id ASC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datak(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration FROM rdmdb.pokestop, rdmdb.incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =8 AND incident.expiration >= UNIX_TIMESTAMP()+300 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY quest_item_id ASC, quest_pokemon_id ASC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests

def isUser(role_ids, channel_id):
    if len(bot.config["cmd_roles"][0]) + len(bot.config["cmd_channels"][0]) == 0:
        return True
    elif str(channel_id) in bot.config["cmd_channels"]:
        return True
    else:
        for role in role_ids:
            if str(role.id) in bot.config["cmd_roles"]:
                return True
        return False

def get_area(areaname):
    stringfence = "-100 -100, -100 100, 100 100, 100 -100, -100 -100"
    namefence = bot.locale['all']
    for area in bot.geofences:
        if area['name'].lower() == areaname.lower():
            namefence = area['name'].title()
            stringfence = ""
            for coordinates in area['path']:
                stringfence = f"{stringfence}{coordinates[0]} {coordinates[1]},"
            stringfence = f"{stringfence}{area['path'][0][0]} {area['path'][0][1]}"
    area_list = [stringfence, namefence]
    return area_list

@bot.command(pass_context=True, aliases=bot.config['quest_aliases'])
async def quest(ctx, areaname = "", *, reward):
    if not isUser(ctx.author.roles, ctx.channel.id):
        print(f"@{ctx.author.name} tried to use !quest but is no user")
        return
    footer_text = ""
    text = ""
    loading = bot.locale['loading_quests']

    area = get_area(areaname)
    if not area[1] == bot.locale['all']:
        footer_text = area[1]
        loading = f"{loading} • {footer_text}"

    print(f"@{ctx.author.name} requested {reward} quests for area {area[1]}")

    if reward == 'Kecleon':
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
    elif reward == 'kecleon':
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
    elif reward == 'keckleon':
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
    elif reward == 'Keckleon':
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
    else:
        embed = discord.Embed(title=bot.locale['quests'], description=text)
    embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    message = await ctx.send(embed=embed)
    
    items = list()
    mons = list()
    item_found = False
    for item_id in bot.items:
        if bot.items[item_id]["name"].lower() == reward.lower():
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}rewards/reward_{item_id}_1.png")
            embed.title = f"{bot.items[item_id]['name']} {bot.locale['quests']}"
            items.append(int(item_id))
            item_found = True
    if not item_found:
        mon = details(reward, bot.config['mon_icon_repo'], bot.config['language'])
        embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon_icon_{str(mon.id).zfill(3)}_00.png")
        embed.title = f"{mon.name} {bot.locale['quests']} - {area[1]}"
        mons.append(mon.id)
    
    await message.edit(embed=embed)
    if not item_found and mon.name == "Kecleon":
        quests = await get_datak(area)
    else:
        quests = await get_data(area)

    length = 0
    reward_mons = list()
    reward_items = list()
    lat_list = list()
    lon_list = list()

    embed.description = text
    if not item_found and mon.name == "Kecleon":
        for lat, lon, stop_name, stop_id, expiration in quests:
            end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
            found_rewards = True
            mon_id = 352
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}pokemon_icon_{str(mon_id).zfill(3)}_00.png"
    
            if found_rewards:
                if len(stop_name) >= 24:
                    stop_name = stop_name[0:24] + "."
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name} **{end}**]({map_url})\n"
                if length + len(entry) >= 2048:
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    else:
        for quest_json, quest_text, lat, lon, stop_name, stop_id in quests:
            quest_json = json.loads(quest_json)
            found_rewards = True
            mon_id = 0
            item_id = 0

            if 'pokemon_id' in quest_json[0]["info"]:
                    mon_id = quest_json[0]["info"]["pokemon_id"]
            if 'item_id' in quest_json[0]["info"]:
                    item_id = quest_json[0]["info"]["item_id"]
            if item_id in items:
                reward_items.append([item_id, lat, lon])
                emote_name = f"i{item_id}"
                emote_img = f"{bot.config['mon_icon_repo']}rewards/reward_{item_id}_1.png"
            elif mon_id in mons:
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"m{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}pokemon_icon_{str(mon_id).zfill(3)}_00.png"
            else:
                found_rewards = False
    
            if found_rewards:
                if len(stop_name) >= 30:
                    stop_name = stop_name[0:30] + "."
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2048:
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
                
    embed.description = text
    image = "https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png"
    if length > 0:
        if bot.config['use_static']:
            if bot.config['static_provider'] == "mapbox":
                guild = await bot.fetch_guild(bot.config['host_server'])
                existing_emotes = await guild.fetch_emojis()
                emote_exist = False
                for existing_emote in existing_emotes:
                    if emote_name == existing_emote.name:
                        emote_exist = True
                if not emote_exist:
                    try:
                        image = await Admin.download_url("", emote_img)
                        emote = await guild.create_custom_emoji(name=emote_name, image=image)
                        emote_ref = f"<:{emote.name}:{emote.id}>"

                        if emote_name in bot.custom_emotes:
                            bot.custom_emotes[emote_name] = emote_ref
                        else:
                            bot.custom_emotes.update({emote_name: emote_ref})
                    except Exception as err:
                        print(err)
                        print(f"Error while importing emote {emote_name}")

                image = await bot.static_map.quest(lat_list, lon_list, reward_items, reward_mons, bot.custom_emotes)

                if not emote_exist:
                    await emote.delete()
                    bot.custom_emotes.pop(emote_name)

            elif bot.config['static_provider'] == "tileserver":
                image = await bot.static_map.quest(lat_list, lon_list, reward_items, reward_mons, bot.custom_emotes)
    else:
        embed.description = bot.locale["no_quests_found"]

    embed.set_footer(text=footer_text)
    embed.set_image(url=image)

    await message.edit(embed=embed)
    
@bot.event
async def on_ready():
    print("Connected to Discord. Ready to take commands.")

    if bot.config['use_static']:
        trash_channel = await bot.fetch_channel(bot.config['host_channel'])
        bot.static_map = util.maps.static_map(config['static_provider'], config['static_key'], trash_channel, bot.config['mon_icon_repo'])

if __name__ == "__main__":
    for extension in extensions:
        bot.load_extension(extension)
    bot.run(bot.config['bot_token'])