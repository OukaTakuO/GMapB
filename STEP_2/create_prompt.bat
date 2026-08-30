@echo off

cd /d %~dp0
cd ..\.tools\python

python create_prompt.py

pause