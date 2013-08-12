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
import binascii
import array
import time
import hashlib
import random
import string,os
import struct
import threading
import json
from pprint import pprint
from datetime import datetime
import os
import shutil
import fnmatch, re
import wotdecoder
# most of those imports are redundand, im lazy like that


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

def getkeyboard(fileold, *filenew):
  while True:
    print("old:", fileold)
    print("    ", datetime.fromtimestamp(os.path.getmtime(fileold)).strftime('%d-%m-%y %H:%M:%S')+",", os.path.getsize(fileold), "bytes")
    if filenew:
      print("new:", filenew[0])
      print("    ", datetime.fromtimestamp(os.path.getmtime(filenew[0])).strftime('%d-%m-%y %H:%M:%S')+",", os.path.getsize(filenew[0]), "bytes")
    choice = input("\n     File already exists, overwrite? (Yes/No/All)")
    if choice == 'n' or choice == 'N':
      choice = 0
      break
    elif choice == 'y' or choice == 'Y':
      choice = 1
      break
    elif choice == 'a' or choice == 'A':
      choice = 2
      break
  return choice


def main():

  verbose = False
  recursive = False
  rename = True
  dry = False
  mode = 0
  b_r = 0
  overwrite = False
  source = os.getcwd()
  output = os.getcwd()
  skip = -1

# Parse arguments
  for argind, arg in enumerate(sys.argv[1:]):
    if argind == skip: pass
    elif arg == "-v" : verbose = True
    elif arg == "-r" : recursive = True
    elif arg == "-n" : rename = False
    elif arg == "-b" : b_r = 1
    elif arg == "-b1" : b_r = 2
    elif arg == "-b2" : b_r = 3
    elif arg == "-f" : overwrite = True
    elif arg == "-c" : mode = 1
    elif arg == "-c0" : mode = 2
    elif arg == "-o" :
      if len(sys.argv) <= argind+2:
        sys.exit("\nUnspecified Output directory.")
      output = sys.argv[argind+2]
      skip = argind+1

      if not os.path.isdir(output):
        print("\nOutput directory: "+output+" doesnt exist. Creating.")
        try:
          os.makedirs(output)
        except:
          sys.exit("Cant create "+output)

    elif arg in ("-h", "-?") or arg.startswith("-") :
                    sys.exit("wotrepparser scans replay files and sorts them into categories (incomplete, result, complete, clanwar, error)."
                             "\nUsage:" \
                             "\n\nwotrepparser file_or_directory -o output_directory -v -r -n" \
                             "\n\n-o  Specify output directory. Default is current." \
                             "\n-v  Verbose, display every file processed." \
                             "\n-r  Recursive scan of all subdirectories." \
                             "\n-n  Dont rename files." \
                             "\n-b  Dump raw battle_results pickle to output_directory\\b_r\\number.pickle" \
                             "\n-b1 Decode battle_results pickle, save output_directory\\b_r\\number.json" \
                             "\n-b2 Same as above, but human readable json." \
                             "\n-f  Force overwrite. Default is ask." \
                             "\n-c  Copy instead of moving." \
                             "\n-c0 Dry run, dont copy, dont move.")

    elif source == os.getcwd():
      if not os.path.exists(arg):
        sys.exit("\n"+arg+" doesnt exist.")
      source = arg


  print ("\nSource:", source)
  print ("Output:", output)
  print ("Mode  :", ("move","copy","dry run")[mode]+",",("dont rename","rename")[rename]+("",", verbose")[verbose]+("",", recursive dir scan")[recursive]+ \
         ("",", raw battle_results pickle",", decoded battle_results json",", decoded human readable battle_results json")[b_r]+".\n")




  t1 = time.clock()

  if os.path.isfile(source):
    listdir = [source]
  else:
    listdir = custom_listfiles(source, "wotreplay", recursive, "temp.wotreplay")

#  listdir = custom_listfiles("G:\\World_of_Tanks\\replays\\clanwars\\", "wotreplay", False)
#  listdir += custom_listfiles("G:\\World_of_Tanks\\replays\\complete\\", "wotreplay", False)
#  listdir += custom_listfiles("G:\\World_of_Tanks\\replays\\incomplete\\", "wotreplay", False)
#  listdir = {"G:\\World_of_Tanks\\replays\\incomplete\\20121213_0553_usa-T110_39_crimea.wotreplay"}

  if not os.path.exists(output + os.path.sep + "clanwar"):
    os.makedirs(output + os.path.sep + "clanwar")
  if not os.path.exists(output + os.path.sep + "incomplete"):
    os.makedirs(output + os.path.sep + "incomplete")
  if not os.path.exists(output + os.path.sep + "result"):
    os.makedirs(output + os.path.sep + "result")
  if not os.path.exists(output + os.path.sep + "complete"):
    os.makedirs(output + os.path.sep + "complete")
  if not os.path.exists(output + os.path.sep + "error"):
    os.makedirs(output + os.path.sep + "error")
  if b_r>0 and (not os.path.exists(output + os.path.sep + "b_r")):
    os.makedirs(output + os.path.sep + "b_r")

  errors = 0
  dest = ["incomplete", "result", "complete", "complete", "clanwar", "error"]
  stats = [0, 0, 0, 0, 0, 0]

  for files in listdir:
    while True:
#      print ("\n"+files)
      fileo = os.path.basename(files)

      chunks, chunks_bitmask, processing, version = wotdecoder.replay(files,7) #7 means try to decode all three blocks (binary 111)

      if processing == 3 and (len(chunks[0]['vehicles'])!=len(chunks[1][1])) or \
         processing == 4 and chunks[2]['common']['bonusType'] == 5: #fogofwar = cw, bonusType = 5 = cw
        dest_index = 4
        stats[dest_index] += 1
        if rename:
          date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
          clan_tag = ["", ""]
          for playind, player in enumerate(chunks[1][1]):
            if playind == 0:
              first_tag = chunks[1][1][player]['clanAbbrev']
              clan_tag[chunks[1][1][player]['team'] - 1] = first_tag
            elif first_tag != chunks[1][1][player]['clanAbbrev']:
              clan_tag[chunks[1][1][player]['team'] - 1] = chunks[1][1][player]['clanAbbrev']
              break

          winlose=("Loss","Win_")[chunks[1][0]['isWinner']==1]

          clan_tag[0] = clan_tag[0] +"_"*(5-len(clan_tag[0]))
          clan_tag[1] = clan_tag[1] +"_"*(5-len(clan_tag[1]))

# You can change cw filename format here.
          fileo = "cw"+date+"_"+clan_tag[0]+"_"+clan_tag[1]+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"

      elif processing <6 and chunks_bitmask&2: #is second Json available? use it to determine win/loss
        dest_index = processing-1
        stats[dest_index] += 1
        if rename:
          date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
          winlose=("Loss","Win_")[chunks[1][0]['isWinner']==1]
          fileo = date+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"
      elif processing <6 and chunks_bitmask&4: #is pickle available? use it to determine win/loss
        dest_index = processing-1
        stats[dest_index] += 1
        if rename:
          date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
          winlose=("Loss","Win_")[chunks[2]['common']['winnerTeam'] == chunks[2]['personal']['team']]
          fileo = date+"_"+winlose+"_"+wotdecoder.tank[chunks[2]['personal']['typeCompDescr']][0]+"_"+wotdecoder.maps[chunks[2]['common']['arenaTypeID'] & 65535][0]+".wotreplay"
      elif processing ==6: #bugged, but has valid score and can be renamed
        dest_index = 5
        stats[dest_index] += 1
        if rename:
          date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
          winlose=("Loss","Win_")[chunks[1][0]['isWinner']==1]
          fileo = date+"_"+winlose+"_"+"-".join(chunks[0]['playerVehicle'].split("-")[1:])+"_"+chunks[0]['mapName']+".wotreplay"
      elif processing ==8: #bugged, but has valid pickle, can be renamed and moved to result
        dest_index = 1
        stats[dest_index] += 1
        if rename:
          date = datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S').strftime('%Y%m%d_%H%M')
          winlose=("Loss","Win_")[chunks[2]['common']['winnerTeam'] == chunks[2]['personal']['team']]
          fileo = date+"_"+winlose+"_"+wotdecoder.tank[chunks[2]['personal']['typeCompDescr']][0]+"_"+wotdecoder.maps[chunks[2]['common']['arenaTypeID'] & 65535][0]+".wotreplay"
      elif processing ==1: #incomplete
        dest_index = processing-1
        stats[dest_index] += 1
      elif processing >6: #bugged, cant be renamed
        dest_index = 5
        stats[dest_index] += 1

      fileo = output + os.path.sep + dest[dest_index] + os.path.sep + fileo
      exists = os.path.isfile(fileo)
      ask = 0
      if not overwrite and exists:
        ask = getkeyboard(fileo, files)
        if ask == 2: overwrite = True
      else: ask = 1

      if mode == 0 and ask>0:
          shutil.move(files, fileo)

      elif mode == 1 and ask>0:
          shutil.copy(files, fileo)

      fileb_r = ""
      if b_r >0 and chunks_bitmask&4:
        fileb_r = output + os.path.sep + "b_r" + os.path.sep + str(chunks[2]['arenaUniqueID']) +("",".pickle",".json",".json")[b_r]
        exists = os.path.isfile(fileb_r)
        ask = 0
        if not overwrite and exists:
          ask = getkeyboard(fileb_r)
          if ask == 2: overwrite = True
        else: ask = 1

        if b_r == 1 and ask>0:
          try:
            fo = open(fileb_r,"wb")
            f = open(files, "rb")
            f.seek(8)
            seek_size = struct.unpack("i",f.read(4))[0]
            f.seek(seek_size,1)
            if chunks_bitmask&2: #replay with Pickle can have 2 or 3 blocks, we are only interested in the last one and need to skip others
              seek_size = struct.unpack("i",f.read(4))[0]
              f.seek(seek_size,1)
            third_size = struct.unpack("i",f.read(4))[0]
            third_chunk = f.read(third_size)
            f.close()
          except:
            raise
          else:
            fo.write(third_chunk)
            fo.close()

        elif b_r == 2 and ask>0:
          try:
            fo = open(fileb_r,"w")
          except:
            raise
          else:
            json.dump(chunks[2],fo)
            fo.close()

        elif b_r == 3 and ask>0:
          try:
            fo = open(fileb_r,"w")
          except:
            raise
          else:
            json.dump(chunks[2], fo, sort_keys=True, indent=4)
            fo.close()

      if verbose:
        print ("\n"+files)
        print ("", dest[dest_index], " | ", wotdecoder.status[processing])
        print (fileo)
        print (fileb_r)
      break


  t2 = time.clock()


  print ("\n{0:10} {1:>5}".format("Processed", str(len(listdir))))

  del dest[2]
  stats[2] += stats[3]
  del stats[3]
  for x in range(0, len(dest)):
    print ("{0:10} {1:>5}".format(dest[x], stats[x]))

  print  ("Took %0.3fms"  % ((t2-t1)*1000))

main()
