# standardized-data-2026

国土交通省「交通空白」解消等リ・デザイン全面展開プロジェクト **モビリティ人材・組織育成タイプ**（2026年度）の演習で用いる、**乗降実績サンプルデータ**の配布リポジトリです。

実在の乗降実績ではなく、各地域の GTFS（標準的なバス情報フォーマット）を入力として機械生成した**ダミーデータ**です。分析ツールの動作確認・演習用途にのみご利用ください。

## データの種類

| 形式 | 内容 | 粒度 |
| --- | --- | --- |
| **停留所別乗降実績**（`stop-trip-detail`） | 運行管理システム / APC 出力を模した停留所×便別の実績。乗車・降車・通過人数（区間断面）、計画／実績時刻、遅延を含む | 1行 = 1便の1停留所 |
| **ODデータ**（`commons-od`） | [COMmmmONS 乗降実績仕様 v1.0](https://www.mlit.go.jp/commmmons/document/005/) に準拠した一件明細。乗車／降車停留所・時刻・決済金額を含む | 1行 = 1トリップ（OD）|

いずれも各 GTFS の**先頭の便・単日分**を対象に生成しています（対象日は `feed_start_date` に最も近い運行日）。

## ダウンロード

| 地域 | 事業者 / 路線 | 対象日 | データ名 | URL |
| --- | --- | --- | --- | --- |
| 7807 秩父 | 秩父市（秩父市営バス 浦山線） | 2026-04-01 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7807-chichibu/7807-chichibu-stop-trip-detail.csv |
| 7807 秩父 | 秩父市（秩父市営バス 浦山線） | 2026-04-01 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7807-chichibu/7807-chichibu-commons-od.csv |
| 7845 山梨 | 山梨県内 15 事業者 | 2025-04-01 ほか | 停留所別乗降実績 / ODデータ | [下表（7845 山梨）](#7845-山梨県内-15-事業者)を参照 |
| 7876 中讃 | 琴参バス（D-1 瀬戸大橋線） | 2026-03-02 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7876-chusan/7876-chusan-stop-trip-detail.csv |
| 7876 中讃 | 琴参バス（D-1 瀬戸大橋線） | 2026-03-02 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7876-chusan/7876-chusan-commons-od.csv |
| 7878 塩尻 | 塩尻市（すてっぷくん 1楢川線） | 2026-04-01 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7878-shiojiri/7878-shiojiri-stop-trip-detail.csv |
| 7878 塩尻 | 塩尻市（すてっぷくん 1楢川線） | 2026-04-01 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7878-shiojiri/7878-shiojiri-commons-od.csv |

### 7845 山梨（県内 15 事業者）

山梨県内で公開されている GTFS 15 フィードそれぞれについて、2 形式（停留所別乗降実績 / ODデータ）を用意しています。
ファイル名は元の GTFS と 1 対 1 に対応し、`gtfs-<名称>.zip` → `<形式>-<名称>.csv` です（名称は日本語のまま、日付サフィックスも含めて変更していません）。

| GTFS（`gtfs/yamanashi/`） | 路線（先頭便） | 対象日 | 停留所別乗降実績 | ODデータ |
| --- | --- | --- | --- | --- |
| `gtfs-NPO法人清里観光振興会2025918.zip` | 大泉周遊ルート1台運行 | 2025-04-28 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-NPO%E6%B3%95%E4%BA%BA%E6%B8%85%E9%87%8C%E8%A6%B3%E5%85%89%E6%8C%AF%E8%88%88%E4%BC%9A2025918.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-NPO%E6%B3%95%E4%BA%BA%E6%B8%85%E9%87%8C%E8%A6%B3%E5%85%89%E6%8C%AF%E8%88%88%E4%BC%9A2025918.csv) |
| `gtfs-北杜市20250122.zip` | 黒森江草線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%8C%97%E6%9D%9C%E5%B8%8220250122.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%8C%97%E6%9D%9C%E5%B8%8220250122.csv) |
| `gtfs-南部町20250923.zip` | 徳間十島線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%8D%97%E9%83%A8%E7%94%BA20250923.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%8D%97%E9%83%A8%E7%94%BA20250923.csv) |
| `gtfs-富士急バス.zip` | 富士山駅−富石甲北−甲府駅北口 | 2026-01-05 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%AF%8C%E5%A3%AB%E6%80%A5%E3%83%90%E3%82%B9.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%AF%8C%E5%A3%AB%E6%80%A5%E3%83%90%E3%82%B9.csv) |
| `gtfs-富士急バスコンシェルジュ（御殿場・小山地区）.zip` | 青少年交流の家線 | 2026-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%AF%8C%E5%A3%AB%E6%80%A5%E3%83%90%E3%82%B9%E3%82%B3%E3%83%B3%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B8%E3%83%A5%EF%BC%88%E5%BE%A1%E6%AE%BF%E5%A0%B4%E3%83%BB%E5%B0%8F%E5%B1%B1%E5%9C%B0%E5%8C%BA%EF%BC%89.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%AF%8C%E5%A3%AB%E6%80%A5%E3%83%90%E3%82%B9%E3%82%B3%E3%83%B3%E3%82%B7%E3%82%A7%E3%83%AB%E3%82%B8%E3%83%A5%EF%BC%88%E5%BE%A1%E6%AE%BF%E5%A0%B4%E3%83%BB%E5%B0%8F%E5%B1%B1%E5%9C%B0%E5%8C%BA%EF%BC%89.csv) |
| `gtfs-小菅村20250303.zip` | 白沢−大津久 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%B0%8F%E8%8F%85%E6%9D%9120250303.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%B0%8F%E8%8F%85%E6%9D%9120250303.csv) |
| `gtfs-山梨交通.zip` | 山宮循環線（伊勢町営業所発） | 2026-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%B1%B1%E6%A2%A8%E4%BA%A4%E9%80%9A.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%B1%B1%E6%A2%A8%E4%BA%A4%E9%80%9A.csv) |
| `gtfs-山梨市20250131.zip` | 山梨循環線 南回り | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%B1%B1%E6%A2%A8%E5%B8%8220250131.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%B1%B1%E6%A2%A8%E5%B8%8220250131.csv) |
| `gtfs-市川三郷町20250108.zip` | 三珠線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E5%B8%82%E5%B7%9D%E4%B8%89%E9%83%B7%E7%94%BA20250108.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E5%B8%82%E5%B7%9D%E4%B8%89%E9%83%B7%E7%94%BA20250108.csv) |
| `gtfs-早川町20250108.zip` | 早川町奈良田身延駅線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E6%97%A9%E5%B7%9D%E7%94%BA20250108.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E6%97%A9%E5%B7%9D%E7%94%BA20250108.csv) |
| `gtfs-栄和交通20250218.zip` | 大菩薩上日川峠線 | 2025-04-19 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E6%A0%84%E5%92%8C%E4%BA%A4%E9%80%9A20250218.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E6%A0%84%E5%92%8C%E4%BA%A4%E9%80%9A20250218.csv) |
| `gtfs-甲府市20250108.zip` | 古関町〜南甲府駅 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E7%94%B2%E5%BA%9C%E5%B8%8220250108.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E7%94%B2%E5%BA%9C%E5%B8%8220250108.csv) |
| `gtfs-甲斐市20250122.zip` | 敷島〜双葉線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E7%94%B2%E6%96%90%E5%B8%8220250122.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E7%94%B2%E6%96%90%E5%B8%8220250122.csv) |
| `gtfs-身延町20250131.zip` | 古関循環線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E8%BA%AB%E5%BB%B6%E7%94%BA20250131.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E8%BA%AB%E5%BB%B6%E7%94%BA20250131.csv) |
| `gtfs-韮崎市20250723.zip` | 円野線 | 2025-04-01 | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/stop-trip-detail-%E9%9F%AE%E5%B4%8E%E5%B8%8220250723.csv) | [CSV](https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/commons-od-%E9%9F%AE%E5%B4%8E%E5%B8%8220250723.csv) |

※ `7845-yamanashi-stop-trip-detail.csv` / `7845-yamanashi-commons-od.csv`（名称なし）は `gtfs-富士急バス.zip` 分と同一内容で、既存リンク互換のため残しています。

文字コードは UTF-8（BOM 付き）です。Excel でそのまま開けます。

## 再生成

GTFS の ZIP（`gtfs/` 配下。リポジトリには含みません）を入力に、以下で再生成できます。

```bash
python3 generate-stop-trip-detail-sample.py <GTFS.zip> -o <地域>/<地域>-stop-trip-detail.csv
python3 generate-commons-od-sample.py       <GTFS.zip> -o <地域>/<地域>-commons-od.csv
```

乱数シードは固定（42）のため、同じ GTFS からは常に同じ結果が得られます。

## ライセンス

[MIT License](LICENSE)
