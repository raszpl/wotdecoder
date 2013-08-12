# World Of Tanks replay file/battle result parser/decoder.
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

import struct
import json
from pprint import pprint
from datetime import datetime
import os
import io

__all__ = ["replay", "battle_result", "status"]


# Pickle opcodes.  See pickletools.py for extensive docs.  The listing
# here is in kind-of alphabetical order of 1-character pickle code.
# pickletools groups them by purpose.

MARK           = b'('   # push special markobject on stack
STOP           = b'.'   # every pickle ends with STOP
#POP            = b'0'   # discard topmost stack item
#POP_MARK       = b'1'   # discard stack top through topmost markobject
#DUP            = b'2'   # duplicate top stack item
FLOAT          = b'F'   # push float object; decimal string argument
BINFLOAT       = b'G'   # push float; arg is 8-byte float encoding
INT            = b'I'   # push integer or bool; decimal string argument
BININT         = b'J'   # push four-byte signed int
BININT1        = b'K'   # push 1-byte unsigned int
LONG           = b'L'   # push long; decimal string argument
BININT2        = b'M'   # push 2-byte unsigned int
NONE           = b'N'   # push None
#PERSID         = b'P'   # push persistent object; id is taken from string arg
#BINPERSID      = b'Q'   #  "       "         "  ;  "  "   "     "  stack
#REDUCE         = b'R'   # apply callable to argtuple, both on stack
STRING         = b'S'   # push string; NL-terminated string argument
BINSTRING      = b'T'   # push string; counted binary string argument
SHORT_BINSTRING= b'U'   #  "     "   ;    "      "       "      " < 256 bytes
#UNICODE        = b'V'   # push Unicode string; raw-unicode-escaped'd argument
#BINUNICODE     = b'X'   #   "     "       "  ; counted UTF-8 string argument
APPEND         = b'a'   # append stack top to list below it
#BUILD          = b'b'   # call __setstate__ or __dict__.update()
#GLOBAL         = b'c'   # push self.find_class(modname, name); 2 string args
DICT           = b'd'   # build a dict from stack items
EMPTY_DICT     = b'}'   # push empty dict
APPENDS        = b'e'   # extend list on stack by topmost stack slice
GET            = b'g'   # push item from memo on stack; index is string arg
#BINGET         = b'h'   #   "    "    "    "   "   "  ;   "    " 1-byte arg
#INST           = b'i'   # build & push class instance
#LONG_BINGET    = b'j'   # push item from memo on stack; index is 4-byte arg
LIST           = b'l'   # build list from topmost stack items
EMPTY_LIST     = b']'   # push empty list
#OBJ            = b'o'   # build & push class instance
PUT            = b'p'   # store stack top in memo; index is string arg
BINPUT         = b'q'   #   "     "    "   "   " ;   "    " 1-byte arg
#LONG_BINPUT    = b'r'   #   "     "    "   "   " ;   "    " 4-byte arg
SETITEM        = b's'   # add key+value pair to dict
TUPLE          = b't'   # build tuple from topmost stack items
EMPTY_TUPLE    = b')'   # push empty tuple
SETITEMS       = b'u'   # modify dict by adding topmost key+value pairs

# Protocol 2

PROTO          = b'\x80'  # identify pickle protocol
#NEWOBJ         = b'\x81'  # build object by applying cls.__new__ to argtuple
#EXT1           = b'\x82'  # push object from extension registry; 1-byte index
#EXT2           = b'\x83'  # ditto, but 2-byte index
#EXT4           = b'\x84'  # ditto, but 4-byte index
#TUPLE1         = b'\x85'  # build 1-tuple from stack top
TUPLE2         = b'\x86'  # build 2-tuple from two topmost stack items
TUPLE3         = b'\x87'  # build 3-tuple from three topmost stack items
NEWTRUE        = b'\x88'  # push True
NEWFALSE       = b'\x89'  # push False
LONG1          = b'\x8a'  # push long from < 256 bytes
#LONG4          = b'\x8b'  # push really big long


# An instance of _Stop is raised by Unpickler.load_stop() in response to
# the STOP opcode, passing the object that is the common_decoded of unpickling.
class _Stop(Exception):
    def __init__(self, value):
        self.value = value

# Unpickling machinery
class _Unpickler:

    def __init__(self, file):
        """This takes a file-like object for reading a pickle data stream.

        The file-like object must have two methods, a read() method that
        takes an integer argument, and a readline() method that requires no
        arguments.  Both methods should return a string.  Thus file-like
        object can be a file object opened for reading, a StringIO object,
        or any other custom object that meets this interface.
        """
        self.readline = file.readline
        self.read = file.read
        self.memo = {}

    def load(self):
        """Read a pickled object representation from the open file.

        Return the reconstituted object hierarchy specified in the file.
        """
        self.mark = object() # any new unique object
        self.stack = []
        self.append = self.stack.append
        read = self.read
        dispatch = self.dispatch

        try:
            while 1:
                key = read(1)
#                print (key)
                dispatch[key](self)
        except _Stop as stopinst:
            return stopinst.value


    # Return largest index k such that self.stack[k]is self.mark.
    # If the stack doesn't contain a mark, eventually raises IndexError.
    # This could be sped by maintaining another stack, of indices at which
    # the mark appears.  For that matter, the latter stack would suffice,
    # and we wouldn't need to push mark objects on self.stack at all.
    # Doing so is probably a good thing, though, since if the pickle is
    # corrupt (or hostile) we may get a clue from finding self.mark embedded
    # in unpickled objects.
    def marker(self):
        stack = self.stack
        mark = self.mark
        k = len(stack)-1
        while stack[k]is not mark: k = k-1
        return k

    dispatch = {}

    def load_eof(self):
        raise EOFError
    dispatch['']= load_eof

    def load_proto(self):
        proto = ord(self.read(1))
        if not 0 <= proto <= 2:
            raise ValueError("unsupported pickle protocol: %d" % proto)
    dispatch[PROTO]= load_proto

    def load_persid(self):
        pid = self.readline()[:-1]
        self.append(self.persistent_load(pid))
#    dispatch[PERSID]= load_persid

    def load_binpersid(self):
        pid = self.stack.pop()
        self.append(self.persistent_load(pid))
#    dispatch[BINPERSID]= load_binpersid

    def load_none(self):
        self.append(None)
    dispatch[NONE]= load_none

    def load_false(self):
        self.append(False)
    dispatch[NEWFALSE]= load_false

    def load_true(self):
        self.append(True)
    dispatch[NEWTRUE]= load_true

    def load_int(self):
        data = self.readline()
        if data == b'00\n':
            val = False
        elif data == b'01\n':
            val = True
        else:
            try:
                val = int(data)
            except ValueError:
                val = long(data)
        self.append(val)
    dispatch[INT]= load_int

    def load_binint(self):
        self.append(struct.unpack('<i', self.read(4))[0])
    dispatch[BININT]= load_binint

    def load_binint1(self):
        self.append(ord(self.read(1)))
    dispatch[BININT1]= load_binint1

    def load_binint2(self):
        self.append(struct.unpack('<i', self.read(2) + b'\000\000')[0])
    dispatch[BININT2]= load_binint2

    def load_long(self):
        val = self.readline()[:-1].decode("ascii")
        if val and val[-1]== 'L':
            val = val[:-1]
        self.append(int(val, 0))
    dispatch[LONG]= load_long

    def load_long1(self):
        n = ord(self.read(1))
        bytes = self.read(n)
        self.append(int.from_bytes(bytes, byteorder='little', signed=True))
    dispatch[LONG1]= load_long1

    def load_long4(self):
#        n = mloads('i' + self.read(4))
        bytes = self.read(n)
        self.append(int.from_bytes(bytes, byteorder='little', signed=True))
#    dispatch[LONG4]= load_long4

    def load_float(self):
        self.append(float(self.readline()[:-1]))
    dispatch[FLOAT]= load_float

    def load_binfloat(self, unpack=struct.unpack):
        self.append(unpack('>d', self.read(8))[0])
    dispatch[BINFLOAT]= load_binfloat

    def load_string(self):
        orig = self.readline()[:-1]
        if not ((orig.startswith(b'"') and orig.endswith(b'"')) or (orig.startswith(b"'") and orig.endswith(b"'"))):
          raise ValueError("insecure string pickle")
        self.append(orig[1:-1].decode('unicode_escape'))
    dispatch[STRING]= load_string

    def load_binstring(self):
        bla = self.read(4)
        dest = bytearray(4)
        for deind, val in enumerate(bla):
          dest[deind]= val

        len = (dest[3]<< 24)+(dest[2]<< 16)+(dest[1]<< 8)+dest[0]
        self.append(self.read(len))
    dispatch[BINSTRING]= load_binstring

    def load_unicode(self):
        self.append(unicode(self.readline()[:-1],'raw-unicode-escape'))
#    dispatch[UNICODE]= load_unicode

    def load_binunicode(self):
#        len = mloads('i' + self.read(4))
        self.append(unicode(self.read(len),'utf-8'))
#    dispatch[BINUNICODE]= load_binunicode

    def load_short_binstring(self):
        len = ord(self.read(1))
        self.append(self.read(len))
    dispatch[SHORT_BINSTRING]= load_short_binstring

    def load_tuple(self):
        k = self.marker()
        self.stack[k:]= [tuple(self.stack[k+1:])]
    dispatch[TUPLE]= load_tuple

    def load_empty_tuple(self):
        self.stack.append(())
    dispatch[EMPTY_TUPLE]= load_empty_tuple

    def load_tuple1(self):
        self.stack[-1]= (self.stack[-1],)
#    dispatch[TUPLE1]= load_tuple1

    def load_tuple2(self):
        self.stack[-2:]= [(self.stack[-2], self.stack[-1])]
    dispatch[TUPLE2]= load_tuple2

    def load_tuple3(self):
        self.stack[-3:]= [(self.stack[-3], self.stack[-2], self.stack[-1])]
    dispatch[TUPLE3]= load_tuple3

    def load_empty_list(self):
        self.stack.append([])
    dispatch[EMPTY_LIST]= load_empty_list

    def load_empty_dictionary(self):
        self.stack.append({})
    dispatch[EMPTY_DICT]= load_empty_dictionary

    def load_list(self):
        k = self.marker()
        self.stack[k:]= [self.stack[k+1:]]
    dispatch[LIST]= load_list

    def load_dict(self):
        k = self.marker()
        d = {}
        items = self.stack[k+1:]
        for i in range(0, len(items), 2):
            key = items[i]
            value = items[i+1]
            d[key]= value
        self.stack[k:]= [d]
    dispatch[DICT]= load_dict

    # INST and OBJ differ only in how they get a class object.  It's not
    # only sensible to do the rest in a common routine, the two routines
    # previously diverged and grew different bugs.
    # klass is the class to instantiate, and k points to the topmost mark
    # object, following which are the arguments for klass.__init__.
    def _instantiate(self, klass, k):
        args = tuple(self.stack[k+1:])
        del self.stack[k:]
        instantiated = 0
        if (not args and
                type(klass) is ClassType and
                not hasattr(klass, "__getinitargs__")):
            try:
                value = _EmptyClass()
                value.__class__ = klass
                instantiated = 1
            except RuntimeError:
                # In restricted execution, assignment to inst.__class__ is
                # prohibited
                pass
        if not instantiated:
            try:
                value = klass(*args)
            except TypeError as err:
                raise TypeError("in constructor for %s: %s" %
                                (klass.__name__, str(err)), sys.exc_info()[2])
        self.append(value)

    def load_inst(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self._instantiate(klass, self.marker())
#    dispatch[INST]= load_inst

    def load_obj(self):
        # Stack is ... markobject classobject arg1 arg2 ...
        k = self.marker()
        klass = self.stack.pop(k+1)
        self._instantiate(klass, k)
#    dispatch[OBJ]= load_obj

    def load_newobj(self):
        args = self.stack.pop()
        cls = self.stack[-1]
        obj = cls.__new__(cls, *args)
        self.stack[-1]= obj
#    dispatch[NEWOBJ]= load_newobj

    def load_global(self):
        module = self.readline()[:-1]
        name = self.readline()[:-1]
        klass = self.find_class(module, name)
        self.append(klass)
#    dispatch[GLOBAL]= load_global

    def load_ext1(self):
        code = ord(self.read(1))
        self.get_extension(code)
#    dispatch[EXT1]= load_ext1

    def load_ext2(self):
#        code = mloads('i' + self.read(2) + '\000\000')
        self.get_extension(code)
#    dispatch[EXT2]= load_ext2

    def load_ext4(self):
#        code = mloads('i' + self.read(4))
        self.get_extension(code)
#    dispatch[EXT4]= load_ext4

    def get_extension(self, code):
        nil = []
        obj = _extension_cache.get(code, nil)
        if obj is not nil:
            self.append(obj)
            return
        key = _inverted_registry.get(code)
        obj = self.find_class(*key)
        _extension_cache[code]= obj
        self.append(obj)

    def find_class(self, module, name):
        # Subclasses may override this
        __import__(module)
        mod = sys.modules[module]
        klass = getattr(mod, name)
        return klass

    def load_reduce(self):
        stack = self.stack
        args = stack.pop()
        func = stack[-1]
        value = func(*args)
        stack[-1]= value
#    dispatch[REDUCE]= load_reduce

    def load_pop(self):
        del self.stack[-1]
#    dispatch[POP]= load_pop

    def load_pop_mark(self):
        k = self.marker()
        del self.stack[k:]
#    dispatch[POP_MARK]= load_pop_mark

    def load_dup(self):
        self.append(self.stack[-1])
#    dispatch[DUP]= load_dup

    def load_get(self):
        self.append(self.memo[self.readline()[:-1]])
    dispatch[GET]= load_get

    def load_binget(self):
        i = ord(self.read(1))
        self.append(self.memo[repr(i)])
#    dispatch[BINGET]= load_binget

    def load_long_binget(self):
#        i = mloads('i' + self.read(4))
        self.append(self.memo[repr(i)])
#    dispatch[LONG_BINGET]= load_long_binget

    def load_put(self):
        self.memo[self.readline()[:-1]]= self.stack[-1]
    dispatch[PUT]= load_put

    def load_binput(self):
        i = ord(self.read(1))
        self.memo[repr(i)]= self.stack[-1]
    dispatch[BINPUT]= load_binput

    def load_long_binput(self):
#        i = mloads('i' + self.read(4))
        self.memo[repr(i)]= self.stack[-1]
#    dispatch[LONG_BINPUT]= load_long_binput

    def load_append(self):
        stack = self.stack
        value = stack.pop()
        list = stack[-1]
        list.append(value)
    dispatch[APPEND]= load_append

    def load_appends(self):
        stack = self.stack
        mark = self.marker()
        list = stack[mark - 1]
        list.extend(stack[mark + 1:])
        del stack[mark:]
    dispatch[APPENDS]= load_appends

    def load_setitem(self):
        stack = self.stack
        value = stack.pop()
        key = stack.pop()
        dict = stack[-1]
        dict[key]= value
    dispatch[SETITEM]= load_setitem

    def load_setitems(self):
        stack = self.stack
        mark = self.marker()
        dict = stack[mark - 1]
        for i in range(mark + 1, len(stack), 2):
            dict[stack[i]]= stack[i + 1]

        del stack[mark:]
    dispatch[SETITEMS]= load_setitems


    def load_mark(self):
        self.append(self.mark)
    dispatch[MARK]= load_mark

    def load_stop(self):
        value = self.stack.pop()
        raise _Stop(value)
    dispatch[STOP]= load_stop

# Helper class for load_inst/load_obj

class _EmptyClass:
    pass


class _Decoder:

    def decode_details(data):
      detail = [
                "spotted",
                "killed",
                "hits",
                "he_hits",
                "pierced",
                "damageDealt",
                "damageAssisted",
                "crits",
                "fire"
               ]
      details = {}

      binlen = len(data) // 22
#      print (len(data))
      for x in range(0, binlen):
        offset = 4*binlen + x*18
        vehic = struct.unpack('i', data[x*4:x*4+4])[0]
        detail_values = struct.unpack('hhhhhhhhh', data[offset:offset+18])
        details[str(vehic)]= dict(zip(detail, detail_values))
#        pprint (data[offset:offset+18].encode('raw_unicode_escape'))
      return details

    def decode_vehicle(data):
#      print(len(data))
#      print(data)
      version = 0

      vehicle = {}
      if len(data) == 30: # 30 = up to 8.3

        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["he_hits"]= data[5]
        vehicle["pierced"]= data[6]
        vehicle["damageDealt"]= data[7]
        vehicle["damageAssisted"]= data[8]
        vehicle["damageReceived"]= data[9]
        vehicle["shotsReceived"]= data[10]
        vehicle["spotted"]= data[11]
        vehicle["damaged"]= data[12]
        vehicle["kills"]= data[13]
        vehicle["tdamageDealt"]= data[14]
        vehicle["tkills"]= data[15]
        vehicle["isTeamKiller"]= data[16]
        vehicle["capturePoints"]= data[17]
        vehicle["droppedCapturePoints"]= data[18]
        vehicle["mileage"]= data[19]
        vehicle["lifeTime"]= data[20]
        vehicle["killerID"]= data[21]
        vehicle["achievements"]= data[22]
        vehicle["repair"]= data[23]
        vehicle["freeXP"]= data[24]
        vehicle["details"]= _Decoder.decode_details(data[25])
        vehicle["accountDBID"]= str(data[26])
        vehicle["team"]= data[27]
        vehicle["typeCompDescr"]= data[28]
        vehicle["gold"]= data[29]

      elif len(data) == 32: # 32 = 8.4
        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["thits"]= data[5]
        vehicle["he_hits"]= data[6]
        vehicle["pierced"]= data[7]
        vehicle["damageDealt"]= data[8]
        vehicle["damageAssisted"]= data[9]
        vehicle["damageReceived"]= data[10]
        vehicle["shotsReceived"]= data[11]
        vehicle["spotted"]= data[12]
        vehicle["damaged"]= data[13]
        vehicle["kills"]= data[14]
        vehicle["tdamageDealt"]= data[15]
        vehicle["tkills"]= data[16]
        vehicle["isTeamKiller"]= data[17]
        vehicle["capturePoints"]= data[18]
        vehicle["droppedCapturePoints"]= data[19]
        vehicle["mileage"]= data[20]
        vehicle["lifeTime"]= data[21]
        vehicle["killerID"]= data[22]
        vehicle["achievements"]= data[23]
        vehicle["potentialDamageReceived"]= data[24]
        vehicle["repair"]= data[25]
        vehicle["freeXP"]= data[26]
        vehicle["details"]= _Decoder.decode_details(data[27])
        vehicle["accountDBID"]= str(data[28])
        vehicle["team"]= data[29]
        vehicle["typeCompDescr"]= data[30]
        vehicle["gold"]= data[31]

      elif len(data) == 37: # 37 = 8.6
        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["thits"]= data[5]
        vehicle["he_hits"]= data[6]
        vehicle["pierced"]= data[7]
        vehicle["damageDealt"]= data[8]
        vehicle["damageAssistedRadio"]= data[9]
        vehicle["damageAssistedTrack"]= data[10]
        vehicle["damageReceived"]= data[11]
        vehicle["shotsReceived"]= data[12]
        vehicle["noDamageShotsReceived"]= data[13]
        vehicle["heHitsReceived"]= data[14]
        vehicle["piercedReceived"]= data[15]
        vehicle["spotted"]= data[16]
        vehicle["damaged"]= data[17]
        vehicle["kills"]= data[18]
        vehicle["tdamageDealt"]= data[19]
        vehicle["tkills"]= data[20]
        vehicle["isTeamKiller"]= data[21]
        vehicle["capturePoints"]= data[22]
        vehicle["droppedCapturePoints"]= data[23]
        vehicle["mileage"]= data[24]
        vehicle["lifeTime"]= data[25]
        vehicle["killerID"]= data[26]
        vehicle["achievements"]= data[27]
        vehicle["potentialDamageReceived"]= data[28]
        vehicle["repair"]= data[29]
        vehicle["freeXP"]= data[30]
        vehicle["details"]= _Decoder.decode_details(data[31])
        vehicle["accountDBID"]= str(data[32])
        vehicle["team"]= data[33]
        vehicle["typeCompDescr"]= data[34]
        vehicle["gold"]= data[35]
        vehicle["deathReason"]= data[36]

      elif len(data) == 50: # 50 = up to 8.3
        version = 830
        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["he_hits"]= data[5]
        vehicle["pierced"]= data[6]
        vehicle["damageDealt"]= data[7]
        vehicle["damageAssisted"]= data[8]
        vehicle["damageReceived"]= data[9]
        vehicle["shotsReceived"]= data[10]
        vehicle["spotted"]= data[11]
        vehicle["damaged"]= data[12]
        vehicle["kills"]= data[13]
        vehicle["tdamageDealt"]= data[14]
        vehicle["tkills"]= data[15]
        vehicle["isTeamKiller"]= data[16]
        vehicle["capturePoints"]= data[17]
        vehicle["droppedCapturePoints"]= data[18]
        vehicle["mileage"]= data[19]
        vehicle["lifeTime"]= data[20]
        vehicle["killerID"]= data[21]
        vehicle["achievements"]= data[22]
        vehicle["repair"]= data[23]
        vehicle["freeXP"]= data[24]
        vehicle["details"]= _Decoder.decode_details(data[25])
        vehicle["accountDBID"]= data[26]
        vehicle["team"]= data[27]
        vehicle["typeCompDescr"]= data[28]
        vehicle["gold"]= data[29]
        vehicle["autoRepairCost"]= data[40]
        vehicle["xpPenalty"]= data[30]
        vehicle["creditsPenalty"]= data[31]
        vehicle["creditsContributionIn"]= data[32]
        vehicle["creditsContributionOut"]= data[33]
        vehicle["tmenXP"]= data[34]
        vehicle["eventCredits"]= data[35]
        vehicle["eventFreeXP"]= data[36] #[36, 38]?
        vehicle["eventXP"]= data[37]
        vehicle["eventGold"]= data[38] #[36, 38]?
        vehicle["eventTMenXP"]= data[39]
        vehicle["autoRepairCost"]= data[40]
        vehicle["autoLoadCost"]= list(data[41])
        vehicle["autoEquipCost"]= list(data[42])
        vehicle["isPremium"]= data[43]
        vehicle["premiumCreditsFactor10"]= data[44] #[44, 45]?
        vehicle["premiumXPFactor10"]= data[45] #[44, 45]?
        vehicle["dailyXPFactor10"]= data[46]
        vehicle["aogasFactor10"]= data[47]
        vehicle["markOfMastery"]= data[48]
        if len(data[49]) >0:
          vehicle["dossierPopUps"]= [list(item) for item in data[49]]
        else:
          vehicle["dossierPopUps"]= data[49]


      elif len(data) == 52: # 52 = 8.4
        version = 840
        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["thits"]= data[5]
        vehicle["he_hits"]= data[6]
        vehicle["pierced"]= data[7]
        vehicle["damageDealt"]= data[8]
        vehicle["damageAssisted"]= data[9]
        vehicle["damageReceived"]= data[10]
        vehicle["shotsReceived"]= data[11]
        vehicle["spotted"]= data[12]
        vehicle["damaged"]= data[13]
        vehicle["kills"]= data[14]
        vehicle["tdamageDealt"]= data[15]
        vehicle["tkills"]= data[16]
        vehicle["isTeamKiller"]= data[17]
        vehicle["capturePoints"]= data[18]
        vehicle["droppedCapturePoints"]= data[19]
        vehicle["mileage"]= data[20]
        vehicle["lifeTime"]= data[21]
        vehicle["killerID"]= data[22]
        vehicle["achievements"]= data[23]
        vehicle["potentialDamageReceived"]= data[24]
        vehicle["repair"]= data[25]
        vehicle["freeXP"]= data[26]
        vehicle["details"]= _Decoder.decode_details(data[27])
        vehicle["accountDBID"]= str(data[28])
        vehicle["team"]= data[29]
        vehicle["typeCompDescr"]= data[30]
        vehicle["gold"]= data[31]
        vehicle["xpPenalty"]= data[32]
        vehicle["creditsPenalty"]= data[33]
        vehicle["creditsContributionIn"]= data[34]
        vehicle["creditsContributionOut"]= data[35]
        vehicle["tmenXP"]= data[36]
        vehicle["eventCredits"]= data[37]
        vehicle["eventFreeXP"]= data[38] #[40, 38]?
        vehicle["eventXP"]= data[39]
        vehicle["eventGold"]= data[40] #[40, 38]?
        vehicle["eventTMenXP"]= data[41]
        vehicle["autoRepairCost"]= data[42]
        vehicle["autoLoadCost"]= list(data[43])
        vehicle["autoEquipCost"]= list(data[44])
        vehicle["isPremium"]= data[45]
        vehicle["premiumCreditsFactor10"]= data[46] #[46, 47]?
        vehicle["premiumXPFactor10"]= data[47] #[46, 47]?
        vehicle["dailyXPFactor10"]= data[48]
        vehicle["aogasFactor10"]= data[49]
        vehicle["markOfMastery"]= data[50]
        if len(data[51]) >0:
          vehicle["dossierPopUps"]= [list(item) for item in data[51]]
        else:
          vehicle["dossierPopUps"]= data[51]

      elif len(data) == 60: # 60 = 8.6
        version = 860
        vehicle["health"]= data[0]
        vehicle["credits"]= data[1]
        vehicle["xp"]= data[2]
        vehicle["shots"]= data[3]
        vehicle["hits"]= data[4]
        vehicle["thits"]= data[5]
        vehicle["he_hits"]= data[6]
        vehicle["pierced"]= data[7]
        vehicle["damageDealt"]= data[8]
        vehicle["damageAssistedRadio"]= data[9]
        vehicle["damageAssistedTrack"]= data[10]
        vehicle["damageReceived"]= data[11]
        vehicle["shotsReceived"]= data[12]
        vehicle["noDamageShotsReceived"]= data[13]
        vehicle["heHitsReceived"]= data[14]
        vehicle["piercedReceived"]= data[15]
        vehicle["spotted"]= data[16]
        vehicle["damaged"]= data[17]
        vehicle["kills"]= data[18]
        vehicle["tdamageDealt"]= data[19]
        vehicle["tkills"]= data[20]
        vehicle["isTeamKiller"]= data[21]
        vehicle["capturePoints"]= data[22]
        vehicle["droppedCapturePoints"]= data[23]
        vehicle["mileage"]= data[24]
        vehicle["lifeTime"]= data[25]
        vehicle["killerID"]= data[26]
        vehicle["achievements"]= data[27]
        vehicle["potentialDamageReceived"]= data[28]
        vehicle["repair"]= data[29]
        vehicle["freeXP"]= data[30]
        vehicle["details"]= _Decoder.decode_details(data[31])
        vehicle["accountDBID"]= str(data[32])
        vehicle["team"]= data[33]
        vehicle["typeCompDescr"]= data[34]
        vehicle["gold"]= data[35]
        vehicle["deathReason"]= data[36]
        vehicle["xpPenalty"]= data[37]
        vehicle["creditsPenalty"]= data[38]
        vehicle["creditsContributionIn"]= data[39]
        vehicle["creditsContributionOut"]= data[40]
        vehicle["originalCredits"]= data[41]
        vehicle["originalXP"]= data[42]
        vehicle["originalFreeXP"]= data[43]
        vehicle["tmenXP"]= data[44]
        vehicle["eventCredits"]= data[45]
        vehicle["eventFreeXP"]= data[46] #[48, 46]?
        vehicle["eventXP"]= data[47]
        vehicle["eventGold"]= data[48] #[48, 46]?
        vehicle["eventTMenXP"]= data[49]
        vehicle["autoRepairCost"]= data[50]
        vehicle["autoLoadCost"]= list(data[51])
        vehicle["autoEquipCost"]= list(data[52])
        vehicle["isPremium"]= data[53]
        vehicle["premiumCreditsFactor10"]= data[54] #[54, 55]?
        vehicle["premiumXPFactor10"]= data[55] #[54, 55]?
        vehicle["dailyXPFactor10"]= data[56]
        vehicle["aogasFactor10"]= data[57]
        vehicle["markOfMastery"]= data[58]
        if len(data[59]) >0:
          vehicle["dossierPopUps"]= [list(item) for item in data[59]]
        else:
          vehicle["dossierPopUps"]= data[59]

      else: 
# This is for reverse engineering purposes, I wrote separate script automagically correlating binary data by comparing
# battle_result.dat files with corresponding replay pickle parts.

        version = 1
        for x in range (0, len(data)):
          if isinstance(data[x], list) and (len(data[x]) >0):
           if isinstance(data[x][0], tuple):
            vehicle[x]= [list(item) for item in data[x]]
           else:
            vehicle[x]= list(data[x])
          elif isinstance(data[x], tuple):
            vehicle[x]= list(data[x])
          else:
            vehicle[x]= data[x]

        print (len(data))
        pprint(vehicle)
        raise ValueError("Dont know this format.")
#        pprint (data)
#        pprint (vehicle)
      return vehicle, version
#    vehicle["achievementlist"]=
#    vehicle["countryID"]= #look up tanks.json
#    vehicle["tankID"]= data[28] >>8 #8 upper bits of typeCompDescr
#    vehicle["tankName"]= tank[typeCompDescr]


try:
  f = open("tanks.json", "r")
  tanks = json.load(f)
except Exception:
  raise
else:
  f.close()
  tank = {}
  for ta in tanks:
# tank [typeCompDescr] = name
    tank [ (ta['tankid']<<8) + (ta['countryid']<<4) + 1 ] = (ta['icon_orig'], ta['title'])

try:
  f = open("maps.json", "r")
  mapss = json.load(f)
except Exception:
  raise
else:
  f.close()
  maps = {}
  for ma in mapss:
    maps [ ma['mapid'] ] = (ma['mapidname'], ma['mapname'])

#1-4 are legit. 6-8 error, but still has some useful data. >=10 error
status =       {
                 1: 'Incomplete.',
                 2: 'Incomplete (past 8.1), with \'Battle Result\' pickle.',
                 3: 'Complete (pre 8.1).',
                 4: 'Complete (past 8.1).',
                 6: 'Bugged (past 8.1). Game crashed somewhere, second Json has game score',
                 8: 'Bugged (past 8.1). Only first Json available, pickle from wrong replay',
                 10: 'File too small to be a valid replay.',
                 11: 'Invalid Magic number. This is not a valid wotreplay file.',
                 12: 'Broken replay file, most likely game crashed while recording. It still has some (maybe valid) battle result data.',
                 13: 'Broken replay file, cant recognize first block.',
                 14: 'Broken replay file, cant recognize second block.',
                 15: 'Broken replay file, cant recognize third block.',
                 16: 'No compatible blocks found, can only process blocks 1-3',
                 20: 'Something went wrong!'
                }
gameplayid    = ["ctf", "encounter", "assault"]
finishreason  = ["", "extermination", "base capture", "timeout"]
bonustype     = ["", "public", "training", "tankcompany", "", "clanwar"]

def replay(filename, to_decode):
# filename= name of .wotreplay file
# to_decode= bitmask of chunks you want decoded.
# We do not just count blocks as they are in replay files. Instead we always decode
# Bit 0 = first Json block, starting player list
# Bit 1 = second Json block, simplified frag count
# Bit 2 = pickle, proper battle result with damage numbers
# 7(binary 111) means decode all three. 5(binary 101) means decode first Json and pikle.
#
# returns decoded_chunks[0:3], chunks bitmask, decoder status

  while True:
    wot_replay_magic_number = "12323411"
    blocks = 0
    first_chunk_decoded = {}
    second_chunk_decoded = {}
    third_chunk_decoded = {}
    chunks_bitmask = 0
    filesize = os.path.getsize(filename)
    if filesize<12: processing =10; break
    f = open(filename, "rb")
    if f.read(4)!=bytes.fromhex(wot_replay_magic_number): processing =11; break  
    blocks = struct.unpack("i",f.read(4))[0]

# 8.1 Adds new unencrypted Python pickle block containing your match stats
# Before 8.1 (< 20121101)
#  Json + binary = 1 = incomplete.
#  Json + Json + binary = 2 = complete.
# After  8.1 (>=20121101)
#  Json + binary = 1 = incomplete.
#  Json + pickle + binary = 2 = incomplete, but you looked at 'Battle Result' screen and replay got updated.
#  Json + Json + pickle + binary = 3 = complete.
# Some oddities:
#  Json + Json + ~8 bytes = 2 = incomplete, game crashed somewhere, second Json has game result, but we are missing Pickle
#
# Proper way to detect replay version is to decrypt and decompress binary part, but that is too slow.
# Instead I am using Date to estimate version in a very crude way. It is only accurade down to a day and doesnt take into
# consideration player timezone so I need to double check replays saved at 20121101. Still faster than decrypting and
# unzipping 1MB files.


    first_size = struct.unpack("i",f.read(4))[0]
#    print (first_size, filename)

    if filesize < (12+first_size+4): processing =10; break

    if (blocks == 1) and (not (to_decode&1)): processing =1; break

    first_chunk = f.read(first_size)
    if first_chunk[0:1] != b'{': processing =13; break
    first_chunk_decoded = json.loads(first_chunk.decode('utf-8'))
    chunks_bitmask = 1

    if blocks == 1: processing =1; break
    if ((blocks!=2) and (blocks!=3)): processing =16; break

    replaydate = datetime.strptime(first_chunk_decoded['dateTime'][0:10], "%d.%m.%Y")

    second_size = struct.unpack("i",f.read(4))[0]
    if filesize < (12+first_size+4+second_size): processing =10; break
    second_chunk = f.read(second_size)

# <20121101 and blocks==2 means Complete (pre 8.1). Second block should be Json.
    if (replaydate < datetime(2012, 11, 1)) and blocks==2:
      if second_chunk[0:2] == b'[{':
# Complete (pre 8.1).
        if to_decode&2:
          second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
          chunks_bitmask = chunks_bitmask|2
        processing =3; break
      else: processing =14; break

# =20121101 and blocks==2 can go both ways, need to autodetect second block.
# >20121101 and blocks==2 can contain broken replay
    elif (replaydate >= datetime(2012, 11, 1)) and blocks==2:
      if second_chunk[0:2] == b'(d':
# Incomplete (past 8.1), with 'Battle Result' pickle.
        if to_decode&4:
          third_chunk_decoded = _Unpickler(io.BytesIO(second_chunk)).load()
          chunks_bitmask = chunks_bitmask|4
          for b in third_chunk_decoded['vehicles']:
            third_chunk_decoded['vehicles'][b]['details']= _Decoder.decode_details(third_chunk_decoded['vehicles'][b]['details'].encode('raw_unicode_escape'))
            third_chunk_decoded['players'][ third_chunk_decoded['vehicles'][b]['accountDBID'] ]["vehicleid"]=b
        processing =2; break
      elif second_chunk[0:2] == b'[{':
        if to_decode&2:
          second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
          chunks_bitmask = chunks_bitmask|2
        if replaydate == datetime(2012, 11, 1):
# Complete (pre 8.1).
          processing =3; break
        else:
# Bugged (past 8.1). Game crashed somewhere, second Json has game result.
          processing =6; break

# >=20121101 and blocks==3 means Complete (past 8.1).
    elif (replaydate >= datetime(2012, 11, 1)) and blocks==3:
      if second_chunk[0:2] == b'[{':
        if to_decode&2:
          second_chunk_decoded = json.loads(second_chunk.decode('utf-8'))
          chunks_bitmask = chunks_bitmask|2
        if filesize<(12+first_size+4+second_size+4): processing =10; break
        third_size = struct.unpack("i",f.read(4))[0]
        if filesize<(12+first_size+4+second_size+4+third_size): processing =10; break
        third_chunk = f.read(third_size)
        if third_chunk[0:2] == b'(d':
          if to_decode&4:
            third_chunk_decoded = _Unpickler(io.BytesIO(third_chunk)).load()
            chunks_bitmask = chunks_bitmask|4
            for b in third_chunk_decoded['vehicles']:
              third_chunk_decoded['vehicles'][b]['details']= _Decoder.decode_details(third_chunk_decoded['vehicles'][b]['details'].encode('raw_unicode_escape'))
              third_chunk_decoded['players'][ third_chunk_decoded['vehicles'][b]['accountDBID'] ]["vehicleid"]=b
          processing =4; break
        else: processing =15; break
      else: processing =14; break


# All states that we can handle broke out of the While loop at this point.
# Unhandled cases trigger this.
    processing =20; break

  f.close()

  if chunks_bitmask&5 ==5:
# lets check if pickle belongs to this replay
# this is weak check, we only compare map and game mode, It can still pass some corrupted ones
    if maps[ third_chunk_decoded['common']['arenaTypeID'] & 65535 ][0] !=first_chunk_decoded['mapName'] or \
       gameplayid[ third_chunk_decoded['common']['arenaTypeID'] >>16] != first_chunk_decoded['gameplayID']:
#      print("EERRRROOOORRRrrrrrr!!!one77")
#      print("json:  ", first_chunk_decoded['mapName'])
#      print("pickle:", maps[ third_chunk_decoded['common']['arenaTypeID'] & 65535 ])
#      print("json:  ", first_chunk_decoded['gameplayID'])
#      print("pickle:", gameplayid[ third_chunk_decoded['common']['arenaTypeID'] >>16])
      processing =8
#      chunks_bitmask = chunks_bitmask^4
#      print(datetime.strptime(chunks[0]['dateTime'], '%d.%m.%Y %H:%M:%S'))
#      print( datetime.fromtimestamp(chunks[2]['common']['arenaCreateTime']))
#      print( mapidname[ chunks[2]['common']['arenaTypeID'] & 65535 ])

#guesstimating version, reliable only since 8.6 because WG added version string, earlier ones can be ~guessed by counting data or comparing dates
  if chunks_bitmask&1 ==1:
   if "clientVersionFromExe" in first_chunk_decoded:
    version = int(first_chunk_decoded["clientVersionFromExe"].replace(', ',''))
#    print (first_chunk_decoded["clientVersionFromExe"], version)
   else:
    
#8.7
#July 29, 2013
#8.4
#05 Mar 2013
#8.3
#16 Jan 2013
#8.2
#12 Dec 2012
#8.1
#Mar 13 2013
#8.0
#Sep 24 2012 
#7.5
#04.08.2012
#7.4
#20.06.2012
#7.3
#11.05.2012
#7.2
#30.03.2012
#7.1
#05.01.2012
#7.0
#19.12.2011
#6.7
#15.09.2011
#6.6
#10.08.2011
#6.5
#Jun 14 2011
#6.4
#Mar 12 2011
#6.3.11
#Apr 12 2011
#6.3.10
#Apr 07 2011
#6.3.9
#Mar 22 2011
#6.3
#Jan 15 2011
#6.2.8
#Dec 28 2010
#6.2.7
#Dec 23 2010
#6.2
#Dec 01 2010
#6.1.5
#Sep 28 2010
#5.5
#Oct 21 2010
#5.4.1
#Jul 16 2010    

    version = 830 # no clue, lets default to safe 8.3
  else:
   version = 0 #no first chunk = no version

# returns decoded_chunk[0:3], bitmap of available chunks, decoder status, ~version
  return (first_chunk_decoded, second_chunk_decoded, third_chunk_decoded), chunks_bitmask, processing, version


def battle_result(filename):
# filename= name of .dat battle_results file
#
# returns decoded_chunk
# Will throw ValueError if filename not a pickle.

  battle_result_magic_number = "80024b01"
  filesize = os.path.getsize(filename)
  f = open(filename, "rb")
  chunk = f.read(filesize)
  f.close()

  if chunk[0:4] != bytes.fromhex(battle_result_magic_number):
    raise ValueError(filename, "Bad pickle magic_number")

  pre_preliminary = _Unpickler(io.BytesIO(chunk)).load()
  pre_preliminary = pre_preliminary[1]
#  print(pre_preliminary[1])

  preliminary = _Unpickler(io.BytesIO(pre_preliminary[2])).load()
#  print(preliminary[2])
#  print(preliminary, pre_preliminary[0])

  common_to_decode = preliminary[0]
#  for deind, val in enumerate(common_to_decode):
#   print(deind, val)
  common_decoded = {}
  common_decoded["arenaTypeID"]= common_to_decode[0] # & 65535 makes more sense, but original replay keeps this number intact
  common_decoded["arenaCreateTime"]= common_to_decode[1]
  common_decoded["winnerTeam"]= common_to_decode[2]
  common_decoded["finishReason"]= common_to_decode[3]
  common_decoded["duration"]= common_to_decode[4]
  common_decoded["bonusType"]= common_to_decode[5]
  common_decoded["guiType"]= common_to_decode[6]
  common_decoded["vehLockMode"]= common_to_decode[7]


#  print(common_to_decode)

# Some additional variables Phalynx's www.vbaddict.net/wot uses.
#  common_decoded["guiType"]= common_to_decode[6]
#  common_decoded["gameplayID"]= common_to_decode[0] >>16 #this doesnt exist in replays, safer to always use (arenaTypeID >>16)
#  common_decoded["arenaCreateTimeH"]= #datetime.datetime.fromtimestamp(common_to_decode[1]).strftime("%Y-%m-%d %H:%M:%S")
#  common_decoded["arenaTypeIcon"]= # who cares about the icon blah
#  common_decoded["arenaTypeName"]= # maps[arenaTypeID & 65535]
#  common_decoded["bonusTypeName"]= #1=public 2=training 3=tankcompany 5=cw
#  common_decoded["finishReasonName"]= #1=extermination, 2=base, 3=timeout
#  common_decoded["gameplayName"]= # (arenaTypeID >>16) 0=random/ctf, 1=encounter 2=assault
#  common_decoded["gameplayTypeID"]= #probably created because Phalynx parses gameplayID wrong way :)


  personal_to_decode = pre_preliminary[1]
  personal_decoded = {}
#  for deind, val in enumerate(personal_to_decode):
#   print(deind, val)
#  print(len(personal_to_decode))
#  print(personal_to_decode)
#  print(personal_decoded)
  personal_decoded, version = _Decoder.decode_vehicle(personal_to_decode)
#  pprint(personal_decoded)

#  personal_decoded["xpPenalty"]= personal_to_decode[30]
#  personal_decoded["creditsPenalty"]= personal_to_decode[31]
#  personal_decoded["creditsContributionIn"]= personal_to_decode[32]
#  personal_decoded["creditsContributionOut"]= personal_to_decode[33]
#  personal_decoded["tmenXP"]= personal_to_decode[34]
#  personal_decoded["eventCredits"]= personal_to_decode[35]
#  personal_decoded["eventGold"]= personal_to_decode[36]
#  personal_decoded["eventXP"]= personal_to_decode[37]
#  personal_decoded["eventFreeXP"]= personal_to_decode[38]
#  personal_decoded["eventTMenXP"]= personal_to_decode[39]
#  personal_decoded["autoRepairCost"]= personal_to_decode[40]
#  personal_decoded["autoLoadCost"]= list(personal_to_decode[41])    
#  personal_decoded["autoEquipCost"]= list(personal_to_decode[42])
#  personal_decoded["isPremium"]= personal_to_decode[43]
#  personal_decoded["premiumXPFactor10"]= personal_to_decode[44]
#  personal_decoded["premiumCreditsFactor10"]= personal_to_decode[45]
#  personal_decoded["dailyXPFactor10"]= personal_to_decode[46]
#  personal_decoded["aogasFactor10"]= personal_to_decode[47]
#  personal_decoded["markOfMastery"]= personal_to_decode[48]
# personal_decoded["dossierPopUps"]= personal_to_decode[49]

# Some additional variables Phalynx's www.vbaddict.net/wot uses.
#  personal_decoded["won"]=

  players_to_decode = preliminary[1]
  players_decoded = {}
  for player in players_to_decode:
#    for deind, val in enumerate(players_to_decode[player]):
#     print(deind, val)
    player_decoded = {}
    player_decoded["name"]= players_to_decode[player][0].decode('unicode_escape')
    player_decoded["clanDBID"]= players_to_decode[player][1]
    player_decoded["clanAbbrev"]= players_to_decode[player][2].decode('unicode_escape')
    player_decoded["prebattleID"]= players_to_decode[player][3] #this is platoonID
    player_decoded["team"]= players_to_decode[player][4]
    players_decoded[str(player)]= player_decoded
# Some additional variables Phalynx's www.vbaddict.net/wot uses.
#  player_decoded["platoonID"]= #prebattleID
#  player_decoded["vehicleid"]= #we will fill that up while decoding vehicles


  vehicles_to_decode = preliminary[2]
  vehicles_decoded = {}
  for vehicle in vehicles_to_decode:
#  for deind, val in enumerate(vehicles_to_decode[vehicle]):
#  print(deind, val)
    vehicles_decoded[str(vehicle)], v= _Decoder.decode_vehicle(vehicles_to_decode[vehicle])
#    players_decoded[str(vehicles_decoded[vehicle]['accountDBID'])]["vehicleid"]=vehicle
  whole_thing = {}
  whole_thing['arenaUniqueID']= pre_preliminary[0]
  whole_thing['common']= common_decoded
  whole_thing['personal']= personal_decoded
  whole_thing['players']= players_decoded
  whole_thing['vehicles']= vehicles_decoded

  return whole_thing, version













