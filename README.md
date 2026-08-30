# GMapB

GMapBは、簡易なテキスト形式（`.map`）から、Unity向けのマップデータを自動生成するツールです。

## GMapBが解決したいこと

Unity等で、ゼロからマップを1マスずつ作る負担を減らすことを目的としています。GMapB自体はタイル画像がどれかを知る必要はなく、「どのタイル（Symbol）を、どういう役割で、どこに配置するか」という情報だけを扱います。実際のタイル配置は、Registryに登録した`role`（役割）情報をもとに、生成AIとの対話で行います。

## 全体の流れ

1. Unity側でマップチップ画像／タイルアセットを用意する
2. `STEP_0`のバッチファイルでRegistryを初期化する（初回と、必要な場合のみ）
3. `STEP_1`のバッチファイルで、使用するタイルを対話形式でRegistryに登録する（名前・Symbol・レイヤー・役割・エンジン別ID）
4. `STEP_2`のバッチファイルで、Registry情報をもとにした自己完結の仕様書（`output_prompt/ai_spec.json`）を生成する
5. `ai_spec.json`を、GMapBの文脈を持たない生成AI（ChatGPT等でも可）に渡し、自然文で「〇〇なマップを作って」と依頼する
6. 生成された`.map`ファイル（好きな場所に保存して構わない）を用意する
7. `STEP_3`のバッチファイルで、`.map`ファイルのパスを入力し、Unity向けのJSON（`output_unity/`）まで一気通貫で出力する
8. Unity側の`UnityScript`内のC#スクリプトでインポートする

## セットアップ

Python 3.9以降が必要です（標準ライブラリのみで動作し、追加のインストールは不要です）。

```bash
git clone <このリポジトリのURL>
```

`.tools/registry/`にRegistryファイル（`assets.json` / `symbols.json` / `registry_meta.json`）が存在しない場合は、初回実行時に自動生成されます。

## 各STEPの内容

| フォルダ | 役割 |
|---|---|
| `STEP_0` | Registryを空の初期状態にリセットする（`reset_registry()`） |
| `STEP_1` | タイルを対話形式でRegistryに登録する（`register_tile_interactive()`） |
| `STEP_2` | Registry情報をもとに、AI向け仕様書`ai_spec.json`を生成する（`export_ai_spec()`） |
| `STEP_3` | `.map`ファイルのパスを入力し、Unity向けJSONまで一気通貫で出力する（`build_and_export_unity_interactive()`） |

それぞれのフォルダ内のバッチファイルを実行してください。
初回実行時にWindowsの警告が出ることがありますが、.batファイルの中身はテキストなので、実行前にメモ帳等で開いて確認いただけます。

### タイル登録（STEP_1）で聞かれる内容

- タイルアセット名（例：草原）
- アセットキー（`.map`で使う1文字のSymbol。例：G）
- レイヤー番号（任意、未入力なら0）
- Unity向けビルドの想定か（はい/いいえ）
  - 「はい」の場合、Unity側のアセットパスと、タイルのピクセルサイズ（任意）を追加で質問します。ピクセルサイズを入力すると、UnityのCell Sizeが自動計算されます（例：32px → 0.32）
- このタイルの役割（role）：AIが自動配置の判断材料にするための自由記述

誤って登録したタイルは`delete_asset_interactive()`で削除できます（使用中のタイルは削除できない安全設計になっています）。

## `.map`ファイルの文法

- 各行がマップの1行、各文字が1マスに対応する
- `.`（ピリオド）は空白マス
- 登録されていない文字を使うとエラーになる
- 通常は`[layer X]`のような指定を書かず、1枚のグリッドとして書く（各Symbolは自分のレイヤーへ自動的に振り分けられる）
- 同じマスに複数のレイヤーを重ねたい場合のみ、`[layer X]`でグリッドを分けて書く
- Presetシンボルは1マスに置くだけで、登録済みのサイズ分だけ自動的に周囲へ展開される（Version 1.0時点では対話形式の登録手段は未実装。詳細は「対応状況」参照）

## ディレクトリ構造

```
GMapBルート
├── .tools
│   ├── python      (Pythonスクリプト一式)
│   └── registry    (assets.json, symbols.json, registry_meta.json)
├── output_prompt   (export_ai_spec()の出力先)
├── output_unity    (build_and_export_unity()の出力先)
├── STEP_0          (Registryリセット用バッチファイル)
├── STEP_1          (タイル登録用バッチファイル)
├── STEP_2          (ai_spec.json生成用バッチファイル)
├── STEP_3          (output.unity.json生成用バッチファイル)
└── UnityScript     (Unity配置用のC#スクリプト)
```

`.tools/registry/`の中身（実データ）はリポジトリに含めていません（`.gitignore`で除外）。クローンした直後はカラの状態から始まります。

## 対応状況（Version 1.0）

- Unity：対応済み、
- RPGツクール（MV/MZ）：現状非対応、対応予定
- RPGツクール（VX Ace以前）：非対応
- ウディタ：非対応
- Preset（複数マスをまとめた構造物）：Python側の登録・展開機能自体は実装済みだが、対話形式の登録手段や実地での通しテストは未実施。Version 1.1以降で本格対応予定

## ライセンス

MIT License。詳細は[LICENSE](./LICENSE)を参照してください。

