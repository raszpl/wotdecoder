## wotdecoder

World Of Tanks replay and battle result parsing/decoding library written in Python 3.  
List of utilities:  
  - [wotrepparser](#wotrepparser)  - Sort replays into categories.
  - [findplayer](#findplayer)  - Search for particular person/clan in replays/battle results.
  - [battle_results.bat](#battle_resultsbat)  - Backup battle results every time you start the game.



## wotrepparser

This program uses wotdecoder to make sense out of your replay files and sort them into five categories:

  - incomplete  - replays from matches you quit before they ended.
  - result      - incomplete replays, but include result of the match.
  - complete    - complete replays.
  - clanwar     - replays containing complete clanwar match.
  - error       - cant recognize as a valid replay.
  - b_r         - optional, stores dumped battle_result pickle/json

Additionally it will rename your replays so they are more palatable.

WoT retroactively updates replay file if you click Details button after the battle. This makes it possible to still
have results saved in a replay of a game you quit. This is important if you want to analyze detailed battle result data.
Files suitable for datamining are in complete, result and clanwar categories.
(WoT is buggy and sometimes saves same battle_result pickle into more than one replay file.)

###Usage

```
wotrepparser file_or_directory -o output_directory -v -r -n -b -f -c0

-o  Specify output directory. Default is current.
-v  Verbose, display every file processed.
-r  Recursive scan of all subdirectories.
-n  Dont rename files.
-b  Dump raw battle_results pickle to output_directory\b_r\number.pickle
-b1 Decode battle_results pickle, save output_directory\b_r\number.json
-b2 Same as above, but human readable json.
-f  Force overwrite. Default is ask.
-c  Copy instead of moving.
-c0 Dry run, dont copy, dont move.

```

###Example

```
wotrepparser g:\World_of_Tanks\replays -o d:\replays -v -r
```

When executed creates 5 subdirectories (incomplete, result, complete, clanwar, error) in d:\replays. 
Next it scans g:\World_of_Tanks\replays recursively for .wotreplay files, renames and moves them accordingly.

###Performance

ST31000523AS HDD and 3GHz cpu gives ~25 replays per second
```
Processed 4737 files. 0 errors.
Took 191699.039ms
```

Fast SSD and 3GHz cpu gives ~300 replays per second
```
Processed 4737 files. 0 errors.
Took 16117.286ms
```

Verbose parameter slows it dramatically under windows console.

###Renaming convention


Clanwar replay file

         20120811_2134_usa-T110_07_lakeville.wotreplay

becomes

         cw20120811_2134_SERB__PCP___Win__T110_07_lakeville.wotreplay

Where SERB is a tag of a clan starting on first flag, PCP starting on the second flag. Win obviously means owner of a replay file won.

       cw20120814_1939_PCP___CSM___Loss_T110_07_lakeville.wotreplay

Here PCP started on first flag, owner of replay file lost the match.


Replays with round result available are renamed to include that result

       20120506_1745_usa-M18_Hellcat_campania.wotreplay

becomes

       20120506_1745_Win__M18_Hellcat_campania.wotreplay


Underscores are used to align text so it is readable on fixed width console (basically a DIR in command prompt).
Format can be easily edited further in wotrepparser.py.



# findplayer

This program scans replay(.wotreplay) or battle_result(.dat) files for players using nickname and/or clantag.
(Currently it stops after finding first match per replay.)

###Usage

```
findplayer nickname [clantag] -c -v0..3 -e -o -r -p -b -i input_file_or_directory

Try `*` for string wildcard, `?` for character wildcard.
-c   Case sensitive search.
-v0  Verbose 0 = silent running, only give summary.
-v1  + list replay name, default.
-v2  + show match result, frag count.
-v3  + detailed stats.
-v4  + stats summary.
-e   Show errors.
-o   Include replay owner stats.
-r   Turn off recursive subdirectory scan.
-p   Show full patch.
-b   Scan battle_results(.dat) instead of wotreplays.
-i   Specify input directory. Default is current.

`*z_?l [1?3]` will match Rasz_pl[123]
`[*]` will match any person in any clan.
`[]` will only match people without clan.
`??` will list all people with 2 letter nicknames.
`*` will match everyone.
```

###Example stat summary output:

```
G:\World_of_Tanks\replays>python findplayer.py kawagreen -o -v4

Looking for nickname: kawagreen  clantag: [*]
Source: G:\World_of_Tanks\replays
Verbose: 4 Recursive: True Errors: hide

...
...
--------------------------------------------------------------------------------
 20130127_1347_Win__AMX_50_120_39_crimea.wotreplay
---
KawaGreen[SAO]                         | Rasz_pl[SAO]
--- Win  on South Coast                                          (extermination)
Died     in T54E1                      | Died     in AMX 50 120
Kills  =    3                          | Kills  =    4
Damage = 3057                          | Damage = 3536
Spotted=  315                          | Spotted=  319

Summary (average):
Kills  =     1.36                       | Kills  =     1.36
Damage =  1721.92                       | Damage =  1990.21
Spotted=   598.28                       | Spotted=   468.61


Found 481 matches. 0 errors.

Processing 4804 files took 115400.359ms
```




## battle_results.bat

Use it to start your game . It will automagically backup your battle_results. WOT keeps them only for
one session, every time you start the game it deletes old ones. This bat file will recursively look into 

  %APPDATA%\Wargaming.net\WorldOfTanks\battle_results\  
  %APPDATA%\Roaming\Wargaming.net\WorldOfTanks\battle_results\  

and copy all .dat files it can find to .\replays\battle_results\

###Usage

Umm, copy into your game directory and start the game with it.



-------------
###Compatibility

Tested with replays from 7.1 up to 8.6 WoT.

###Requirements

Python 3 http://www.python.org/

###Credits

Based on  
http://blog.wot-replays.org  
https://github.com/Phalynx/WoT-Dossier-Cache-to-JSON  