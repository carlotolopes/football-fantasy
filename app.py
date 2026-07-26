"""
FOOTBALL FANTASY — UK EDITION
Premier League, EFL Championship, League One, League Two
Scottish Premiership, Championship, League One, League Two
Streamlit App — Full Version
"""

import streamlit as st
import sqlite3
import pandas as pd
import random
import requests
import json
import hashlib
import os
from datetime import datetime, timezone, timedelta

#
# CONFIGURATION
#

DB_PATH = "football_fantasy.db"
SEASON = 2026
MAX_PICKS = 5
BONUS_POINTS = 1
WIN_POINTS = 3
DRAW_POINTS = 1

# API-Football v3 League IDs
PREMIER_LEAGUE_ID = 39
CHAMPIONSHIP_ID = 40
LEAGUE_ONE_ID = 41
LEAGUE_TWO_ID = 42
SCOTTISH_PREMIERSHIP_ID = 179
SCOTTISH_CHAMPIONSHIP_ID = 180
SCOTTISH_LEAGUE_ONE_ID = 181
SCOTTISH_LEAGUE_TWO_ID = 182

API_BASE = "https://v3.football.api-sports.io"

# All leagues
LEAGUES = [
    ("Premier League", PREMIER_LEAGUE_ID),
    ("Championship", CHAMPIONSHIP_ID),
    ("League One", LEAGUE_ONE_ID),
    ("League Two", LEAGUE_TWO_ID),
    ("Scottish Premiership", SCOTTISH_PREMIERSHIP_ID),
    ("Scottish Championship", SCOTTISH_CHAMPIONSHIP_ID),
    ("Scottish League One", SCOTTISH_LEAGUE_ONE_ID),
    ("Scottish League Two", SCOTTISH_LEAGUE_TWO_ID),
]

# Full team lists 2026/27
PREMIER_LEAGUE_TEAMS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford",
    "Brighton and Hove Albion", "Chelsea", "Coventry City",
    "Crystal Palace", "Everton", "Fulham", "Hull City",
    "Ipswich Town", "Leeds United", "Liverpool",
    "Manchester City", "Manchester United", "Newcastle United",
    "Nottingham Forest", "Sunderland", "Tottenham Hotspur"
]

CHAMPIONSHIP_TEAMS = [
    "Birmingham City", "Blackburn Rovers", "Bolton Wanderers",
    "Bristol City", "Burnley", "Cardiff City", "Charlton Athletic",
    "Derby County", "Lincoln City", "Middlesbrough", "Millwall",
    "Norwich City", "Portsmouth", "Preston North End",
    "Queens Park Rangers", "Sheffield United", "Southampton",
    "Stoke City", "Swansea City", "Watford", "West Bromwich Albion",
    "West Ham United", "Wolverhampton Wanderers", "Wrexham"
]

LEAGUE_ONE_TEAMS = [
    "AFC Wimbledon", "Barnsley", "Blackpool", "Bradford City",
    "Bromley", "Burton Albion", "Cambridge United",
    "Doncaster Rovers", "Huddersfield Town", "Leicester City",
    "Leyton Orient", "Luton Town", "Mansfield Town",
    "Milton Keynes Dons", "Notts County", "Oxford United",
    "Peterborough United", "Plymouth Argyle", "Reading",
    "Sheffield Wednesday", "Stevenage", "Stockport County",
    "Wigan Athletic", "Wycombe Wanderers"
]

LEAGUE_TWO_TEAMS = [
    "Accrington Stanley", "Barnet", "Bristol Rovers",
    "Cheltenham Town", "Chesterfield", "Colchester United",
    "Crawley Town", "Crewe Alexandra", "Exeter City",
    "Fleetwood Town", "Gillingham", "Grimsby Town",
    "Newport County", "Northampton Town", "Oldham Athletic",
    "Port Vale", "Rochdale", "Rotherham United",
    "Salford City", "Shrewsbury Town", "Swindon Town",
    "Tranmere Rovers", "Walsall", "York City"
]

SCOTTISH_PREMIERSHIP_TEAMS = [
    "Aberdeen", "Celtic", "Dundee", "Dundee United",
    "Falkirk", "Heart of Midlothian", "Hibernian",
    "Kilmarnock", "Motherwell", "Rangers",
    "St Johnstone", "St Mirren"
]

SCOTTISH_CHAMPIONSHIP_TEAMS = [
    "Arbroath", "Ayr United", "Dunfermline Athletic",
    "Greenock Morton", "Inverness Caledonian Thistle",
    "Livingston", "Partick Thistle", "Queen's Park",
    "Raith Rovers", "Stenhousemuir"
]

SCOTTISH_LEAGUE_ONE_TEAMS = [
    "Airdrieonians", "Alloa Athletic", "Cove Rangers",
    "East Fife", "East Kilbride", "Hamilton Academical",
    "Montrose", "Peterhead", "Queen of the South",
    "Ross County"
]

SCOTTISH_LEAGUE_TWO_TEAMS = [
    "Annan Athletic", "Clyde", "Dumbarton",
    "Edinburgh City", "Elgin City", "Forfar Athletic",
    "Kelty Hearts", "Stirling Albion", "Stranraer",
    "The Spartans"
]

ALL_TEAMS = sorted(set(
    PREMIER_LEAGUE_TEAMS + CHAMPIONSHIP_TEAMS + LEAGUE_ONE_TEAMS +
    LEAGUE_TWO_TEAMS + SCOTTISH_PREMIERSHIP_TEAMS +
    SCOTTISH_CHAMPIONSHIP_TEAMS + SCOTTISH_LEAGUE_ONE_TEAMS +
    SCOTTISH_LEAGUE_TWO_TEAMS
))

#
# UTILITIES
#

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

#
# DATABASE
#

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','-3 hours'))
        );

        CREATE TABLE IF NOT EXISTS game_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now','-3 hours'))
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL,
            league TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            status TEXT DEFAULT 'scheduled',
            fixture_id INTEGER,
            UNIQUE(round_number, league, home_team, away_team)
        );

        CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            FOREIGN KEY (player_id) REFERENCES players(id),
            UNIQUE(player_id, round_number, team_name)
        );

        CREATE TABLE IF NOT EXISTS matchups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_number INTEGER NOT NULL,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER NOT NULL,
            player1_goals INTEGER DEFAULT 0,
            player2_goals INTEGER DEFAULT 0,
            player1_points INTEGER DEFAULT 0,
            player2_points INTEGER DEFAULT 0,
            FOREIGN KEY (player1_id) REFERENCES players(id),
            FOREIGN KEY (player2_id) REFERENCES players(id)
        );

        CREATE TABLE IF NOT EXISTS standings (
            player_id INTEGER PRIMARY KEY,
            total_points INTEGER DEFAULT 0,
            bonus_points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            rounds_played INTEGER DEFAULT 0,
            total_goals INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS game_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Create default admin if not exists
    cursor.execute("SELECT id FROM players WHERE is_admin=1 LIMIT 1")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT OR IGNORE INTO players (name, password_hash, is_admin) VALUES (?, ?, 1)",
            ("admin", hash_password("admin123"))
        )

    # Ensure every player has a standings record
    cursor.execute("""
        INSERT OR IGNORE INTO standings (player_id, total_points, bonus_points, wins, draws, losses, rounds_played, total_goals)
        SELECT id, 0, 0, 0, 0, 0, 0, 0 FROM players
    """)

    conn.commit()
    conn.close()

#
# DATABASE FUNCTIONS
#

def get_player(player_id=None, name=None):
    conn = get_conn()
    cursor = conn.cursor()
    if player_id:
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
    elif name:
        cursor.execute("SELECT * FROM players WHERE name = ?", (name,))
    else:
        cursor.execute("SELECT * FROM players ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    if player_id or name:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]

def get_players():
    return get_player()

def get_current_round():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT round_number FROM game_rounds WHERE status != 'completed' ORDER BY round_number DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row)['round_number'] if row else None

def get_round_status(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM game_rounds WHERE round_number = ?", (round_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)['status'] if row else None

def get_or_create_round(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO game_rounds (round_number, status) VALUES (?, 'pending')",
                   (round_number,))
    conn.commit()
    conn.close()

def set_round_status(round_number, status):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE game_rounds SET status = ? WHERE round_number = ?", (status, round_number))
    conn.commit()
    conn.close()

def get_matches(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE round_number = ? ORDER BY league, home_team", (round_number,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_match(round_number, league, home_team, away_team, home_goals, away_goals, status, fixture_id=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO matches
        (round_number, league, home_team, away_team, home_goals, away_goals, status, fixture_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (round_number, league, home_team, away_team, home_goals, away_goals, status, fixture_id))
    conn.commit()
    conn.close()

def get_picks(player_id, round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM picks WHERE player_id = ? AND round_number = ?",
                   (player_id, round_number))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r)['team_name'] for r in rows]

def save_picks(player_id, round_number, teams):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM picks WHERE player_id = ? AND round_number = ?",
                   (player_id, round_number))
    for team in teams:
        cursor.execute(
            "INSERT INTO picks (player_id, round_number, team_name) VALUES (?, ?, ?)",
            (player_id, round_number, team)
        )
    conn.commit()
    conn.close()

def get_all_picks(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.player_id, p.team_name, pl.name as player_name
        FROM picks p
        JOIN players pl ON pl.id = p.player_id
        WHERE p.round_number = ?
        ORDER BY pl.name
    """, (round_number,))
    rows = cursor.fetchall()
    conn.close()
    result = {}
    for r in rows:
        d = dict(r)
        pid = d['player_id']
        if pid not in result:
            result[pid] = {'name': d['player_name'], 'teams': []}
        result[pid]['teams'].append(d['team_name'])
    return result

def get_matchups(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, p1.name as p1_name, p2.name as p2_name
        FROM matchups m
        JOIN players p1 ON p1.id = m.player1_id
        JOIN players p2 ON p2.id = m.player2_id
        WHERE m.round_number = ?
    """, (round_number,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def generate_matchups(round_number):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT p.player_id, pl.name
        FROM picks p
        JOIN players pl ON pl.id = p.player_id
        WHERE p.round_number = ?
    """, (round_number,))
    players = [dict(r) for r in cursor.fetchall()]
    random.shuffle(players)

    if len(players) < 2:
        conn.close()
        return False, "Need at least 2 players with picks to generate matchups."

    by_player = None
    if len(players) % 2 != 0:
        by_player = players.pop()

    cursor.execute("DELETE FROM matchups WHERE round_number = ?", (round_number,))

    for i in range(0, len(players), 2):
        if i + 1 < len(players):
            p1 = players[i]
            p2 = players[i + 1]
            cursor.execute("""
                INSERT INTO matchups (round_number, player1_id, player2_id)
                VALUES (?, ?, ?)
            """, (round_number, p1['player_id'], p2['player_id']))

    if by_player:
        cursor.execute("""
            INSERT INTO matchups (round_number, player1_id, player2_id, player1_points, player2_points, player1_goals)
            VALUES (?, ?, ?, 3, 0, 999)
        """, (round_number, by_player['player_id'], by_player['player_id']))

    conn.commit()
    conn.close()
    return True, f"Matchups generated for {len(players)} players."

def calculate_round_scores(round_number):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT home_team, away_team, home_goals, away_goals
        FROM matches
        WHERE round_number = ? AND status = 'finished'
    """, (round_number,))
    match_results = {}
    for r in cursor.fetchall():
        d = dict(r)
        match_results[d['home_team']] = d['home_goals']
        match_results[d['away_team']] = d['away_goals']

    all_picks = get_all_picks(round_number)

    player_goals = {}
    for pid, data in all_picks.items():
        total = 0
        for team in data['teams']:
            if team in match_results:
                total += match_results[team]
        player_goals[pid] = total

    cursor.execute("SELECT * FROM matchups WHERE round_number = ?", (round_number,))
    matchups = cursor.fetchall()

    for m in matchups:
        m = dict(m)
        p1_id = m['player1_id']
        p2_id = m['player2_id']
        p1_goals = player_goals.get(p1_id, 0)
        p2_goals = player_goals.get(p2_id, 0)

        if p1_id == p2_id:
            p1_points = 3
            p2_points = 0
        else:
            if p1_goals > p2_goals:
                p1_points = WIN_POINTS
                p2_points = 0
            elif p2_goals > p1_goals:
                p1_points = 0
                p2_points = WIN_POINTS
            else:
                p1_points = DRAW_POINTS
                p2_points = DRAW_POINTS

        cursor.execute("""
            UPDATE matchups
            SET player1_goals=?, player2_goals=?, player1_points=?, player2_points=?
            WHERE id=?
        """, (p1_goals, p2_goals, p1_points, p2_points, m['id']))

    if player_goals:
        max_goals = max(player_goals.values())
        bonus_players = [pid for pid, g in player_goals.items() if g == max_goals and g > 0]

        cursor.execute("SELECT * FROM matchups WHERE round_number = ?", (round_number,))
        updated_matchups = cursor.fetchall()

        for m in updated_matchups:
            m = dict(m)
            for pid, pts_field, goals_field in [
                (m['player1_id'], 'player1_points', 'player1_goals'),
                (m['player2_id'], 'player2_points', 'player2_goals')
            ]:
                pts = m[pts_field]
                goals = m[goals_field]
                bonus = BONUS_POINTS if pid in bonus_players else 0

                if m['player1_id'] == m['player2_id']:
                    is_win = 1
                    is_draw = 0
                    is_loss = 0
                elif pid == m['player1_id']:
                    is_win = 1 if m['player1_goals'] > m['player2_goals'] else 0
                    is_draw = 1 if m['player1_goals'] == m['player2_goals'] else 0
                    is_loss = 1 if m['player1_goals'] < m['player2_goals'] else 0
                else:
                    is_win = 1 if m['player2_goals'] > m['player1_goals'] else 0
                    is_draw = 1 if m['player2_goals'] == m['player1_goals'] else 0
                    is_loss = 1 if m['player2_goals'] < m['player1_goals'] else 0

                cursor.execute("""
                    INSERT INTO standings (player_id, total_points, bonus_points, wins, draws, losses, rounds_played, total_goals)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(player_id) DO UPDATE SET
                        total_points = total_points + ?,
                        bonus_points = bonus_points + ?,
                        wins = wins + ?,
                        draws = draws + ?,
                        losses = losses + ?,
                        rounds_played = rounds_played + 1,
                        total_goals = total_goals + ?
                """, (pid, pts + bonus, bonus, is_win, is_draw, is_loss, goals,
                      pts + bonus, bonus, is_win, is_draw, is_loss, goals))

    cursor.execute("UPDATE game_rounds SET status = 'completed' WHERE round_number = ?", (round_number,))

    conn.commit()
    conn.close()
    return True, "Scores calculated successfully!"

def get_standings():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pl.name, s.*
        FROM standings s
        JOIN players pl ON pl.id = s.player_id
        ORDER BY s.total_points DESC, s.total_goals DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

#
# API-FOOTBALL CLIENT
#

class FootballAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
        }

    def _get(self, endpoint, params=None):
        if not self.api_key:
            return None
        try:
            url = f"{API_BASE}/{endpoint}"
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('results', 0) > 0:
                    return data
            return None
        except Exception as e:
            st.error(f"API error: {e}")
            return None

    def get_current_round(self, league_id):
        data = self._get("fixtures/rounds", {
            "league": league_id,
            "season": SEASON,
            "current": "true"
        })
        if data and data.get('response'):
            return data['response'][0]
        return None

    def get_round_fixtures(self, league_id, round_name):
        data = self._get("fixtures", {
            "league": league_id,
            "season": SEASON,
            "round": round_name
        })
        if data:
            return data['response']
        return []

    def fetch_and_save_round(self, round_number):
        """Fetch results from all UK leagues and save to database"""
        try:
            total_saved = 0
            for league_name, league_id in LEAGUES:
                try:
                    round_data = self.get_current_round(league_id)
                    if not round_data:
                        continue

                    fixtures = self.get_round_fixtures(league_id, round_data)

                    for f in fixtures:
                        status = f['fixture']['status']['short']
                        home = f['teams']['home']['name']
                        away = f['teams']['away']['name']
                        home_goals = f['goals']['home']
                        away_goals = f['goals']['away']
                        fixture_id = f['fixture']['id']
                        is_finished = status in ('FT', 'AET', 'PEN')
                        save_match(
                            round_number, league_name,
                            home, away,
                            home_goals, away_goals,
                            'finished' if is_finished else 'scheduled',
                            fixture_id
                        )
                        total_saved += 1
                except Exception:
                    continue

            if total_saved == 0:
                return False, "No matches found for this round."
            return True, f"{total_saved} matches saved for Round {round_number}."

        except Exception as e:
            return False, f"Error fetching data: {e}"

#
# STREAMLIT INTERFACE
#

def login_screen():
    st.markdown("""
    <h1 style='text-align: center;'>🏆 Football Fantasy</h1>
    <h3 style='text-align: center; color: #FFD700;'>UK Edition — Premier League, EFL &amp; SPFL</h3>
    <hr>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            name = st.text_input("Your name")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign in / Register", use_container_width=True)

            if submit and name:
                if not password:
                st.error("Please enter a password.")
                return

                conn = get_conn()
                cursor = conn.cursor()
                pw_hash = hash_password(password)
                cursor.execute("SELECT * FROM players WHERE name = ?", (name,))
                player = cursor.fetchone()

                if player:
                    player = dict(player)
                    if player['password_hash'] == pw_hash:
                        st.session_state['player'] = player
                        conn.close()
                        st.rerun()
                else:
                    st.error("Incorrect password!")
                    conn.close()
                    return
            else:
                cursor.execute(
                    "INSERT INTO players (name, password_hash) VALUES (?, ?)",
                    (name, pw_hash)
                )
                new_id = cursor.lastrowid
                conn.commit()
                cursor.execute("""
                    INSERT OR IGNORE INTO standings (player_id) VALUES (?)
                """, (new_id,))
                conn.commit()
                conn.close()
                st.success("Account created! Please sign in.")
                st.rerun()
            conn.close()

        st.markdown("---")
        st.markdown("""
        **🏆 How it works:**
        - Each round, pick **5 teams** from the Premier League, EFL, and SPFL
        - Your score = **total goals** scored by those teams in that round
        - You're randomly drawn against another player in a **head-to-head match**
        - **Winner = 3 points**, Draw = 1 point each
        - **Bonus:** highest scoring player of the round gets +1 extra point
        """)

        st.markdown("---")
        st.markdown("### 📺 Check fixtures & results at:")
        st.markdown("""
- [Premier League](https://www.premierleague.com) — Official PL site
- [EFL Championship / League One / League Two](https://www.efl.com/competitions/efl-championship/) — Official EFL site
- [SPFL (Scottish Football)](https://spfl.co.uk/) — Official SPFL site
        """)

def admin_panel():
    st.header("🔧 Admin Panel")
    players = get_players()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Rounds", "📊 Manage Results", "👥 Players", "⚙️ Settings"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Start New Round")
            round_num = st.number_input("Round number", min_value=1, max_value=46, value=1)

            api_key = st.secrets.get("API_FOOTBALL_KEY", "")
            use_api = len(api_key) > 0

            if st.button("🚀 Start Round", use_container_width=True):
                get_or_create_round(round_num)

                if use_api:
                    with st.spinner("Fetching match data from the internet..."):
                        client = FootballAPIClient(api_key)
                        success, msg = client.fetch_and_save_round(round_num)
                        if success:
                            matches = get_matches(round_num)
                            finished = [m for m in matches if m['status'] == 'finished']
                            if finished:
                                set_round_status(round_num, 'picking')
                                st.success(f"Round {round_num} started! {len(finished)} finished matches loaded.")
                            else:
                                st.warning("No finished matches yet in this round. Players can still see the teams and choose.")
                                set_round_status(round_num, 'picking')
                        else:
                            st.warning(f"{msg} — you can enter results manually.")
                            set_round_status(round_num, 'picking')
                else:
                    set_round_status(round_num, 'picking')
                    st.info("Manual mode: enter results in the 'Manage Results' tab.")
                st.rerun()

        with col2:
            st.subheader("Current Status")
            current = get_current_round()
            if current:
                status = get_round_status(current)
                st.metric("Active Round", f"Round {current}")
                st.metric("Status", status.upper())

                if status == 'picking':
                    player_count = get_all_picks(current)
                    st.metric("Players who have picked", len(player_count))
                elif status == 'closed':
                    matchups = get_matchups(current)
                    st.metric("Matchups generated", len(matchups))

                if status == 'picking':
                    if st.button("🔒 Close Picks & Draw Matchups", use_container_width=True):
                        success, msg = generate_matchups(current)
                        if success:
                            set_round_status(current, 'closed')
                            st.success(msg)
                            st.rerun()
                        else:
                            st.warning(msg)

                elif status == 'closed':
                    if st.button("📊 Calculate Scores!", use_container_width=True, type="primary"):
                        success, msg = calculate_round_scores(current)
                        if success:
                            st.success(msg)
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.info("No active round. Start one above.")

    with tab2:
        st.subheader("Manage Match Results")
        round_edit = st.number_input("Round to edit", min_value=1, max_value=46, value=get_current_round() or 1)

        matches = get_matches(round_edit)
        if matches:
            league_filter = st.selectbox("Filter by league", ["All", "Premier League", "Championship", "League One", "League Two",
                                                               "Scottish Premiership", "Scottish Championship", "Scottish League One", "Scottish League Two"])
            filtered = matches
            if league_filter != "All":
                filtered = [m for m in matches if m['league'] == league_filter]

            st.info(f"Showing {len(filtered)} matches. Edit scores directly:")
            for match in filtered:
                cols = st.columns([3, 1, 1, 1, 3])
                with cols[0]:
                    st.markdown(f"**{match['home_team']}**")
                with cols[1]:
                    home_goals = st.number_input(
                        f"h_{match['id']}",
                        value=match['home_goals'] if match['home_goals'] is not None else 0,
                        min_value=0, max_value=20,
                        key=f"h_{match['id']}",
                        label_visibility="collapsed"
                    )
                with cols[2]:
                    st.markdown("×")
                with cols[3]:
                    away_goals = st.number_input(
                        f"a_{match['id']}",
                        value=match['away_goals'] if match['away_goals'] is not None else 0,
                        min_value=0, max_value=20,
                        key=f"a_{match['id']}",
                        label_visibility="collapsed"
                    )
                with cols[4]:
                    st.markdown(f"**{match['away_team']}**")

                if st.button(f"💾 Save", key=f"save_{match['id']}"):
                    save_match(
                        round_edit, match['league'],
                        match['home_team'], match['away_team'],
                        home_goals, away_goals,
                        'finished', match['fixture_id']
                    )
                    st.success(f"{match['home_team']} {home_goals}×{away_goals} {match['away_team']} saved!")
                    st.rerun()
        else:
            st.info("No matches registered yet for this round.")
            st.markdown("**Add match manually:**")
            with st.form("add_match"):
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    home = st.text_input("Home team")
                with col2:
                    hg = st.number_input("Home goals", 0, 20, 0, label_visibility="collapsed")
                    st.markdown("×")
                    ag = st.number_input("Away goals", 0, 20, 0, label_visibility="collapsed")
                with col3:
                    away = st.text_input("Away team")
                league = st.selectbox("League", [l[0] for l in LEAGUES])
                if st.form_submit_button("➕ Add"):
                    save_match(round_edit, league, home.strip(), away.strip(), hg, ag, 'finished')
                    st.success("Match added!")
                    st.rerun()

    with tab3:
        st.subheader(f"Registered Players ({len(players)})")
        for p in players:
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"{'👑 ' if p['is_admin'] else '👤 '}**{p['name']}**")
            with cols[1]:
                if not p['is_admin']:
                    if st.button(f"❌ Remove", key=f"del_{p['id']}"):
                        conn = get_conn()
                        c = conn.cursor()
                        c.execute("DELETE FROM players WHERE id = ?", (p['id'],))
                        c.execute("DELETE FROM standings WHERE player_id = ?", (p['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun()

    with tab4:
        st.subheader("API Configuration")
        key_status = "✅ Configured" if st.secrets.get("API_FOOTBALL_KEY", "") else "❌ Not configured"
        st.markdown(f"**API-Football:** {key_status}")
        if not st.secrets.get("API_FOOTBALL_KEY", ""):
            st.warning("""
            To fetch results automatically:
            1. Go to https://dashboard.api-football.com/register
            2. Create a free account (100 req/day)
            3. Copy your API key
            4. Add it in Streamlit Cloud Secrets as `API_FOOTBALL_KEY`
            """)

        if st.button("🔄 Reset Database (careful!)"):
            if st.checkbox("I confirm I want to delete all data"):
                os.remove(DB_PATH)
                init_database()
                st.success("Database reset!")
                st.rerun()

def player_dashboard(player):
    st.header(f"👋 Hello, **{player['name']}**!")
    current_round = get_current_round()

    if not current_round:
        st.info("⏳ Waiting for the admin to start a new round.")
        return

    status = get_round_status(current_round)
    round_info = st.container(border=True)
    with round_info:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("Current Round", f"Round {current_round}")
        with col2:
            st.metric("Status", status.upper())

    st.markdown("---")
    st.markdown("📺 **Check full fixtures & results at:**")
    st.markdown("""
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 [Premier League](https://www.premierleague.com)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 [EFL Championship](https://www.efl.com/competitions/efl-championship/)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 [EFL League One](https://www.efl.com/competitions/efl-league-one/)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 [EFL League Two](https://www.efl.com/competitions/efl-league-two/)
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 [SPFL Premiership & lower](https://spfl.co.uk/)
    """)

    # Show matches
    matches = get_matches(current_round)
    if matches:
        with st.expander("📋 Matches this round", expanded=True):
            league_order = ["Premier League", "Championship", "League One", "League Two",
                           "Scottish Premiership", "Scottish Championship", "Scottish League One", "Scottish League Two"]
            for league_name in league_order:
                league_matches = [m for m in matches if m['league'] == league_name]
                if league_matches:
                    st.markdown(f"**{league_name}**")
                    for m in league_matches:
                        if m['status'] == 'finished':
                            st.markdown(f"• {m['home_team']} **{m['home_goals']}×{m['away_goals']}** {m['away_team']}")
                        else:
                            st.markdown(f"• {m['home_team']} × {m['away_team']} _(awaiting)_")

    # Picking phase
    if status == 'picking':
        st.markdown("---")
        st.subheader("🎯 Pick Your 5 Teams")
        my_picks = get_picks(player['id'], current_round)

        available_teams = []
        for m in matches:
            if m['home_team'] not in available_teams:
                available_teams.append(m['home_team'])
            if m['away_team'] not in available_teams:
                available_teams.append(m['away_team'])
        available_teams = sorted(set(available_teams + ALL_TEAMS))

        selected = st.multiselect(
            f"Select **{MAX_PICKS} teams** (you've picked {len(my_picks)}/{MAX_PICKS})",
            options=available_teams,
            default=my_picks,
            max_selections=MAX_PICKS,
            placeholder="Click to choose your teams..."
        )

        # Check if player already submitted picks for this round
        already_submitted = len(my_picks) == MAX_PICKS

        if already_submitted:
            st.success(f"✅ You've already submitted your {MAX_PICKS} picks for this round!")
            st.markdown(f"**Your teams:** {', '.join(my_picks)}")
        else:
            if st.button("💾 Save My Picks", use_container_width=True, type="primary"):
                if len(selected) == MAX_PICKS:
                    save_picks(player['id'], current_round, selected)
                    st.success(f"✅ {MAX_PICKS} teams saved successfully!")
                    st.rerun()
                else:
                    st.warning(f"Choose exactly {MAX_PICKS} teams (you selected {len(selected)}).")
        all_picks = get_all_picks(current_round)
        st.markdown("---")
        st.markdown(f"**Players who have picked:** {len(all_picks)}")
        for pid, data in all_picks.items():
            st.markdown(f"✅ {data['name']}")

    elif status == 'closed':
        matchups = get_matchups(current_round)
        my_matchup = None
        for m in matchups:
            if m['player1_id'] == player['id'] or m['player2_id'] == player['id']:
                my_matchup = m
                break

        st.markdown("---")
        st.subheader("⚔️ Your Matchup")
        if my_matchup:
            opponent_id = my_matchup['player2_id'] if my_matchup['player1_id'] == player['id'] else my_matchup['player1_id']
            opponent_name = my_matchup['p2_name'] if my_matchup['player1_id'] == player['id'] else my_matchup['p1_name']
            my_picks_list = get_picks(player['id'], current_round)
            opp_picks_list = get_picks(opponent_id, current_round)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"### 🟢 You")
                for t in my_picks_list:
                    st.markdown(f"- {t}")
            with col2:
                st.markdown(f"### 🔴 {opponent_name}")
                for t in opp_picks_list:
                    st.markdown(f"- {t}")

            st.info("⏳ Waiting for the admin to calculate the scores...")
        else:
            st.info("You're not in any matchup this round (maybe you didn't pick your teams).")

    elif status == 'completed':
        matchups = get_matchups(current_round)
        my_matchup = None
        for m in matchups:
            if m['player1_id'] == player['id'] or m['player2_id'] == player['id']:
                my_matchup = m
                break

        if my_matchup:
            st.markdown("---")
            st.subheader("📊 Round Result")
            is_p1 = my_matchup['player1_id'] == player['id']
            my_goals = my_matchup['player1_goals'] if is_p1 else my_matchup['player2_goals']
            opp_goals = my_matchup['player2_goals'] if is_p1 else my_matchup['player1_goals']
            my_pts = my_matchup['player1_points'] if is_p1 else my_matchup['player2_points']
            my_bonus = 0

            all_picks = get_all_picks(current_round)
            player_goals = {}
            for m in matchups:
                player_goals[m['player1_id']] = m['player1_goals']
                if m['player1_id'] != m['player2_id']:
                    player_goals[m['player2_id']] = m['player2_goals']

            if player_goals:
                max_goals = max(player_goals.values())
                if player_goals.get(player['id'], 0) == max_goals and max_goals > 0:
                    my_bonus = BONUS_POINTS

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Your goals", my_goals)
            with col2:
                st.metric("Opponent's goals", opp_goals)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏆 Match points", my_pts)
            with col2:
                st.metric("⭐ Bonus", my_bonus)
            with col3:
                st.metric("📊 Round total", my_pts + my_bonus)

def leaderboard_screen():
    st.header("🏆 Overall Standings")
    standings = get_standings()

    if standings:
        df = pd.DataFrame(standings)
        df = df.rename(columns={
            'name': 'Player',
            'total_points': 'Pts',
            'bonus_points': 'Bonus',
            'wins': 'W',
            'draws': 'D',
            'losses': 'L',
            'rounds_played': 'R',
            'total_goals': 'Goals'
        })
        df.insert(0, '#', range(1, len(df) + 1))

        st.dataframe(
            df[['#', 'Player', 'Pts', 'Bonus', 'W', 'D', 'L', 'Goals', 'R']],
            use_container_width=True,
            hide_index=True,
            column_config={
                'Player': st.column_config.TextColumn(width='large'),
            }
        ))

        st.markdown("---")
        st.markdown("🏅 **Key:** Pts = Points | W = Wins | D = Draws | L = Losses | Goals = Goals scored | R = Rounds")
    else:
        st.info("No data yet. The standings will appear after the first scored round.")

#
# MAIN APP
#

def main():
    st.set_page_config(
        page_title="Football Fantasy - UK Edition",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS
    st.markdown("""
    <style>
        .stApp { background: #0a0a1a; }
        .stApp h1, .stApp h2, .stApp h3 { color: #FFD700 !important; }
        .stApp h4, .stApp h5, .stApp h6, .stApp p { color: #FFD700 !important; }
        .stTextInput label, .stPassword label { color: #FFD700 !important; font-weight: bold; }
        .stTextInput input, .stPassword input {
            background-color: #1a1a2e;
            color: #ffffff;
            border: 1px solid #FFD700;
        }
        .stForm [data-testid="stForm"] { background: transparent; }
        .stMarkdown p, .stMarkdown li, .stMarkdown span:not(.emoji) { color: #e0c040 !important; }
        div[data-testid="stExpander"] { background: #1a1a2e; border: 1px solid #333; }
        .stButton button { border-radius: 8px; }
        .stButton button[kind="primary"] { background: #FFD700; color: #000; font-weight: bold; }
        .st-emotion-cache-1v7f65g .st-emotion-cache-1wmy9hl { background: #1a1a2e; }
        .stSelectbox label, .stMultiSelect label { color: #ddd !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { border-radius: 6px 6px 0 0; }
        section[data-testid="stSidebar"] .stMarkdown p { color: #FFD700 !important; }
        .stMetric label { color: #FFD700 !important; }
        .stAlert { background-color: #1a1a2e; border: 1px solid #FFD700; }
    </style>
    """, unsafe_allow_html=True)

    # Init DB
    init_database()

    # Sidebar
    with st.sidebar:
        st.markdown("### 🏆 Football Fantasy")
        st.markdown("UK Edition — Premier League, EFL & SPFL")

        if 'player' in st.session_state:
            player = st.session_state['player']
            st.markdown(f"👤 **{player['name']}**")

            menu = ["📊 Dashboard", "🏆 Standings"]
            if player['is_admin']:
                menu.append("🔧 Admin")

            choice = st.radio("", menu, label_visibility="collapsed")

            if st.button("🚪 Sign Out", use_container_width=True):
                del st.session_state['player']
                st.rerun()
        else:
            choice = "login"

        current = get_current_round()
        if current:
            st.markdown(f"📅 Round: **{current}**")
        standings = get_standings()
        if standings:
            st.markdown(f"👥 Players: **{len(standings)}**")

    # Render page
    if 'player' not in st.session_state:
        login_screen()
    else:
        player = st.session_state['player']
        if choice == "📊 Dashboard":
            player_dashboard(player)
        elif choice == "🏆 Standings":
            leaderboard_screen()
        elif choice == "🔧 Admin":
            admin_panel()

if __name__ == "__main__":
    main()
