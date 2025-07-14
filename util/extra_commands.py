import discord
import requests
from PIL import Image
from io import BytesIO
from discord.ext import commands
from util.mondetails import details
from util.pokemon_lookup import (
    lookup_form_id_for_mon,
    lookup_costume_id_for_mon,
    get_api_filecode,
)

def parse_mon_args(parts):
    mon_name = parts[0]
    form_query = None
    shiny = False
    mega = False
    for part in parts[1:]:
        if part.lower() == "shiny":
            shiny = True
        elif part.lower() == "mega":
            mega = True
        else:
            form_query = part
    return mon_name, form_query, shiny, mega

async def setup(bot):
    @bot.command(pass_context=True)
    async def costume(ctx, *, args):
        try:
            parts = args.strip().split()
            if not parts:
                await ctx.send("Usage: !costume <pokemon name> [costume] [shiny]")
                return
            shiny = False
            costume_query = None
            mon_name = None

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

            if costume_query:
                full_costume = f"{mon_name}_{costume_query.replace(' ', '_')}"
                costume_id, costume_name = bot.lookup_costume_id_for_mon(mon.id, full_costume)
                if costume_id == 0 or costume_id is None:
                    costume_id, costume_name = bot.lookup_costume_id_for_mon(mon.id, costume_query)
                if costume_id == 0 or costume_id is None:
                    costume_id, costume_name = 0, None
            else:
                costume_id, costume_name = 0, None

            filecode = bot.get_api_filecode(mon.id, costume_id=costume_id, shiny=shiny)
            if not filecode:
                await ctx.send("Could not find that Pokémon or costume (API crossref failed).")
                return

            url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"
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
                form_id, _ = bot.lookup_form_id_for_mon(mon.id, full_form)
                if form_id == 0 or form_id is None:
                    form_id, _ = bot.lookup_form_id_for_mon(mon.id, form_query)
            mega_id = 1 if mega else None

            filecode = bot.get_api_filecode(mon.id, form_id=form_id, shiny=shiny, mega_id=mega_id)
            if not filecode:
                await ctx.send("Could not find that Pokémon or form (API crossref failed).")
                return

            url = bot.config.get('form_icon_repo', bot.config['mon_icon_repo']) + f"pokemon/{filecode}.png"
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

            mon = details(mon_name, bot.config['mon_icon_repo'], bot.config['language'])
            if not hasattr(mon, "id") or not mon.id:
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
            response = requests.get(url)
            if response.status_code != 200:
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