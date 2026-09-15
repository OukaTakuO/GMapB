# GMapB

GMapBは、簡易なテキスト形式（`.map`）から、UnityまたはRPGツクールMV/MZ向けのマップデータを自動生成するツールです。

## GMapBが解決したいこと

Unity等で、ゼロからマップを1マスずつ作る負担を減らすことを目的としています。GMapB自体はタイル画像がどれかを知る必要はなく、「どのタイル（Symbol）を、どういう役割で、どこに配置するか」という情報だけを扱います。実際のタイル配置は、Registryに登録した`role`（役割）情報をもとに、生成AIとの対話で行います。

## 全体の流れ

1. （Unityの場合）マップチップ画像／タイルアセットを用意する
   （ツクールの場合）デフォルトタイルセットを使用可能、ただしオートタイル（A1～A4）は非対応
      ツクール側で空のマップを作成し、マップサイズ・どのタイルを使うかとそのタイルセット内での行数・列数を控えておく
2. `STEP_0`のバッチファイルでRegistryを初期化する（初回と、必要な場合のみ）
3. `STEP_1`のバッチファイルで、使用するタイルを対話形式でRegistryに登録する
4. `STEP_2`のバッチファイルで、Registry情報をもとにした自己完結の仕様書（`output_prompt/spec.json`）を生成する
5. `spec.json`を、GMapBの文脈を持たない生成AI（ChatGPT等でも可）に渡し、自然文で「〇〇なマップを作って」と依頼する
6. 生成された`.map`ファイル（好きな場所に保存して構わない）を用意する
7. `STEP_4`のバッチファイルで、`.map`ファイルのパスを入力し、Unity/RPGツクール向けのJSONまで一気通貫で出力する
8. （Unityの場合）Unity側の`UnityScript`内のC#スクリプトでインポートする
   （ツクールの場合）プロジェクトフォルダ内のマップJSONファイルを出力されたJSONに置き換える（JSONファイル名は既存のものに揃える）

* バッチファイル時の初回起動時などに警告表示などが出る場合があります。
　実行内容は安全なものですが、.batの内容・実行されるPythonファイルの内容をご確認いただいてから実行することも可能です。
　Pythonスクリプトのファイルパス: ./.tools/python/

## セットアップ

Python 3.9以降が必要です（標準ライブラリのみで動作し、追加のインストールは不要です）。
Unityプロジェクト内にAssets/Editorフォルダを作成し、./UnityScriptフォルダ内の「GMapBImporter.cs」を配置してください。

```bash
git clone <このリポジトリのURL>
```

`.tools/registry/`にRegistryファイル（`assets.json` / `symbols.json` / `registry_meta.json`）が存在しない場合は、
STEP_0の初回実行時に自動生成されます。

## 各STEPの内容

| フォルダ | 役割 |
|---|---|
| `STEP_0` | Registryを空の初期状態にリセットする（`reset_gmapb.bat`） |
| `STEP_1` | タイルを対話形式でRegistryに登録する（`register_tile.bat`） |
| `STEP_2` | Registry情報をもとに、AI向け仕様書`spec.json`を生成する（`create_prompt.bat`） |
| `STEP_3` | `spec.json`を生成AIにアップロードし、作りたいマップのイメージを指示、`.map`ファイルを生成する |
| `STEP_4` | `.map`ファイルのパスを入力し、Unity/RPGツクール向けJSONとして出力する（`export_rpgtkool.bat`/`export_unity.bat`） |

それぞれのフォルダ内のバッチファイルをダブルクリックで実行してください（STEP_3は実際に生成AI（ChatGPT・Claudeなど）を開いて作業してください）

### タイル登録（STEP_1）で聞かれる内容（バッチファイル: register_tile.bat）

- タイルアセット名（例：草原）
- アセットキー（`.map`で使う1文字のSymbol。例：G）
- レイヤー番号（任意、未入力なら0）
- Unity向けビルドの想定か（はい/いいえ）
  - 「はい」の場合、Unity側のアセットパスと、タイルのピクセルサイズ（任意）を追加で質問します。ピクセルサイズを入力すると、UnityのCell Sizeが自動計算されます（例：32px → 0.32）
- RPGツクール向けビルドの想定か（はい/いいえ）
　- 「はい」の場合、使用するシート（B/C/D/E/A5）と行・列番号（0始まり）を追加で質問し、tileIdを自動計算します（オートタイルA1～A4は非対応）
- このタイルの役割（role）：AIが自動配置の判断材料にするための自由記述

誤って登録したタイルは `delete_tile.bat` で削除できます（使用中のタイルは削除できない安全設計になっています）。

## `.map`ファイルの文法

- 各行がマップの1行、各文字が1マスに対応する
- `.`（ピリオド）は空白マス
- 登録されていない文字を使うとエラーになる
- 通常は`[layer X]`のような指定を書かず、1枚のグリッドとして書く（各Symbolは自分のレイヤーへ自動的に振り分けられる）
- 同じマスに複数のレイヤーを重ねたい場合のみ、`[layer X]`でグリッドを分けて書く
- Presetシンボルは1マスに置くだけで、登録済みのサイズ分だけ自動的に周囲へ展開される（Version 2.0時点では対話形式の登録手段は未実装。詳細は「対応状況」参照）
- RPGツクール向け出力時は、GMapBのレイヤー番号を昇順でz0〜z3に割り当てます（5層以上は出力時にエラー）

## ディレクトリ構造

```
GMapBルート
├── .tools
│   ├── python      (Pythonスクリプト一式)
│   └── registry    (assets.json, symbols.json, registry_meta.json)
├── output_prompt   (export_ai_spec()の出力先)
├── output_rpgtkool (build_and_export_rpgtkool()の出力先)
├── output_unity    (build_and_export_unity()の出力先)
├── STEP_0          (Registryリセット用バッチファイル)
├── STEP_1          (タイル登録用バッチファイル)
├── STEP_2          (spec.json生成用バッチファイル)
├── STEP_3          (STEP_3の簡単な説明テキストファイル)
├── STEP_4          (インポート用JSON生成用バッチファイル)
└── UnityScript     (Unity配置用のC#スクリプト)
```

`.tools/registry/`の中身（実データ）はリポジトリに含めていません（`.gitignore`で除外）。クローンした直後はカラの状態から始まります。

## 対応状況（Version 2.0）

- Unity：対応済み
- RPGツクール（MV/MZ）：対応済み
- RPGツクール（VX Ace以前）：非対応
- ウディタ：非対応
- Preset（複数マスをまとめた構造物）：Python側の登録・展開機能自体は実装済みだが、対話形式の登録手段や実地での通しテストは未実施。Version 2.1以降で本格対応予定

## ライセンス

MIT License。詳細は[LICENSE](./LICENSE)を参照してください。

