#!/usr/bin/env python3
"""
GTFS から、運行管理システム / APC 出力を模した「停留所×便別実績」形式
（`stop-trip-detail`）のダミー乗降実績 CSV を生成する。

1 行 = 1 便の 1 停留所（OD なし・区間断面 = 通過人数あり）。

対象は OD サンプル（generate-commons-od-sample.py）と揃えて GTFS の最初の便のみ。
対象日は feed_start_date（feed_info.txt、無ければ calendar の最小 start_date）に
最も近い、その便の運行日を自動選択する。

シミュレーション方針:
- 1 便を停留所順に辿り、乗車→車内人数→降車の推移を再現（通過人数 = 発車時の車内人数）
- 起点側で乗車が多く、終点側で降車が多い。終点では全員降車（通過人数 0）
- 駅 / 営業所 / センター等の主要停留所を重み付け
- 平日朝夕ピーク (7-9, 17-19) を高密度化、土休日は低密度

対象 GTFS を使う:
- 第 1 引数に任意の GTFS ZIP のパスを渡すと、そのフィードの先頭便で生成する。

  python3 generate-stop-trip-detail-sample.py [GTFS.zip] [-o OUT.csv]

参考: gtfs-cooker では自動判定で `stop-trip-detail` として認識され、
      `通過人数` を区間断面利用者数（segment）として GTFS と結合できる。
"""

import argparse
import csv
import io
import math
import random
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # 再現性のため固定

SAMPLES_DIR = Path(__file__)
DEFAULT_FEED = SAMPLES_DIR / "gtfs/gtfs.zip"
DEFAULT_OUT = SAMPLES_DIR / "stop-trip-detail-sample.csv"

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 坂出202601.csv と同一のヘッダ（24 名前付き列 + 末尾の空列 6 = 計 30 列）
HEADER = [
    "データキー", "日付", "曜日", "休日区分", "路線ID", "路線名", "経路ID", "経路名",
    "便ID", "停留所順(路線)", "停留所順", "停留所ID", "停留所名",
    "乗車人数", "降車人数", "乗降車人数", "通過人数",
    "計画時刻", "実績時刻", "遅延時間(分)", "所要時間(分)",
    "車輌番号", "ダイヤ番号", "始発計画時刻",
] + [""] * 6


def read_table(zf: zipfile.ZipFile, name: str):
    with zf.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))


def load_feed(zip_path: Path):
    zf = zipfile.ZipFile(zip_path)
    stops = {r["stop_id"]: r["stop_name"] for r in read_table(zf, "stops.txt")}
    routes = {r["route_id"]: r for r in read_table(zf, "routes.txt")}

    trips = {}
    for r in read_table(zf, "trips.txt"):
        trips[r["trip_id"]] = {
            "route_id": r["route_id"],
            "service_id": r["service_id"],
            "headsign": r.get("trip_headsign", ""),
            "shape_id": r.get("shape_id", ""),
        }

    calendar = {}
    try:
        for r in read_table(zf, "calendar.txt"):
            calendar[r["service_id"]] = {
                "flags": [r[d] for d in (
                    "monday", "tuesday", "wednesday", "thursday",
                    "friday", "saturday", "sunday")],
                "start": r.get("start_date", ""),
                "end": r.get("end_date", ""),
            }
    except KeyError:
        pass

    cal_dates = {}
    try:
        for r in read_table(zf, "calendar_dates.txt"):
            cal_dates[(r["service_id"], r["date"])] = r["exception_type"]
    except KeyError:
        pass

    stop_times = defaultdict(list)
    for r in read_table(zf, "stop_times.txt"):
        stop_times[r["trip_id"]].append((
            int(r["stop_sequence"]), r["stop_id"],
            r.get("departure_time") or r.get("arrival_time"),
            r.get("arrival_time") or r.get("departure_time"),
        ))
    for tid in stop_times:
        stop_times[tid].sort(key=lambda x: x[0])

    # feed_start_date: feed_info.txt を優先し、無ければ calendar の最小 start_date
    feed_start = None
    try:
        fi = read_table(zf, "feed_info.txt")
        if fi and fi[0].get("feed_start_date"):
            feed_start = fi[0]["feed_start_date"]
    except KeyError:
        pass
    if not feed_start:
        starts = [c["start"] for c in calendar.values() if c.get("start")]
        feed_start = min(starts) if starts else None

    return stops, routes, trips, calendar, cal_dates, stop_times, feed_start


def build_pattern_ids(trips):
    """(route_id, headsign, shape_id) ごとに 14 桁ゼロ埋めの経路 ID を採番する。"""
    order = []
    seen = set()
    for tid in trips:  # trips.txt の並び順で安定採番
        t = trips[tid]
        key = (t["route_id"], t["headsign"], t["shape_id"])
        if key not in seen:
            seen.add(key)
            order.append(key)
    return {key: format(i + 1, "014d") for i, key in enumerate(order)}


def active_services(d, calendar, cal_dates):
    ymd = d.strftime("%Y%m%d")
    wd = d.weekday()  # 月=0
    active = set()
    for sid, c in calendar.items():
        if c["start"] and ymd < c["start"]:
            continue
        if c["end"] and ymd > c["end"]:
            continue
        if c["flags"][wd] == "1":
            active.add(sid)
    for (sid, dt), ex in cal_dates.items():
        if dt != ymd:
            continue
        if ex == "1":
            active.add(sid)
        elif ex == "2":
            active.discard(sid)
    return active


def parse_hms(t):
    """'6:38:00' / '25:10:00' -> (hour, minute, total_minutes)。24 時超も許容。"""
    parts = (t.split(":") + ["0", "0"])[:3]
    h, m = int(parts[0]), int(parts[1])
    return h, m, h * 60 + m


def peak_factor(hour):
    hod = hour % 24
    if hod in (7, 8, 17, 18):
        return 1.9
    if hod in (6, 9, 16, 19):
        return 1.4
    if 10 <= hod <= 15:
        return 1.0
    return 0.6


def holiday_class(d):
    wd = d.weekday()
    if wd <= 4:
        return "平日"
    if wd == 5:
        return "土曜"
    return "休日"


def stop_weight(name):
    """駅・営業所・センター等の拠点停留所を重み付け。"""
    for kw, w in (("駅", 2.0), ("営業所", 1.6), ("センター", 1.4),
                  ("港", 1.3), ("役所", 1.4), ("病院", 1.3), ("学校", 1.2)):
        if kw in name:
            return w
    return 1.0


def pois(lmbda):
    """簡易ポアソン乱数（Knuth 法）。"""
    if lmbda <= 0:
        return 0
    L = math.exp(-lmbda)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= L:
            return k - 1


def simulate_trip(stop_seq, is_weekday):
    """1 便の各停留所の (乗車, 降車, 通過人数) を返す。stop_seq: [(name, hour)]。"""
    n = len(stop_seq)
    results = []
    onboard = 0
    base = 0.8 if is_weekday else 0.45
    for i, (name, hour) in enumerate(stop_seq):
        w = stop_weight(name)
        pf = peak_factor(hour)
        is_last = (i == n - 1)
        if is_last:
            boarded = 0
            alighted = onboard
        else:
            board_w = 1.0 - i / max(1, n - 1)
            alight_w = i / max(1, n - 1)
            boarded = pois(base * pf * w * (0.4 + 1.2 * board_w))
            alighted = min(onboard, pois(base * pf * w * (0.3 + 1.3 * alight_w)))
        onboard = onboard + boarded - alighted
        results.append((boarded, alighted, onboard))
    return results


def num(n):
    """坂出202601.csv の数値書式（後ろに半角空白）。"""
    return f"{n} "


def find_target_date(service_id, calendar, cal_dates, feed_start):
    """feed_start_date に最も近い、指定サービスが運行する日を返す。"""
    if not feed_start:
        raise SystemExit("feed_start_date を特定できません（feed_info / calendar 不足）")
    base = datetime.strptime(feed_start, "%Y%m%d").date()
    for delta in range(0, 366):
        # 近い順に探索（同距離なら feed_start 以降を優先）
        candidates = [base] if delta == 0 else [
            base + timedelta(days=delta), base - timedelta(days=delta)]
        for d in candidates:
            if service_id in active_services(d, calendar, cal_dates):
                return d
    raise SystemExit(f"サービス {service_id} の運行日が見つかりません")


def build_trip_rows(d, tid, t, bin_id, routes, stops, stop_times, pattern_ids):
    """指定日 d・便 tid の停留所×便別実績を行リストで返す。"""
    ymd = d.strftime("%Y%m%d")
    ymd_slash = d.strftime("%Y/%m/%d")
    wd_jp = WEEKDAY_JP[d.weekday()]
    hclass = holiday_class(d)
    is_weekday = d.weekday() <= 4

    route = routes.get(t["route_id"], {})
    route_name = (route.get("route_long_name")
                  or route.get("route_short_name") or t["route_id"])
    pattern_id = pattern_ids[(t["route_id"], t["headsign"], t["shape_id"])]
    pattern_name = t["headsign"] or route_name

    seq = stop_times[tid]
    stop_seq = [(stops.get(sid, sid), parse_hms(dep)[0]) for _, sid, dep, _arr in seq]
    sim = simulate_trip(stop_seq, is_weekday)

    first_plan = "{:02d}:{:02d}".format(*parse_hms(seq[0][2])[:2])
    rows = []
    prev_min = None
    for idx, (_seqno, sid, dep, _arr) in enumerate(seq):
        h, m, tot = parse_hms(dep)
        plan = f"{h % 24:02d}:{m:02d}"
        delay = random.choices([0, 0, 0, 1, 2], weights=[6, 6, 6, 2, 1])[0]
        act_tot = tot + delay
        act = f"{(act_tot // 60) % 24:02d}:{(act_tot % 60):02d}"
        run_min = 0 if prev_min is None else max(0, tot - prev_min)
        prev_min = tot

        boarded, alighted, onboard = sim[idx]
        stop_name = stops.get(sid, sid)
        data_key = f"{ymd}_{pattern_id}_{bin_id:03d}_{idx + 1:03d}_{sid}"

        rows.append([
            data_key, ymd_slash, wd_jp, hclass,
            t["route_id"], route_name, pattern_id, pattern_name,
            num(bin_id), num(idx + 1), num(idx + 1), sid, stop_name,
            num(boarded), num(alighted), num(boarded + alighted), num(onboard),
            plan, act, num(delay), num(run_min),
            "", "", first_plan,
        ] + [""] * 6)
    return rows


def generate(feed_path, out_path):
    stops, routes, trips, calendar, cal_dates, stop_times, feed_start = load_feed(feed_path)
    pattern_ids = build_pattern_ids(trips)

    # 対象は GTFS の最初の便（trips.txt の先頭行）
    first_tid = next(iter(trips))
    t = trips[first_tid]
    if not stop_times.get(first_tid):
        raise SystemExit(f"先頭便 {first_tid} の stop_times がありません")

    # 対象日は feed_start_date に最も近い、その便の運行日
    target = find_target_date(t["service_id"], calendar, cal_dates, feed_start)

    rows = build_trip_rows(target, first_tid, t, 1, routes, stops, stop_times, pattern_ids)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    return rows, first_tid, t, target, feed_start, routes


def main():
    parser = argparse.ArgumentParser(
        description="坂出202601.csv 形式の停留所×便別実績サンプル生成（先頭便・単日）")
    parser.add_argument("feed", nargs="?", default=str(DEFAULT_FEED),
                        help="GTFS ZIP のパス（省略時: 坂出フィード）")
    parser.add_argument("-o", "--out", default=str(DEFAULT_OUT), help="出力 CSV パス")
    args = parser.parse_args()

    rows, tid, t, target, feed_start, routes = generate(Path(args.feed), Path(args.out))

    route_name = (routes.get(t["route_id"], {}).get("route_long_name") or t["route_id"])
    fs = datetime.strptime(feed_start, "%Y%m%d").date() if feed_start else None
    print(f"Feed:          {args.feed}")
    print(f"feed_start:    {fs}")
    print(f"対象便:        {tid}  ({t['route_id']} / {route_name})")
    print(f"対象日:        {target} ({WEEKDAY_JP[target.weekday()]})  ← feed_start に最も近い運行日")
    print(f"生成完了:      {args.out}  ({len(rows):,} 行 = 停留所数)")


if __name__ == "__main__":
    main()
