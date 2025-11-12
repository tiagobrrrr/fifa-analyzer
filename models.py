# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, Date, Time, DateTime, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
db = SQLAlchemy()

class Player(db.Model):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(150))
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Player {self.username}>"

class Team(db.Model):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Team {self.name}>"

class Match(db.Model):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    match_id = Column(String(200), nullable=False)
    player = Column(String(100), nullable=False, index=True)
    team = Column(String(200), nullable=False)
    opponent = Column(String(200), nullable=False)
    goals = Column(Integer, nullable=True)
    goals_against = Column(Integer, nullable=True)
    win = Column(Boolean, nullable=True)
    league = Column(String(200), nullable=True, index=True)
    stadium = Column(String(200), nullable=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=True)
    status = Column(String(50), default="planned")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('match_id', name='uix_match_id'),
        Index('ix_player_date_time', 'player', 'date', 'time'),
    )

    def __repr__(self):
        return f"<Match {self.match_id} {self.player} {self.team} vs {self.opponent}>"

class FinishedMatchArchive(db.Model):
    __tablename__ = "finished_matches"
    id = Column(Integer, primary_key=True)
    match_id = Column(String(200), nullable=False, index=True)
    player = Column(String(100), nullable=False)
    team = Column(String(200), nullable=False)
    opponent = Column(String(200), nullable=False)
    goals = Column(Integer, nullable=True)
    goals_against = Column(Integer, nullable=True)
    win = Column(Boolean, nullable=True)
    league = Column(String(200), nullable=True)
    stadium = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('match_id', name='uix_finished_match_id'),
    )

    def __repr__(self):
        return f"<Finished {self.match_id}>"
