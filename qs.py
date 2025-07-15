import discord
import json
import asyncio
import re
import aiomysql
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime, date
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
from util.pokemon_lookup import (
    lookup_form_id_for_mon,
    lookup_costume_id_for_mon,
    fuzzy_find_pokemon,
    get_api_filecode,
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

with open("config/geofence.json", encoding="utf-8") as f:
    bot.geofences = json.load(f)
    
with open("config/emotes.json", encoding="utf-8") as f:
    bot.custom_emotes = json.load(f)

with open("data/api.json", encoding="utf-8") as f:
    api_data = f.read()

rows = re.findall(r"<tr>(.*?)</tr>", api_data, re.DOTALL)
poke_lookup = []
for row in rows:
    cols = re.findall(r"<td>(.*?)</td>", row, re.DOTALL)
    if len(cols) >= 7:
        name = re.sub(r"<.*?>", "", cols[0]).strip()
        pokedex = re.sub(r"<.*?>", "", cols[1]).strip()
        form = re.sub(r"<.*?>", "", cols[2]).strip()
        costume = re.sub(r"<.*?>", "", cols[3]).strip()
        mega = re.sub(r"<.*?>", "", cols[4]).strip()
        filecode = re.sub(r"<.*?>", "", cols[6]).strip()
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

bot.get_area = get_area

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
        return text, length, True
    else:
        if shiny:
            text = entry + text
        else:
            text = text + entry
        length += len(entry)
        return text, length, False

def normalize_item_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

@bot.command(pass_context=True, aliases=bot.config['quest_aliases'])
async def quest(ctx, areaname="", *, args=""):
    parts = args.strip().split()
    if not parts:
        await ctx.send("Usage: !q <area> <reward> [pokemon]")
        return

    if parts[0].lower() == "mega" and len(parts) > 1:
        reward = "mega"
        mon_name = " ".join(parts[1:])
    else:
        reward = parts[0]
        mon_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    footer_text = ""
    text = ""
    loading = bot.locale['loading_quests']

    embed = discord.Embed()

    area = get_area(areaname)
    if not area[1] == bot.locale['all']:
        footer_text = area[1]
        loading = f"{loading} • {footer_text}"

    print(f"@{ctx.author.name} requested {reward} {mon_name} quests for area {area[1]}")

    items = list()
    mons = list()
    item_found = False
    user_item = normalize_item_name(reward)
    for item_id, item in bot.items.items():
        item_name_norm = normalize_item_name(item["name"])
        if area[1] == bot.locale['unknown']:
            footer_text = area[1]
            loading = f"{footer_text}"
            embed.description = bot.locale["no_area_found"]
            item_found = True
            break
        elif item_name_norm == user_item:
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/item/{item_id}.png")
            embed.title = f"{item['name']} {bot.locale['quests']} - {area[1]}"
            items.append(int(item_id))
            item_found = True
            quests = await get_dataitem(bot.config, area, item_id)
            quests2 = await get_alt_dataitem(bot.config, area, item_id)
            break

    if item_found:
        length = 0
        reward_items = []
        lat_list = []
        lon_list = []
        text = ""
        for quest in quests:
            quest_json, quest_template, lat, lon, stop_name, stop_id = quest
            try:
                quest_data = json.loads(quest_json)
                info = quest_data[0]["info"]
                quest_item_id = info.get("item_id")
                amount = info.get("amount")
            except Exception:
                continue
            if quest_item_id == int(item_id):
                reward_items.append([quest_item_id, lat, lon])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, quest_item_id, [int(item_id)], amount, False, length, text,
                    max_len=31
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
        for quest in quests2:
            quest_json, quest_template, lat, lon, stop_name, stop_id = quest
            try:
                quest_data = json.loads(quest_json)
                info = quest_data[0]["info"]
                quest_item_id = info.get("item_id")
                amount = info.get("amount")
            except Exception:
                continue
            if quest_item_id == int(item_id):
                reward_items.append([quest_item_id, lat, lon])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, quest_item_id, [int(item_id)], amount, False, length, text,
                    max_len=22, entry_suffix="-NO AR"
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
        embed.description = text or bot.locale["no_quests_found"]
        embed.set_footer(text=footer_text)
        embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
        message = await ctx.send(embed=embed)
        if bot.config['use_static'] and reward_items:
            if bot.config['static_provider'] == "mapbox":
                image = await bot.static_map.quest(lat_list, lon_list, reward_items, [], bot.custom_emotes)
            elif bot.config['static_provider'] == "tileserver":
                image = await bot.static_map.quest(lat_list, lon_list, reward_items, [], bot.custom_emotes)
            embed.set_image(url=image)
            await message.edit(embed=embed)
        return

    if not item_found:
        mon_query = mon_name if mon_name else reward
        mon = details(mon_query, bot.config['mon_icon_repo'], bot.config['language'])
        reward_lower = reward.lower()

        def add_lat_lon(lat, lon):
            lat_list.append(lat)
            lon_list.append(lon)

        if reward_lower.startswith("mega"):
            embed.title = f"{mon.name} {bot.locale['mega']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}reward/mega_resource/{str(mon.id)}.png")
            quests = await get_datamega(bot.config, area)
            quests2 = await get_alt_datamega(bot.config, area)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for quest in quests:
                quest_json, quest_template, lat, lon, stop_name, stop_id = quest
                try:
                    quest_data = json.loads(quest_json)
                    info = quest_data[0]["info"]
                    quest_pokemon_id = info.get("pokemon_id")
                    amount = info.get("amount")
                except Exception:
                    continue
                if quest_pokemon_id == mon.id:
                    reward_mons.append([quest_pokemon_id, lat, lon])
                    text, length, stop = add_quest_entry(
                        stop_name, lat, lon, stop_id, quest_pokemon_id, [mon.id], amount, False, length, text,
                        max_len=31
                    )
                    lat_list.append(lat)
                    lon_list.append(lon)
                    if stop:
                        break
            for quest in quests2:
                quest_json, quest_template, lat, lon, stop_name, stop_id = quest
                try:
                    quest_data = json.loads(quest_json)
                    info = quest_data[0]["info"]
                    quest_pokemon_id = info.get("pokemon_id")
                    amount = info.get("amount")
                except Exception:
                    continue
                if quest_pokemon_id == mon.id:
                    reward_mons.append([quest_pokemon_id, lat, lon])
                    text, length, stop = add_quest_entry(
                        stop_name, lat, lon, stop_id, quest_pokemon_id, [mon.id], amount, False, length, text,
                        max_len=22, entry_suffix="-NO AR"
                    )
                    lat_list.append(lat)
                    lon_list.append(lon)
                    if stop:
                        break
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, [], reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, [], reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return
        elif reward_lower.startswith("showcase"):
            embed.title = f"{mon.name} {bot.locale['showcase']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_datashow(bot.config, area)
        elif reward_lower.startswith("station") or reward_lower.startswith("power"):
            embed.title = f"{bot.locale['station']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/showcase.png")
            quests = await get_stations(bot.config, area)
        elif reward_lower.startswith("lure"):
            embed.title = f"{bot.locale['active_lures']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}pokestop/501.png")
            quests = await get_lures(bot.config, area)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for lure_expire_timestamp, lure_id, lat, lon, stop_name in quests:
                tstamp1 = datetime.fromtimestamp(lure_expire_timestamp)
                tstamp2 = datetime.now()
                td = tstamp1 - tstamp2
                left = int(round(td.total_seconds() / 60))
                luretype = {
                    501: "Normal",
                    502: "Glacial",
                    503: "Mossy",
                    504: "Magnetic",
                    505: "Rainy",
                    506: "Golden"
                }.get(lure_id, f"Type {lure_id}")
                reward_mons.append([lure_id, lat, lon])
                entry = f"[{truncate_stop_name(stop_name, 31)} - {luretype} - {left} Min]({get_map_url(lat, lon)})\n"
                if length + len(entry) >= 2400:
                    text = text + " lots more ..."
                    break
                else:
                    text = text + entry
                    length += len(entry)
                lat_list.append(lat)
                lon_list.append(lon)
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            # Static map for lures
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, 99993, reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, 99993, reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return
        elif reward_lower.startswith("route"):
            embed.title = f"{bot.locale['routes']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}misc/route-start.png")
            quests = await get_dataroute(bot.config, area)
        elif reward_lower.startswith("giovan"):
            embed.title = f"{bot.locale['giovani']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/44.png")
            quests = await get_datagiovani(bot.config, area)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for lat, lon, stop_name, stop_id, expiration, character in quests:
                found_rewards = True
                mon_id = 99944
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"r{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}invasion/44.png"
                end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, 0, [], None, False, length, text,
                    max_len=26, extra=end
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            # Static map for Giovanni
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, 99944, reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, 99944, reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return

        elif reward_lower.startswith("sierra"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/43.png")
            quests = await get_dataleaders(bot.config, area, 43)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for lat, lon, stop_name, stop_id, expiration, character in quests:
                found_rewards = True
                mon_id = 99943
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"r{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}invasion/43.png"
                end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, 0, [], None, False, length, text,
                    max_len=26, extra=end
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            # Static map for Sierra
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, 99943, reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, 99943, reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return

        elif reward_lower.startswith("arlo"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/42.png")
            quests = await get_dataleaders(bot.config, area, 42)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for lat, lon, stop_name, stop_id, expiration, character in quests:
                found_rewards = True
                mon_id = 99942
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"r{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}invasion/42.png"
                end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, 0, [], None, False, length, text,
                    max_len=26, extra=end
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            # Static map for Arlo
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, 99942, reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, 99942, reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return

        elif reward_lower.startswith("cliff"):
            embed.title = f"{bot.locale['leaders']} - {area[1]}"
            embed.set_thumbnail(url=f"{bot.config['mon_icon_repo']}invasion/41.png")
            quests = await get_dataleaders(bot.config, area, 41)
            length = 0
            reward_mons = []
            lat_list = []
            lon_list = []
            text = ""
            for lat, lon, stop_name, stop_id, expiration, character in quests:
                found_rewards = True
                mon_id = 99941
                reward_mons.append([mon_id, lat, lon])
                emote_name = f"r{mon_id}"
                emote_img = f"{bot.config['mon_icon_repo']}invasion/41.png"
                end = datetime.fromtimestamp(expiration).strftime(bot.locale['time_format_hm'])
                text, length, stop = add_quest_entry(
                    stop_name, lat, lon, stop_id, 0, [], None, False, length, text,
                    max_len=26, extra=end
                )
                lat_list.append(lat)
                lon_list.append(lon)
                if stop:
                    break
            embed.description = text or bot.locale["no_quests_found"]
            embed.set_footer(text=footer_text)
            embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
            message = await ctx.send(embed=embed)
            # Static map for Cliff
            if bot.config['use_static'] and reward_mons:
                if bot.config['static_provider'] == "mapbox":
                    image = await bot.static_map.quest(lat_list, lon_list, 99941, reward_mons, bot.custom_emotes)
                elif bot.config['static_provider'] == "tileserver":
                    image = await bot.static_map.quest(lat_list, lon_list, 99941, reward_mons, bot.custom_emotes)
                embed.set_image(url=image)
                await message.edit(embed=embed)
            return
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
            # Use add_quest_entry to get stop value
            text, length, stop = add_quest_entry(
                stop_name, lat, lon, stop_id, 0, [0], amount, False, length, text,
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
                stop_name, lat, lon, stop_id, 0, [0], amount, False, length, text,
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

        embed.set_image(url=image)
        await message.edit(embed=embed)
    else:
        embed.description = bot.locale["no_quests_found"]
        embed.set_footer(text=footer_text)
        embed.set_image(url="https://raw.githubusercontent.com/ccev/dp_emotes/master/blank.png")
        await ctx.send(embed=embed)
    
bot.get_area = get_area
bot.poke_lookup = poke_lookup
bot.lookup_form_id_for_mon = lambda mon_id, form_query: lookup_form_id_for_mon(mon_id, form_query, poke_lookup)
bot.lookup_costume_id_for_mon = lambda mon_id, costume_query: lookup_costume_id_for_mon(mon_id, costume_query, poke_lookup)
bot.fuzzy_find_pokemon = lambda query: fuzzy_find_pokemon(query, poke_lookup)
bot.get_api_filecode = lambda *args, **kwargs: get_api_filecode(*args, poke_lookup=bot.poke_lookup, **kwargs)
bot.get_data = get_data
bot.get_lures = get_lures
bot.get_stations = get_stations
bot.get_datarocket = get_datarocket
bot.get_datarocketquery = get_datarocketquery
bot.get_datagiovani = get_datagiovani
bot.get_dataleaders = get_dataleaders
bot.get_alt_data = get_alt_data
bot.get_dataitem = get_dataitem
bot.get_alt_dataitem = get_alt_dataitem
bot.get_datamega = get_datamega
bot.get_alt_datamega = get_alt_datamega
bot.get_dataroute = get_dataroute
bot.get_datastar = get_datastar
bot.get_alt_datastar = get_alt_datastar
bot.get_datak = get_datak
bot.get_datashow = get_datashow
bot.get_datacoin = get_datacoin
@bot.event
async def on_ready():
    print("Connected to Discord. Ready to take commands.")

    if bot.config['use_static']:
        trash_channel = await bot.fetch_channel(bot.config['host_channel'])
        bot.static_map = util.maps.static_map(config['static_provider'], config['static_key'], trash_channel, bot.config['mon_icon_repo'])

with open ("data/forms/formsen.json", encoding="utf-8") as f:
    forms_data = json.load(f)

if __name__ == "__main__":
    print("Starting QuestSearch bot...")

    async def main():
        await bot.load_extension("qform")
        await bot.load_extension("util.extra_commands")
        await bot.start(bot.config['bot_token'])

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Bot stopped.")