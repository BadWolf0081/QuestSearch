import aiomysql

async def get_data(config, area, mon_id):
    conn = await aiomysql.connect(
        host=config['db_host'],
        user=config['db_user'],
        password=config['db_pass'],
        db=config['db_dbname'],
        port=config['db_port']
    )
    async with conn.cursor() as cur:
        await cur.execute(
            f"SELECT quest_rewards, quest_template, lat, lon, name, id FROM pokestop WHERE quest_pokemon_id = {mon_id} AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_pokemon_id ASC, name;"
        )
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

async def get_dataitem(config, area, item_id):
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
        await cur.execute(f"SELECT alternative_quest_reward_amount, alternative_quest_template, lat, lon, name, id FROM pokestop WHERE alternative_quest_reward_type = 3 AND alternative_quest_reward_amount >= 999 AND ST_Contains(ST_GeomFromText('POLYGON(({area[0]}))'), POINT(lat,lon)) AND updated >= UNIX_TIMESTAMP()-86400 ORDER BY quest_reward_amount DESC, name;")
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