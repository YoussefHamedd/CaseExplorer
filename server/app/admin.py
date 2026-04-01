"""
Admin API — lets the client trigger the harvest/scrape/parse pipeline
and manage their ZenRows API key without touching the server directly.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from .utils import db_session
import threading
import shutil
import os
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

_pipeline_status = {
    "running": False,
    "step": None,
    "log": [],
    "last_run": None,
    "last_start_date": None,
    "last_end_date": None,
}

def _start_background_poller():
    import time
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')
    log_file    = os.path.join(harvester_dir, 'ui_pipeline.log')
    status_file = os.path.join(harvester_dir, 'ui_status.json')
    while True:
        try:
            with open(status_file) as f:
                st = json.load(f)
            _pipeline_status["step"]    = st.get("step", _pipeline_status["step"])
            _pipeline_status["running"] = bool(st.get("running", False))
        except Exception:
            pass
        if _pipeline_status["running"]:
            try:
                with open(log_file) as f:
                    lines = [l.rstrip() for l in f.readlines() if l.strip()]
                _pipeline_status["log"] = lines[-200:]
            except Exception:
                pass
        time.sleep(2)

threading.Thread(target=_start_background_poller, daemon=True).start()

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'admin_settings.json')

def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {"zenrows_key": "", "scraperapi_key": ""}

def _save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f)

def _log(msg):
    print(msg, flush=True)
    _pipeline_status["log"].append(msg)
    if len(_pipeline_status["log"]) > 200:
        _pipeline_status["log"] = _pipeline_status["log"][-200:]

def _run_pipeline(start_date, end_date, zenrows_key):
    from datetime import datetime
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')
    job_file    = os.path.join(harvester_dir, 'ui_job.json')
    log_file    = os.path.join(harvester_dir, 'ui_pipeline.log')
    status_file = os.path.join(harvester_dir, 'ui_status.json')
    _pipeline_status["running"] = True
    _pipeline_status["log"] = ["Submitting job to host runner..."]
    _pipeline_status["step"] = "Pending"
    _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    _pipeline_status["last_start_date"] = start_date
    _pipeline_status["last_end_date"] = end_date or "today"
    try:
        open(log_file, 'w').close()
        with open(status_file, 'w') as f:
            json.dump({"running": True, "step": "Pending"}, f)
    except Exception:
        pass
    with open(job_file, 'w') as f:
        json.dump({"start_date": start_date, "end_date": end_date, "zenrows_key": zenrows_key}, f)


@admin_bp.route('/settings', methods=['GET'])
def get_settings():
    s = _load_settings()
    masked = {
        k: (v[:6] + "..." + v[-4:] if len(v) > 10 else ("***" if v else ""))
        for k, v in s.items()
    }
    return jsonify(masked)

@admin_bp.route('/settings', methods=['POST'])
def save_settings():
    data = request.get_json()
    s = _load_settings()
    if 'zenrows_key' in data:
        s['zenrows_key'] = data['zenrows_key']
    if 'scraperapi_key' in data:
        s['scraperapi_key'] = data['scraperapi_key']
    _save_settings(s)
    return jsonify({"ok": True})


@admin_bp.route('/status', methods=['GET'])
def get_status():
    with db_session() as db:
        try:
            total        = db.execute(text("SELECT COUNT(*) FROM cases")).scalar()
            scraped      = db.execute(text("SELECT COUNT(*) FROM cases WHERE last_scrape IS NOT NULL")).scalar()
            parsed       = db.execute(text("SELECT COUNT(*) FROM cases WHERE last_parse IS NOT NULL")).scalar()
            remaining    = db.execute(text("SELECT COUNT(*) FROM cases WHERE last_scrape IS NULL AND scrape_exempt = false")).scalar()
            foreclosures = db.execute(text("""
                SELECT COUNT(*) FROM cases
                WHERE case_type IN ('Foreclosure','Foreclosure - Residential',
                  'Foreclosure - Commercial','Foreclosure - In Rem.',
                  'Foreclosure - In Rem','Right of Redemption')
                AND filing_date >= '2024-01-01'
            """)).scalar()

            last_scraped_filing = db.execute(text(
                "SELECT MAX(filing_date) FROM cases WHERE last_scrape IS NOT NULL"
            )).scalar()
            oldest_unscraped = db.execute(text(
                "SELECT MIN(filing_date) FROM cases WHERE last_scrape IS NULL AND scrape_exempt = false"
            )).scalar()
            first_scraped_filing = db.execute(text(
                "SELECT MIN(filing_date) FROM cases WHERE last_scrape IS NOT NULL"
            )).scalar()

            year_rows = db.execute(text("""
                SELECT EXTRACT(YEAR FROM filing_date)::int AS yr, COUNT(*) AS cnt
                FROM cases
                WHERE filing_date >= '2024-01-01'
                GROUP BY yr ORDER BY yr
            """)).fetchall()
            by_year = {str(yr): int(cnt) for yr, cnt in year_rows}

            scraped_24h = db.execute(text(
                "SELECT COUNT(*) FROM cases WHERE last_scrape >= NOW() - INTERVAL '24 hours'"
            )).scalar()
            scraped_1h = db.execute(text(
                "SELECT COUNT(*) FROM cases WHERE last_scrape >= NOW() - INTERVAL '1 hour'"
            )).scalar()
            newest_filing = db.execute(text(
                "SELECT MAX(filing_date) FROM cases WHERE last_scrape IS NOT NULL"
            )).scalar()

            # Service health based on DB activity
            scraper_active = db.execute(text(
                "SELECT COUNT(*) FROM cases WHERE last_scrape >= NOW() - INTERVAL '5 minutes'"
            )).scalar() > 0
            parser_active = db.execute(text(
                "SELECT COUNT(*) FROM cases WHERE last_parse >= NOW() - INTERVAL '10 minutes'"
            )).scalar() > 0

        except Exception:
            total = scraped = parsed = remaining = foreclosures = 0
            scraped_24h = scraped_1h = 0
            scraper_active = parser_active = False
            last_scraped_filing = oldest_unscraped = first_scraped_filing = newest_filing = None
            by_year = {}

    def fmt_date(d):
        if d is None:
            return None
        try:
            return d.strftime('%m/%d/%Y')
        except Exception:
            return str(d)

    def _disk():
        for path in ['/opt/minio', '/opt', '/']:
            try:
                u = shutil.disk_usage(path)
                return {
                    "total_gb": round(u.total / 1e9, 1),
                    "used_gb":  round(u.used  / 1e9, 1),
                    "free_gb":  round(u.free  / 1e9, 1),
                    "pct":      round(u.used / u.total * 100, 1),
                }
            except Exception:
                continue
        return None

    def _qllen(q):
        try:
            import socket
            s = socket.socket()
            s.settimeout(2)
            s.connect(('172.18.0.1', 6379))
            cmd = f'*2\r\n$4\r\nLLEN\r\n${len(q)}\r\n{q}\r\n'
            s.send(cmd.encode())
            resp = s.recv(64).decode().strip()
            s.close()
            return int(resp.lstrip(':'))
        except Exception:
            return None

    scraper_q   = _qllen('queue:scraper-queue')
    parser_q    = _qllen('queue:parser-queue')

    return jsonify({
        "pipeline": _pipeline_status,
        "db": {
            "total": total,
            "scraped": scraped,
            "parsed": parsed,
            "remaining": remaining,
            "foreclosures_scraped": foreclosures,
            "scraped_last_24h": scraped_24h,
            "scraped_last_1h": scraped_1h,
            "by_year": by_year,
            "last_scraped_filing_date": fmt_date(last_scraped_filing),
            "first_scraped_filing_date": fmt_date(first_scraped_filing),
            "oldest_unscraped_filing_date": fmt_date(oldest_unscraped),
            "newest_filing_date": fmt_date(newest_filing),
        },
        "queues": {
            "scraper": scraper_q,
            "parser":  parser_q,
        },
        "services": {
            "scraper": scraper_active,
            "parser":  parser_active,
        },
        "disk": _disk(),
    })


@admin_bp.route('/run', methods=['POST'])
def run_pipeline():
    if _pipeline_status["running"]:
        return jsonify({"error": "Pipeline already running"}), 409
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date', '')
    zenrows_key = data.get('zenrows_key') or _load_settings().get('zenrows_key', '')
    if not start_date:
        return jsonify({"error": "start_date required (MM/DD/YYYY)"}), 400
    _run_pipeline(start_date, end_date, zenrows_key)
    return jsonify({"ok": True, "message": "Pipeline started"})


@admin_bp.route('/stop', methods=['POST'])
def stop_pipeline():
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')
    try:
        os.remove(os.path.join(harvester_dir, 'ui_job.json'))
    except Exception:
        pass
    _pipeline_status["running"] = False
    _pipeline_status["step"] = "Stopped"
    return jsonify({"ok": True})


@admin_bp.route('/restart-spider', methods=['POST'])
def restart_spider():
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')
    flag = os.path.join(harvester_dir, 'restart_spider.flag')
    try:
        open(flag, 'w').close()
        return jsonify({'ok': True, 'message': 'Restart requested'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@admin_bp.route('/spider-health', methods=['GET'])
def spider_health():
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')
    health_file = os.path.join(harvester_dir, 'spider_health.json')
    try:
        with open(health_file) as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify({'datadome_2min': 0, 'spider1': 0, 'spider2': 0})
