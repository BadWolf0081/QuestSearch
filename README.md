# QuestSearch
 Features I've Added:
  1.  Now Searches both AR and Non AR with identifyer for non ar.
  2.  Stardust, Poffin, and other items, also displays amount for all items in order.
  3.  Kecleon or Coin encounters.
  4.  UICONS
  5.  Mega Energy (Just put Mega or mega before the name of the pokemon.)
  
 Install Instructions:
  1.  `sudo apt install python3 python3-pip`
  2.  `git clone https://github.com/BadWolf0081/QuestSearch.git`
  3.  `cd QuestSearch && cp config/config.ini.example config/config.ini && cp config/geofence.json.example config/geofence.json`
  4.  `nano config/config.ini`
      Fill out DB info etc...You will need a discord bot & token.  (https://www.writebots.com/discord-bot-token/)
  5.  `nano config/geofence.json`
      You can also copy from stopwatcher, it's the same format.
  6.  `python3 -m venv QSvenv`
  7.  `/home/your_username/QuestSearch/QSvenv/bin/pip3 install -r requirements.txt`
  8.  `nano ecosystem.config.js` (only change your_username to your username)
  9.  `pm2 start ecosystem.config.js`

This bot was originally written by ccev / Malte.  I removed all other commands and features except for the quest search command and slimmed down the code immensly.  Then added new features.
