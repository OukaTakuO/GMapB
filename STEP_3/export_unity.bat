@echo off

cd /d %~dp0
cd ..\.tools\python

python export_unity.py

pause