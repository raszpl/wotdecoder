@echo off

rem ### Set INDIR to
rem %APPDATA%\Wargaming.net\WorldOfTanks\battle_results\
rem or %APPDATA%\Roaming\Wargaming.net\WorldOfTanks\battle_results\

set INDIR="%APPDATA%\Wargaming.net\WorldOfTanks\battle_results\"

rem set OUTDIR wherever you like, I suggest same place where you keep replays.

set OUTDIR=".\replays\battle_results\"
for /R %INDIR% %%a in (*.dat) do xcopy "%%a" %OUTDIR% /q /y

rem ### This is where you start the game. Uncomment the one you like or write your own.

rem ### WoT with XVN Ratings
rem start xvm-stat.exe

rem ### WoT
rem start WorldOfTanks.exe

rem ### WoT launcher? lol who would do that :)
rem start WOTLauncher.exe


rem exit