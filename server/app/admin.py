"""
Admin API — lets the client trigger the harvest/scrape/parse pipeline
and manage their ZenRows API key without touching the server directly.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from .utils import db_session
import subprocess
import threading
import os
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

# In-memory pipeline status (resets on server restart, good enough)
_pipeline_status = {
    "running": False,
    "step": None,
    "log": [],
    "last_run": None,
    "last_start_date": None,
    "last_end_date": None,
}

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
    """Runs spider → scraper → parser in a background thread."""
    import sys
    from datetime import datetime

    _pipeline_status["running"] = True
    _pipeline_status["log"] = []
    _pipeline_status["last_run"] = datetime.utcnow().isoformat()
    _pipeline_status["last_start_date"] = start_date
    _pipeline_status["last_end_date"] = end_date or "today"

    # CaseHarvester is mounted into the container at /opt/caseharvester
    harvester_dir = os.environ.get('HARVESTER_DIR', '/opt/caseharvester')

    # Inject the ZenRows key into the environment
    env = os.environ.copy()
    if zenrows_key:
        env["ZENROWS_KEY"] = zenrows_key

    venv_activate = os.path.join(harvester_dir, "venv", "bin", "activate")
    _log(f"[Init] harvester_dir={harvester_dir}")
    _log(f"[Init] venv activate={venv_activate}, exists={os.path.exists(venv_activate)}")

    def run_step(step_name, harvester_args):
        _pipeline_status["step"] = step_name
        _log(f"[{step_name}] Starting...")
        # Build the full shell command — activate venv then run harvester
        args_str = " ".join(harvester_args)
        shell_cmd = (
            f"cd {harvester_dir} && "
            f"source {venv_activate} && "
            f"python3 harvester.py --environment production {args_str}"
        )
        try:
            result = subprocess.run(
                ["bash", "-c", shell_cmd],
                cwd=harvester_dir, env=env,
                capture_output=True, text=True, timeout=3600
            )
            for line in (result.stdout + result.stderr).splitlines():
                _log(f"[{step_name}] {line}")
            if result.returncode != 0:
                _log(f"[{step_name}] FAILED (exit {result.returncode})")
                return False
            _log(f"[{step_name}] Done.")
            return True
        except subprocess.TimeoutExpired:
            _log(f"[{step_name}] TIMEOUT after 1 hour")
            return False
        except Exception as e:
            _log(f"[{step_name}] ERROR: {e}")
            return False

    try:
        # Step 1: Spider
        spider_args = ["spider", "--start-date", start_date]
        if end_date:
            spider_args += ["--end-date", end_date]
        if not run_step("Spider", spider_args):
            return

        # Step 2: Queue unscraped
        run_step("Queue", ["scraper", "--stale", "--include-unscraped"])

        # Step 3: Scrape
        if not run_step("Scraper", ["scraper", "--from-queue"]):
            return

        # Step 4: Parse
        run_step("Parser", ["parser", "--queue", "--parallel"])

        _pipeline_status["step"] = "Complete"
        _log("Pipeline finished successfully.")
    finally:
        _pipeline_status["running"] = False


# ── Routes ────────────────────────────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET'])
def get_settings():
    s = _load_settings()
    # Mask the keys for display
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
            foreclosures = db.execute(text("SELECT COUNT(*) FROM cases WHERE case_type ILIKE '%foreclosure%' AND last_scrape IS NOT NULL")).scalar()

            # Last filing date that was fully scraped — resume NEXT run from the day after this
            last_scraped_filing = db.execute(text(
                "SELECT MAX(filing_date) FROM cases WHERE last_scrape IS NOT NULL"
            )).scalar()

            # Oldest filing date not yet scraped — the earliest gap
            oldest_unscraped = db.execute(text(
                "SELECT MIN(filing_date) FROM cases WHERE last_scrape IS NULL AND scrape_exempt = false"
            )).scalar()

            # Date range that has been scraped (min → max)
            first_scraped_filing = db.execute(text(
                "SELECT MIN(filing_date) FROM cases WHERE last_scrape IS NOT NULL"
            )).scalar()

        except Exception:
            total = scraped = parsed = remaining = foreclosures = 0
            last_scraped_filing = oldest_unscraped = first_scraped_filing = None

    def fmt_date(d):
        if d is None:
            return None
        try:
            return d.strftime('%m/%d/%Y')
        except Exception:
            return str(d)

    return jsonify({
        "pipeline": _pipeline_status,
        "db": {
            "total": total,
            "scraped": scraped,
            "parsed": parsed,
            "remaining": remaining,
            "foreclosures_scraped": foreclosures,
            "last_scraped_filing_date": fmt_date(last_scraped_filing),
            "first_scraped_filing_date": fmt_date(first_scraped_filing),
            "oldest_unscraped_filing_date": fmt_date(oldest_unscraped),
        }
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

    thread = threading.Thread(
        target=_run_pipeline,
        args=(start_date, end_date, zenrows_key),
        daemon=True
    )
    thread.start()

    return jsonify({"ok": True, "message": "Pipeline started"})


@admin_bp.route('/stop', methods=['POST'])
def stop_pipeline():
    # Mark as stopped — running subprocess can't be killed easily,
    # but spider/scraper check for Forbidden and stop themselves.
    _pipeline_status["running"] = False
    _pipeline_status["step"] = "Stopped"
    return jsonify({"ok": True})
