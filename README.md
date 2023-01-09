# QuestSearch
 
 Install Instructions:
  1.  '''sudo apt install python3 python3-pip'''
  2.  '''git clone https://github.com/BadWolf0081/QuestSearch.git'''
  3.  cd QuestSearch && cp config/config.ini.example config/config.ini
  4.  nano config/config.ini - Fill out DB info etc, You will need a discord bot & token.  (https://www.writebots.com/discord-bot-token/)
  5.  python3 -m venv QSvenv
  6.  nano ecosystem.config.js (Then change your_username to your username)
  7.  pm2 start ecosystem.config.js
