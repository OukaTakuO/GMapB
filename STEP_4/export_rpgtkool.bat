@echo off

cd /d %~dp0
cd ..\.tools\python

python export_rpgtkool.py

pause
