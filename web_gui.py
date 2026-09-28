#!/usr/bin/env python3
"""
Web GUI for Bonus Hedge Finder.

Flask app that wraps the same core functions main.py's CLI and gui.py's
Tkinter GUI use (collect_all_odds, find_all_opportunities, ...). Searches
run in a background thread per request so the browser can poll progress
instead of blocking on a single long HTTP request.

Run directly for local testing:
    python3 web_gui.py
Or in production via gunicorn (see README "Web GUI" section):
    gunicorn -w 2 -b 0.0.0.0:8080 --timeout 120 web_gui:app
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import uuid
from dataclasses import asdict
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, Response

from main import (
    BOOK_ALIASES,
    SPORT_KEYS,
    parse_books,
    get_regions_needed,
    collect_all_odds,
    find_all_opportunities,
    select_best_opportunity,
    find_qualifying_opportunities,
    select_best_qualifying_opportunity,
    calculate_hedge,
    calculate_alt_bonus_hedge,
    calculate_qualifying_hedge,
)

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
AUTH_PATH = BASE_DIR / "web_gui_auth.json"

app = Flask(__name__)

# -----------------------
# BASIC AUTH
# -----------------------
# The GUI is meant to be reachable on an open VPS port, so it is gated by
# HTTP Basic Auth. Credentials come from WEBGUI_USER / WEBGUI_PASSWORD env
# vars if set, otherwise from web_gui_auth.json, generating one on first run.

def _load_auth() -> tuple[str, str]:
    env_user = os.environ.get("WEBGUI_USER")
    env_password = os.environ.get("WEBGUI_PASSWORD")
    if env_user and env_password:
        return env_user, env_password

    if AUTH_PATH.exists():
        data = json.loads(AUTH_PATH.read_text())
        return data["user"], data["password"]

    user = env_user or "admin"
    password = env_password or secrets.token_urlsafe(12)
    AUTH_PATH.write_text(json.dumps({"user": user, "password": password}, indent=2))
    AUTH_PATH.chmod(0o600)
    return user, password


AUTH_USER, AUTH_PASSWORD = _load_auth()


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != AUTH_USER or auth.password != AUTH_PASSWORD:
            return Response(
                "Authentication required", 401,
                {"WWW-Authenticate": 'Basic realm="Bonus Hedge Finder"'},
            )
        return f(*args, **kwargs)
    return wrapped


# -----------------------
# CONFIG (books/sports only - never the API key)
# -----------------------

DEFAULT_CONFIG = {
    "allowed_books": sorted(BOOK_ALIASES.keys()),
    "sports": sorted(SPORT_KEYS.keys()),
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=4))


# -----------------------
# SEARCH JOBS (background thread + polling)
# -----------------------

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def opp_to_dict(opp) -> dict:
    return asdict(opp)


def run_search_job(job_id: str, params: dict) -> None:
    def progress_cb(sport_name, current, total):
        with jobs_lock:
            jobs[job_id]["progress"] = {"current": current, "total": total, "label": sport_name}

    try:
        odds_rows = collect_all_odds(
            params["api_key"],
            params["sports"],
            params["regions"],
            params["all_books"],
            progress_callback=progress_cb,
        )

        if params["mode"] in ("bonus", "alt_bonus"):
            calc_fn = calculate_alt_bonus_hedge if params["mode"] == "alt_bonus" else calculate_hedge
            opportunities = find_all_opportunities(
                odds_rows, params["bonus_book"], params["stake"], params["threshold"], calc_fn=calc_fn
            )
            best = select_best_opportunity(opportunities)
            sorted_opps = sorted(opportunities, key=lambda o: o.efficiency, reverse=True)
        else:
            opportunities = find_qualifying_opportunities(
                odds_rows, params["bonus_book"], params["stake"], params["threshold"]
            )
            best = select_best_qualifying_opportunity(opportunities)
            sorted_opps = sorted(opportunities, key=lambda o: o.loss_pct)

        result = {
            "mode": params["mode"],
            "odds_count": len(odds_rows),
            "opportunity_count": len(opportunities),
            "opportunities": [opp_to_dict(o) for o in sorted_opps[:50]],
            "best": opp_to_dict(best) if best else None,
        }
        with jobs_lock:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = result
    except Exception as e:  # noqa: BLE001 - surfaced to the UI, not swallowed
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


# -----------------------
# ROUTES
# -----------------------

@app.route("/")
@require_auth
def index():
    return INDEX_HTML


@app.route("/api/meta")
@require_auth
def meta():
    cfg = load_config()
    return jsonify({
        "books": sorted(BOOK_ALIASES.keys()),
        "sports": sorted(SPORT_KEYS.keys()),
        "config": cfg,
    })


@app.route("/api/config", methods=["POST"])
@require_auth
def update_config():
    body = request.get_json(force=True)
    cfg = {
        "allowed_books": [b for b in body.get("allowed_books", []) if b in BOOK_ALIASES],
        "sports": [s for s in body.get("sports", []) if s in SPORT_KEYS],
    }
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/calc", methods=["POST"])
@require_auth
def calc():
    body = request.get_json(force=True)
    try:
        stake = float(body["stake"])
        odds_a = float(body["odds_a"])
        odds_b = float(body["odds_b"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "stake, odds_a, odds_b must be numbers"}), 400

    bonus_hedge, bonus_profit, bonus_eff = calculate_hedge(stake, odds_a, odds_b)
    alt_bonus_hedge, alt_bonus_profit, alt_bonus_eff = calculate_alt_bonus_hedge(stake, odds_a, odds_b)
    qual_hedge, qual_loss, qual_loss_pct = calculate_qualifying_hedge(stake, odds_a, odds_b)

    return jsonify({
        "bonus": {"hedge_stake": bonus_hedge, "profit": bonus_profit, "efficiency_pct": bonus_eff * 100},
        "alt_bonus": {"hedge_stake": alt_bonus_hedge, "profit": alt_bonus_profit, "efficiency_pct": alt_bonus_eff * 100},
        "qualifying": {"hedge_stake": qual_hedge, "loss": qual_loss, "loss_pct": qual_loss_pct * 100},
    })


@app.route("/api/search", methods=["POST"])
@require_auth
def start_search():
    body = request.get_json(force=True)

    api_key = (body.get("api_key") or "").strip()
    mode = body.get("mode", "bonus")
    bonus_book_input = (body.get("bonus_book") or "").strip().lower()
    sports = body.get("sports") or []
    books = body.get("books") or []

    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if bonus_book_input not in BOOK_ALIASES:
        return jsonify({"error": f"Invalid book: {bonus_book_input}"}), 400
    if not sports:
        return jsonify({"error": "Select at least one sport"}), 400
    if not books:
        return jsonify({"error": "Select at least one hedge book"}), 400
    if mode not in ("bonus", "alt_bonus", "qualifying"):
        return jsonify({"error": "mode must be 'bonus', 'alt_bonus', or 'qualifying'"}), 400

    try:
        stake = float(body.get("stake", 0))
        threshold = float(body.get("threshold", 0)) / 100.0
    except (TypeError, ValueError):
        return jsonify({"error": "stake and threshold must be numbers"}), 400

    if stake <= 0:
        return jsonify({"error": "Stake must be positive"}), 400

    try:
        bonus_book = BOOK_ALIASES[bonus_book_input]
        hedge_books = parse_books(",".join(books))
    except KeyError as e:
        return jsonify({"error": f"Invalid book: {e}"}), 400

    all_books = hedge_books | {bonus_book}
    regions = get_regions_needed(all_books)

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "running", "progress": {"current": 0, "total": 0, "label": ""}, "result": None, "error": None}

    params = {
        "api_key": api_key,
        "mode": mode,
        "bonus_book": bonus_book,
        "stake": stake,
        "threshold": threshold,
        "sports": sports,
        "all_books": all_books,
        "regions": regions,
    }
    thread = threading.Thread(target=run_search_job, args=(job_id, params), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/search/<job_id>")
@require_auth
def search_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({"error": "unknown job"}), 404
        return jsonify(dict(job))


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


INDEX_HTML = (BASE_DIR / "templates" / "index.html").read_text()


if __name__ == "__main__":
    print(f"Web GUI credentials -> user: {AUTH_USER}  password: {AUTH_PASSWORD}")
    print("(stored in web_gui_auth.json; set WEBGUI_USER / WEBGUI_PASSWORD env vars to override)")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
