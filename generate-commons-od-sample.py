#!/usr/bin/env python3
"""
GTFS ZIP から、COMmmmONS 乗降実績仕様 (v1.0) に準拠した OD（一件明細）の
ダミー乗降実績 CSV を 10 件生成する。

対象の路線・便:
- GTFS の最初の便 (trips.txt の先頭行) を対象とする。
- その便が停車する停留所の順序 (stop_times) に沿って OD を作る。

レコード分布 (計 10 件):
- 始点 → 終点 の全区間 OD: 3 件
- その他の区間 OD (中間区間をランダムに選択, 全て相異なる): 7 件（各 1 件）

他の GTFS を使う:
- 第 1 引数に GTFS ZIP のパスを渡すと、そのフィードで生成する。

  python3 generate-commons-od-sample.py [GTFS.zip] [-o OUT.csv]

特定の停留所に接続する路線に絞る:
- --via に停留所名（stops.txt の stop_name）をカンマ区切りで渡すと、そのいずれかに
  停車する路線ごとに、その停留所に停まる先頭の便で上記 10 件を生成し、1 ファイルに連結する。

  python3 generate-commons-od-sample.py GTFS.zip --via 桂駅東口,桂駅西口 -o OUT.csv

出典: https://www.mlit.go.jp/commmmons/document/005/
"""

import argparse
import csv
import io
import random
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)  # 再現性のため固定

SAMPLES_DIR = Path(__file__)
DEFAULT_FEED = SAMPLES_DIR / "gtfs/gtfs.zip"
DEFAULT_OUT = SAMPLES_DIR / "commons-od-sample.csv"

N_RECORDS = 10
N_FULL_SPAN = 3  # 始点 → 終点 の件数
# 対象日は feed の calendar から自動決定する（feed_start_date に最も近い先頭便の運行日）。
# 解決できない場合のフォールバックのみ固定値を使う。
FALLBACK_SERVICE_DATE = date(2024, 10, 1)


def read_table(zf: zipfile.ZipFile, name: str):
    """GTFS の txt を dict のリストとして読む（BOM 付き UTF-8 対応）。"""
    with zf.open(name) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        return list(reader)


def open_feed(zip_path: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(zip_path)


def parse_gtfs_time(hms: str, base: date) -> datetime:
    """GTFS 時刻 (24 時超あり) を base 日付基準の datetime に変換する。"""
    h, m, s = (int(x) for x in hms.split(":"))
    return datetime(base.year, base.month, base.day) + timedelta(hours=h, minutes=m, seconds=s)


def iter_table(zf: zipfile.ZipFile, name: str):
    """GTFS の txt を 1 行ずつ dict で返す（stop_times.txt のような大きな表向け）。"""
    with zf.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))


def load_masters(zf: zipfile.ZipFile):
    """routes / stops / agency を id 引きの dict で返す。"""
    routes = {r["route_id"]: r for r in read_table(zf, "routes.txt")}
    stops = {s["stop_id"]: s for s in read_table(zf, "stops.txt")}
    agencies = {a.get("agency_id", ""): a for a in read_table(zf, "agency.txt")}
    return routes, stops, agencies


def build_sequence(trip, times, stops):
    """stop_times の行から、停車停留所の順序付きリストを作る。"""
    times = sorted(times, key=lambda r: int(r["stop_sequence"]))
    if len(times) < 2:
        raise SystemExit(f"便 {trip['trip_id']} の停車停留所が不足しています")

    def fnum(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    return [
        {
            "stop_id": t["stop_id"],
            "stop_name": stops.get(t["stop_id"], {}).get("stop_name", t["stop_id"]),
            "lat": fnum(stops.get(t["stop_id"], {}).get("stop_lat")),
            "lon": fnum(stops.get(t["stop_id"], {}).get("stop_lon")),
            "arrival": t.get("arrival_time") or t.get("departure_time"),
            "departure": t.get("departure_time") or t.get("arrival_time"),
        }
        for t in times
    ]


def route_and_agency(trip, routes, agencies):
    route = routes.get(trip["route_id"], {})
    agency = agencies.get(route.get("agency_id", "")) or next(iter(agencies.values()), {})
    return route, agency


def load_first_trip(zf: zipfile.ZipFile):
    """先頭の便と、その停車停留所（順序付き）を返す。"""
    trips = read_table(zf, "trips.txt")
    if not trips:
        raise SystemExit("trips.txt に便がありません")
    trip = trips[0]

    routes, stops, agencies = load_masters(zf)
    route, agency = route_and_agency(trip, routes, agencies)

    times = [r for r in iter_table(zf, "stop_times.txt") if r["trip_id"] == trip["trip_id"]]
    sequence = build_sequence(trip, times, stops)
    return trip, route, agency, sequence, load_fares(zf)


def load_trips_via(zf: zipfile.ZipFile, via_names):
    """指定した停留所名のいずれかに停車する路線ごとに、その停留所に停まる先頭の便
    （trips.txt の並び順）を選び、[(trip, route, agency, sequence), ...] を route_id 順で返す。"""
    routes, stops, agencies = load_masters(zf)
    via_ids = {sid for sid, s in stops.items() if s.get("stop_name") in via_names}
    missing = set(via_names) - {stops[sid]["stop_name"] for sid in via_ids}
    if missing:
        raise SystemExit(f"stops.txt に無い停留所名: {', '.join(sorted(missing))}")

    # 1 パス目: 指定停留所に停まる便を洗い出す
    hit_trips = {r["trip_id"] for r in iter_table(zf, "stop_times.txt") if r["stop_id"] in via_ids}
    chosen = {}  # route_id -> trip
    for trip in read_table(zf, "trips.txt"):
        if trip["trip_id"] in hit_trips and trip["route_id"] not in chosen:
            chosen[trip["route_id"]] = trip
    if not chosen:
        raise SystemExit("指定停留所に停車する便がありません")

    # 2 パス目: 選んだ便の stop_times だけを集める
    chosen_ids = {t["trip_id"] for t in chosen.values()}
    times_by_trip = {tid: [] for tid in chosen_ids}
    for r in iter_table(zf, "stop_times.txt"):
        if r["trip_id"] in chosen_ids:
            times_by_trip[r["trip_id"]].append(r)

    result = []
    for route_id in sorted(chosen):
        trip = chosen[route_id]
        route, agency = route_and_agency(trip, routes, agencies)
        result.append((trip, route, agency, build_sequence(trip, times_by_trip[trip["trip_id"]], stops)))
    return result


def resolve_service_date(zf: zipfile.ZipFile, service_id: str) -> date:
    """feed_start_date に最も近い、指定サービスの運行日を返す。
    calendar の有効期間・曜日と calendar_dates の例外を反映する。
    解決できなければ FALLBACK_SERVICE_DATE。"""
    # feed_start_date（feed_info 優先、無ければ calendar の最小 start_date）
    feed_start = None
    try:
        fi = read_table(zf, "feed_info.txt")
        if fi and fi[0].get("feed_start_date"):
            feed_start = fi[0]["feed_start_date"]
    except KeyError:
        pass

    try:
        calendar = {r["service_id"]: r for r in read_table(zf, "calendar.txt")}
    except KeyError:
        calendar = {}
    if not feed_start:
        starts = [r.get("start_date") for r in calendar.values() if r.get("start_date")]
        feed_start = min(starts) if starts else None
    if not feed_start:
        return FALLBACK_SERVICE_DATE

    cal_dates = {}
    try:
        for r in read_table(zf, "calendar_dates.txt"):
            cal_dates[(r["service_id"], r["date"])] = r["exception_type"]
    except KeyError:
        pass

    weekday_cols = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def active(d: date) -> bool:
        ymd = d.strftime("%Y%m%d")
        c = calendar.get(service_id)
        ok = False
        if c:
            within = (not c.get("start_date") or ymd >= c["start_date"]) and \
                     (not c.get("end_date") or ymd <= c["end_date"])
            if within and c.get(weekday_cols[d.weekday()]) == "1":
                ok = True
        ex = cal_dates.get((service_id, ymd))
        if ex == "1":
            ok = True
        elif ex == "2":
            ok = False
        return ok

    base = datetime.strptime(feed_start, "%Y%m%d").date()
    for delta in range(0, 731):
        for d in ([base] if delta == 0 else [base + timedelta(days=delta), base - timedelta(days=delta)]):
            if active(d):
                return d
    return FALLBACK_SERVICE_DATE


def load_fares(zf: zipfile.ZipFile):
    """fare_attributes.txt の運賃額（JPY）を昇順ユニークで返す。無ければ空。"""
    try:
        rows = read_table(zf, "fare_attributes.txt")
    except KeyError:
        return []
    prices = set()
    for r in rows:
        try:
            prices.add(int(float(r["price"])))
        except (KeyError, ValueError):
            continue
    return sorted(prices)


def fare_for_span(fares, b_idx, a_idx, n_stops):
    """乗車区間の長さに応じた決済金額（JPY）。運賃表があれば実額の段階を使う。"""
    frac = (a_idx - b_idx) / max(1, n_stops - 1)  # 0<frac<=1
    if fares:
        tier = round(frac * (len(fares) - 1))
        return fares[tier]
    # フォールバック: 初乗り 190 円 + 区間ごとに 30 円加算
    return 190 + 30 * (a_idx - b_idx - 1)


def haversine_m(a, b):
    """2 点 (lat, lon 持ち dict) 間の距離(m)。"""
    import math
    r = 6371000.0
    dlat = math.radians(b["lat"] - a["lat"])
    dlon = math.radians(b["lon"] - a["lon"])
    la1 = math.radians(a["lat"])
    la2 = math.radians(b["lat"])
    h = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def pick_od_pairs(sequence):
    """(乗車 index, 降車 index) を N_RECORDS 件返す。
    - 乗車停留所と降車停留所は**名前が異なる**ペアのみ（アプリ側が boarding==alighting を
      除外するため）。
    - 先頭 N_FULL_SPAN 件は 始点(0) → **始点から最も遠い停留所**（始点と異名の中で最大距離）。
    - 残りは名前が異なる相異なる区間からランダム抽出。
    """
    n = len(sequence)
    names = [s["stop_name"] for s in sequence]

    # 終点 = 始点から地理的に最も遠い停留所（始点と異名）
    far_idx, far_dist = 0, -1.0
    for i in range(1, n):
        if names[i] == names[0]:
            continue
        d = haversine_m(sequence[0], sequence[i])
        if d > far_dist:
            far_dist, far_idx = d, i
    if far_idx == 0:
        raise SystemExit("始点と異なる名前の停留所が無いため OD を作成できません")
    full = (0, far_idx)
    pairs = [full] * N_FULL_SPAN

    candidates = [
        (b, a)
        for b in range(n)
        for a in range(b + 1, n)
        if names[b] != names[a] and (b, a) != full
    ]
    n_others = N_RECORDS - N_FULL_SPAN
    if len(candidates) < n_others:
        raise SystemExit(
            f"名前の異なる中間区間の候補が {len(candidates)} 件しかなく、{n_others} 件を作れません"
        )
    pairs.extend(random.sample(candidates, n_others))
    return pairs


def build_records(trip, route, agency, sequence, fares, service_date, start_id=1):
    agency_code = agency.get("agency_id", "")
    agency_name = agency.get("agency_name", "")
    route_id = route.get("route_id", trip["route_id"])
    route_name = route.get("route_long_name") or route.get("route_short_name", "")
    trip_code = trip["trip_id"]

    pairs = pick_od_pairs(sequence)
    rows = []
    for i, (b_idx, a_idx) in enumerate(pairs, start=start_id):
        b = sequence[b_idx]
        a = sequence[a_idx]
        boarding_dt = parse_gtfs_time(b["departure"], service_date)
        alighting_dt = parse_gtfs_time(a["arrival"], service_date)
        payment_dt = alighting_dt  # 降車時精算 (IC) を想定

        # IC カード事業者判別コード（COMmmmONS No.2）。IC 利用時のみ付与。
        ic_card_agency_identification_code = "".join(random.choices("0123456789ABCDEF", k=17))

        # 決済金額（JPY）。乗車区間の長さに応じて運賃表の段階を割り当てる。
        payment_amount = fare_for_span(fares, b_idx, a_idx, len(sequence))

        rows.append(
            {
                "ridership_record_id": i,
                "ic_card_agency_identification_code": ic_card_agency_identification_code,
                "transportation_mode_code": route.get("route_type", "3"),
                "operating_agency_code": agency_code,
                "operating_agency_name": agency_name,
                "boarding_route_id": route_id,
                "boarding_route_name": route_name,
                "trip_code": trip_code,
                "operation_type": "EXIT",
                "boarding_station_sequence": b_idx + 1,
                "boarding_station_code": b["stop_id"],
                "boarding_station_name": b["stop_name"],
                "boarding_at": boarding_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "alighting_station_code": a["stop_id"],
                "alighting_station_name": a["stop_name"],
                "alighting_at": alighting_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_at": payment_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_amount": payment_amount,
                "adult_passenger_count": 1,
                "adult_challenged_passenger_count": 0,
                "child_passenger_count": 0,
                "child_challenged_passenger_count": 0,
                "payment_type": "IC_CARD",
            }
        )
    return rows


def write_csv(rows, path: Path):
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="COMmmmONS 乗降実績 OD サンプル生成")
    parser.add_argument(
        "feed",
        nargs="?",
        default=str(DEFAULT_FEED),
        help="GTFS ZIP のパス（省略時: さくらやまなみバスのサンプル）",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=str(DEFAULT_OUT),
        help="出力 CSV パス（省略時: commons-od-sample.csv）",
    )
    parser.add_argument(
        "--via",
        help="停留所名をカンマ区切りで指定すると、そのいずれかに停車する路線ごとに"
             "（その停留所に停まる先頭の便で）OD を各 10 件生成して 1 ファイルにまとめる",
    )
    args = parser.parse_args()

    if args.via:
        main_via(args, [n.strip() for n in args.via.split(",") if n.strip()])
        return

    with open_feed(Path(args.feed)) as zf:
        trip, route, agency, sequence, fares = load_first_trip(zf)
        service_date = resolve_service_date(zf, trip.get("service_id", ""))

    rows = build_records(trip, route, agency, sequence, fares, service_date)
    write_csv(rows, Path(args.out))

    origin = rows[0]["boarding_station_name"]
    dest = rows[0]["alighting_station_name"]  # 先頭（始点→終点）レコードの降車停留所
    print(f"Feed:  {args.feed}")
    print(f"Route: {route.get('route_id', '')} / {route.get('route_long_name', '')}")
    print(f"Trip:  {trip['trip_id']}  ({len(sequence)} stops)")
    print(f"対象日: {service_date} ({trip.get('service_id', '')})  ← feed_start に最も近い運行日")
    print(f"始点:  {origin}  →  終点: {dest}")
    print(f"Wrote {len(rows)} rows to {args.out}\n")
    for r in rows:
        print(f"  #{r['ridership_record_id']:2d}  {r['boarding_station_name']} → {r['alighting_station_name']}")


def main_via(args, via_names):
    """--via 指定時: 指定停留所に停車する路線ごとに OD を生成して連結する。"""
    with open_feed(Path(args.feed)) as zf:
        selected = load_trips_via(zf, via_names)
        fares = load_fares(zf)
        dates = {}
        for trip, *_ in selected:
            sid = trip.get("service_id", "")
            if sid not in dates:
                dates[sid] = resolve_service_date(zf, sid)

    rows = []
    print(f"Feed:  {args.feed}")
    print(f"Via:   {', '.join(via_names)}")
    print(f"対象路線: {len(selected)}\n")
    for trip, route, agency, sequence in selected:
        service_date = dates[trip.get("service_id", "")]
        recs = build_records(trip, route, agency, sequence, fares, service_date, start_id=len(rows) + 1)
        rows.extend(recs)
        via_hit = sorted({s["stop_name"] for s in sequence if s["stop_name"] in via_names})
        print(f"  {route.get('route_id', '')} {route.get('route_long_name', '')}"
              f"  便 {trip['trip_id']} ({len(sequence)} stops, {service_date})"
              f"  {recs[0]['boarding_station_name']} → {recs[0]['alighting_station_name']}"
              f"  [経由: {', '.join(via_hit)}]")
    write_csv(rows, Path(args.out))
    print(f"\nWrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
