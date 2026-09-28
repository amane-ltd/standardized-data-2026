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


def load_first_trip(zf: zipfile.ZipFile):
    """先頭の便と、その停車停留所（順序付き）を返す。"""
    trips = read_table(zf, "trips.txt")
    if not trips:
        raise SystemExit("trips.txt に便がありません")
    trip = trips[0]

    routes = {r["route_id"]: r for r in read_table(zf, "routes.txt")}
    stops = {s["stop_id"]: s for s in read_table(zf, "stops.txt")}
    agencies = {a.get("agency_id", ""): a for a in read_table(zf, "agency.txt")}

    route = routes.get(trip["route_id"], {})
    agency = agencies.get(route.get("agency_id", "")) or next(iter(agencies.values()), {})

    times = [r for r in read_table(zf, "stop_times.txt") if r["trip_id"] == trip["trip_id"]]
    times.sort(key=lambda r: int(r["stop_sequence"]))
    if len(times) < 2:
        raise SystemExit(f"便 {trip['trip_id']} の停車停留所が不足しています")

    def fnum(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    sequence = [
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
    return trip, route, agency, sequence, load_fares(zf)


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


def build_records(trip, route, agency, sequence, fares, service_date):
    agency_code = agency.get("agency_id", "")
    agency_name = agency.get("agency_name", "")
    route_id = route.get("route_id", trip["route_id"])
    route_name = route.get("route_long_name") or route.get("route_short_name", "")
    trip_code = trip["trip_id"]

    pairs = pick_od_pairs(sequence)
    rows = []
    for i, (b_idx, a_idx) in enumerate(pairs, start=1):
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
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
