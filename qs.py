import discord
import json
import asyncio
import re
import aiomysql
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime, date
import matplotlib.pyplot as plt
import pyshorteners
from discord.ext import commands
from util.mondetails import details
import util.config
import util.maps
from util.db import (
    get_data, get_lures, get_stations, get_datarocket, get_datarocketquery,
    get_datagiovani, get_dataleaders, get_alt_data, get_dataitem, get_alt_dataitem,
    get_datamega, get_alt_datamega, get_dataroute, get_datastar, get_alt_datastar,
    get_datak, get_datashow, get_datacoin
)

extensions = ["qform"]

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

# Load and parse api.json at startup
with open("data/api.json", encoding="utf-8") as f:
    api_data = f.read()

# Extract all rows from the HTML table in api.json
rows = re.findall(r"<tr>(.*?)</tr>", api_data, re.DOTALL)
poke_lookup = []
for row in rows:
    cols = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
    if len(cols) >= 7:  # <-- was 6
        name = re.sub(r"<.*?>", "", cols[0]).strip()
        pokedex = re.sub(r"<.*?>", "", cols[1]).strip()
        form = re.sub(r"<.*?>", "", cols[2]).strip()
        costume = re.sub(r"<.*?>", "", cols[3]).strip()
        mega = re.sub(r"<.*?>", "", cols[4]).strip()
        # filecode = re.sub(r"<.*?>", "", cols[5]).strip()  # Full UICON (old)
        filecode = re.sub(r"<.*?>", "", cols[6]).strip()    # Used UICON (new)
        poke_lookup.append({
            "name": name,
            "pokedex": pokedex,
            "form": form,
            "costume": costume,
            "mega": mega,
            "filecode": filecode
        })

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

# --- Helper Functions for DRY code ---

def make_loading_embed(title, text, loading):
    loading_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
    embed = discord.Embed(title=title, description=text)
    embed.set_image(url=loading_img)
    embed.set_footer(text=loading, icon_url=loading_img)
    return embed

def get_map_url(lat, lon, stop_id=None):
    if bot.config['use_map']:
        if stop_id is not None:
            return bot.map_url.quest(lat, lon, stop_id)
        else:
            return bot.map_url.quest(lat, lon)
    else:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def truncate_stop_name(stop_name, max_len):
    return stop_name[:max_len] if len(stop_name) > max_len else stop_name

def make_entry(stop_name, extra, map_url):
    if extra:
        return f"[{stop_name} **{extra}**]({map_url})\n"
    else:
        return f"[{stop_name}]({map_url})\n"

def set_shiny_embed(embed, mon, area):
    embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}_s.png")
    embed.title = f"{mon.name} Quests SHINY DETECTED!! - {area[1]}"

def add_quest_entry(
    stop_name, lat, lon, stop_id, item_id, items, amount, shiny, length, text, 
    max_len=31, max_total=2400, extra=None, entry_suffix="", map_url_override=None
):
    stop_name = truncate_stop_name(stop_name, max_len)
    map_url = map_url_override if map_url_override else get_map_url(lat, lon, stop_id)
    if item_id in items and amount is not None:
        entry = f"[{stop_name} **{amount}{entry_suffix}**]({map_url})\n"
    elif extra:
        entry = f"[{stop_name} **{extra}{entry_suffix}**]({map_url})\n"
    else:
        entry = f"[{stop_name}{entry_suffix}]({map_url})\n"
    if length + len(entry) >= max_total:
        theend = " lots more ..."
        if shiny:
            text = entry + text
        else:
            text = text + theend
        length += len(entry)
        return text, length, True  # True = break/stop
    else:
        if shiny:
            text = entry + text
        else:
            text = text + entry
        length += len(entry)
        return text, length, False

@bot.command(pass_context=True, aliases=bot.config['quest_aliases'])
async def quest(ctx, areaname="", *, args=""):
    parts = args.strip().split()
    reward = parts[0] if parts else ""
    formcostume = parts[1] if len(parts) > 1 else None

    footer_text = ""
    text = ""
    loading = bot.locale['loading_quests']

    area = get_area(areaname)
    if not area[1] == bot.locale['all']:
        footer_text = area[1]
        loading = f"{loading} • {footer_text}"

    print(f"@{ctx.author.name} requested {reward} quests for area {area[1]}")

    # Use helper for loading embed
    if area[1] == "Unknown Area":
        embed = make_loading_embed(bot.locale['no_area_found'], text, loading)
    elif reward.startswith("Mega") or reward.startswith("mega"):
        embed = make_loading_embed(bot.locale['mega'], text, loading)
    elif reward.startswith("Lure") or reward.startswith("lure"):
        embed = make_loading_embed(bot.locale['active_lures'], text, loading)
    elif reward.startswith("Station") or reward.startswith("Power") or reward.startswith("station") or reward.startswith("power"):
        embed = make_loading_embed(bot.locale['station'], text, loading)
    elif reward.startswith("Showcase") or reward.startswith("showcase"):
        embed = make_loading_embed(bot.locale['showcase'], text, loading)
    elif reward.startswith("Giovan") or reward.startswith("giovan"):
        embed = make_loading_embed(bot.locale['giovani'], text, loading)
    elif reward.startswith("Leader") or reward.startswith("leader"):
        embed = make_loading_embed(bot.locale['leaders'], text, loading)
    elif reward == "Stardust" or reward == "stardust":
        embed = make_loading_embed(bot.locale['quests'], text, loading)
    elif reward.startswith("Route") or reward.startswith("route"):
        embed = make_loading_embed(bot.locale['routes'], text, loading)
    elif reward.lower() in ["kecleon", "keckleon"]:
        embed = make_loading_embed(bot.locale['eventstop'], text, loading)
    elif reward.lower() == "coins":
        embed = make_loading_embed(bot.locale['eventstop'], text, loading)
    else:
        embed = make_loading_embed(bot.locale['quests'], text, loading)
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
            quests = await get_dataitem(bot.config, area, item_id)
            quests2 = await get_alt_dataitem(bot.config, area, item_id)
    if not item_found:
        mon = details(reward, bot.config['mon_icon_repo'], bot.config['language'])
        if reward.startswith("Mega") or reward.startswith("mega"):
            embed.title = f"{mon.name} {bot.locale['mega']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/mega_resource/{str(mon.id)}.png")
            quests = await get_datamega(bot.config, area)
            quests2 = await get_alt_datamega(bot.config, area)
        elif reward.startswith("Showcase") or reward.startswith("showcase"):
            embed.title = f"{mon.name} {bot.locale['showcase']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_datashow(bot.config, area)
        elif reward.startswith("station") or reward.startswith("Power") or reward.startswith("Station") or reward.startswith("power"):
            embed.title = f"{bot.locale['station']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_stations(bot.config, area)
        elif reward.startswith("Lure") or reward.startswith("lure"):
            embed.title = f"{bot.locale['active_lures']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokestop/501.png")
            quests = await get_lures(bot.config, area)
        elif reward.startswith("Route") or reward.startswith("route"):
            embed.title = f"{bot.locale['routes']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/route-start.png")
            quests = await get_dataroute(bot.config, area)
        elif reward.startswith("Giovan") or reward.startswith("giovan"):
            embed.title = f"{bot.locale['giovani']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/44.png")
            quests = await get_datagiovani(bot.config, area)
        elif reward.startswith("Sierra") or reward.startswith("sierra"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/43.png")
            quests = await get_dataleaders(bot.config, area, 43)
        elif reward.startswith("Arlo") or reward.startswith("arlo"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/42.png")
            quests = await get_dataleaders(bot.config, area, 42)
        elif reward.startswith("Cliff") or reward.startswith("cliff"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/41.png")
            quests = await get_dataleaders(bot.config, area, 41)
        elif mon.name == "Kecleon":
            embed.title = f"{mon.name} {bot.locale['eventstop']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png")
            quests = await get_datak(bot.config, area)
        elif mon.name == "Coins":
            embed.title = f"{mon.name} {bot.locale['eventstop']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/event_coin.png")
            quests = await get_datacoin(bot.config, area)
        elif mon.name == "Stardust":
            embed.title = f"{mon.name} {bot.locale['quests']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/stardust/0.png")
            quests = await get_datastar(bot.config, area)
            quests2 = await get_alt_datastar(bot.config, area)
        else:
            embed.title = f"{mon.name} {bot.locale['quests']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokemon/{str(mon.id)}.png")
            quests = await get_data(bot.config, area, mon.id)
            quests2 = await get_alt_data(bot.config, area, mon.id)
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
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, 0, items, None, False, length, text,
                max_len=26, extra=f"{left} Min"
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif not item_found and mon.name == "Coins":
        for lat, lon, stop_name, stop_id, expiration in quests:
            end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
            found_rewards = True
            mon_id = 99999
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"m{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/event_coin.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, 0, items, None, False, length, text,
                max_len=26, extra=end
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif not item_found and mon.name == "Stardust":
        for quest_reward_amount, quest_text, lat, lon, stop_name, stop_id in quests:
            found_rewards = True
            amount = quest_reward_amount
            mon_id = 99998
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"s{amount}"
            emote_img = f"{bot.config['mon_icon_repo']}reward/stardust/0.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, 0, items, amount, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
        for alternative_quest_reward_amount, alternative_quest_text, lat, lon, stop_name, stop_id in quests2:
            found_rewards = True
            amount = alternative_quest_reward_amount
            mon_id = 99998
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"s{amount}"
            emote_img = f"{bot.config['mon_icon_repo']}reward/stardust/0.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, 0, items, amount, False, length, text,
                max_len=22, entry_suffix="-NO AR"
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif reward.startswith("Showcase") or reward.startswith("showcase"):
        for lat, lon, stop_name, stop_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99996
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}misc/showcase.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
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
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31, extra=f"{left} Days Left"
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif reward.startswith("grunt") or reward.startswith("giovan"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99944
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/44.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif reward.startswith("Sierra") or reward.startswith("sierra"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99943
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/43.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif reward.startswith("Arlo") or reward.startswith("arlo"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99942
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/42.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
    elif reward.startswith("Cliff") or reward.startswith("cliff"):
        for lat, lon, stop_name, stop_id, expire, char_id in quests:
            found_rewards = True
            mon_id = 0
            item_id = 0
            reward_items = 99941
            reward_mons.append([mon_id, lat, lon])
            emote_name = f"e{mon_id}"
            emote_img = f"{bot.config['mon_icon_repo']}invasion/41.png"
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, item_id, items, None, False, length, text,
                max_len=31
            )
            lat_list.append(lat)
            lon_list.append(lon)
            if stop:
                break
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
    if length > 0:
        placeholder_img = "https://mir-s3-cdn-cf.behance.net/project_modules/disp/c3c4d331234507.564a1d23db8f9.gif"
        embed.set_image(url=placeholder_img)
        embed.set_footer(text=footer_text)
        message = await ctx.send(embed=embed)

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

        # Replace the placeholder with the real image
        embed.set_image(url=image)
        await message.edit(embed=embed)
    else:
        embed.description = bot.locale["no_quests_found"]
        embed.set_footer(text=footer_text)
        embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
        await ctx.send(embed=embed)
    
@bot.command(pass_context=True)
async def costume(ctx, *, args):
    """
    Usage: !costume <pokemon name> [costume] [shiny]
    """
    try:
        parts = args.strip().split()
        if not parts:
            await ctx.send("Usage: !costume <pokemon name> [costume] [shiny]")
            return
        shiny = False
        costume_query = None
        mon_name = None

        # Check for shiny at the end
        if parts and parts[-1].lower() == "shiny":
            shiny = True
            parts = parts[:-1]

        if len(parts) > 1:
            mon_name = parts[0]
            costume_query = " ".join(parts[1:])
        else:
            mon_name = parts[0]
            costume_query = None

        mon = details(mon_name, bot.config['mon_icon_repo'], bot.config['language'])
        if not hasattr(mon, "id") or not mon.id:
            await ctx.send(f"Could not find Pokémon: {mon_name}")
            return

        costume_id = 0
        costume_name = None

        # Try full costume string (e.g. pikachu_libre)
        if costume_query:
            full_costume = f"{mon_name}_{costume_query.replace(' ', '_')}"
            costume_id, costume_name = lookup_costume_id_for_mon(mon.id, full_costume, poke_lookup)
            if costume_id == 0 or costume_id is None:
                # Try just the costume part (e.g. libre)
                costume_id, costume_name = lookup_costume_id_for_mon(mon.id, costume_query, poke_lookup)
            if costume_id == 0 or costume_id is None:
                costume_id, costume_name = 0, None
        else:
            costume_id, costume_name = 0, None

        filecode = get_api_filecode(mon.id, poke_lookup, costume_id=costume_id, shiny=shiny)
        if not filecode:
            await ctx.send("Could not find that Pokémon or costume (API crossref failed).")
            return

        url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"
        print(f"[COSTUME URL] {url}")
        response = requests.get(url)
        if response.status_code != 200:
            await ctx.send("Could not find that Pokémon or costume.")
            return
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        scale_factor = 3
        new_icon_size = (img.width * scale_factor, img.height * scale_factor)
        img = img.resize(new_icon_size, Image.LANCZOS)
        new_size = (max(512, img.width), max(512, img.height))
        new_img = Image.new("RGBA", new_size, (255, 255, 255, 0))
        offset = ((new_size[0] - img.width) // 2, (new_size[1] - img.height) // 2)
        new_img.paste(img, offset, img)
        buffer = BytesIO()
        new_img.save(buffer, format="PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename="icon.png"))
    except Exception as e:
        print(f"[COSTUME ERROR] {e}")
        await ctx.send("Could not find that Pokémon or costume.")

@bot.command(pass_context=True)
async def form(ctx, *, args):
    try:
        parts = args.strip().split()
        if not parts:
            await ctx.send("Usage: !form <pokemon name> [form] [mega] [shiny]")
            return

        mon_name, form_query, shiny, mega = parse_mon_args(parts)
        mon = details(mon_name, bot.config['mon_icon_repo'], bot.config['language'])
        if not hasattr(mon, "id") or not mon.id:
            await ctx.send(f"Could not find Pokémon: {mon_name}")
            return

        form_id = 0
        if form_query:
            full_form = f"{mon_name}_{form_query.replace(' ', '_')}"
            form_id, _ = lookup_form_id_for_mon(mon.id, full_form, poke_lookup)
            if form_id == 0 or form_id is None:
                form_id, _ = lookup_form_id_for_mon(mon.id, form_query, poke_lookup)
        mega_id = 1 if mega else None

        filecode = get_api_filecode(mon.id, poke_lookup, form_id=form_id, shiny=shiny, mega_id=mega_id)
        if not filecode:
            await ctx.send("Could not find that Pokémon or form (API crossref failed).")
            return

        url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"
        print(f"[FORM URL] {url}")
        response = requests.get(url)
        if response.status_code != 200:
            await ctx.send("Could not find that Pokémon or form.")
            return
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        scale_factor = 3
        new_icon_size = (img.width * scale_factor, img.height * scale_factor)
        img = img.resize(new_icon_size, Image.LANCZOS)
        new_size = (max(512, img.width), max(512, img.height))
        new_img = Image.new("RGBA", new_size, (255, 255, 255, 0))
        offset = ((new_size[0] - img.width) // 2, (new_size[1] - img.height) // 2)
        new_img.paste(img, offset, img)
        buffer = BytesIO()
        new_img.save(buffer, format="PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename="icon.png"))
    except Exception as e:
        print(f"[FORM ERROR] {e}")
        await ctx.send("Could not find that Pokémon or form.")

@bot.command(pass_context=True)
async def custom(ctx, *, args):
    """
    Usage: !custom <pokemon name> [custom_id] [shiny]
    Example: !custom pikachu 001 shiny
    If no custom_id is given, returns the default icon.
    Add 'shiny' as the last argument to get the shiny version.
    This uses the format: pokemon/{dex}_{custom_id}.png (no _f or _c)
    """
    try:
        parts = args.strip().split()
        if not parts:
            await ctx.send("Usage: !custom <pokemon name> [custom_id] [shiny]")
            return
        shiny = False
        if len(parts) > 2 and parts[-1].lower() == "shiny":
            shiny = True
            custom_id = parts[-2]
            mon_name = " ".join(parts[:-2])
        elif len(parts) > 1 and parts[-1].lower() == "shiny":
            shiny = True
            custom_id = None
            mon_name = " ".join(parts[:-1])
        elif len(parts) > 1:
            custom_id = parts[-1]
            mon_name = " ".join(parts[:-1])
        else:
            mon_name = parts[0]
            custom_id = None

        try:
            mon = details(mon_name, bot.config['mon_icon_repo'], bot.config['language'])
            if not hasattr(mon, "id") or not mon.id:
                print(f"[CUSTOM ERROR] Could not resolve Pokémon name '{mon_name}'")
                await ctx.send(f"Could not find Pokémon: {mon_name}")
                return
        except Exception as e:
            print(f"[CUSTOM ERROR] Exception during details lookup: {e}")
            await ctx.send(f"Could not find Pokémon: {mon_name}")
            return

        icon_repo = bot.config.get('form_icon_repo', bot.config['mon_icon_repo'])
        if custom_id:
            url = f"{icon_repo}pokemon/{str(mon.id).zfill(1)}_{custom_id}"
        else:
            url = f"{icon_repo}pokemon/{str(mon.id).zfill(1)}"
        if shiny:
            url += "_s"
        url += ".png"
        print(f"[CUSTOM URL] {url}")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"[CUSTOM ERROR] HTTP {response.status_code} for URL: {url}")
            await ctx.send("Could not find that Pokémon or custom icon.")
            return
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        scale_factor = 3
        new_icon_size = (img.width * scale_factor, img.height * scale_factor)
        img = img.resize(new_icon_size, Image.LANCZOS)
        new_size = (max(512, img.width), max(512, img.height))
        new_img = Image.new("RGBA", new_size, (255, 255, 255, 0))
        offset = ((new_size[0] - img.width) // 2, (new_size[1] - img.height) // 2)
        new_img.paste(img, offset, img)
        buffer = BytesIO()
        new_img.save(buffer, format="PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, filename="icon.png"))
    except Exception as e:
        print(f"[CUSTOM ERROR] {e}")
        await ctx.send("Could not find that Pokémon or custom icon.")

@bot.event
async def on_ready():
    print("Connected to Discord. Ready to take commands.")

    if bot.config['use_static']:
        trash_channel = await bot.fetch_channel(bot.config['host_channel'])
        bot.static_map = util.maps.static_map(config['static_provider'], config['static_key'], trash_channel, bot.config['mon_icon_repo'])

with open ("data/forms/formsen.json", encoding="utf-8") as f:
    forms_data = json.load(f)

def fuzzy_find_pokemon(query, poke_lookup):
    """Fuzzy find a Pokémon by name."""
    from difflib import get_close_matches
    query = query.lower()
    names = [p["name"].lower() for p in poke_lookup]
    matches = get_close_matches(query, names, n=5, cutoff=0.6)
    if matches:
        return [p for p in poke_lookup if p["name"].lower() in matches]
    return []

def fuzzy_find_variant(pokemon, query, variant_type, poke_lookup):
    """Fuzzy find a variant (form/costume) for a given Pokémon."""
    from difflib import get_close_matches
    query = query.lower()
    if variant_type == "form":
        variants = [f["form"] for f in poke_lookup if f["name"].lower() == pokemon.lower()]
    elif variant_type == "costume":
        variants = [c["costume"] for c in poke_lookup if c["name"].lower() == pokemon.lower()]
    else:
        return None

    matches = get_close_matches(query, variants, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None

def fuzzy_lookup_form_id(query, forms_data):
    # Find best match for form name, return (form_id, form_name)
    form_keys = [k for k in forms_data if k.startswith("form_")]
    form_names = [forms_data[k].lower() for k in form_keys]
    match = difflib.get_close_matches(query.lower(), form_names, n=1, cutoff=0.6)
    if match:
        for k in form_keys:
            if forms_data[k].lower() == match[0]:
                return int(k.split("_")[1]), forms_data[k]
    return None, None

def fuzzy_lookup_costume_id(query, forms_data):
    # Find best match for costume name, return (costume_id, costume_name)
    costume_keys = [k for k in forms_data if k.startswith("costume_")]
    costume_names = [forms_data[k].lower() for k in costume_keys]
    match = difflib.get_close_matches(query.lower(), costume_names, n=1, cutoff=0.6)
    if match:
        for k in costume_keys:
            if forms_data[k].lower() == match[0]:
                return int(k.split("_")[1]), forms_data[k]
    return None, None

def get_api_filecode(pokedex_id, poke_lookup, form_id=None, costume_id=None, shiny=False, mega_id=None):
    print(f"[API FILECODE] Looking up: pokedex_id={pokedex_id}, form_id={form_id}, costume_id={costume_id}, shiny={shiny}, mega_id={mega_id}")
    candidates = []
    for entry in poke_lookup:
        if f"({pokedex_id})" not in entry["pokedex"]:
            continue
        if form_id and f"({form_id})" not in entry["form"]:
            continue
        if costume_id and f"({costume_id})" not in entry["costume"]:
            continue
        if mega_id is not None and str(mega_id) != entry.get("mega", "0"):
            continue
        filecode = entry["filecode"]
        if not filecode:
            continue
        candidates.append(filecode)
    # Prefer shiny if available
    if shiny:
        shiny_candidates = [c for c in candidates if c.endswith("_s")]
        if shiny_candidates:
            print(f"[API FILECODE] Returning shiny filecode: {shiny_candidates[0]}")
            return shiny_candidates[0]
    if candidates:
        print(f"[API FILECODE] Returning filecode: {candidates[0]}")
        return candidates[0]
    print(f"[API FILECODE] No candidates found for pokedex_id={pokedex_id}, form_id={form_id}, costume_id={costume_id}, shiny={shiny}, mega_id={mega_id}")
    return None

def lookup_form_id_for_mon(mon_id, form_query, poke_lookup):
    """Find the correct form_id for a given Pokémon ID and form name (case-insensitive, fuzzy)."""
    candidates = [entry for entry in poke_lookup if f"({mon_id})" in entry["pokedex"]]
    form_map = {}
    for entry in candidates:
        form_field = entry["form"]
        if form_field:
            form_base = form_field.split(" (")[0].strip().lower()
            form_map[form_base] = entry
            if "_" in form_base:
                _, form_only = form_base.split("_", 1)
                form_map[form_only] = entry
    print(f"[LOOKUP DEBUG] Candidates for mon_id={mon_id}: {list(form_map.keys())}")
    form_query_clean = form_query.strip().lower() if form_query else ""
    if form_query_clean in form_map:
        entry = form_map[form_query_clean]
        m = re.search(r"\((\d+)\)", entry["form"])
        if m:
            return int(m.group(1)), entry["form"]
    import difflib
    match = difflib.get_close_matches(form_query_clean, form_map.keys(), n=1, cutoff=0.7)
    if match:
        entry = form_map[match[0]]
        m = re.search(r"\((\d+)\)", entry["form"])
        if m:
            return int(m.group(1)), entry["form"]
    return None
bot.poke_lookup = poke_lookup
bot.get_area = get_area