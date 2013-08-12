# World Of Tanks replay file parser/clanwar filter.
# Copyright (C) 20120817 Rasz_pl
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For more information please view the readme file.
#

import sys
import time
import struct
import json
from pprint import pprint
from datetime import datetime
import os
import shutil
import fnmatch, re
import wotdecoder


# Returns the list of .extension files in path directory. Omit skip file. Can be recursive.
def custom_listfiles(path, extension, recursive, skip = None):
  if recursive:
    files = []
    for root, subFolders, filename in os.walk(path):
      for f in filename:
        if f.endswith("."+extension) and f!=skip:
          files.append(os.path.join(root,f))
  else:
    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(path + os.path.sep + f) and f.endswith("."+extension) and f!=skip]
  return files



def main():

  nickname = "*"
  clantag = "*"
  csens = re.IGNORECASE
  verbose = 4
  show_errors = False
  owner = False
  recursive = True
  full_path = False
  battle_result = False
  source = os.getcwd()

# Parse arguments
  skip = -1
  for argind, arg in enumerate(sys.argv[1:]):
    if argind == skip: pass
    elif arg == "-c" : csens = 0
    elif arg == "-v0" : verbose = 0
    elif arg == "-v1" : verbose = 1
    elif arg == "-v2" : verbose = 2
    elif arg == "-v3" : verbose = 3
    elif arg == "-v4" : verbose = 4
    elif arg == "-e" : show_errors = True
    elif arg == "-o" : owner = True
    elif arg == "-r" : recursive = False
    elif arg == "-p" : full_path = True
    elif arg == "-b" : battle_result = True
    elif arg == "-i" :
      if len(sys.argv) <= argind+2:
        sys.exit("\nUnspecified input directory.")
      source = sys.argv[argind+2]
      if not os.path.exists(source):
        sys.exit("\n"+source+" doesnt exist.")
      skip = argind+1

    elif arg in ("-h", "-?") or arg.startswith("-") :
                    sys.exit("findplayer scans replay files for players using nickname and/or clantag."
                             "\nUsage:" \
                             "\n\nfindplayer nickname [clantag] -c -v0..3 -e -o -r -p -b -i input_file_or_directory" \
                             "\n\nTry `*` for string wildcard, `?` for character wildcard." \
                             "\n-c   Case sensitive search." \
                             "\n-v0  Verbose 0 = silent running, only give summary." \
                             "\n-v1  + list replay name, default." \
                             "\n-v2  + show match result, frag count." \
                             "\n-v3  + detailed stats." \
                             "\n-v4  + stats summary." \
                             "\n-e   Show errors." \
                             "\n-o   Include replay owner stats." \
                             "\n-r   Turn off recursive subdirectory scan." \
                             "\n-p   Show full patch." \
                             "\n-b   Scan battle_results(.dat) instead of wotreplays." \
                             "\n-i   Specify input directory. Default is current." \
                             "\n\nExamples:" \
                             "\n`*z_?l [1?3]` will match Rasz_pl[123]" \
                             "\n`[*]` will match any person in a clan." \
                             "\n`[]` will only match people without clan." \
                             "\n`??` will list all people with 2 letter nicknames." \
                             "\n`*` will match everyone.")
    elif arg.startswith("[") and arg.endswith("]"): clantag = arg[1:-1]
    else: nickname = arg


  print ("\nLooking for nickname:", nickname, " clantag: ["+clantag+"]")
  print ("Source:", source)
  print ("Verbose:", verbose, "Recursive:", recursive, "Errors:", ("hide","show")[show_errors])


  t1 = time.clock()

  if os.path.isfile(source):
    listdir = [source]
    if source.endswith(".dat"):
      battle_result = True
  else:
    listdir = custom_listfiles(source, ("wotreplay", "dat")[battle_result], recursive, "temp.wotreplay")

# Prepare regex filters
  regexnickname = fnmatch.translate(nickname)
  regexclantag = fnmatch.translate(clantag)
  reobjnickname = re.compile(regexnickname, csens)
  reobjclantag = re.compile(regexclantag, csens)

  matches = 0
  matches_kills = 0
  matches_stats = 0
  errors = 0

  owner_kills = 0
  owner_damage = 0
  owner_spotted = 0
  player_kills = 0
  player_damage = 0
  player_spotted = 0

  for files in listdir:
    while True:

#      if verbose < 2:
#        scan_mask = 1 #1 means try to only decode first block (binary 001)
#      else:
#        scan_mask = 7 #7 means decode everything (binary 111)
      scan_mask = 7 #above speeds -v0 -v1 scanning x3, but it doesnt detect certain errors, defaulting to slower method

      if battle_result:
        chunks = ["", "", ""]
        chunks[2], version = wotdecoder.battle_result(files)
        chunks_bitmask = 4
        processing = 4
      else:
        chunks, chunks_bitmask, processing, version = wotdecoder.replay(files, scan_mask)

#      pprint (chunks[0])
#      pprint (chunks[1])chunks[2]['arenaUniqueID']
#      pprint (chunks[2])

#      pprint (chunks[2]['personal']['accountDBID'])
#      pprint (chunks[2]['players'][ chunks[2]['personal']['accountDBID'] ]['name'])

#      pprint(chunks)

#      print(datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S'))
#      print(chunks[2]['common']['arenaCreateTime'])
#      print( (datetime.fromtimestamp(chunks[2]['common']['arenaCreateTime'])- datetime(1970, 1, 1, 0, 0)).total_seconds())


#      print(datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').timestamp())
#      xx = (datetime.fromtimestamp(chunks[2]['common']['arenaCreateTime'])- datetime(1970, 1, 1, 0, 0)).total_seconds()
#      print( datetime.fromtimestamp(chunks[2]['common']['arenaCreateTime']))
#      print( datetime.fromtimestamp(xx))
#      print( mapidname[ chunks[2]['common']['arenaTypeID'] & 65535 ])
#      print( chunks[0]['mapName'])

      if (processing >8) or (not chunks_bitmask&5): #ignore replays with no useful data, must have at least first Json or pickle
        errors += 1
        if show_errors:
          print ("\n\n---")
          print ("", ("",os.path.dirname(files)+os.path.sep)[full_path] + os.path.basename(files))
          print (wotdecoder.status[processing])
          print ("---", end="")
        break

      elif processing ==6: #show error messages for recoverable errors
        errors += 1
        if show_errors:
          print ("\n\n---")
          print ("", ("",os.path.dirname(files)+os.path.sep)[full_path] + os.path.basename(files))
          print (wotdecoder.status[processing])
          print ("---", end="")

      elif processing ==8: #very broken replay, only first json valid, have to disabble pickle
        errors += 1
        chunks_bitmask = 1
        if show_errors:
          print ("\n\n---")
          print ("", ("",os.path.dirname(files)+os.path.sep)[full_path] + os.path.basename(files))
          print (wotdecoder.status[processing])
          print ("---", end="")

      match = False
      player_found = 0
      owner_found = 0
      owner_name = ""
      owner_clan = ""

      if chunks_bitmask&4:
        vehicles = chunks[2]['players']
        owner_name = chunks[2]['players'][ chunks[2]['personal']['accountDBID'] ]['name']
        owner_found = chunks[2]['personal']['accountDBID']
      elif chunks_bitmask&2:
        vehicles = chunks[1][1]
        owner_name = chunks[0]['playerName']
      else:
        vehicles = chunks[0]['vehicles']
        owner_name = chunks[0]['playerName']

      for player in vehicles:
        check_player_name = vehicles[player]['name']
        check_player_clan = vehicles[player]['clanAbbrev']

        if not match and reobjnickname.match(check_player_name) and reobjclantag.match(check_player_clan):
          match = True
          matches += 1
          player_found = player
          player_name = vehicles[player]['name']
          player_clan = "["+vehicles[player]['clanAbbrev']+"]"

        if owner_found==0 and (vehicles[player]['name'] == owner_name): #find owner playerID
          owner_found = player
          owner_clan = "["+vehicles[player]['clanAbbrev']+"]"

      if not match: break

      if verbose >0:
            print ("\n\n--------------------------------------------------------------------------------")
            print ("", ("",os.path.dirname(files)+os.path.sep)[full_path] + os.path.basename(files))
            print ("---")
            print ("{0:39}{1:39}".format(player_name+player_clan, ("","| "+owner_name+owner_clan)[owner]))

      if chunks_bitmask&4:
        vehicle_player_found = chunks[2]['players'][player_found]['vehicleid']
        vehicle_owner_found = chunks[2]['players'][owner_found]['vehicleid']

      if verbose >1:
            if chunks_bitmask&4: #is pickle available?
              if chunks[2]['common']['finishReason']==3:
                win_loss="Draw"
              else:
                win_loss = ("Loss","Win ")[chunks[2]['common']['winnerTeam']==chunks[2]['vehicles'][vehicle_player_found]['team']]
              finishReason = "("+ wotdecoder.finishreason[ chunks[2]['common']['finishReason'] ] +")"
#              print ("--- {0:4} on {1:28}{2:>40}".format(win_loss, wotdecoder.maps[ chunks[2]['common']['arenaTypeID'] & 65535 ][1], finishReason))
              print ("--- {0:4} on {1:28}{2:>40}".format(win_loss, wotdecoder.maps[ chunks[2]['common']['arenaTypeID'] & 65535 ][1], finishReason))
#wotdecoder.gameplayid[ chunks[2]['common']['arenaTypeID'] >>16 ]
#wotdecoder.bonustype[ chunks[2]['common']['bonusType'] ]
            elif chunks_bitmask&2: #is second Json available?
              finishReason = ""
              print ("--- {0:4} on {1:28}{2:15}".format(("Loss","Win ")[chunks[1][0]['isWinner']==1], chunks[0]['mapDisplayName'], finishReason))
            else: #incomplete, all we can tell is tanks
              if owner:
                owner_string = "                       {0:<18}".format(chunks[0]['vehicles'][owner_found]['vehicleType'].split(":")[1])
              else:
                owner_string = ""
              print ("                     {0:<18}{1:39}".format(chunks[0]['vehicles'][player_found]['vehicleType'].split(":")[1], owner_string))

            if chunks_bitmask&4: #is second Json available?
              if owner:
                owner_string_kills = "| Kills  ={0:>5}".format( chunks[2]['vehicles'][vehicle_owner_found]['kills'])
                owner_string_tank = "| {0:8} in {1:<27}".format( ("Died","Survived")[chunks[2]['vehicles'][vehicle_owner_found]['health']>0], wotdecoder.tank[ chunks[2]['vehicles'][vehicle_owner_found]['typeCompDescr'] ][1])
                owner_kills += chunks[2]['vehicles'][vehicle_owner_found]['kills']
              else:
                owner_string_kills = ""
                owner_string_tank = ""
              print ("{0:8} in {1:<27}{2:39}".format(("Died","Survived")[chunks[2]['vehicles'][vehicle_player_found]['health']>0], wotdecoder.tank[ chunks[2]['vehicles'][vehicle_player_found]['typeCompDescr'] ][1], owner_string_tank ))
              print ("Kills  ={0:>5}{1:26}{2:39}".format(chunks[2]['vehicles'][vehicle_player_found]['kills'], "", owner_string_kills ))
              player_kills += chunks[2]['vehicles'][vehicle_player_found]['kills']
              matches_kills += 1

            elif chunks_bitmask&2: #is second Json available?
              if owner:
#                print (player_found, owner_found)
#                pprint (chunks[1][1])
                owner_string_kills = "| Kills  ={0:>5}".format( len(chunks[1][0]['killed']) )
                owner_string_tank = "| {0:8} in {1:<27}".format( ("Died","Survived")[ chunks[1][1][owner_found]['isAlive']==1 ], chunks[1][1][owner_found]['vehicleType'].split(":")[1] )
                owner_kills += chunks[1][2][owner_found]['frags']
              else:
                owner_string_kills = ""
                owner_string_tank = ""
              print ("{0:8} in {1:<27}{2:39}".format(("Died","Survived")[ chunks[1][1][player_found]['isAlive']==1 ], chunks[1][1][player_found]['vehicleType'].split(":")[1], owner_string_tank))
              if player_found in chunks[1][2]: #WTF WG, why Y hate sanity? sometimes not all player frag counts saved :/
                frags = chunks[1][2][player_found]['frags']
              else:
                frags = 0
              print ("Kills  ={0:>5}{1:26}{2:39}".format(frags, "", owner_string_kills))
              player_kills += frags
              matches_kills += 1



      if verbose >2 and chunks_bitmask&4: #is pickle available? use it for detailed stats
        player = int(player)
        if owner:
          if version >= 860:
            chunks[2]['vehicles'][vehicle_owner_found]['damageAssisted'] = chunks[2]['vehicles'][vehicle_owner_found]['damageAssistedTrack'] + chunks[2]['vehicles'][vehicle_owner_found]['damageAssistedRadio']
          owner_string_damage = "| Damage ={0:>5}".format(chunks[2]['vehicles'][vehicle_owner_found]['damageDealt'])
          owner_string_spotted = "| Spotted={0:>5}".format(chunks[2]['vehicles'][vehicle_owner_found]['damageAssisted'])
          owner_damage += chunks[2]['vehicles'][vehicle_owner_found]['damageDealt']
          owner_spotted += chunks[2]['vehicles'][vehicle_owner_found]['damageAssisted']
        else:
          owner_string_damage = ""
          owner_string_spotted = ""
        print ("Damage ={0:>5}{1:26}{2:39}".format(chunks[2]['vehicles'][vehicle_player_found]['damageDealt'], "", owner_string_damage))
        if version >= 860:
          chunks[2]['vehicles'][vehicle_player_found]['damageAssisted'] = chunks[2]['vehicles'][vehicle_player_found]['damageAssistedTrack'] + chunks[2]['vehicles'][vehicle_player_found]['damageAssistedRadio']
        print ("Spotted={0:>5}{1:26}{2:39}".format(chunks[2]['vehicles'][vehicle_player_found]['damageAssisted'], "", owner_string_spotted))
        player_damage += chunks[2]['vehicles'][vehicle_player_found]['damageDealt']
        player_spotted += chunks[2]['vehicles'][vehicle_player_found]['damageAssisted']
        matches_stats += 1
        if battle_result: #we are decoding battle_result, lets more-or-less reconstruct potential replay name
# its not 'pixel' accurate, im too lazy to get tank country and underscores correct.
          timestamp = datetime.fromtimestamp(chunks[2]['common']['arenaCreateTime']).strftime('%Y%m%d_%H%M')
          print ("Belongs to~", timestamp+"_"+wotdecoder.tank[ chunks[2]['vehicles'][vehicle_owner_found]['typeCompDescr'] ][1]+"_"+wotdecoder.maps[ chunks[2]['common']['arenaTypeID'] & 65535 ][0]+".wotreplay")



      break


  if matches > 0:
    if verbose >3 and (matches_kills!=0 or matches_stats!=0) : # stats summary
      if matches_kills==0: matches_kills =1 #lets not divide by zero today :)
      if matches_stats==0: matches_stats =1
      if owner:
        owner_string_kills = "| Kills  ={0:>9.2f}".format( owner_kills/matches_kills )
        owner_string_damage = "| Damage ={0:>9.2f}".format( owner_damage/matches_stats )
        owner_string_spotted = "| Spotted={0:>9.2f}".format( owner_spotted/matches_stats )
      else:
        owner_string_kills = ""
        owner_string_damage = ""
        owner_string_spotted = ""

      print ("\nSummary (average):")
      print ("Kills  ={0:>9.2f}{1:23}{2:39}".format(player_kills/matches_kills , "", owner_string_kills))
      print ("Damage ={0:>9.2f}{1:23}{2:39}".format(player_damage/matches_stats , "", owner_string_damage))
      print ("Spotted={0:>9.2f}{1:23}{2:39}".format(player_spotted/matches_stats , "", owner_string_spotted))

    print("\n\nFound", matches, "matches. ", end="")
  else:
    print("\n\nNo matches found. ", end="")
  print(errors, "errors.")

  t2 = time.clock()
  print  ("\nProcessing "+str(len(listdir))+" files took %0.3fms"  % ((t2-t1)*1000))


main()
