#!/usr/bin/env python3
"""
generate-stop-trip-detail-sample.py の出力に、停留所の緯度・経度を付与した版。

生成ロジック（対象便・対象日・乗降人数の乱数・--via による路線の絞り込み）は
generate-stop-trip-detail-sample.py をそのまま使うため、緯度・経度以外の列は
同じ引数で実行した元スクリプトの出力と一致する。

付与する列:
- 緯度 / 経度 : stops.txt の stop_lat / stop_lon（文字列のまま、丸めない）
- 既存列の位置を変えないよう、末尾の空列 6 列のうち先頭 2 列に入れる（計 30 列のまま）

  python3 generate-stop-trip-detail-sample-latlon.py [GTFS.zip] [-o OUT.csv] [--via 停留所名,...]

※ generate-stop-trip-detail-sample.py と同じディレクトリに置いて実行すること。
"""

import argparse
import importlib.util
import zipfile
from pathlib import Path

BASE_SCRIPT = Path(__file__).with_name("generate-stop-trip-detail-sample.py")

LAT_COL = 24  # 名前付き 24 列の直後（末尾空列の 1 列目）
LON_COL = 25


def load_base():
    spec = importlib.util.spec_from_file_location("stop_trip_detail_base", BASE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # random.seed(42) もここで実行される
    return mod


def load_stop_coords(base, feed_path):
    """stop_id -> (stop_lat, stop_lon) を返す。"""
    with zipfile.ZipFile(feed_path) as zf:
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

    header = list(base.HEADER)
    header[LAT_COL], header[LON_COL] = "緯度", "経度"
    base.HEADER = header

    build_trip_rows = base.build_trip_rows

    def build_trip_rows_latlon(*args, **kwargs):
        rows = build_trip_rows(*args, **kwargs)
        for row in rows:
            lat, lon = coords.get(row[11], ("", ""))  # row[11] = 停留所ID
            row[LAT_COL], row[LON_COL] = lat, lon
        return rows

    base.build_trip_rows = build_trip_rows_latlon
    base.main()


if __name__ == "__main__":
    main()
