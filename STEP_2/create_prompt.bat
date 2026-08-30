@echo off

cd /d %~dp0
cd ..\.tools\python

python create_prompt.py

echo 「output_prompt」フォルダに生成AI用データを作成しました。

pause