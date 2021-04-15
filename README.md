# MKT-MogiBot
This is a Python rewrite of 255MP's MogiBot, with some significant changes - this is configured just for MKT Lounge, with their requested settings. 

- Instead of !3 or !4 to ping, just do !p and the bot will ping with the correct number.
- !votes will show you who voted for what
- There is no queue cooldown - I see benefits and drawbacks to both sides, and I don't want to do extra work.
- There is no !end, !start, !next - only !esn - mogis always go. If you temporarily do not want the bot to allow people to queue for some reason, just don't let the bot see the channel.

If the bot needs to be downloaded and run because mine crashed or something, download this repo. A minimum of Python 3.5 is needed.

The bot key goes on the 2nd line of "private.txt". The Google Sheets API key goes on the 3rd and final line of "private.txt". I will not explain how to run a Discord bot, nor how to get those keys. You'll need your own keys. And Google is your friend.

Additionally, I will not explain which libraries you need. However, pip can install all of the needed libraries. Off the top of my head, needed libraries include (but are not limited to): discord.py, dill, pathlib
