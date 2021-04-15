'''
Created on Sep 26, 2020

@author: willg
'''
import discord
import aiohttp
import dill as p
import os
from pathlib import Path
import shutil
from datetime import datetime
import re
from typing import List, Set
import copy
import Player

prefix = "!"
alternate_prefix = "^"
all_prefixes = [prefix, alternate_prefix]
war_lounge_live = False

REPORTER_ID = 1
REPORTER_2_ID = 1
UPDATER_ID = 821998979193110540
UPDATER_2_ID = 1
DEVELOPER_ID = 630514545856610314
LOWER_TIER_ARBITRATOR_ID = 742435127438868511
HIGHER_TIER_ARBITRATOR_ID = 698245935561572373
CT_ARBITRATOR_ID = 760257183144607804
ADMIN_ID = 816970540316360717
LOUNGE_STAFF = 821993711869231114
backup_folder = "backups/"
player_fc_pickle_path = "player_fcs.pkl"
restricted_filter_data_pickle_path = "restricted_data.pkl"
backup_file_list = [player_fc_pickle_path, restricted_filter_data_pickle_path]
add_fc_commands = {"setfc"}
get_fc_commands = {"fc"}
#Need here to avoid circular import...
ml_terms = {"ml","mogilist", "wl", "warlist"}
mllu_terms = {"mllu","mogilistlineup","wllu","warlistlineup"}
go_live_terms = {"golive"}
update_role_terms = {"ur", "updaterole"}
set_host_terms = {"sethost", "sh"}
get_host_terms = {"host"}
stats_commands = {"stats"}
mmrlu_lookup_terms = {"mmrlu", "mmrlineup"}
mmr_lookup_terms = {"mmr"}

player_data_commands = set.union(mmr_lookup_terms, mmrlu_lookup_terms, get_host_terms, set_host_terms, get_fc_commands, add_fc_commands, stats_commands)

google_sheets_url_base = "https://sheets.googleapis.com/v4/spreadsheets/"
google_sheet_id = "1bvoJSerq9--gjSZhjT6COgU_fzQ20tnYikrwz6KwYw0"

google_sheet_gid_url = None
google_api_key = None


runner_leaderboard_name = "Runner Leaderboard"
bagger_leaderboard_name = "Bagger Leaderboard"

runner_mmr_range = "'" + runner_leaderboard_name + "'!C2:D"
bagger_mmr_range = "'" + bagger_leaderboard_name + "'!C2:D"

can_update_role = {UPDATER_ID, DEVELOPER_ID, LOWER_TIER_ARBITRATOR_ID, HIGHER_TIER_ARBITRATOR_ID, ADMIN_ID}
player_fcs = None
medium_delete = 7

def has_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    return message.startswith(prefix)

def strip_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    if message.startswith(prefix):
        return message[len(prefix):]
    
def is_in(message:str, valid_terms:set, prefix:str=prefix):
    if (has_prefix(message, prefix)):
        message = strip_prefix(message, prefix).strip()
        args = message.split()
        if len(args) == 0:
            return False
        return args[0].lower().strip() in valid_terms
            
    return False

def addRanges(base_url, ranges):
    temp = copy.copy(base_url)
    for r in ranges:
        temp += "&ranges=" + r
    return temp
def get_emoji_by_name(emojis:List[discord.Emoji], name):
    for emoji in emojis:
        if emoji.name == name:
            return str(emoji)
    return name

def find_members_by_names(members:List[discord.Member], names:List[str], removeNone=False):
    names_edited = [name.lower().replace(" ", "") for name in names]
    found = [None] * len(names)
    for member in members:
        member_name = member.display_name.lower().replace(" ", "")
        if member_name in names_edited:
            name_index = names_edited.index(member_name)
            found[name_index] = member
    if removeNone:
        found = list(filter(lambda m: m != None, found))
    
    return found
            
        
def find_member_by_str(members:List[discord.Member], name:str):
    name = name.lower().replace(" ", "")
    for member in members:
        if name == member.display_name.lower().replace(" ", ""):
            return member
    return None
    

def strip_prefix_and_command(message:str, valid_terms:set, prefix:str=prefix):
    message = strip_prefix(message, prefix)
    args = message.split()
    if len(args) == 0:
        return message
    if args[0].lower().strip() in valid_terms:
        message = message[len(args[0].lower().strip()):]
    return message.strip()

def is_boss(member:discord.Member):
    return has_any_role_ids(member, {ADMIN_ID})
def is_developer(member:discord.Member):
    return has_any_role_ids(member, {DEVELOPER_ID})

def has_authority(author:discord.Member, valid_roles:set, admin_allowed=True):
    if admin_allowed:
        if author.guild_permissions.administrator:
            return True
        
    for role in author.roles:
        if role.id in valid_roles:
            return True
    return False 
    


def get_role_mapping(role_ids, guild:discord.guild):
    if isinstance(role_ids, int):
        role_ids = {role_ids}
    mappings = {}
    for role in guild.roles:
        if role.id in role_ids:
            mappings[role.id] = role
    if role_ids != set(mappings.keys()):
        return mappings, False
    return mappings, True
    

def _is_fc(fc):
    return re.match("^[0-9]{4}[-][0-9]{4}[-][0-9]{4}$", fc.strip()) != None

def _is_almost_fc(fc):
    fc = fc.replace(" ", "")
    return re.match("^[0-9]{12}$", fc.strip()) != None

#No out of bounds checking is done - caller is responsible for ensuring that the FC is 12 numbers, only being separated by spaces
def _fix_fc(fc):
    fc = fc.replace(" ", "")
    return fc[0:4] + "-" + fc[4:8] + "-" + fc[8:12]


#returns runner and bagger mmr list from Google Sheets
    #Returns None,None is either data is corrupt
def get_mmr_for_names(names:List[str], mmr_list):
    if len(names) == 0:
        return {}
    to_send_back = {}
    for name in names:
        temp = name.replace(" ","").lower()
        if len(temp) == 0:
            continue
        if temp not in to_send_back:
            to_send_back[temp] = (name.strip(), -1)
    
    for player_and_mmr in mmr_list:
        if not isinstance(player_and_mmr, list) or len(player_and_mmr) != 2\
                or not isinstance(player_and_mmr[0], str) or not isinstance(player_and_mmr[1], str):
            break
        if not player_and_mmr[1].isnumeric():
            try:
                float(player_and_mmr[1])
            except ValueError:
                break
        lookup = player_and_mmr[0].replace(" ", "").lower()
        if lookup in to_send_back.keys():
            to_send_back[lookup] = (player_and_mmr[0].strip(), int(float(player_and_mmr[1])))
            #check if we' found everyone - this is an efficiency thing, and not strictly necessary
            #For curiosity sake, if the lookup was all high MMR players, this little check right here makes this function super fast
            #But if the check was for even one low mmr player, this check does almost nothing to speed this up
            found_count = sum(1 for p in to_send_back.values() if p[1] != -1)
            if found_count >= len(to_send_back):
                break
    
    return to_send_back

def get_mmr_for_members(members, mmr_list):
    if len(members) == 0:
        return {}
    is_discord_members = False
    if isinstance(members[0], discord.Member):
        is_discord_members = True
    elif isinstance(members[0], Player.Player):
        is_discord_members = False
    else:
        print("Well, you done messed up somehow. Don't call get_mmr_for_members with type " + type(members))
        return {}
    
    to_send_back = {}
    for m in members:
        if is_discord_members:
            to_send_back[hash(m)] = (m, -1)
        else:
            to_send_back[hash(m.member)] = (m, -1)
        
    for player_and_mmr in mmr_list:
        if not isinstance(player_and_mmr, list) or len(player_and_mmr) != 2\
                or not isinstance(player_and_mmr[0], str) or not isinstance(player_and_mmr[1], str):
            break
        if not player_and_mmr[1].isnumeric():
            try:
                float(player_and_mmr[1])
            except ValueError:
                break
        lookup = player_and_mmr[0].replace(" ", "").lower()

        for m_hash, (m, _) in to_send_back.items():
            if not is_discord_members:
                m = m.member
            if lookup == m.display_name.replace(" ", "").lower():
                to_send_back[m_hash] = (to_send_back[m_hash][0], int(float(player_and_mmr[1])))
    
    return to_send_back

def get_runner_mmr_list(json_resp): #No error handling - caller is responsible that the data is good
        return json_resp['valueRanges'][0]['values']
def get_bagger_mmr_list(json_resp): #No error handling - caller is responsible that the data is good
    return json_resp['valueRanges'][1]['values']
    
def combine_mmrs(runner_mmr_dict, bagger_mmr_dict):
    if set(runner_mmr_dict.keys()) != set(bagger_mmr_dict.keys()):
        return {}
    mmr_dict = {}
    for lookup in runner_mmr_dict:
        mmr_dict[lookup] = runner_mmr_dict[lookup][0], runner_mmr_dict[lookup][1], bagger_mmr_dict[lookup][1]
    return mmr_dict

def combine_and_sort_mmrs(runner_mmr_dict, bagger_mmr_dict): #caller has responsibility of making sure the keys for both dicts are the same
    mmr_dict = combine_mmrs(runner_mmr_dict, bagger_mmr_dict)
    
    sorted_mmr = sorted(mmr_dict.values(), key=lambda p: (-p[1], -p[2], p[0])) #negatives are a hack way, so that in case of a tie, the names will be sorted alphabetically
    for ind, item in enumerate(sorted_mmr):
        if item[1] == -1:
            sorted_mmr[ind] = (sorted_mmr[ind][0], "Unknown", sorted_mmr[ind][2]) 
        if item[2] == -1:
            sorted_mmr[ind] = (sorted_mmr[ind][0], sorted_mmr[ind][1], "Unknown") 
    return sorted_mmr

def mmr_data_is_corrupt(json_resp):
        if not isinstance(json_resp, dict): 
            return True
        #data integrity check #2
        if 'valueRanges' not in json_resp\
                    or not isinstance(json_resp['valueRanges'], list)\
                    or len(json_resp['valueRanges']) != 2:
            return True
            
        #data integrity check #3
        runner_leaderboard_dict = json_resp['valueRanges'][0]
        bagger_leaderboard_dict = json_resp['valueRanges'][1]
        if not isinstance(runner_leaderboard_dict, dict) or\
                    not isinstance(bagger_leaderboard_dict, dict) or\
                    'range' not in runner_leaderboard_dict or\
                    'range' not in bagger_leaderboard_dict or\
                    runner_leaderboard_name not in runner_leaderboard_dict['range'] or\
                    bagger_leaderboard_name not in bagger_leaderboard_dict['range'] or\
                    'values' not in runner_leaderboard_dict or\
                    'values' not in bagger_leaderboard_dict or\
                    not isinstance(runner_leaderboard_dict['values'], list) or\
                    not isinstance(bagger_leaderboard_dict['values'], list):
            return True
        return False
    
async def pull_all_mmr():
    full_url = addRanges(google_sheet_gid_url, [runner_mmr_range, bagger_mmr_range])
    json_resp = None
    try:
        json_resp = await fetch(full_url)
    except:
        return None, None
    if mmr_data_is_corrupt(json_resp):
        return None, None
    
    #At this point, we've verified that the data is not corrupt/bad
    #Let's send the list of runners and baggers to another function along with who we are looking up,
    #and they can return the mmr for each person looked up
    #Note that the function we give these lists to will still have to do some data integrity checking, but at least it won't be as bad
    
    runner_mmr = get_runner_mmr_list(json_resp)
    bagger_mmr = get_bagger_mmr_list(json_resp)
    return runner_mmr, bagger_mmr



def has_any_role_ids(member:discord.Member, role_ids:Set[int]):
    if isinstance(role_ids, int):
        role_ids = {role_ids}
        
    for role in member.roles:
        if role.id in role_ids:
            return True
    return False


#============== PUG Bot Command Functions ==============

def is_add_fc_check(message:str, prefix=prefix):
    return is_in(message, add_fc_commands, prefix)
def is_get_fc_check(message:str, prefix=prefix):
    return is_in(message, get_fc_commands, prefix)
def is_update_role(message:str, prefix=prefix):
    return is_in(message, update_role_terms, prefix)
def is_go_live(message:str, prefix=prefix):
    return is_in(message, go_live_terms, prefix)
 
async def send_add_fc(message:discord.Message, valid_terms=add_fc_commands, prefix=prefix):
    str_msg = message.content
    str_msg = strip_prefix_and_command(str_msg, valid_terms, prefix)
    if len(str_msg) == 0:
        await message.channel.send("Provide an FC.", delete_after=medium_delete)
    elif _is_fc(str_msg):
        player_fcs[message.author.id] = str_msg
        await message.channel.send("FC has been set. You can do `!sethost` now.", delete_after=medium_delete)
    elif _is_almost_fc(str_msg):
        player_fcs[message.author.id] = _fix_fc(str_msg)
        await message.channel.send("FC has been set. You can do `!sethost` now.", delete_after=medium_delete)
    else:
        await message.channel.send("FC should be in the following format: ####-####-####", delete_after=medium_delete)

async def send_fc(message:discord.Message, valid_terms=get_fc_commands, prefix=prefix):
    str_msg = message.content
    str_msg = strip_prefix_and_command(str_msg, valid_terms, prefix)
    if len(str_msg) == 0: #getting author's fc
        if message.author.id in player_fcs:
            await message.channel.send(player_fcs[message.author.id] + "\t do `!sethost` to make your FC the host")
        else:
            await message.channel.send("You have not set an FC. Do: " + prefix + "setfc ####-####-####", delete_after=medium_delete)
    else:
        player_name = str_msg
        member = find_member_by_str(message.guild.members, player_name)
        if member == None:
            await message.channel.send("No one in this server has that name.", delete_after=medium_delete)
        else:
            if member.id in player_fcs:
                await message.channel.send(player_fcs[member.id])
            else:
                await message.channel.send(member.display_name + " doesn't have an fc set.", delete_after=medium_delete)
        
    
    
async def process_other_command(message:discord.Message, prefix=prefix):
    if not has_prefix(message.content, prefix):
        return False
    if is_add_fc_check(message.content, prefix):
        await send_add_fc(message, prefix=prefix)
    elif is_get_fc_check(message.content, prefix):
        await send_fc(message, prefix=prefix)
    elif is_go_live(message.content, prefix=prefix):
        if is_boss(message.author) or is_developer(message.author):
            global war_lounge_live
            war_lounge_live = not war_lounge_live
            await message.channel.send("War Lounge live: " + str(war_lounge_live))
        
    else:
        return False
    return True


def is_ml(message:str, prefix:str=prefix):
    return is_in(message, ml_terms, prefix)

def is_mllu(message:str, prefix:str=prefix):
    return is_in(message, mllu_terms, prefix)

    

#============== Synchronous HTTPS Functions ==============
async def fetch(url, headers=None):
    async with aiohttp.ClientSession() as session:
        if headers == None:
            async with session.get(url) as response:
                return await response.json()
        else:
            async with session.get(url, headers=headers) as response:
                return await response.json()



#============== PICKLES AND BACKUPS ==============         
def initialize():
    load_player_fc_pickle()

def check_create(file_name):
    if not os.path.isfile(file_name):
        f = open(file_name, "w")
        f.close()
  
def backup_files(to_back_up=backup_file_list):
    Path(backup_folder).mkdir(parents=True, exist_ok=True)
    todays_backup_path = backup_folder + str(datetime.date(datetime.now())) + "/"
    Path(todays_backup_path).mkdir(parents=True, exist_ok=True)
    for file_name in to_back_up:
        try:
            if not os.path.exists(file_name):
                continue
            temp_file_n = file_name
            if os.path.exists(todays_backup_path + temp_file_n):
                for i in range(50):
                    temp_file_n = file_name + "_" + str(i) 
                    if not os.path.exists(todays_backup_path + temp_file_n):
                        break
            shutil.copy2(file_name, todays_backup_path + temp_file_n)
        except Exception as e:
            print(e)
            
    
def load_player_fc_pickle():
    global player_fcs
    player_fcs = {}
    if os.path.exists(player_fc_pickle_path):
        with open(player_fc_pickle_path, "rb") as pickle_in:
            try:
                player_fcs = p.load(pickle_in)
            except:
                print("Could not read in pickle for player fcs.")
                raise
    
    

def player_fc_pickle_dump():
    with open(player_fc_pickle_path, "wb") as pickle_out:
        try:
            p.dump(player_fcs, pickle_out)
        except:
            print("Could not dump pickle for player fcs.")
            raise
