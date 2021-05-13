'''
Created on Sep 14, 2020

@author: willg
'''

import discord
from typing import List, Tuple
from discord.ext import tasks

import TierMogi
import Player
import Shared
import os
import dill as p
import sys
import atexit
import signal
import MMR
import gspread

bot_key = None
testing_bot_key = None
pickle_dump_path = "tiers_pickle.pkl"
private_info_file = "private.txt"

pug_lounge_server_id = 629221606064914442

new_pug_lounge_server_id = Shared.new_pug_lounge_server_id
ECHELON_CATEGORY = 397230115400187907
BOT_TESTING_CATEGORY = 1
MODERATION_CATEGORY = 765290812686336001
allowed_mogi_categories = [ECHELON_CATEGORY, BOT_TESTING_CATEGORY, MODERATION_CATEGORY]
#mogi_bot_id = 450127943012712448
DEBUGGING = False
bot_started = False

tier_mogi_instances = None
mmr_channel_instances = {}
tier_instances = {}
client = discord.Client(intents=discord.Intents.all())

allowed_without_prefix = {"<:pepecan:822360781139345438>", "<:pepedrop:822360714978131988>", "<:pepec:768060077453737994>", "<:peped:768059756404670474>"}


if DEBUGGING:
    new_pug_lounge_server_id = 739733336871665696
def command_allowed_without_prefix(message:str):
    for term in allowed_without_prefix:
        if message.startswith(term):
            return True
    return False

@client.event
async def on_message(message: discord.Message):
    if message.guild == None:
        return
    #ignore your own messages
    if message.author == client.user:
        return
    if message.author.bot:
        return
    #ignore everything outside of 5v5 Lounge
    if message.guild.id != new_pug_lounge_server_id:
        return
    if not bot_started:
        return
    
    
    
    channel_id = message.channel.id  
    if message.channel.id not in tier_mogi_instances:
        tier_mogi_instances[channel_id] = TierMogi.TierMogi(message.channel)
        
    if channel_id not in mmr_channel_instances:
        mmr_channel_instances[channel_id] = MMR.MMR()
        
    tier_mogi = tier_mogi_instances[channel_id]
    channel_mmr = mmr_channel_instances[channel_id]
        
    
    
    #The following snippets of code make the bot more efficient - unfortunately at the cost of making the code less readable
    #TODO: Come back here
    await tier_mogi_instances[channel_id].__update__(message)
        

    if command_allowed_without_prefix(message.content):
        message.content = "!" + message.content
        
    message_str = message.content.strip()
    if message_str == "" or message_str[0] not in Shared.all_prefixes:
        return
    
    #we know that the command starts with ^ or ! now - we check for ^ here and only allow certain commands
    #TODO: Come back here
    if message_str[0] == Shared.alternate_prefix:
        if Shared.is_in(message_str, Shared.player_data_commands, prefix=Shared.alternate_prefix):
            was_mmr_command = await channel_mmr.mmr_handle(message, Shared.alternate_prefix)
            if was_mmr_command:
                return
            #It's okay to do these because we already verified their command was a player data command
            was_other_command = await Shared.process_other_command(message, Shared.alternate_prefix)
            if was_other_command:
                return
        await tier_mogi.sent_message(message, tier_mogi_instances, Shared.alternate_prefix, client=client)
        return
    
    #Their command starts with !
    #TODO: Come back here
    
    was_tier_mogi_command = await tier_mogi.sent_message(message, tier_mogi_instances, Shared.prefix, client=client)
    if was_tier_mogi_command:
        return
    
    was_mmr_command = await channel_mmr.mmr_handle(message)
    if was_mmr_command:
        return
    
    
    was_other_command = await Shared.process_other_command(message)
    if was_other_command:
        return
  
@tasks.loop(seconds=45)
async def routine_tier_checks():
    for tier_mogi in tier_mogi_instances.values():
        try:
            await tier_mogi.drop_warn_check()
        except:
            print("Exception occurred in routine_tier_checks, but was caught. Hopefully method is still running.")
        

@tasks.loop(seconds=60)
async def routine_force_vote_checks():
    if tier_mogi_instances != None:
        for mogi in tier_mogi_instances.values():
            await mogi.force_overtime_pick_check()
    
        
@tasks.loop(hours=24)
async def backup_data():
    Shared.player_fc_pickle_dump()
    Shared.backup_files(Shared.backup_file_list)
        
       
       
def get_channel(channels, channel_id):
    temp = discord.utils.get(channels, id=channel_id)
    return temp
def get_member(members, member_id):
    temp = discord.utils.get(members, id=member_id)
    return temp

def private_data_init():
    global testing_bot_key
    global bot_key
    with open(private_info_file, "r") as f:
        testing_bot_key = f.readline().strip("\n")
        bot_key = f.readline().strip("\n")
        Shared.google_api_key = f.readline().strip("\n")
        Shared.google_sheet_gid_url = Shared.google_sheets_url_base + Shared.google_sheet_id + "/values:batchGet?" + "key=" + Shared.google_api_key
        Shared.gc = gspread.service_account(filename='credentials.json').open_by_key(Shared.google_sheet_id).worksheet(Shared.runner_leaderboard_name)
        
@client.event
async def on_ready():
    """global user_flag_exceptions
    unlockCheck.start()"""

    global tier_mogi_instances
    global bot_started
    
    if not bot_started:
        if tier_mogi_instances is None:
            tier_mogi_instances = {}
            #TODO: COme back here
            if os.path.exists(pickle_dump_path):
                guild = client.get_guild(new_pug_lounge_server_id)
                members = guild.members
                channels = guild.text_channels
                picklable_dict = {}
                with open(pickle_dump_path, "rb") as pickle_in:
                    try:
                        picklable_dict = p.load(pickle_in)
                    except:
                        print("Could not read tier instances in.")
                        picklable_dict = {}
                        raise
                    
                new_tier_instances = {}
                for channel_id, picklable_tier_mogi in picklable_dict.items():
                    cur_channel = get_channel(channels, picklable_tier_mogi.channel_id)
                    if cur_channel == None:
                        continue
                    
                    mogi_list = []
                    player_error = False
                    for picklable_player in picklable_tier_mogi.mogi_list:
                        curPlayer = Player.Player(None, None)
                        curMember = get_member(members, picklable_player.member_id)
                        if curMember == None:
                            player_error = True
                        else:
                            curPlayer.reconstruct(picklable_player, curMember)
                            mogi_list.append(curPlayer)
                    curTier = TierMogi.TierMogi(None)
                    curTier.reconstruct(mogi_list, cur_channel, picklable_tier_mogi)
                    if player_error:
                        curTier.recalculate()
                    new_tier_instances[channel_id] = curTier
                
                tier_mogi_instances = new_tier_instances
                
        if Shared.player_fcs == None: 
            Shared.load_player_fc_pickle()

        routine_tier_checks.start()
        backup_data.start()
        routine_force_vote_checks.start()
        print("Finished on ready.")
        bot_started = True
    

def pickle_dump_tier_mogis():
    global tier_mogi_instances
    global pickle_dump_path
    with open(pickle_dump_path, "wb") as pickle_out:
        try:
            mogis = {}
            for channel_id, mogi in tier_mogi_instances.items():
                if not mogi.isEmpty():
                    mogis[channel_id] = mogi.getPicklableTierMogi()
            p.dump(mogis, pickle_out)
        except:
            print("Could not dump pickle for tier instances.")
            
def on_exit():
    print("Exiting...")

    pickle_dump_tier_mogis()
    Shared.player_fc_pickle_dump()
    

def handler(signum, frame):
    sys.exit()

signal.signal(signal.SIGINT, handler)

atexit.register(on_exit)

private_data_init()
if DEBUGGING:
    client.run(testing_bot_key)
else:
    client.run(bot_key)
