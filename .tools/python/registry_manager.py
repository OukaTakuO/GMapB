import json
from pathlib import Path


# ========================================
# Registry
# ========================================

REGISTRY_PATH = Path(__file__).parent.parent / "registry"
ASSETS_PATH = REGISTRY_PATH / "assets.json"
SYMBOLS_PATH = REGISTRY_PATH / "symbols.json"
META_PATH = REGISTRY_PATH / "registry_meta.json"

VALID_SYMBOLS = set()
SYMBOLS = {}
ASSETS = {}
META = {}


def load_registry():
    """
    RegistryからAsset、Symbol、採番情報を読み込む。
    """

    global VALID_SYMBOLS
    global SYMBOLS
    global ASSETS
    global META

    with ASSETS_PATH.open("r", encoding="utf-8") as file:
        ASSETS = json.load(file)

    with SYMBOLS_PATH.open("r", encoding="utf-8") as file:
        symbol_registry = json.load(file)

    # ----------------------------------------
    # Symbol Registry
    # ----------------------------------------

    SYMBOLS = {}

    for symbol, asset_id in symbol_registry.items():

        if asset_id not in ASSETS:
            raise ValueError(
                f"Symbol '{symbol}' refers to "
                f"unknown asset '{asset_id}'."
            )

        asset = ASSETS[asset_id]

        symbol_info = {
            "asset_id": asset_id,
            "type": asset["type"],
            "name": asset["name"],
            "layer": asset["layer"],
            "role": asset.get("role", "")
        }

        if asset["type"] == "terrain":
            symbol_info["tile"] = asset["tile"]
            symbol_info["export_ids"] = asset.get("export_ids", {})

        elif asset["type"] == "preset":
            symbol_info["file"] = asset["file"]

        else:
            raise ValueError(
                f"Unknown asset type: "
                f"'{asset['type']}'"
            )

        SYMBOLS[symbol] = symbol_info

    VALID_SYMBOLS = set(SYMBOLS.keys())

    # ----------------------------------------
    # Registry Meta
    # ----------------------------------------

    if META_PATH.exists():

        with META_PATH.open("r", encoding="utf-8") as file:
            META = json.load(file)

        # 既存のregistry_meta.jsonにcell_sizeがない場合は補完する
        if "cell_size" not in META:
            META["cell_size"] = 1
            save_registry()

    else:

        # 既存Registryから次の番号を計算
        next_tile_id = 1
        next_preset_id = 1

        for asset_id in ASSETS:

            if asset_id.startswith("tile_"):

                number = int(
                    asset_id.split("_")[1]
                )

                next_tile_id = max(
                    next_tile_id,
                    number + 1
                )

            elif asset_id.startswith("preset_"):

                number = int(
                    asset_id.split("_")[1]
                )

                next_preset_id = max(
                    next_preset_id,
                    number + 1
                )

        META = {
            "next_tile_id": next_tile_id,
            "next_preset_id": next_preset_id,
            "cell_size": 1
        }

        save_registry()


def reset_registry():
    """
    Registry(ASSETS, SYMBOLS, META)を空の初期状態にリセットする。

    既存のassets.json / symbols.json / registry_meta.jsonの内容は
    失われる。確認は行わないため、呼び出し側で必要なら
    バックアップ・確認を行うこと。
    """

    global ASSETS, SYMBOLS, VALID_SYMBOLS, META

    ASSETS = {}
    SYMBOLS = {}
    VALID_SYMBOLS = set()
    META = {
        "next_tile_id": 1,
        "next_preset_id": 1,
        "cell_size": 1
    }

    save_registry()


def save_registry():
    """
    現在のRegistryをJSONへ保存する。
    """

    REGISTRY_PATH.mkdir(exist_ok=True)

    # ----------------------------------------
    # Assets
    # ----------------------------------------

    with ASSETS_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            ASSETS,
            file,
            ensure_ascii=False,
            indent=4
        )

    # ----------------------------------------
    # Symbols
    # ----------------------------------------

    symbol_registry = {}

    for symbol, symbol_info in SYMBOLS.items():
        symbol_registry[symbol] = symbol_info["asset_id"]

    with SYMBOLS_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            symbol_registry,
            file,
            ensure_ascii=False,
            indent=4
        )

    # ----------------------------------------
    # Meta
    # ----------------------------------------

    with META_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            META,
            file,
            ensure_ascii=False,
            indent=4
        )


def get_next_asset_id(asset_type):
    """
    次に使用するAsset IDを取得する。
    """

    if asset_type == "terrain":

        asset_id = f"tile_{META['next_tile_id']:03d}"

        META["next_tile_id"] += 1

    elif asset_type == "preset":

        asset_id = f"preset_{META['next_preset_id']:03d}"

        META["next_preset_id"] += 1

    else:

        raise ValueError(
            f"Unknown asset type: '{asset_type}'"
        )

    return asset_id


def set_cell_size(value):
    """
    Unity Grid上でのセルサイズを設定する。
    Tileごとではなく、Registry全体で共有する値。
    """

    if value <= 0:
        raise ValueError(
            "cell_size must be greater than 0."
        )

    META["cell_size"] = value

    save_registry()


def register_tile(name, symbol, layer, tile, export_ids=None, role=""):
    """
    Tile Assetを登録する。

    export_ids:
        他エンジンへのエクスポート用ID。
        例: {"unity": "Assets/Tiles/Grass.asset", "rpgtkool": 5}
        省略した場合は空の辞書として扱う。

    role:
        このTileのマップ上での役割を表す自由記述の文字列。
        例: "壁：境界に使う", "床：内部を埋める"
        AIが自動配置の判断材料として参照する想定。
        省略した場合は空文字列として扱う。
    """

    if symbol in SYMBOLS:
        raise ValueError(
            f"Symbol '{symbol}' is already registered."
        )

    if export_ids is None:
        export_ids = {}

    asset_id = get_next_asset_id("terrain")

    ASSETS[asset_id] = {
        "type": "terrain",
        "name": name,
        "layer": layer,
        "tile": tile,
        "export_ids": export_ids,
        "role": role
    }

    SYMBOLS[symbol] = {
        "asset_id": asset_id,
        "type": "terrain",
        "name": name,
        "layer": layer,
        "tile": tile,
        "export_ids": export_ids,
        "role": role
    }

    VALID_SYMBOLS.add(symbol)

    save_registry()

    return asset_id


def register_tile_interactive():
    """
    対話形式でTile Assetを登録する。
    """

    name = input(
        "タイルアセット名を登録してください。（例）草原\n> "
    ).strip()

    symbol = input(
        "アセットキーを登録してください （例）G\n> "
    ).strip()

    layer_input = input(
        "レイヤー番号を登録してください（任意、未入力の場合は0）\n> "
    ).strip()

    if layer_input == "":
        layer = 0
    else:
        layer = int(layer_input)

    export_ids = {}

    unity_answer = input(
        "Unity向けビルドの想定ですか？ (Y/N)\n> "
    ).strip()

    if unity_answer in ("y", "Y"):

        unity_path = input(
            "Unityプロジェクト内のタイルアセット配置パスを"
            "登録してください （例）Assets/Tiles/Grass.asset\n> "
        ).strip()

        export_ids["unity"] = unity_path

        pixel_size_input = input(
            "使用するマップチップの1タイルあたりのサイズ(px)を"
            "登録してください（任意、未入力の場合はCell Sizeを"
            "変更しません）（例）32\n> "
        ).strip()

        if pixel_size_input != "":

            pixel_size = float(pixel_size_input)
            cell_size = pixel_size / 100

            set_cell_size(cell_size)

    role = input(
        "このタイルアセットの役割を記述してください。\n> "
        "（例）地面：屋外シーンの背景に使う、通行可能な基本の地面\n"
    ).strip()

    asset_id = register_tile(
        name=name,
        symbol=symbol,
        layer=layer,
        tile=symbol,
        export_ids=export_ids,
        role=role
    )

    print(f"登録しました: {asset_id} ({name})")

    return asset_id


def register_preset(name, symbol, layer, file, role=""):
    """
    Preset Assetを登録する。

    file:
        GMapBルートからの相対パスとして保存する。

    role:
        このPresetのマップ上での役割を表す自由記述の文字列。
        省略した場合は空文字列として扱う。
    """

    if symbol in SYMBOLS:
        raise ValueError(
            f"Symbol '{symbol}' is already registered."
        )

    # ----------------------------------------
    # Presetファイルのパスを正規化
    # ----------------------------------------

    preset_path = Path(file)

    if preset_path.is_absolute():

        try:
            file = preset_path.relative_to(
                Path.cwd()
            ).as_posix()

        except ValueError:
            raise ValueError(
                "Preset file must be inside "
                "the GMapB project."
            )

    else:

        file = preset_path.as_posix()

    # ----------------------------------------
    # 循環参照チェック（自己参照を含む）
    #
    # これから登録するPreset(symbol, file)を起点として、
    # 既に登録済みのPresetを辿っていき、
    # 途中でこのSymbol自身に戻ってこないか確認する。
    # ファイルがまだ存在しない場合はチェックをスキップする。
    # ----------------------------------------

    check_path = Path(file)

    if check_path.exists():

        visited_presets = set()
        files_to_check = [check_path]

        while files_to_check:

            current_path = files_to_check.pop()

            if not current_path.exists():
                continue

            with current_path.open(
                "r",
                encoding="utf-8"
            ) as preset_file:

                preset_data = json.load(preset_file)

            tiles = preset_data.get("tiles", [])

            symbols_found = set()

            for row in tiles:
                symbols_found.update(row)

            # ----------------------------------------
            # Presetの入れ子チェック（34章で方針決定）
            #
            # Presetの中に別のPresetを配置することは許容しない。
            # 対象は「これから登録しようとしているPreset自身」の
            # tilesのみ（current_path == check_path の1回目のみ）。
            # 既存の循環参照チェック用の走査（下のwhileループ）は、
            # そのまま流用する。
            # ----------------------------------------

            if current_path == check_path:

                for found_symbol in symbols_found:

                    if found_symbol not in SYMBOLS:
                        continue

                    if SYMBOLS[found_symbol]["type"] != "preset":
                        continue

                    raise ValueError(
                        f"Preset '{name}' cannot be registered: "
                        f"nesting a preset inside another preset is "
                        f"not supported (found preset symbol "
                        f"'{found_symbol}' in "
                        f"'{current_path.as_posix()}')."
                    )

            # 辿った先で、これから割り当てるSymbol自身が
            # 見つかったら循環参照が成立してしまう
            if symbol in symbols_found:
                raise ValueError(
                    f"Preset '{name}' cannot be registered: "
                    f"circular reference detected via "
                    f"'{current_path.as_posix()}' "
                    f"(references symbol '{symbol}')."
                )

            # 見つかったSymbolのうち、既に登録済みのPresetを
            # 指すものがあれば、そのPresetも辿る対象に加える
            for found_symbol in symbols_found:

                if found_symbol not in SYMBOLS:
                    continue

                info = SYMBOLS[found_symbol]

                if info["type"] != "preset":
                    continue

                next_asset_id = info["asset_id"]

                if next_asset_id in visited_presets:
                    continue

                visited_presets.add(next_asset_id)

                files_to_check.append(
                    Path(info["file"])
                )

    # ----------------------------------------
    # Asset ID取得
    # ----------------------------------------

    asset_id = get_next_asset_id("preset")

    ASSETS[asset_id] = {
        "type": "preset",
        "name": name,
        "layer": layer,
        "file": file,
        "role": role
    }

    SYMBOLS[symbol] = {
        "asset_id": asset_id,
        "type": "preset",
        "name": name,
        "layer": layer,
        "file": file,
        "role": role
    }

    VALID_SYMBOLS.add(symbol)

    save_registry()

    return asset_id


def change_symbol(asset_id, new_symbol):
    """
    Assetに割り当てられているSymbolを変更する。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    if new_symbol in SYMBOLS:
        raise ValueError(
            f"Symbol '{new_symbol}' is already registered."
        )

    old_symbol = None

    for symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            old_symbol = symbol
            break

    if old_symbol is None:
        raise ValueError(
            f"Asset '{asset_id}' has no registered symbol."
        )

    symbol_info = SYMBOLS.pop(old_symbol)

    SYMBOLS[new_symbol] = symbol_info

    VALID_SYMBOLS.discard(old_symbol)
    VALID_SYMBOLS.add(new_symbol)

    save_registry()


def change_layer(asset_id, new_layer):
    """
    AssetのLayerを変更する。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    ASSETS[asset_id]["layer"] = new_layer

    for symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            info["layer"] = new_layer
            break

    save_registry()


def change_role(asset_id, new_role):
    """
    Assetのroleを変更する。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    ASSETS[asset_id]["role"] = new_role

    for symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            info["role"] = new_role
            break

    save_registry()


def change_preset_file(asset_id, new_file):
    """
    Preset Assetのfileパスを変更する。

    new_file:
        GMapBルートからの相対パスとして保存する
        （register_presetと同じ正規化ルール）。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    if ASSETS[asset_id]["type"] != "preset":
        raise ValueError(
            f"Asset '{asset_id}' is not a preset."
        )

    # ----------------------------------------
    # Presetファイルのパスを正規化
    # （register_presetと同じロジック）
    # ----------------------------------------

    preset_path = Path(new_file)

    if preset_path.is_absolute():

        try:
            new_file = preset_path.relative_to(
                Path.cwd()
            ).as_posix()

        except ValueError:
            raise ValueError(
                "Preset file must be inside "
                "the GMapB project."
            )

    else:

        new_file = preset_path.as_posix()

    ASSETS[asset_id]["file"] = new_file

    for symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            info["file"] = new_file
            break

    save_registry()


def change_export_id(asset_id, engine, export_id):
    """
    Tile Assetのexport_idsに、指定エンジン用のIDを追加・更新する。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    if ASSETS[asset_id]["type"] != "terrain":
        raise ValueError(
            f"Asset '{asset_id}' is not a terrain tile."
        )

    if "export_ids" not in ASSETS[asset_id]:
        ASSETS[asset_id]["export_ids"] = {}

    ASSETS[asset_id]["export_ids"][engine] = export_id

    for symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            info.setdefault("export_ids", {})
            info["export_ids"][engine] = export_id
            break

    save_registry()


def find_asset_usage(asset_id):
    """
    Assetがどこで使用されているか調べる。

    戻り値:
        使用箇所の一覧
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    # ----------------------------------------
    # Assetに対応するSymbolを取得
    # ----------------------------------------

    symbol = None

    for current_symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            symbol = current_symbol
            break

    if symbol is None:
        raise ValueError(
            f"Asset '{asset_id}' has no registered symbol."
        )

    usage = []

    # ----------------------------------------
    # .mapファイルを検索
    # ----------------------------------------

    for map_path in Path(".").rglob("*.map"):

        # Registryディレクトリ内は検索対象外
        if REGISTRY_PATH in map_path.parents:
            continue

        with map_path.open("r", encoding="utf-8") as file:
            content = file.read()

        for line in content.splitlines():

            # レイヤー指定などの制御行は除外
            if line.startswith("["):
                continue

            if symbol in line:
                usage.append(
                    f"map: {map_path}"
                )
                break

    # ----------------------------------------
    # Presetファイルを検索
    # ----------------------------------------

    for preset_id, asset in ASSETS.items():

        if asset["type"] != "preset":
            continue

        preset_path = Path(asset["file"])

        if not preset_path.exists():
            continue

        with preset_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            preset_data = json.load(file)

        tiles = preset_data.get("tiles", [])

        for row in tiles:

            if symbol in row:
                usage.append(
                    f"preset: {preset_path}"
                )
                break

    return usage


def delete_asset(asset_id):
    """
    AssetをRegistryから削除する。
    使用中のAssetは削除できない。
    """

    if asset_id not in ASSETS:
        raise ValueError(
            f"Unknown asset ID: '{asset_id}'"
        )

    # ----------------------------------------
    # 使用状況を確認
    # ----------------------------------------

    usage = find_asset_usage(asset_id)

    if usage:
        raise ValueError(
            f"Cannot delete asset '{asset_id}'. "
            f"It is used by: {usage}"
        )

    # ----------------------------------------
    # Symbolを特定
    # ----------------------------------------

    symbol = None

    for current_symbol, info in SYMBOLS.items():

        if info["asset_id"] == asset_id:
            symbol = current_symbol
            break

    if symbol is None:
        raise ValueError(
            f"Asset '{asset_id}' has no registered symbol."
        )

    # ----------------------------------------
    # Asset削除
    # ----------------------------------------

    del ASSETS[asset_id]

    # ----------------------------------------
    # Symbol削除
    # ----------------------------------------

    del SYMBOLS[symbol]
    VALID_SYMBOLS.discard(symbol)

    # ----------------------------------------
    # 保存
    # ----------------------------------------

    save_registry()


def delete_asset_interactive():
    """
    対話形式で、削除したいTile/PresetのSymbol（アルファベット等）を
    入力し、該当Assetを削除する。
    """

    symbol = input(
        "削除したいアセットのSymbolを入力してください （例）G\n> "
    ).strip()

    if symbol not in SYMBOLS:
        print(f"Symbol '{symbol}' は登録されていません。")
        return None

    asset_id = SYMBOLS[symbol]["asset_id"]
    name = SYMBOLS[symbol]["name"]

    delete_asset(asset_id)

    print(f"削除しました: {symbol} ({name} / {asset_id})")

    return asset_id