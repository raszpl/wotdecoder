@echo off

rem ### Set OUTDIR wherever you like. Default is same place as replays.
set OUTDIR=".\replays\battle_results\"

rem ### lets try both potential locations just in case
set INDIR="%APPDATA%\Wargaming.net\WorldOfTanks\battle_results\"
for /R %INDIR% %%a in (*.dat) do xcopy "%%a" %OUTDIR% /q /y

set INDIR="%APPDATA%\Roaming\Wargaming.net\WorldOfTanks\battle_results\"
for /R %INDIR% %%a in (*.dat) do xcopy "%%a" %OUTDIR% /q /y

rem ### This is where you start the game. Uncomment the one you like or write your own.

rem ### WoT with XVM Ratings
rem start xvm-stat.exe

rem ### WoT
rem start WorldOfTanks.exe

rem ### WoT launcher? lol who would do that :)
rem start WOTLauncher.exe


rem exit