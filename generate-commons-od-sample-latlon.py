#!/usr/bin/env python3
"""
generate-commons-od-sample.py の出力に、乗車・降車停留所の緯度・経度を付与した版。

生成ロジック（対象便・対象日・OD の乱数・--via による路線の絞り込み）は
generate-commons-od-sample.py をそのまま使うため、緯度・経度以外の列は
同じ引数で実行した元スクリプトの出力と一致する。

付与する列（COMmmmONS 乗降実績仕様 v1.0 には無い拡張列。既存列の後ろに追加）:
- boarding_station_lat / boarding_station_lon
- alighting_station_lat / alighting_station_lon
値は stops.txt の stop_lat / stop_lon（文字列のまま、丸めない）。

  python3 generate-commons-od-sample-latlon.py [GTFS.zip] [-o OUT.csv] [--via 停留所名,...]

※ generate-commons-od-sample.py と同じディレクトリに置いて実行すること。
"""

import argparse
import importlib.util
from pathlib import Path

BASE_SCRIPT = Path(__file__).with_name("generate-commons-od-sample.py")


def load_base():
    spec = importlib.util.spec_from_file_location("commons_od_base", BASE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # random.seed(42) もここで実行される
    return mod


def load_stop_coords(base, feed_path):
    """stop_id -> (stop_lat, stop_lon) を返す。"""
    with base.open_feed(feed_path) as zf:
        return {
            r["stop_id"]: (r.get("stop_lat", ""), r.get("stop_lon", ""))
            for r in base.read_table(zf, "stops.txt")
        }


def main():
    base = load_base()

    # 元スクリプトと同じ位置引数の解釈で、座標を引く GTFS を特定する
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("feed", nargs="?", default=str(base.DEFAULT_FEED))
    known, _ = pre.parse_known_args()
    coords = load_stop_coords(base, Path(known.feed))

    build_records = base.build_records

    def build_records_latlon(*args, **kwargs):
        rows = build_records(*args, **kwargs)
        for row in rows:
            b_lat, b_lon = coords.get(row["boarding_station_code"], ("", ""))
            a_lat, a_lon = coords.get(row["alighting_station_code"], ("", ""))
            row["boarding_station_lat"] = b_lat
            row["boarding_station_lon"] = b_lon
            row["alighting_station_lat"] = a_lat
            row["alighting_station_lon"] = a_lon
        return rows

    base.build_records = build_records_latlon
    base.main()


if __name__ == "__main__":
    main()
