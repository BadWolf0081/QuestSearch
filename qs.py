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

async def get_data(area, mon_id):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT quest_rewards, quest_template, lat, lon, name, id FROM pokestop WHERE quest_pokemon_id = {mon_id} AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_pokemon_id ASC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_lures(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT lure_expire_timestamp, lure_id, lat, lon, name FROM pokestop WHERE ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND lure_expire_timestamp >= UNIX_TIMESTAMP() ORDER BY name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_stations(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT lat, lon, name, end_time FROM station WHERE ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND end_time >= UNIX_TIMESTAMP() ORDER BY end_time;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datarocket(area, type):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration, incident.character FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.character={type} AND incident.display_type =1 AND incident.expiration >= UNIX_TIMESTAMP() AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.character ASC, pokestop.name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datarocketquery(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration, incident.character FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =1 AND incident.expiration >= UNIX_TIMESTAMP() AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.character ASC, pokestop.name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datagiovani(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration, incident.character FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =3 AND incident.expiration >= UNIX_TIMESTAMP() AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.expiration ASC, pokestop.name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_dataleaders(area, char_id):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration, incident.character FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =2 AND incident.character={char_id} AND incident.expiration >= UNIX_TIMESTAMP() AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.expiration ASC, pokestop.name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests

async def get_alt_data(area, mon_id):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT alternative_quest_rewards, alternative_quest_template, lat, lon, name, id FROM pokestop WHERE alternative_quest_pokemon_id = {mon_id} AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY alternative_quest_pokemon_id ASC, name;")
        quests2 = await cur.fetchall()
    await conn.ensure_closed()
    return quests2

async def get_dataitem(area, item_id):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT quest_rewards, quest_template, lat, lon, name, id FROM pokestop WHERE quest_item_id = {item_id} AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_reward_amount DESC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests

async def get_alt_dataitem(area, item_id):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT alternative_quest_rewards, alternative_quest_template, lat, lon, name, id FROM pokestop WHERE alternative_quest_item_id = {item_id} AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY alternative_quest_reward_amount DESC, name;")
        quests2 = await cur.fetchall()
    await conn.ensure_closed()
    return quests2
    
async def get_datamega(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT quest_rewards, quest_template, lat, lon, name, id FROM pokestop WHERE quest_reward_type = 12 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_item_id ASC, quest_pokemon_id ASC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_alt_datamega(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT alternative_quest_rewards, alternative_quest_template, lat, lon, name, id FROM pokestop WHERE alternative_quest_reward_type = 12 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY alternative_quest_item_id ASC, alternative_quest_pokemon_id ASC, name;")
        quests2 = await cur.fetchall()
    await conn.ensure_closed()
    return quests2

async def get_dataroute(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT distance_meters, start_lat, start_lon, name, id FROM route WHERE ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(start_lat,start_lon)) ORDER BY distance_meters ASC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datastar(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT quest_reward_amount, quest_template, lat, lon, name, id FROM pokestop WHERE quest_reward_type = 3 AND quest_reward_amount >= 999 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_reward_amount DESC, name;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_alt_datastar(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT alternative_quest_reward_amount, alternative_quest_template, lat, lon, name, id FROM pokestop WHERE alternative_quest_reward_type = 3 AND alternative_quest_reward_amount >= 999 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY alternative_quest_reward_amount DESC, name;")
        quests2 = await cur.fetchall()
    await conn.ensure_closed()
    return quests2
    
async def get_datak(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =8 AND incident.expiration >= UNIX_TIMESTAMP()+300 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.expiration DESC;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests
    
async def get_datashow(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =9 AND incident.expiration >= UNIX_TIMESTAMP()+300 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.expiration DESC;")
        quests = await cur.fetchall()
    await conn.ensure_closed()
    return quests

async def get_datacoin(area):
    conn = await aiomysql.connect(host=config['db_host'],user=config['db_user'],password=config['db_pass'],db=config['db_dbname'],port=config['db_port'])    
    cur = await conn.cursor()
    async with conn.cursor() as cur:
        await cur.execute(f"SELECT pokestop.lat, pokestop.lon, pokestop.name, pokestop.id, incident.expiration FROM pokestop, incident WHERE pokestop.id = incident.pokestop_id AND incident.display_type =7 AND incident.expiration >= UNIX_TIMESTAMP()+300 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) ORDER BY incident.expiration DESC;")
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
    stringfence = "-1 -1, -1 1, 1 1, 1 -1, -1 -1"
    namefence = bot.locale['unknown']
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

    if area[1] == "Unknown Area":
        embed = discord.Embed(title=bot.locale['no_area_found'], description=text)
    elif reward.startswith("Mega") or reward.startswith("mega"):
        embed = discord.Embed(title=bot.locale['mega'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Lure") or reward.startswith("lure"):
        embed = discord.Embed(title=bot.locale['active_lures'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Station") or reward.startswith("Power") or reward.startswith("Station") or reward.startswith("power"):
        embed = discord.Embed(title=bot.locale['station'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Showcase") or reward.startswith("showcase"):
        embed = discord.Embed(title=bot.locale['showcase'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Giovan") or reward.startswith("giovan"):
        embed = discord.Embed(title=bot.locale['giovani'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Leader") or reward.startswith("leader"):
        embed = discord.Embed(title=bot.locale['leaders'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "Stardust":
        embed = discord.Embed(title=bot.locale['quests'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward.startswith("Route") or reward.startswith("route"):
        embed = discord.Embed(title=bot.locale['routes'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "stardust":
        embed = discord.Embed(title=bot.locale['quests'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "Kecleon":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "kecleon":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "keckleon":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "Keckleon":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "Coins":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    elif reward == "coins":
        embed = discord.Embed(title=bot.locale['eventstop'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    else:
        embed = discord.Embed(title=bot.locale['quests'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    message = await ctx.send(embed=embed)
    
    items = list()
    mons = list()
    item_found = False
    for item_id in bot.items:
        if area[1] == "Unknown Area":
            footer_text = area[1]
            loading = f"{footer_text}"
            embed.description = bot.locale["no_area_found"]
            item_found = True
        elif bot.items[item_id]["name"].lower() == reward.lower():
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/item/{item_id}.png")
            embed.title = f"{bot.items[item_id]['name']} {bot.locale['quests']} - {area[1]}"
            items.append(int(item_id))
            item_found = True
            quests = await get_dataitem(area, item_id)
            quests2 = await get_alt_dataitem(area, item_id)
    if not item_found:
        mon = details(reward, bot.config['mon_icon_repo'], bot.config['language'])
        if reward.startswith("Mega") or reward.startswith("mega"):
            embed.title = f"{mon.name} {bot.locale['mega']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/mega_resource/{str(mon.id)}.png")
            quests = await get_datamega(area)
            quests2 = await get_alt_datamega(area)
        elif reward.startswith("Showcase") or reward.startswith("showcase"):
            embed.title = f"{mon.name} {bot.locale['showcase']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_datashow(area)
        elif reward.startswith("station") or reward.startswith("Power") or reward.startswith("Station") or reward.startswith("power"):
            embed.title = f"{bot.locale['station']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_stations(area)
        elif reward.startswith("Lure") or reward.startswith("lure"):
            embed.title = f"{bot.locale['active_lures']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokestop/501.png")
            quests = await get_lures(area)
        elif reward.startswith("Route") or reward.startswith("route"):
            embed.title = f"{bot.locale['routes']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/route-start.png")
            quests = await get_dataroute(area)
        elif reward.startswith("Giovan") or reward.startswith("giovan"):
            embed.title = f"{bot.locale['giovani']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/44.png")
            quests = await get_datagiovani(area)
        elif reward.startswith("Sierra") or reward.startswith("sierra"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/43.png")
            quests = await get_dataleaders(area, 43)
        elif reward.startswith("Arlo") or reward.startswith("arlo"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/42.png")
            quests = await get_dataleaders(area, 42)
        elif reward.startswith("Cliff") or reward.startswith("cliff"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/41.png")
            quests = await get_dataleaders(area, 41)
        elif mon.name == "Kecleon":
            embed.title = f"{mon.name} {bot.locale['eventstop']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png")
            quests = await get_datak(area)
        elif mon.name == "Coins":
            embed.title = f"{mon.name} {bot.locale['eventstop']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/event_coin.png")
            quests = await get_datacoin(area)
        elif mon.name == "Stardust":
            embed.title = f"{mon.name} {bot.locale['quests']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/stardust/0.png")
            quests = await get_datastar(area)
            quests2 = await get_alt_datastar(area)
        else:
            embed.title = f"{mon.name} {bot.locale['quests']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png")
            quests = await get_data(area, mon.id)
            quests2 = await get_alt_data(area, mon.id)
        mons.append(mon.id)
    
    length = 0
    reward_mons = list()
    reward_items = list()
    lat_list = list()
    lon_list = list()

    embed.description = text
    if not item_found and mon.name == "Kecleon":
        for lat, lon, stop_name, stop_id, expiration in quests:
            tstamp1 = datetime.fromtimestamp(expiration)
            tstamp2 = datetime.now()
            td = tstamp1 - tstamp2
            left = int(round(td.total_seconds() / 60))
            found_rewards = True
            mon_id = 352
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png"
    
            if found_rewards:
                if len(stop_name) >= 26:
                    stop_name = stop_name[0:25]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name}-**{left} Min**]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f"and more..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif not item_found and mon.name == "Coins":
        for lat, lon, stop_name, stop_id, expiration in quests:
            end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
            found_rewards = True
            mon_id = 99999
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/event_coin.png"
    
            if found_rewards:
                if len(stop_name)+len(end) >= 26:
                    stop_name = stop_name[0:25]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name} **{end}**]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f"and more..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif not item_found and mon.name == "Stardust":
        for quest_reward_amount, quest_text, lat, lon, stop_name, stop_id in quests:
            found_rewards = True
            amount = quest_reward_amount
            mon_id = 99998
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"s{amount}"
            emote_img = f"{bot.config['mon_icon_repo']}reward/stardust/0.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name} **{amount}**]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f"and more..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
        for alternative_quest_reward_amount, alternative_quest_text, lat, lon, stop_name, stop_id in quests2:
            found_rewards = True
            amount = alternative_quest_reward_amount
            mon_id = 99998
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"s{amount}"
            emote_img = f"{bot.config['mon_icon_repo']}reward/stardust/0.png"
            if found_rewards:
                if len(stop_name) >= 22:
                    stop_name = stop_name[0:21]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                entry = f"[{stop_name} **{amount}-NO AR**]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f"lots more..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("Showcase") or reward.startswith("showcase"):
        for lat, lon, stop_name, stop_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99996
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/showcase.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        theend = f" lots more ..."
                        text = text + theend
                        break
                else:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        text = text + entry
                        length = length + len(entry)
    elif reward.startswith("station") or reward.startswith("Power") or reward.startswith("Station") or reward.startswith("power"):
        for lat, lon, stop_name, expiration in quests:
            tstamp1 = datetime.fromtimestamp(expiration)
            tstamp2 = datetime.now()
            td = tstamp1 - tstamp2
            left = int(round(td.total_seconds() / 8640))
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99996
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/showcase.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{left}**]({map_url})\n"
                else:
                    entry = f"[{stop_name} **{left}** Days Left]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f" lots more ..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("grunt") or reward.startswith("giovan"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99944
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/44.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f" lots more ..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("Sierra") or reward.startswith("sierra"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99943
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/43.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f" lots more ..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("Arlo") or reward.startswith("arlo"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99942
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/42.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f" lots more ..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("Cliff") or reward.startswith("cliff"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99941
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/41.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    theend = f" lots more ..."
                    text = text + theend
                    break
                else:
                    text = text + entry
                    length = length + len(entry)
    elif reward.startswith("Lure") or reward.startswith("lure"):
        for lure_expire_timestamp, lure_id, lat, lon, stop_name in quests:
            tstamp1 = datetime.fromtimestamp(lure_expire_timestamp)
            tstamp2 = datetime.now()
            td = tstamp1 - tstamp2
            left = int(round(td.total_seconds() / 60))
            found_rewards = True
            shiny = False
            mon_id = 0
            item_id = 0
            reward_items = 99993
            reward_mons.append([mon_id, lat, lon, lure_id])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}pokestop/501.png"
            if lure_id == 501:
                luretype= "Normal"
            elif lure_id == 502:
                luretype= "Glacial"
            elif lure_id == 503:
                luretype= "Mossy"
            elif lure_id == 504:
                luretype= "Magnetic"
            elif lure_id == 505:
                luretype= "Rainy"
            elif lure_id == 506:
                luretype= "Gold"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{luretype}**]({map_url})\n"
                elif shiny:
                    entry = f"[{stop_name} **SHINY**]({map_url})\n"
                    embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png")
                    embed.title = f"{mon.name} Quests SHINY DETECTED!! - {area[1]}"
                else:
                    entry = f"[{stop_name} - {luretype} - {left} Min]({map_url})\n"
                if length + len(entry) >= 2400:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        theend = f" lots more ..."
                        text = text + theend
                        break
                else:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        text = text + entry
                        length = length + len(entry)
    elif reward.startswith("Route") or reward.startswith("route"):
        for distance, lat, lon, stop_name, stop_id in quests:
            found_rewards = True
            shiny = False
            mon_id = 0
            item_id = 0
            reward_items = 99994
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/route-start.png"
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{distance}M**]({map_url})\n"
                else:
                    entry = f"[{stop_name} **{distance}M**]({map_url})\n"
                if length + len(entry) >= 2400:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        theend = f" lots more ..."
                        text = text + theend
                        break
                else:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        text = text + entry
                        length = length + len(entry)
    else:
        for quest_json, quest_text, lat, lon, stop_name, stop_id in quests:
            quest_json = json.loads(quest_json)
            found_rewards = True
            shiny = False
            mon_id = 0
            item_id = 0
            if 'pokemon_id' in quest_json[0]["info"]:
                    mon_id = quest_json[0]["info"]["pokemon_id"]
            if 'item_id' in quest_json[0]["info"]:
                    item_id = quest_json[0]["info"]["item_id"]
                    amount = quest_json[0]["info"]["amount"]
            if 'shiny' in quest_json[0]["info"]:
                    shiny = quest_json[0]["info"]["shiny"]
            if item_id in items:
                reward_items.append([item_id, lat, lon])
                emote_name = f"i{item_id}"
                emote_img = f"{bot.config['mon_icon_repo']}reward/item/{item_id}.png"
            elif mon_id in mons and reward.startswith("Mega") or mon_id in mons and reward.startswith("mega"):
                reward_items = 99997
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"e{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}reward/mega_resource/{str(mon.id)}.png"
            elif mon_id in mons and shiny:
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"m{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png"
            elif mon_id in mons:
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"m{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png"
            else:
                found_rewards = False
            if found_rewards:
                if len(stop_name) >= 31:
                    stop_name = stop_name[0:30]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}**]({map_url})\n"
                elif shiny:
                    entry = f"[{stop_name} **SHINY**]({map_url})\n"
                    embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png")
                    embed.title = f"{mon.name} Quests SHINY DETECTED!! - {area[1]}"
                else:
                    entry = f"[{stop_name}]({map_url})\n"
                if length + len(entry) >= 2400:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        theend = f" lots more ..."
                        text = text + theend
                        break
                else:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        text = text + entry
                        length = length + len(entry)
        for alternative_quest_json, alternative_quest_text, lat, lon, stop_name, stop_id in quests2:
            quest_json = json.loads(alternative_quest_json)
            found_alt_rewards = True
            shiny = False
            mon_id = 0
            item_id = 0
            if 'pokemon_id' in quest_json[0]["info"]:
                    mon_id = quest_json[0]["info"]["pokemon_id"]
            if 'item_id' in quest_json[0]["info"]:
                    item_id = quest_json[0]["info"]["item_id"]
                    amount = quest_json[0]["info"]["amount"]
            if 'shiny' in quest_json[0]["info"]:
                    shiny = quest_json[0]["info"]["shiny"]
            if item_id in items:
                reward_items.append([item_id, lat, lon])
                emote_name = f"i{item_id}"
                emote_img = f"{bot.config['mon_icon_repo']}reward/item/{item_id}.png"
            elif mon_id in mons and reward.startswith("Mega") or mon_id in mons and reward.startswith("mega"):
                reward_items = 99997
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"e{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}reward/mega_resource/{str(mon.id)}.png"
            elif mon_id in mons and shiny:
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"m{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png"
            elif mon_id in mons:
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"m{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png"
            else:
                found_alt_rewards = False
            if found_alt_rewards:
                if len(stop_name) >= 26:
                    stop_name = stop_name[0:25]
                lat_list.append(lat)
                lon_list.append(lon)

                if bot.config['use_map']:
                    map_url = bot.map_url.quest(lat, lon, stop_id)
                else:
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                if item_id in items:
                    entry = f"[{stop_name} **{amount}-NO AR**]({map_url})\n"
                elif shiny:
                    entry = f"[{stop_name} **SHINY-NO AR**]({map_url})\n"
                    embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png")
                    embed.title = f"{mon.name} Quests SHINY DETECTED!! - {area[1]}"
                else:
                    entry = f"[{stop_name} **NO AR**]({map_url})\n"
                if length + len(entry) >= 2400:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
                    else:
                        theend = f" lots more ..."
                        text = text + theend
                        break
                else:
                    if shiny:
                        text = entry + text
                        length = length + len(entry)
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
    
@bot.command(pass_context=True, aliases=bot.config['rocket_aliases'])
async def rocket(ctx, areaname = "", *, reward):
    if not isUser(ctx.author.roles, ctx.channel.id):
        print(f"@{ctx.author.name} tried to use !rocket but is no user")
        return
    footer_text = ""
    text = ""
    loading = bot.locale['loading_quests']

    area = get_area(areaname)
    if not area[1] == bot.locale['all']:
        footer_text = area[1]
        loading = f"{loading} • {footer_text}"

    print(f"@{ctx.author.name} requested {reward} Rocket Stops for area {area[1]}")

    if area[1] == "Unknown Area":
        embed = discord.Embed(title=bot.locale['no_area_found'], description=text)
    else:
        embed = discord.Embed(title=bot.locale['rocket'], description=text)
        embed.set_image(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
        embed.set_footer(text=loading, icon_url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif")
    message = await ctx.send(embed=embed)
    
    items = list()
    mons = list()
    item_found = False
    mon = details(reward, bot.config['mon_icon_repo'], bot.config['language'])
    embed.title = f"{mon.name} {bot.locale['rocket']} - {area[1]}"
    embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png")
    rocketq = await get_datarocketquery(area)
    mons.append(mon.id)
    
    length = 0
    reward_mons = list()
    reward_items = list()
    lat_list = list()
    lon_list = list()

    embed.description = text

    for rocket_json, rocket_text, lat, lon, stop_name, stop_id in rocketq:
        rocket_json = json.loads(rocket_json)
        found_rewards = True
        shiny = False
        mon_id = 0
        item_id = 0
        if 'pokemon_id' in rocket_json[0]["info"]:
                mon_id = rocket_json[0]["info"]["pokemon_id"]
        if 'shiny' in rocket_json[0]["info"]:
                shiny = rocket_json[0]["info"]["shiny"]
        elif mon_id in mons and shiny:
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png"
        elif mon_id in mons:
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png"
        else:
            found_rewards = False
        if found_rewards:
            if len(stop_name) >= 31:
                stop_name = stop_name[0:30]
            lat_list.append(lat)
            lon_list.append(lon)

            if bot.config['use_map']:
                map_url = bot.map_url.quest(lat, lon, stop_id)
            else:
                map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

            if item_id in items:
                entry = f"[{stop_name} **{amount}**]({map_url})\n"
            elif shiny:
                entry = f"[{stop_name} **SHINY**]({map_url})\n"
                embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png")
                embed.title = f"{mon.name} Rocket Reward SHINY DETECTED!?! - {area[1]}"
            else:
                entry = f"[{stop_name}]({map_url})\n"
            if length + len(entry) >= 2400:
                if shiny:
                    text = entry + text
                    length = length + len(entry)
                else:
                    theend = f" lots more ..."
                    text = text + theend
                    break
            else:
                if shiny:
                    text = entry + text
                    length = length + len(entry)
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