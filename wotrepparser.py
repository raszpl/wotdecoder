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
# most of those imports are redundand, im lazy like that

wazup = {
              0: 'Processing',
              1: 'Incomplete replay',
              2: 'No compatible blocks found, file is all binary?',
              3: 'Same team clan mismatch',
              4: 'Opposite team clan mismatch',
              5: 'Same clan on both sides, WTF?',
              11: 'No fog of war = not a clanwar',
              10: 'CW'
        }

def custom_listfiles(path):
# Returns the list of .wotreplay files by ordering the names alphabetically. Omits temp.wotreplay.

  files = sorted([f for f in os.listdir(path) if os.path.isfile(path + os.path.sep + f) and f.endswith(".wotreplay") and f!="temp.wotreplay"])

  return files


def main():

  file = "1"
  t1 = time.clock()

  for files in custom_listfiles("."):
     while True:
      processing = 0
      f = open(files, "rb")
      f.seek(4)
      blocks = struct.unpack("i",f.read(4))[0]

# 8.1 Adds new unencrypted Python pickle block containing your match stats
# Before 8.1 (< 20121101) 
#  Json + binary = 1 = incomplete.
#  Json + Json + binary = 2 = complete.
# After  8.1 (>=20121101)
#  Json + binary = 1 = incomplete. 
#  Json + pickle + binary = 2 = incomplete !!!WTF!!! 
#  Json + Json + pickle + binary = 3 = complete.
# Sadly there is no version number in Json, and date is unreliable because its local time. Replays saved on day of
# patch are dicey and some completed ones might be counted as incomplete due to patch downtime not being synced 
# with local time.


#      f.seek(8)
      first_size = struct.unpack("i",f.read(4))[0]
#      print (first_size, files)

      if (blocks==1): processing =1; f.close(); break
# blocks==1 is always incomplete

      if ((blocks!=2) and (blocks!=3)): processing =2; f.close(); break
# We can only process blocks==2 or 3

      first_chunk = f.read(first_size)
      first_chunk_decoded = json.loads(first_chunk.decode('utf-8'))

      if ((datetime.strptime(first_chunk_decoded['dateTime'][0:10], "%d.%m.%Y") >= datetime(2012, 11, 1)) and blocks==2): processing =1; f.close(); break
# >=20121101 and blocks==2 means incomplete
# sadly there is still possibility we just stopped processing valid completed replay
          
      
      second_size = struct.unpack("i",f.read(4))[0]
#      print (second_size, files)

      second_chunk = f.read(second_size)
      second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
#      pprint (second_chunk_decoded)

      f.close()

# This prints out JSON heared containing all the info at the start of the map
#     pprint (first_chunk_decoded)
# This prints out JSON heared containing map results = scores, damage, awards
#     pprint (second_chunk_decoded)


# list clantags of ur team 
 #     for a in first_chunk_decoded['vehicles']:
  #      print (first_chunk_decoded['vehicles'][a]['clanAbbrev'])


#      for a in first_chunk_decoded:

 #     pprint (first_chunk_decoded)
 #     print (first_chunk_decoded['playerID'])
#      print (first_chunk_decoded['vehicles'][first_chunk_decoded['playerID']])
#      print (" number of players: ",len(first_chunk_decoded['vehicles']))
      
#      count = len(first_chunk_decoded['vehicles'])
      #print ( first_chunk_decoded['vehicles'][first_chunk_decoded['vehicles'].keys()[0]] )


      if (len(first_chunk_decoded['vehicles'])==len(second_chunk_decoded[1])): processing =11; break

      first_tag = ""
      first_team = ""
      second_tag = ""

      for num in second_chunk_decoded[1]:
       a = second_chunk_decoded[1][num]
       if (first_tag == ""):
        first_tag = a['clanAbbrev']
        first_team = a['team']
       elif (a['team'] != first_team) and (a['clanAbbrev'] != first_tag) and (second_tag == ""):
        second_tag = a['clanAbbrev']
       elif (a['team'] == first_team) and (a['clanAbbrev'] != first_tag):
        processing =3; break
       elif (a['team'] != first_team) and (a['clanAbbrev'] == first_tag):
        processing =5; break
       elif (a['team'] != first_team) and (a['clanAbbrev'] != second_tag):
        processing =4; break

        
# At this point we are sure this is a CW
      processing =10; break

# dont remember what this commented out part did, I used it during development
# might be usefull if you are trying to write some custom filters
     
  #    for a in first_chunk_decoded['vehicles']:
 #       clan = first_chunk_decoded['vehicles'][a]['clanAbbrev']
 #       if (struct.unpack("i",f.read(4))[0])==2: 


     #  print (first_chunk_decoded['gameplayType'])
#      for a in first_chunk_decoded:
 #      print (first_chunk_decoded['gameplayType'])
  #     print ([a])
      
 #      second_size = struct.unpack("i",f.read(4))
#      print (second_size[0], size, size-second_size[0]-first_size[0])

#     f.seek(second_size[0],0)
#       second_chunk = f.read(second_size[0])
  #     second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
       
 #      print (" number of players2 ",len(second_chunk_decoded))
 #      pprint (second_chunk_decoded)
#     print (second_chunk.decode("utf-8"))



 #     for a in second_chunk_decoded[1]:
  #     print (second_chunk_decoded[1][a]['clanAbbrev'])
    


# uncomment those to see what is happening with processed files
#     print ()
#     print (files)
#     print (wazup[processing])

     if processing==1:
      if not os.path.exists("incomplete"):
       os.makedirs("incomplete")
# move or copy? too lazy to make it a command line parameter       
#      shutil.copy(files, "incomplete/"+files)
      shutil.move(files, "incomplete/"+files)
      print ()
      print ("Incomplete --> ", files)

     elif processing==10:
      if not os.path.exists("clanwars"):
        os.makedirs("clanwars")
      
      if first_team != 1:
       first_tag, second_tag = second_tag, first_tag
      print ()
      print ("CW between",first_tag,"and", second_tag)

      d = datetime.strptime(first_chunk_decoded['dateTime'], '%d.%m.%Y %H:%M:%S')
      d= d.strftime('%Y%m%d_%H%M')
      
      winlose=("Loss","Win")[second_chunk_decoded[0]['isWinner']==1]

      first_tag = first_tag +"_"*(5-len(first_tag))
      second_tag = second_tag +"_"*(5-len(second_tag))
# You can change cw filename format here.
      newfile = "clanwars/"+"cw"+d+"_"+first_tag+"_"+second_tag+"_"+winlose+"_"+"-".join(first_chunk_decoded['playerVehicle'].split("-")[1:])+"_"+first_chunk_decoded['mapName']+".wotreplay"

# move or copy? too lazy to make it a command line parameter
#      shutil.copy2(files, newfile)
      shutil.move(files, newfile)
      print ("CW --> ", newfile)

     elif processing==11:
      if not os.path.exists("complete"):
       os.makedirs("complete")
# move or copy? too lazy to make it a command line parameter
#      shutil.copy(files, "complete/"+files)
      shutil.move(files, "complete/"+files)
      print ()
      print ("Complete --> ", files)

     else:
      print ()
      print (files)
      print (wazup[processing])


  t2 = time.clock()
  print ()
  print  ("Processing took %0.3fms"  % ((t2-t1)*1000))


main()