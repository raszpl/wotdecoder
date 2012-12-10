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
# most of those imports are redundand, im lazy like that


def custom_listfiles(path):
# Returns the list of .wotreplay files by ordering the names alphabetically. Omits temp.wotreplay.

  files = sorted([f for f in os.listdir(path) if os.path.isfile(path + os.path.sep + f) and f.endswith(".wotreplay") and f!="temp.wotreplay"])

  return files


def main():

  t1 = time.clock()

# Parse parameters
  if len(sys.argv) == 1 or len(sys.argv) > 3: sys.argv[1:] = ["-h"]
    
  nickname = "*"
  clantag = "*"
  for arg in sys.argv[1:]:
#    print (arg)
    if arg.startswith("-") : 
    	              sys.exit("Findplayer can search for players using nickname and/or clantag." 
    	                       "\nusage:" \
    	                       "\nfindplayer nickname [clantag]" \
    	                       "\nTry `*` for string wildcard, `?` for character wildcard. Searching is case insensitive." \
    	                       "\nExamples:" \
    	                       "\n`*z_?l [1?3]` will match Rasz_pl[123]" \
    	                       "\n`[*]` will match any person in any clan." \
    	                       "\n`[]` will only match people without clan." \
    	                       "\n`??` will list all people with 2 letter nicknames." \
    	                       "\n`*` will match everyone.")
    elif arg.startswith("[") and arg.endswith("]"): clantag = arg[1:-1]
    else : nickname = arg


  print ("Looking for nickname:", nickname, " clantag:", clantag)

# Prepare regex filters
  regexnickname = fnmatch.translate(nickname)
  regexclantag = fnmatch.translate(clantag)
  reobjnickname = re.compile(regexnickname, re.IGNORECASE)
  reobjclantag = re.compile(regexclantag, re.IGNORECASE)

# Prepare list of .wotreplay files in current dir, ./incomplete/ ./complete/ and ./clanwars/
  listdir = custom_listfiles(".") + ["./incomplete/" + i for i in custom_listfiles("./incomplete/")] + ["./complete/" + i for i in custom_listfiles("./complete/")] + ["./clanwars/" + i for i in custom_listfiles("./clanwars/")]

  for files in listdir:
     while True:
      f = open(files, "rb")
      f.seek(4)
      blocks = struct.unpack("i",f.read(4))[0]
# Json data is only in files with blocks==1, 2 or 3
      if ((blocks!=1) and (blocks!=2) and (blocks!=3)): f.close(); break

      first_size = struct.unpack("i",f.read(4))[0]
      first_chunk = f.read(first_size)
      first_chunk_decoded = json.loads(first_chunk.decode('utf-8'))

#      pprint (first_chunk_decoded)      

      for a in first_chunk_decoded['vehicles']:
        name = first_chunk_decoded['vehicles'][a]['name']
        clan = first_chunk_decoded['vehicles'][a]['clanAbbrev']
#        print (name,"["+clan+"]")
        
        if reobjnickname.match(name) and reobjclantag.match(clan):
          print (name,"["+clan+"]","    ",files)
          
          f.seek(4)
          blocks = struct.unpack("i",f.read(4))[0]
          if (blocks==1): f.close(); break
# Battle summary Json only available when blocks==2 or 3
          if ((blocks!=2) and (blocks!=3)): processing =2; f.close(); break
          if ((datetime.strptime(first_chunk_decoded['dateTime'][0:10], "%d.%m.%Y") >= datetime(2012, 11, 1)) and blocks==2): f.close(); break
# >=20121101 and blocks==2 means incomplete

          f.seek(12+first_size)
          second_size = struct.unpack("i",f.read(4))[0]
          second_chunk = f.read(second_size)
          second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
          print ("frags =", second_chunk_decoded[2][a]['frags'],",",("Loss","Win ")[second_chunk_decoded[0]['isWinner']==1],",",("Died","Survived")[second_chunk_decoded[1][a]['isAlive']==1],"in",second_chunk_decoded[1][a]['vehicleType'])
      f.close() 
      break


  t2 = time.clock()
  print ()
  print  ("Processing took %0.3fms"  % ((t2-t1)*1000))


main()