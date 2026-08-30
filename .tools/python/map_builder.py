import json
from pathlib import Path
import registry_manager


def load_map(file_path):
    """
    .mapファイルを読み込む

    [layer X] が存在しない場合:
        自動レイヤーモード

    [layer X] が存在する場合:
        手動レイヤーモード
    """

    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        lines = file.readlines()

    # ----------------------------------------
    # レイヤーブロックの有無を確認
    # ----------------------------------------

    has_layer_block = any(
        line.strip().startswith("[layer ")
        for line in lines
    )

    # ========================================
    # 自動モード
    # ========================================

    if not has_layer_block:

        map_data = []

        for line in lines:

            line = line.strip()

            if line == "":
                continue

            map_data.append(list(line))

        return {
            "mode": "auto",
            "map": map_data
        }

    # ========================================
    # 手動モード
    # ========================================

    layers = {}
    current_layer = None

    for line_number, line in enumerate(lines, start=1):

        line = line.strip()

        # 空行
        if line == "":
            continue

        # ------------------------------------
        # [layer X]
        # ------------------------------------

        if line.startswith("[layer "):

            if not line.endswith("]"):
                raise ValueError(
                    f"Invalid layer declaration at Line {line_number}: "
                    f"'{line}'"
                )

            layer_text = line[7:-1].strip()

            try:
                layer = int(layer_text)
            except ValueError:
                raise ValueError(
                    f"Invalid layer number at Line {line_number}: "
                    f"'{line}'"
                )

            if layer in layers:
                raise ValueError(
                    f"Duplicate layer declaration: Layer {layer}"
                )

            layers[layer] = []
            current_layer = layer

            continue

        # ------------------------------------
        # レイヤーブロック外のマップデータ
        # ------------------------------------

        if current_layer is None:
            raise ValueError(
                f"Map data found before layer declaration "
                f"at Line {line_number}."
            )

        layers[current_layer].append(list(line))

    if len(layers) == 0:
        raise ValueError("No layer blocks found.")

    return {
        "mode": "manual",
        "layers": layers
    }


def validate_map(map_data):
    """マップデータを検証する"""

    mode = map_data["mode"]

    # ========================================
    # 自動モード
    # ========================================

    if mode == "auto":

        grid = map_data["map"]

        # 空チェック
        if len(grid) == 0:
            raise ValueError("Map is empty.")

        # 横幅チェック
        width = len(grid[0])

        for row_index, row in enumerate(grid):

            if len(row) != width:

                difference = len(row) - width

                if difference > 0:
                    message = f"{difference} characters too many."
                else:
                    message = f"{abs(difference)} characters missing."

                raise ValueError(
                    f"Line {row_index + 1} length mismatch.\n"
                    f"\n"
                    f"Expected: {width}\n"
                    f"Actual: {len(row)}\n"
                    f"\n"
                    f"{message}"
                )

        # 記号チェック
        for row_index, row in enumerate(grid):

            for column_index, symbol in enumerate(row):

                if symbol == ".":
                    continue

                if symbol not in registry_manager.VALID_SYMBOLS:
                    raise ValueError(
                        f"Unknown symbol '{symbol}' "
                        f"(Line {row_index + 1}, "
                        f"Column {column_index + 1})"
                    )

        return

    # ========================================
    # 手動モード
    # ========================================

    elif mode == "manual":

        layers = map_data["layers"]

        if len(layers) == 0:
            raise ValueError("No layers found.")

        # ------------------------------------
        # 基準サイズを取得
        # ------------------------------------

        first_layer = next(iter(layers.values()))

        if len(first_layer) == 0:
            raise ValueError("Layer is empty.")

        expected_height = len(first_layer)
        expected_width = len(first_layer[0])

        # ------------------------------------
        # 各Layerを検証
        # ------------------------------------

        for layer, grid in layers.items():

            if len(grid) == 0:
                raise ValueError(
                    f"Layer {layer} is empty."
                )

            # 高さ
            if len(grid) != expected_height:

                raise ValueError(
                    f"Layer {layer} height mismatch.\n"
                    f"\n"
                    f"Expected: {expected_height}"
                    f"Actual: {len(grid)}"
                )

            # 幅
            for row_index, row in enumerate(grid):

                if len(row) != expected_width:

                    raise ValueError(
                        f"Layer {layer} width mismatch "
                        f"at Line {row_index + 1}.\n"
                        f"\n"
                        f"Expected: {expected_width}\n"
                        f"Actual: {len(row)}"
                    )

            # --------------------------------
            # 記号チェック
            # --------------------------------

            for row_index, row in enumerate(grid):

                for column_index, symbol in enumerate(row):

                    if symbol == ".":
                        continue

                    if symbol not in registry_manager.VALID_SYMBOLS:

                        raise ValueError(
                            f"Unknown symbol '{symbol}' "
                            f"(Layer {layer}, "
                            f"Line {row_index + 1}, "
                            f"Column {column_index + 1})"
                        )

        return

    # ========================================
    # 不正なmode
    # ========================================

    else:

        raise ValueError(
            f"Invalid map mode: '{mode}'"
        )


def calculate_layout(map_data):
    '''
    シンボルのレイアウトと座標を計算する。

    全レイヤーで同じ座標系を使用するため、
    まず各列・各行について、originを基準にした
    左右・上下それぞれの必要スペースを求め、
    その後に各シンボルの描画座標を決定する。
    '''

    layouts = {}

    # ========================================
    # ① 処理対象のグリッドを取得
    # ========================================

    if map_data["mode"] == "auto":

        grids = {
            0: map_data["map"]
        }

        auto_mode = True

    elif map_data["mode"] == "manual":

        grids = map_data["layers"]

        auto_mode = False

    else:

        raise ValueError(
            f"Invalid map mode: '{map_data['mode']}'"
        )

    # ========================================
    # ② マップサイズを取得
    # ========================================

    first_grid = next(iter(grids.values()))

    map_height = len(first_grid)
    map_width = len(first_grid[0])

    # ========================================
    # ③ 各列・各行の必要スペースを調べる
    #
    # originを基準に、左右・上下を別々に記録する。
    # 例：origin[2,3]・width5・height4のPresetなら
    #     left=2, right=3, top=3, bottom=1
    # ========================================

    left_extents = [0] * map_width
    right_extents = [1] * map_width

    top_extents = [0] * map_height
    bottom_extents = [1] * map_height

    for layer, grid in grids.items():

        for y, row in enumerate(grid):

            for x, symbol in enumerate(row):

                # 空セル
                if symbol == ".":
                    continue

                symbol_info = get_symbol_info(symbol)

                origin_x, origin_y, width, height = \
                    get_symbol_footprint(symbol_info)

                left = origin_x
                right = width - origin_x

                top = origin_y
                bottom = height - origin_y

                if left > left_extents[x]:
                    left_extents[x] = left

                if right > right_extents[x]:
                    right_extents[x] = right

                if top > top_extents[y]:
                    top_extents[y] = top

                if bottom > bottom_extents[y]:
                    bottom_extents[y] = bottom

    # ========================================
    # ④ 各論理座標の基準位置(origin[0,0]相当の
    #    位置)を計算する
    # ========================================

    column_positions = [0] * map_width
    row_positions = [0] * map_height

    current_x = 0

    for x in range(map_width):
        current_x += left_extents[x]
        column_positions[x] = current_x
        current_x += right_extents[x]

    current_y = 0

    for y in range(map_height):
        current_y += top_extents[y]
        row_positions[y] = current_y
        current_y += bottom_extents[y]

    # ========================================
    # ⑤ 各Layerのレイアウトを作成
    # ========================================

    for layer, grid in grids.items():

        for y, row in enumerate(grid):

            for x, symbol in enumerate(row):

                # 空セル
                if symbol == ".":
                    continue

                symbol_info = get_symbol_info(symbol)

                # --------------------------------
                # Layer決定
                # --------------------------------

                if auto_mode:

                    if symbol_info["type"] == "terrain":
                        target_layer = 0

                    elif symbol_info["type"] == "preset":
                        target_layer = 2

                    else:
                        raise ValueError(
                            f"Unknown symbol type: "
                            f"'{symbol_info['type']}'"
                        )

                else:

                    target_layer = layer

                # --------------------------------
                # footprint取得
                # --------------------------------

                origin_x, origin_y, width, height = \
                    get_symbol_footprint(symbol_info)

                # --------------------------------
                # Layer作成
                # --------------------------------

                if target_layer not in layouts:
                    layouts[target_layer] = []

                # --------------------------------
                # レイアウト登録
                #
                # origin分だけ左・上にずらして配置する
                # --------------------------------

                layouts[target_layer].append({
                    "symbol": symbol,

                    "dsl_x": x,
                    "dsl_y": y,

                    "render_x": column_positions[x] - origin_x,
                    "render_y": row_positions[y] - origin_y,

                    "width": width,
                    "height": height
                })

    return layouts


def calculate_canvas_size(layouts):
    max_width = 0
    max_height = 0

    for layer_layout in layouts.values():

        for item in layer_layout:
            right = item["render_x"] + item["width"]
            bottom = item["render_y"] + item["height"]

            max_width = max(max_width, right)
            max_height = max(max_height, bottom)

    return max_width, max_height


def create_canvas(width, height, fill = "."):
    '''
    プリセット展開用キャンバス作成
    '''

    canvas = []

    for _ in range(height):
        canvas.append([fill] * width)

    return canvas


def get_symbol_info(symbol):
    '''
    各シンボルの情報を取り出す
    '''

    return registry_manager.SYMBOLS[symbol]


def get_symbol_footprint(symbol_info):
    '''
    Symbol(terrainまたはpreset)のfootprint情報を取得する。

    戻り値:
        (origin_x, origin_y, width, height)

    terrainは1マス・origin[0,0]固定として扱う。
    presetはPreset JSONのorigin/width/heightをそのまま使う。
    '''

    if symbol_info["type"] == "terrain":
        return 0, 0, 1, 1

    elif symbol_info["type"] == "preset":

        preset = load_preset(symbol_info["file"])
        origin_x, origin_y = preset["origin"]

        return origin_x, origin_y, preset["width"], preset["height"]

    else:
        raise ValueError(
            f"Unknown symbol type: '{symbol_info['type']}'"
        )


def load_preset(file_name):
    '''
    プリセットJSONファイルの内容を取得する
    '''

    path = Path(file_name)

    with open(path, "r", encoding="utf-8") as f:
        preset = json.load(f)

    # ----------------------------------------
    # origin未指定の場合はデフォルトの[0, 0]（左上）を補う
    # ----------------------------------------

    if "origin" not in preset:
        preset["origin"] = [0, 0]

    # ----------------------------------------
    # width / height は保存せず、
    # tilesの行数・列数からその場で計算する
    # ----------------------------------------

    tiles = preset.get("tiles", [])

    preset["height"] = len(tiles)
    preset["width"] = max(
        (len(row) for row in tiles),
        default=0
    )

    return preset


def get_preset_tiles(preset):
    '''
    ロードしたプリセットJSONファイルのタイル構成をリスト化
    '''

    tiles = []

    for row in preset["tiles"]:
        tiles.append(list(row))

    return tiles


def place_preset(canvas, tiles, start_x, start_y):
    '''
    キャンバスにプリセット配置
    '''

    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            canvas[start_y + y][start_x + x] = tile


def export_gmapb(map_data, layouts, canvas_width, canvas_height):
    """
    展開済みのレイアウトを .gmapb 形式(dict)に変換する。

    layouts:
        calculate_layout()の戻り値。
        レイヤーごとに配置済みシンボルのリストを持つ。

    戻り値:
        .gmapbとして書き出すJSON互換のdict
    """

    gmapb_data = {
        "width": canvas_width,
        "height": canvas_height,
        "layers": {}
    }

    for layer, items in layouts.items():

        grid = [
            [None] * canvas_width
            for _ in range(canvas_height)
        ]

        for item in items:

            symbol_info = get_symbol_info(item["symbol"])

            # ----------------------------------------
            # このSymbol自体のasset_idを、footprint全域に敷き詰める
            #
            # Presetの場合、中身のTileのasset_idではなく
            # Preset自身のasset_idが入ってしまうため、
            # Presetは個別Tileへ展開する必要がある(下で対応)
            # ----------------------------------------

            if symbol_info["type"] == "terrain":

                grid[item["render_y"]][item["render_x"]] = \
                    symbol_info["asset_id"]

            elif symbol_info["type"] == "preset":

                preset = load_preset(symbol_info["file"])
                tiles = get_preset_tiles(preset)

                for dy, row in enumerate(tiles):

                    for dx, inner_symbol in enumerate(row):

                        if inner_symbol == ".":
                            continue

                        inner_info = get_symbol_info(inner_symbol)

                        grid[item["render_y"] + dy][item["render_x"] + dx] = \
                            inner_info["asset_id"]

            else:
                raise ValueError(
                    f"Unknown symbol type: "
                    f"'{symbol_info['type']}'"
                )

        gmapb_data["layers"][str(layer)] = grid

    return gmapb_data


def export_unity(gmapb_data):
    """
    .gmapbの展開済みデータを、Unity用の出力形式に変換する。

    各マスのasset_idを、export_ids["unity"]（Unityのアセットパス）に
    置き換える。export_idsに"unity"が登録されていないTileが
    含まれる場合はエラーとする。
    """

    unity_data = {
        "width": gmapb_data["width"],
        "height": gmapb_data["height"],
        "cell_size": registry_manager.META["cell_size"],
        "layers": {}
    }

    for layer, grid in gmapb_data["layers"].items():

        new_grid = []

        for row in grid:

            new_row = []

            for asset_id in row:

                if asset_id is None:
                    new_row.append(None)
                    continue

                asset = registry_manager.ASSETS[asset_id]
                export_ids = asset.get("export_ids", {})

                if "unity" not in export_ids:
                    raise ValueError(
                        f"Asset '{asset_id}' ({asset['name']}) has no "
                        f"'unity' export_id registered. "
                        f"Use change_export_id() to register one."
                    )

                new_row.append(export_ids["unity"])

            new_grid.append(new_row)

        unity_data["layers"][layer] = new_grid

    return unity_data


def save_unity_json(unity_data, output_path):
    """
    Unity用データをJSONファイルへ保存する。
    """

    output_path = Path(output_path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            unity_data,
            file,
            ensure_ascii=False,
            indent=4
        )


def export_rpgtkool(gmapb_data):
    """
    .gmapbの展開済みデータを、RPGツクール(MV/MZ)用の出力形式に変換する。

    各マスのasset_idを、export_ids["rpgtkool"]（ツクール側のtileId）に
    置き換える。export_idsに"rpgtkool"が登録されていないTileが
    含まれる場合はエラーとする。

    現時点ではオートタイル非対応（固定タイルIDのみ）。VX Ace以前の
    バイナリ形式にも非対応。
    """

    rpgtkool_data = {
        "width": gmapb_data["width"],
        "height": gmapb_data["height"],
        "layers": {}
    }

    for layer, grid in gmapb_data["layers"].items():

        new_grid = []

        for row in grid:

            new_row = []

            for asset_id in row:

                if asset_id is None:
                    new_row.append(None)
                    continue

                asset = registry_manager.ASSETS[asset_id]
                export_ids = asset.get("export_ids", {})

                if "rpgtkool" not in export_ids:
                    raise ValueError(
                        f"Asset '{asset_id}' ({asset['name']}) has no "
                        f"'rpgtkool' export_id registered. "
                        f"Use change_export_id() to register one."
                    )

                new_row.append(export_ids["rpgtkool"])

            new_grid.append(new_row)

        rpgtkool_data["layers"][layer] = new_grid

    return rpgtkool_data


def save_rpgtkool_json(rpgtkool_data, output_path):
    """
    RPGツクール用データをJSONファイルへ保存する。
    """

    output_path = Path(output_path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            rpgtkool_data,
            file,
            ensure_ascii=False,
            indent=4
        )


def build_rpgtkool_map(rpgtkool_data, tileset_id=1, display_name=""):
    """
    export_rpgtkool()の出力を、RPGツクールMV/MZの
    MapXXX.json形式(dict)に変換する。

    GMapBのレイヤー番号は昇順にソートし、順番に
    z0, z1, z2, z3(ツクールの通常タイル4層)へ割り当てる。
    4つを超えるレイヤーが含まれる場合はエラーとする。

    z4(影)・z5(リージョン)は常に0で埋める。
    """

    width = rpgtkool_data["width"]
    height = rpgtkool_data["height"]

    sorted_layers = sorted(
        rpgtkool_data["layers"].keys(),
        key=lambda k: int(k)
    )

    if len(sorted_layers) > 4:
        raise ValueError(
            f"RPGツクールは通常タイル層を4つまでしかサポートしていません "
            f"(z0〜z3)。現在{len(sorted_layers)}個のレイヤーが "
            f"指定されています: {sorted_layers}"
        )

    data = [0] * (width * height * 6)

    for z, layer_key in enumerate(sorted_layers):

        grid = rpgtkool_data["layers"][layer_key]

        for y, row in enumerate(grid):

            for x, tile_id in enumerate(row):

                if tile_id is None:
                    continue

                index = (z * height + y) * width + x
                data[index] = tile_id

    map_data = {
        "autoplayBgm": False,
        "bgm": {"name": "", "pan": 0, "pitch": 100, "volume": 90},
        "autoplayBgs": False,
        "bgs": {"name": "", "pan": 0, "pitch": 100, "volume": 90},
        "battleback1Name": "",
        "battleback2Name": "",
        "disableDashing": False,
        "displayName": display_name,
        "encounterList": [],
        "encounterStep": 30,
        "height": height,
        "note": "",
        "parallaxLoopX": False,
        "parallaxLoopY": False,
        "parallaxName": "",
        "parallaxShow": True,
        "parallaxSx": 0,
        "parallaxSy": 0,
        "scrollType": 0,
        "specifyBattleback": False,
        "tilesetId": tileset_id,
        "width": width,
        "data": data,
        "events": [None]
    }

    return map_data


def save_rpgtkool_map(map_data, output_path):
    """
    RPGツクールのMapXXX.json形式で保存する。
    """

    output_path = Path(output_path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            map_data,
            file,
            ensure_ascii=False,
            indent=4
        )


def build_and_export_unity(map_path, output_dir=Path(__file__).parent.parent.parent / "output_unity"):
    """
    .mapファイルを読み込み、検証・レイアウト計算・Preset展開を経て、
    .gmapbとUnity用JSONの両方をoutput_dirへ書き出す一気通貫の実行関数。

    戻り値: (gmapb_path, unity_path) のタプル
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    map_data = load_map(map_path)
    validate_map(map_data)
    layouts = calculate_layout(map_data)
    canvas_width, canvas_height = calculate_canvas_size(layouts)

    gmapb_data = export_gmapb(
        map_data,
        layouts,
        canvas_width,
        canvas_height
    )

    unity_data = export_unity(gmapb_data)

    unity_path = output_dir / "output.unity.json"
    save_unity_json(unity_data, unity_path)

    return unity_data, unity_path


def build_and_export_unity_interactive():
    """
    対話形式で.mapファイルのパスを指定し、
    Unity用JSONまで一気通貫で出力する。
    """

    map_path = input(
        ".mapファイルのパスを入力してください "
        "（例）C:/Users/user/Downloads/grassland_10x10.map\n> "
    ).strip()

    unity_path = build_and_export_unity(map_path)

    print(f"unity: {unity_path}")

    return unity_path


MAP_FORMAT_GUIDE = """
GMapBの.mapファイルは、プレーンテキストでマップを表現する形式です。
書き方には「シンプルな書き方」と「レイヤー分けする書き方」の2種類があり、
必要に応じて使い分けます。

【共通のルール】
- 各行がマップの1行（縦方向の座標）、各文字が1マス（横方向の座標）に対応する
- 各グリッドの全ての行は同じ文字数でなければならない（長方形である必要がある）
- "."（半角ピリオド）は「何も置かない空白マス」を表す
- それ以外の文字は、この仕様書内の"symbols"に登録されているSymbolの
  いずれかでなければならない（登録されていない文字を使うとエラーになる）
- 大文字・小文字は区別される
- 空行は無視される
- "symbols"の"type"が"preset"のシンボルは、1マスに置くだけで
  "width"×"height"のサイズで自動的に周囲へ展開される
  (展開先のための空白マスをあらかじめ用意しておく必要はない)

【シンプルな書き方】
[layer X]のような見出しを一切書かず、1枚のグリッドだけを書く。

- タイルアセットの"layer"番号の値が全て0の場合のみこの方式を採る
  

【レイヤー分けする書き方】
「同じ座標(同じマス)に、複数のSymbolを重ねて配置したい」場合にだけ、
以下のように[layer X]という見出しでグリッドを分けて書く。
Xには、それぞれのSymbolの"layer"番号を指定する。

例（(1,1)のマスに、layer0のSymbolとlayer1のSymbolを重ねる場合）:
[layer 0]
GGGGG
GGGGG
GGGGG

[layer 1]
.....
.T...
.....

- 各[layer X]ブロックのグリッドは、全て同じ行数・同じ文字数でなければ
  ならない(座標を揃えて重ね合わせるため)
- タイルアセットの"layer"番号を精査し、値に1つ以上の「0以外の数値」が
  見つかった場合は必ずこの書き方をする

出力方法について:
- ファイル生成機能がある場合は、この内容を拡張子".map"のテキスト
  ファイルとして生成してください(特殊な形式ではなく、ただの
  プレーンテキストファイルです)
- ファイル生成機能がない場合は、.mapファイルの中身をそのまま
  テキストとして出力してください
- どちらの場合も、説明文やコードブロックの言語指定は不要です
""".strip()


def export_spec(filename="spec.json", output_dir=Path(__file__).parent.parent.parent / "output_prompt"):
    """
    外部のAI・ユーザーが.mapファイルを生成できるようにするための、
    自己完結した仕様書(JSON)を書き出す。output_prompt/フォルダへ出力する。

    .map文法の説明(固定文)と、現在Registryに登録されている
    Symbol一覧(名前・種別・role・サイズ)を1つのJSONにまとめる。
    roleの内容はRegistryに登録された値をそのまま使い、
    ここで書き換えたり言い換えたりはしない。
    """

    symbols = {}

    for symbol, info in registry_manager.SYMBOLS.items():

        symbol_data = {
            "type": info["type"],
            "name": info["name"],
            "layer": info["layer"],
            "role": info.get("role", "")
        }

        if info["type"] == "preset":

            preset = load_preset(info["file"])
            symbol_data["width"] = preset["width"]
            symbol_data["height"] = preset["height"]

        symbols[symbol] = symbol_data

    spec = {
        "map_format_guide": MAP_FORMAT_GUIDE,
        "symbols": symbols
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            spec,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("「output_prompt」フォルダにAI用ファイルを生成しました。")

    return output_path


def main():

    try:
        registry_manager.load_registry()

        map_data = load_map("samples/sample02.map")
        validate_map(map_data)
        layouts = calculate_layout(map_data)

        canvas_width, canvas_height = calculate_canvas_size(layouts)

        canvas = create_canvas(
            canvas_width, 
            canvas_height
        )

        for layer in sorted(layouts):
            layer_layout = layouts[layer]

            for item in layer_layout:
                symbol = item["symbol"]
                symbol_info = get_symbol_info(symbol)

                if symbol_info["type"] == "terrain":
                    canvas[item["render_y"]][item["render_x"]] = symbol_info["tile"]

                elif symbol_info["type"] == "preset":
                    preset = load_preset(symbol_info["file"])
                    tiles = get_preset_tiles(preset)
                    place_preset(
                        canvas, 
                        tiles, 
                        item["render_x"], 
                        item["render_y"]
                    )

        for row in canvas:
            print("".join(row))

        print()
        print(f"Canvas size: {canvas_width} x {canvas_height}")


    except ValueError as error:
        print(error)


if __name__ == "__main__":
    main()