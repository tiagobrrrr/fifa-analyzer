import os
import logging
import datetime
import pytz
from threading import Thread, Event
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler

# IMPORTAÇÕES DO PROJETO
from models import db, Player, Team, Match, FinishedMatchArchive
from web_scraper import FIFA25Scraper
from data_analyzer import DataAnalyzer
from email_service import EmailService


# -----------------------------------------------------------------------------
# GARANTE QUE A PASTA /data EXISTE (EVITA ERRO SQLITE NO RENDER)
# -----------------------------------------------------------------------------
if not os.path.exists("data"):
    os.makedirs("data")


# -----------------------------------------------------------------------------
# CONFIGURAÇÃO PRINCIPAL DO FLASK
# -----------------------------------------------------------------------------
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///data/fifa25_bot.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("SESSION_SECRET", "fifa25-secret")

db.init_app(app)

# TIMEZONE
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

# SERVICES
scraper = FIFA25Scraper()
analyzer = DataAnalyzer()
email_service = EmailService()

stop_event = Event()
SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL", 30))
last_scan = None


# -----------------------------------------------------------------------------
# LOGGING PARA ARQUIVO
# -----------------------------------------------------------------------------
if not os.path.exists("logs"):
    os.makedirs("logs")

handler = RotatingFileHandler("logs/fifa25.log", maxBytes=5_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# FUNÇÃO PARA CRIAR O BANCO NO FLASK 3+
# -----------------------------------------------------------------------------
def create_database():
    with app.app_context():
        db.create_all()
        app.logger.info("Banco criado/verificado com sucesso.")


# -----------------------------------------------------------------------------
# SALVA PARTIDA NO BANCO
# -----------------------------------------------------------------------------
def persist_match_if_new(m):
    try:
        ts = None
        if m.get("timestamp"):
            try:
                ts = datetime.datetime.fromisoformat(m["timestamp"])
            except:
                ts = None

        date_val = ts.date() if ts else datetime.date.today()
        time_val = ts.time() if ts else None

        existing = Match.query.filter_by(
            match_id=m["match_id"],
            player=m["player_left"]
        ).first()

        if existing:
            changed = False
            if existing.status != m.get("status"):
                existing.status = m.get("status")
                changed = True
            if changed:
                db.session.commit()
            return existing

        left = Match(
            match_id=m["match_id"],
            player=m["player_left"],
            team=m["team_left"],
            opponent=m["team_right"],
            goals=m.get("goals_left"),
            goals_against=m.get("goals_right"),
            win=(m.get("goals_left") > m.get("goals_right"))
            if m.get("goals_left") is not None else None,
            league=m.get("league"),
            stadium=m.get("stadium"),
            date=date_val,
            time=time_val,
            status=m.get("status", "planned")
        )

        right = Match(
            match_id=m["match_id"],
            player=m["player_right"],
            team=m["team_right"],
            opponent=m["team_left"],
            goals=m.get("goals_right"),
            goals_against=m.get("goals_left"),
            win=(m.get("goals_right") > m.get("goals_left"))
            if m.get("goals_right") is not None else None,
            league=m.get("league"),
            stadium=m.get("stadium"),
            date=date_val,
            time=time_val,
            status=m.get("status", "planned")
        )

        db.session.add_all([left, right])
        db.session.commit()

        return left

    except Exception as e:
        db.session.rollback()
        app.logger.exception("Erro persistindo partida: %s", e)
        return None


# -----------------------------------------------------------------------------
# PROCESSO DE SCAN
# -----------------------------------------------------------------------------
def scan_and_persist():
    global last_scan
    try:
        app.logger.info("🔎 Scaneando partidas...")

        matches = scraper.get_live_matches() + scraper.get_recent_matches()
        last_scan = datetime.datetime.now(BRAZIL_TZ)

        players = {p.username for p in Player.query.all()}

        for m in matches:
            if players:
                if not (m["player_left"] in players or m["player_right"] in players):
                    continue
            persist_match_if_new(m)

        return True

    except Exception as e:
        app.logger.exception("Erro no scan: %s", e)
        return False


# -----------------------------------------------------------------------------
# BACKGROUND WORKER
# -----------------------------------------------------------------------------
def background_worker():
    app.logger.info("🔥 Background worker iniciado.")

    while not stop_event.is_set():
        ok = scan_and_persist()

        if ok:
            stop_event.wait(SCAN_INTERVAL_SECONDS)
        else:
            stop_event.wait(60)

    app.logger.info("❌ Background worker finalizado.")


# Inicia a thread
Thread(target=background_worker, daemon=True).start()


# -----------------------------------------------------------------------------
# ROTAS
# -----------------------------------------------------------------------------
@app.route("/")
def dashboard():
    today = datetime.date.today()
    matches = Match.query.filter(Match.date == today).all()

    matches_data = [
        {
            "match_id": m.match_id,
            "player": m.player,
            "team": m.team,
            "opponent": m.opponent,
            "goals": m.goals,
            "goals_against": m.goals_against,
            "win": m.win,
            "league": m.league,
            "stadium": m.stadium,
            "date": m.date.isoformat(),
            "time": m.time.isoformat() if m.time else None,
            "status": m.status
        }
        for m in matches
    ]

    stats = analyzer.get_daily_stats(matches_data)

    return render_template("dashboard.html",
                           matches=matches_data,
                           stats=stats,
                           last_scan=last_scan)


@app.route("/api/live")
def api_live():
    rows = Match.query.filter(Match.status.in_(
        ["Live", "Started", "live", "started"])).all()

    data = [
        {
            "player": r.player,
            "team": r.team,
            "opponent": r.opponent,
            "match_id": r.match_id,
            "goals": r.goals,
            "status": r.status
        } for r in rows
    ]

    return jsonify({
        "matches": data,
        "count": len(data),
        "last_scan": last_scan.isoformat() if last_scan else None
    })


# -----------------------------------------------------------------------------
# KEEP ALIVE - PORTA SEPARADA
# -----------------------------------------------------------------------------
from flask import Flask as KAFlask
keep_alive_app = KAFlask("keep_alive")


@keep_alive_app.route("/")
def alive():
    return "✅ FIFA Analyzer Online"


def run_keep_alive():
    keep_alive_app.run(host="0.0.0.0",
                       port=int(os.getenv("KEEP_ALIVE_PORT", 8080)))


Thread(target=run_keep_alive, daemon=True).start()


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    create_database()
    app.run(host="0.0.0.0",
            port=int(os.getenv("PORT", 5000)))
