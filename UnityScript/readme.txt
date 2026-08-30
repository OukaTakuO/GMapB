本スクリプトは、Game Map Builder で作成したマップデータをUnityプロジェクトに
タイルマップとしてインポートするための追加機能を実装するものです。


【Unityプロジェクト内配置パス】
Assets/Editor/GMapBImporter.cs
※Assets内にEditorフォルダがない場合は作成してください。


【使い方】
1. Unityメニューから GMapB → Import Map JSON を選択
2. Pythonで出力したUnity用JSON（unity_output.jsonなど）を選ぶ
3. GMapB_Map というGameObjectが生成され、その下にレイヤーごとの
   Layer_0, Layer_2 というTilemapが自動的に作られ、タイルが敷き詰められる

【注意点】
Tileアセットのパスが実際のプロジェクト構成と一致している必要があります。
そのためTile登録時にUnityプロジェクト構成と一致したパスを登録するか、
後からプロジェクト構成に一致するようパスを再登録してください。