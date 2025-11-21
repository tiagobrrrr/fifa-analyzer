import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from threading import Thread, Event
import datetime
import pytz

from models import db, Player, Team, Match, FinishedMatchArchive
from web_scraper import FIFA25Scraper
from data_analyzer import DataAnalyzer
from email_service import EmailService

# -------------------------------------------------------------
# CONFIGURAÇÃO DO APP
# -------------------------------------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///data/fifa25_bot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SESSION_SECRET", "fifa25-bot-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
db.init_app(app)

# -------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------
if not os.path.exists("logs"):
    os.makedirs("logs")

handler = RotatingFileHandler("logs/fifa25_bot.log", maxBytes=5_000_000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# -------------------------------------------------------------
# TIMEZONE
# -------------------------------------------------------------
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

# -------------------------------------------------------------
# SERVIÇOS
# -------------------------------------------------------------
scraper = FIFA25Scraper()
analyzer = DataAnalyzer()
email_service = EmailService()

# -------------------------------------------------------------
# CONTROLE DO BOT
# -------------------------------------------------------------
stop_event = Event()
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL", 30))  # seconds
last_scan = None

# -------------------------------------------------------------
# FUNÇÃO DE CRIAÇÃO DO BANCO (corrigido para Flask 3+)
# -------------------------------------------------------------
def create_database():
    with app.app_context():
        db.create_all()
        app.logger.info("📌 Banco de dados inicializado com sucesso!")

# -------------------------------------------------------------
# FUNÇÃO PARA SALVAR PARTIDAS
# -------------------------------------------------------------
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

        existing = Match.query.filter_by(match_id=m["match_id"], player=m["player_left"]).first()
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
            win=((m.get("goals_left") or 0) > (m.get("goals_right") or 0)),
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
            win=((m.get("goals_right") or 0) > (m.get("goals_left") or 0)),
            league=m.get("league"),
            stadium=m.get("stadium"),
            date=date_val,
            time=time_val,
            status=m.get("status", "planned")
        )

        db.session.add_all([left, right])
        db.session.commit()

        # Se finalizada → arquiva
        if m.get("status", "").lower() in ["finished", "final"]:
            a1 = FinishedMatchArchive(
                match_id=m["match_id"], player=left.player, team=left.team,
                opponent=left.opponent, goals=left.goals, goals_against=left.goals_against,
                win=left.win, league=left.league, stadium=left.stadium,
                date=left.date, time=left.time
            )
            a2 = FinishedMatchArchive(
                match_id=m["match_id"], player=right.player, team=right.team,
                opponent=right.opponent, goals=right.goals, goals_against=right.goals_against,
                win=right.win, league=right.league, stadium=right.stadium,
                date=right.date, time=right.time
            )
            db.session.add_all([a1, a2])
            db.session.commit()

        app.logger.info(f"Saved match {m['match_id']}")
        return left

    except Exception as e:
        app.logger.exception(f"Error persisting match: {e}")
        db.session.rollback()
        return None

# -------------------------------------------------------------
# SCAN DE PARTIDAS
# -------------------------------------------------------------
def scan_and_persist():
    global last_scan
    try:
        app.logger.info("Scanning for matches...")
        matches = scraper.get_live_matches() + scraper.get_recent_matches()
        last_scan = datetime.datetime.now(BRAZIL_TZ)

        players = {p.username for p in Player.query.all()}

        for m in matches:
            if players and not (m["player_left"] in players or m["player_right"] in players):
                continue
            persist_match_if_new(m)

        return True

    except Exception as e:
        app.logger.exception(f"Error scanning: {e}")
        try:
            email_service.send_report(
                os.getenv("EMAIL_ALERT_TO", os.getenv("EMAIL_ADDRESS")),
                None,
                subject="Bot scanning error",
                body_html=str(e)
            )
        except:
            pass
        return False

# -------------------------------------------------------------
# THREAD DO BOT
# -------------------------------------------------------------
def background_worker():
    app.logger.info("Background worker started")
    while not stop_event.is_set():
        ok = scan_and_persist()
        interval = SCAN_INTERVAL_SECONDS if ok else max(60, SCAN_INTERVAL_SECONDS * 2)
        stop_event.wait(interval)

    app.logger.info("Background worker stopped")
    try:
        email_service.send_report(
            os.getenv("EMAIL_ALERT_TO", os.getenv("EMAIL_ADDRESS")),
            None,
            subject="FIFA Analyzer stopped",
            body_html="Background worker stopped"
        )
    except:
        pass

worker_thread = Thread(target=background_worker, daemon=True)
worker_thread.start()

# -------------------------------------------------------------
# ROTAS
# -------------------------------------------------------------
@app.route("/")
def dashboard():
    today = datetime.date.today()
    matches = Match.query.filter(Match.date == today).all()

    def m_to_dict(m):
        return {
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

    matches_data = [m_to_dict(m) for m in matches]
    stats = analyzer.get_daily_stats(matches_data)

    return render_template("dashboard.html", matches=matches_data, stats=stats, last_scan=last_scan)

@app.route("/api/live_matches")
def api_live_matches():
    rows = Match.query.filter(Match.status.in_(["Live","Started","live","started"])).all()
    data = [{"player":r.player,"team":r.team,"opponent":r.opponent,
             "goals":r.goals,"status":r.status,"match_id":r.match_id} for r in rows]
    return jsonify({"matches": data, "count": len(data),
                    "last_scan": last_scan.isoformat() if last_scan else None})

@app.route("/players")
def players_page():
    players = Player.query.order_by(Player.username).all()
    return render_template("players.html", players=players)

@app.route("/players/add", methods=["POST"])
def players_add():
    username = request.form.get("username")
    display = request.form.get("display_name")

    if not username:
        flash("username required", "error")
        return redirect(url_for("players_page"))

    if Player.query.filter_by(username=username).first():
        flash("Player already exists", "warning")
        return redirect(url_for("players_page"))

    p = Player(username=username, display_name=display)
    db.session.add(p)
    db.session.commit()

    flash("Player added", "success")
    return redirect(url_for("players_page"))

@app.route("/players/delete/<int:player_id>", methods=["POST"])
def players_delete(player_id):
    p = Player.query.get(player_id)
    if p:
        db.session.delete(p)
        db.session.commit()
        flash("Player removed", "info")
    return redirect(url_for("players_page"))

@app.route("/teams")
def teams_page():
    teams = Team.query.order_by(Team.name).all()
    return render_template("teams.html", teams=teams)

@app.route("/teams/add", methods=["POST"])
def teams_add():
    name = request.form.get("name")
    if not name:
        flash("Team name required", "error")
        return redirect(url_for("teams_page"))

    if Team.query.filter_by(name=name).first():
        flash("Team already exists", "warning")
        return redirect(url_for("teams_page"))

    t = Team(name=name)
    db.session.add(t)
    db.session.commit()

    flash("Team added", "success")
    return redirect(url_for("teams_page"))

@app.route("/matches")
def matches_page():
    page = int(request.args.get("page", 1))
    per = 200
    rows = Match.query.order_by(Match.date.desc(), Match.time.desc()).limit(per).offset((page - 1) * per).all()
    return render_template("matches.html", matches=rows, page=page)

@app.route("/reports", methods=["GET", "POST"])
def reports_page():
    if request.method == "POST":
        email_to = request.form.get("email_to")

        today = datetime.date.today()
        rows = Match.query.filter(Match.date == today).all()

        matches = []
        for r in rows:
            matches.append({
                "match_id": r.match_id,
                "player": r.player,
                "team": r.team,
                "opponent": r.opponent,
                "goals": r.goals,
                "goals_against": r.goals_against,
                "win": r.win,
                "league": r.league,
                "stadium": r.stadium,
                "date": r.date.isoformat(),
                "time": r.time.isoformat() if r.time else None
            })

        report_file = analyzer.generate_excel_report(matches)

        if email_to:
            email_service.send_report(email_to, report_file)

        return redirect(url_for("reports_page"))

    return render_template("reports.html")

@app.route("/admin/shutdown", methods=["POST"])
def admin_shutdown():
    stop_event.set()
    flash("Shutdown requested", "info")
    return redirect(url_for("dashboard"))

# -------------------------------------------------------------
# KEEP ALIVE (UptimeRobot)
# -------------------------------------------------------------
keep_alive_app = Flask("keep_alive")

@keep_alive_app.route("/")
def keep_alive_home():
    return "✅ FIFA Analyzer rodando 24/7 - versão deploy Render"

def run_keep_alive():
    keep_alive_app.run(host="0.0.0.0", port=int(os.environ.get("KEEP_ALIVE_PORT", "8080")))

Thread(target=run_keep_alive, daemon=True).start()

# -------------------------------------------------------------
# START DO APP - CRIA DB AQUI (CORREÇÃO)
# -------------------------------------------------------------
if __name__ == "__main__":
    create_database()  # <-- FIX DO FLASK 3+
    app.logger.info("🚀 Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

