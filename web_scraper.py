# web_scraper.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FIFA25Scraper:
    def __init__(self, base_url="https://football.esportsbattle.com/"):
        self.base_url = base_url
        self.session = requests.Session()

    def fetch_page(self, path=""):
        url = self.base_url + path
        r = self.session.get(url, timeout=15)
        r.raise_for_status()
        return r.text

    def parse_matches_from_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        matches = []
        # Placeholder selectors - adapt to real HTML
        for card in soup.select(".match-card"):
            try:
                match_id = card.get("data-match-id") or card.get("id") or None
                status = card.select_one(".status").get_text(strip=True) if card.select_one(".status") else "Planned"
                left_player = card.select_one(".left .player-name").get_text(strip=True)
                right_player = card.select_one(".right .player-name").get_text(strip=True)
                left_team = card.select_one(".left .team-name").get_text(strip=True)
                right_team = card.select_one(".right .team-name").get_text(strip=True)
                score_text = card.select_one(".score").get_text(strip=True) if card.select_one(".score") else ""
                goals_left, goals_right = None, None
                if ":" in score_text:
                    parts = [p.strip() for p in score_text.split(":")]
                    if len(parts) >= 2:
                        try:
                            goals_left = int(parts[0])
                            goals_right = int(parts[1])
                        except:
                            goals_left, goals_right = None, None
                league = card.select_one(".league").get_text(strip=True) if card.select_one(".league") else None
                stadium = card.select_one(".stadium").get_text(strip=True) if card.select_one(".stadium") else None
                time_text = card.select_one(".time").get_text(strip=True) if card.select_one(".time") else None
                timestamp = None
                if time_text:
                    try:
                        t = datetime.strptime(time_text, "%H:%M")
                        today = datetime.now().date()
                        timestamp = datetime.combine(today, t.time()).isoformat()
                    except:
                        timestamp = None
                if not match_id:
                    match_id = f"{left_player}-{right_player}-{left_team[:10]}-{right_team[:10]}-{league}-{time_text}"
                matches.append({
                    "match_id": match_id,
                    "player_left": left_player,
                    "player_right": right_player,
                    "team_left": left_team,
                    "team_right": right_team,
                    "goals_left": goals_left,
                    "goals_right": goals_right,
                    "status": status,
                    "league": league,
                    "stadium": stadium,
                    "timestamp": timestamp
                })
            except Exception as e:
                logger.debug(f"Error parsing card: {e}")
                continue
        return matches

    def get_live_matches(self):
        html = self.fetch_page("live")
        return self.parse_matches_from_html(html)

    def get_recent_matches(self):
        html = self.fetch_page("results")
        return self.parse_matches_from_html(html)
