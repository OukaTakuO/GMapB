using UnityEngine;
using UnityEngine.Tilemaps;
using UnityEditor;
using System.IO;
using System.Collections.Generic;
using System.Text;

public class GMapBImporter : EditorWindow
{
    [MenuItem("GMapB/Import Map JSON")]
    public static void ShowWindow()
    {
        string path = EditorUtility.OpenFilePanel(
            "Select GMapB Unity JSON",
            "Assets",
            "json"
        );

        if (string.IsNullOrEmpty(path))
        {
            return;
        }

        ImportMap(path);
    }

    private static void ImportMap(string jsonPath)
    {
        string jsonText = File.ReadAllText(jsonPath);

        Dictionary<string, object> root =
            (Dictionary<string, object>)MiniJson.Deserialize(jsonText);

        Dictionary<string, object> layers =
            (Dictionary<string, object>)root["layers"];

        GameObject rootObject = new GameObject("GMapB_Map");
        Grid grid = rootObject.AddComponent<Grid>();

        if (root.ContainsKey("cell_size"))
        {
            float cellSize = System.Convert.ToSingle(root["cell_size"]);
            grid.cellSize = new Vector3(cellSize, cellSize, 1f);
        }

        foreach (KeyValuePair<string, object> layerEntry in layers)
        {
            string layerId = layerEntry.Key;
            List<object> rows = (List<object>)layerEntry.Value;

            GameObject layerObject = new GameObject($"Layer_{layerId}");
            layerObject.transform.parent = rootObject.transform;

            Tilemap tilemap = layerObject.AddComponent<Tilemap>();
            TilemapRenderer renderer = layerObject.AddComponent<TilemapRenderer>();
            renderer.sortingOrder = int.Parse(layerId);

            for (int row = 0; row < rows.Count; row++)
            {
                List<object> cells = (List<object>)rows[row];

                for (int x = 0; x < cells.Count; x++)
                {
                    object cell = cells[x];

                    if (cell == null)
                    {
                        continue;
                    }

                    string assetPath = (string)cell;

                    TileBase tile = AssetDatabase.LoadAssetAtPath<TileBase>(
                        assetPath
                    );

                    if (tile == null)
                    {
                        Debug.LogWarning(
                            $"Tile not found at path: {assetPath}"
                        );
                        continue;
                    }

                    // JSON側の行0(一番上)がUnity上でも一番上に来るよう、
                    // Y軸を反転させる
                    int cellY = -row;

                    tilemap.SetTile(
                        new Vector3Int(x, cellY, 0),
                        tile
                    );
                }
            }
        }

        Debug.Log("GMapB map imported successfully.");
    }
}

// ========================================
// MiniJson
//
// JsonUtilityは辞書型を扱えないため、
// 汎用的なJSONパーサーを自前で用意する。
// (Dictionary<string, object> / List<object> へ変換する
//  最小限の実装。外部パッケージへの依存なし)
// ========================================

public static class MiniJson
{
    public static object Deserialize(string json)
    {
        int index = 0;
        return ParseValue(json, ref index);
    }

    private static object ParseValue(string json, ref int index)
    {
        SkipWhitespace(json, ref index);

        char c = json[index];

        if (c == '{') return ParseObject(json, ref index);
        if (c == '[') return ParseArray(json, ref index);
        if (c == '"') return ParseString(json, ref index);
        if (c == 't') { index += 4; return true; }
        if (c == 'f') { index += 5; return false; }
        if (c == 'n') { index += 4; return null; }

        return ParseNumber(json, ref index);
    }

    private static Dictionary<string, object> ParseObject(string json, ref int index)
    {
        var result = new Dictionary<string, object>();
        index++; // '{'
        SkipWhitespace(json, ref index);

        if (json[index] == '}') { index++; return result; }

        while (true)
        {
            SkipWhitespace(json, ref index);
            string key = ParseString(json, ref index);
            SkipWhitespace(json, ref index);
            index++; // ':'
            object value = ParseValue(json, ref index);
            result[key] = value;

            SkipWhitespace(json, ref index);

            if (json[index] == ',') { index++; continue; }
            if (json[index] == '}') { index++; break; }
        }

        return result;
    }

    private static List<object> ParseArray(string json, ref int index)
    {
        var result = new List<object>();
        index++; // '['
        SkipWhitespace(json, ref index);

        if (json[index] == ']') { index++; return result; }

        while (true)
        {
            object value = ParseValue(json, ref index);
            result.Add(value);

            SkipWhitespace(json, ref index);

            if (json[index] == ',') { index++; continue; }
            if (json[index] == ']') { index++; break; }
        }

        return result;
    }

    private static string ParseString(string json, ref int index)
    {
        var sb = new StringBuilder();
        index++; // opening '"'

        while (json[index] != '"')
        {
            if (json[index] == '\\')
            {
                index++;
                char esc = json[index];
                switch (esc)
                {
                    case 'n': sb.Append('\n'); break;
                    case 't': sb.Append('\t'); break;
                    case 'r': sb.Append('\r'); break;
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    default: sb.Append(esc); break;
                }
            }
            else
            {
                sb.Append(json[index]);
            }

            index++;
        }

        index++; // closing '"'
        return sb.ToString();
    }

    private static object ParseNumber(string json, ref int index)
    {
        int start = index;

        while (index < json.Length &&
               (char.IsDigit(json[index]) || json[index] == '-' ||
                json[index] == '+' || json[index] == '.' ||
                json[index] == 'e' || json[index] == 'E'))
        {
            index++;
        }

        string numberString = json.Substring(start, index - start);

        if (numberString.Contains(".") || numberString.Contains("e") ||
            numberString.Contains("E"))
        {
            return double.Parse(numberString);
        }

        return int.Parse(numberString);
    }

    private static void SkipWhitespace(string json, ref int index)
    {
        while (index < json.Length && char.IsWhiteSpace(json[index]))
        {
            index++;
        }
    }
}