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
import pickle
# most of those imports are redundand, im lazy like that


def custom_listdir(path):
# Returns the content of a directory by showing directories first
# and then files by ordering the names alphabetically

  dirs = sorted([d for d in os.listdir(path) if os.path.isdir(path + os.path.sep + d)])
  dirs.extend(sorted([f for f in os.listdir(path) if os.path.isfile(path + os.path.sep + f)]))

  return dirs


def main():

  file = "1"
  t1 = time.clock()

# Ready current dir, ./incomplete/ ./complete/ and ./clanwars/
  listdir = custom_listdir(".") + ["./incomplete/" + i for i in custom_listdir("./incomplete/")] + ["./complete/" + i for i in custom_listdir("./complete/")] + ["./clanwars/" + i for i in custom_listdir("./clanwars/")]
#  print (listdir)
  
  if len(sys.argv) < 2: sys.exit("Give name of a player you want to find as a parameter")

  lookingfor = sys.argv[1]

  for files in listdir:
   if (files.endswith(".wotreplay") and not files.endswith("temp.wotreplay")):

      f = open(files, "rb")
      f.seek(8)
      first_size = struct.unpack("i",f.read(4))[0]
      first_chunk = f.read(first_size)
      first_chunk_decoded = json.loads(first_chunk.decode('utf-8'))

#      pprint (first_chunk_decoded)      

      for a in first_chunk_decoded['vehicles']:
        name = first_chunk_decoded['vehicles'][a]['name']
        clan = first_chunk_decoded['vehicles'][a]['clanAbbrev']
#        print (name,"["+clan+"]")
        
        if name == lookingfor:
          print (name,"["+clan+"]","    ",files)
          
          f.seek(4)
          blocks = struct.unpack("i",f.read(4))[0]
          if (blocks==1): f.close(); break
          if ((datetime.strptime(first_chunk_decoded['dateTime'][0:10], "%d.%m.%Y") >= datetime(2012, 11, 1)) and blocks==2): break
          f.seek(12+first_size)
          second_size = struct.unpack("i",f.read(4))[0]
          second_chunk = f.read(second_size)
          second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
          print ("frags =", second_chunk_decoded[2][a]['frags'])
       
      f.close() 


  t2 = time.clock()
  print ()
  print  ("Shit took %0.3fms"  % ((t2-t1)*1000))


main()