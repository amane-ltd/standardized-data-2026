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
| 7845 山梨 | 富士急バス（富士山駅−甲府駅北口） | 2026-01-05 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/7845-yamanashi-stop-trip-detail.csv |
| 7845 山梨 | 富士急バス（富士山駅−甲府駅北口） | 2026-01-05 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7845-yamanashi/7845-yamanashi-commons-od.csv |
| 7876 中讃 | 琴参バス（D-1 瀬戸大橋線） | 2026-03-02 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7876-chusan/7876-chusan-stop-trip-detail.csv |
| 7876 中讃 | 琴参バス（D-1 瀬戸大橋線） | 2026-03-02 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7876-chusan/7876-chusan-commons-od.csv |
| 7878 塩尻 | 塩尻市（すてっぷくん 1楢川線） | 2026-04-01 | 停留所別乗降実績 | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7878-shiojiri/7878-shiojiri-stop-trip-detail.csv |
| 7878 塩尻 | 塩尻市（すてっぷくん 1楢川線） | 2026-04-01 | ODデータ | https://raw.githubusercontent.com/amane-ltd/standardized-data-2026/main/7878-shiojiri/7878-shiojiri-commons-od.csv |

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
