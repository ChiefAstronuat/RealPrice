from __future__ import annotations

import json
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"

with open(DATA_DIR / "specs.json", "r", encoding="utf-8") as f:
    SPECS = json.load(f)

with open(DATA_DIR / "regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

with open(DATA_DIR / "mart_sweetpotato_price_daily.json", "r", encoding="utf-8") as f:
    PRICE_DAILY = json.load(f)

with open(DATA_DIR / "mart_sweetpotato_market_daily.json", "r", encoding="utf-8") as f:
    MARKET_DAILY = json.load(f)

VALID_MODES = {"final", "both", "retail"}


def parse_query(path: str):
    parsed = urllib.parse.urlparse(path)
    query = urllib.parse.parse_qs(parsed.query)
    return parsed.path, {k: v[0] for k, v in query.items()}


def json_response(handler: BaseHTTPRequestHandler, payload, status=HTTPStatus.OK):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def file_response(handler: BaseHTTPRequestHandler, file_path: Path, content_type: str):
    if not file_path.exists():
        return json_response(handler, {"error": "Static file not found"}, status=HTTPStatus.NOT_FOUND)
    content = file_path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def filter_price_rows(spec_id: str, region_id: str):
    return [
        row
        for row in PRICE_DAILY
        if row["spec_id"] == spec_id and row["region_id"] == region_id
    ]


def find_row_by_date(rows, target_date: str):
    picked = None
    for idx, row in enumerate(rows):
        if row["date"] <= target_date:
            picked = (idx, row)
        else:
            break
    return picked


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path, query = parse_query(self.path)

        if path in {"/", "/sweetpotato"}:
            return file_response(self, STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/static/app.js":
            return file_response(self, STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
        if path == "/static/style.css":
            return file_response(self, STATIC_DIR / "style.css", "text/css; charset=utf-8")

        if path == "/api/v1/sweetpotato/specs":
            return json_response(self, SPECS)

        if path == "/api/v1/regions":
            level = query.get("level", "si_do")
            return json_response(self, [r for r in REGIONS if r["level"] == level])

        if path == "/api/v1/sweetpotato/timeseries":
            spec_id = query.get("spec_id", "SP001")
            region_id = query.get("region_id", "11")
            start = query.get("start", "1900-01-01")
            end = query.get("end", "2999-12-31")
            mode = query.get("mode", "both")

            if mode not in VALID_MODES:
                return json_response(
                    self,
                    {"error": f"Invalid mode: {mode}. Use one of {sorted(VALID_MODES)}"},
                    status=HTTPStatus.BAD_REQUEST,
                )

            rows = [
                row
                for row in filter_price_rows(spec_id, region_id)
                if start <= row["date"] <= end
            ]

            series = []
            for row in rows:
                status = row.get("status", "final")
                nowcast_value = row["nowcast_krw_per_kg"] if status in {"mixed", "nowcast"} else None
                series.append(
                    {
                        "date": row["date"],
                        "final": row["final_krw_per_kg"],
                        "nowcast": nowcast_value if mode == "both" else None,
                        "retail": row["retail_avg_krw_per_kg"] if mode == "retail" else None,
                        "p10": row["p10"],
                        "p90": row["p90"],
                        "wholesale_volume_kg": row["wholesale_volume_kg"],
                        "n_markets": row["n_markets"],
                        "confidence": row["confidence_score"],
                        "status": status,
                        "as_of": row["as_of_timestamp"],
                    }
                )
            return json_response(self, series)

        if path == "/api/v1/sweetpotato/summary":
            spec_id = query.get("spec_id", "SP001")
            region_id = query.get("region_id", "11")
            date = query.get("date")

            rows = filter_price_rows(spec_id, region_id)
            if not rows:
                return json_response(self, {"error": "No data"}, status=HTTPStatus.NOT_FOUND)

            if date:
                found = find_row_by_date(rows, date)
                if not found:
                    return json_response(self, {"error": "No data for date"}, status=HTTPStatus.NOT_FOUND)
                idx, picked = found
            else:
                idx, picked = len(rows) - 1, rows[-1]

            yesterday = rows[max(0, idx - 1)]
            week_ago = rows[max(0, idx - 7)]

            return json_response(
                self,
                {
                    "date": picked["date"],
                    "final": picked["final_krw_per_kg"],
                    "nowcast": picked["nowcast_krw_per_kg"] if picked["status"] in {"mixed", "nowcast"} else None,
                    "retail": picked["retail_avg_krw_per_kg"],
                    "p10": picked["p10"],
                    "p90": picked["p90"],
                    "confidence": picked["confidence_score"],
                    "as_of": picked["as_of_timestamp"],
                    "delta_day": picked["final_krw_per_kg"] - yesterday["final_krw_per_kg"],
                    "delta_week": picked["final_krw_per_kg"] - week_ago["final_krw_per_kg"],
                    "status": picked["status"],
                    "note": "확정은 보통 T+3일 반영, 최근 3일은 잠정치입니다.",
                },
            )

        if path == "/api/v1/sweetpotato/market_breakdown":
            spec_id = query.get("spec_id", "SP001")
            date = query.get("date")
            if not date:
                date = max(row["date"] for row in MARKET_DAILY)

            rows = [
                row
                for row in MARKET_DAILY
                if row["spec_id"] == spec_id and row["date"] == date
            ]
            rows = sorted(rows, key=lambda x: x["volume_kg"], reverse=True)[:10]

            return json_response(
                self,
                {
                    "date": date,
                    "markets": rows,
                    "summary": {
                        "total_volume_kg": round(sum(r["volume_kg"] for r in rows), 2),
                        "n_markets": len(rows),
                    },
                },
            )

        return json_response(self, {"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        return


def main():
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[RealPrice] {now} KST - server started at http://127.0.0.1:8000")
    server = ThreadingHTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
