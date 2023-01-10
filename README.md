# QuestSearch
 
 Install Instructions:
  1.  `sudo apt install python3 python3-pip`
  2.  `git clone https://github.com/BadWolf0081/QuestSearch.git`
  3.  `cd QuestSearch && cp config/config.ini.example config/config.ini && cp config/geofence.json.example config/geofence.json`
  4.  `nano config/config.ini`
  
Fill out DB info etc...You will need a discord bot & token.  (https://www.writebots.com/discord-bot-token/)

  5.  `python3 -m venv QSvenv`
  6.  `nano ecosystem.config.js` (only change your_username to your username)
  7.  `pm2 start ecosystem.config.js`

This bot is a heavily modified / stripped version of Discordopole develop branch.  It was originally written by ccev / Malte.  I removed all other commands and features except for the quest search command and slimmed down the code immensly.  Updated all requirements to the latest making adjustments to fix errors.  Database connections are also closed properly now.
