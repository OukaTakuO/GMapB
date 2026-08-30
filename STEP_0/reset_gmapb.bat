@echo off

cd /d %~dp0
cd ..\.tools\python

python reset_gmapb.py

echo GMapBをリセットしました。

pause