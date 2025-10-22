import streamlit as st
import pandas as pd
import sqlite3
import itertools
import random
from openpyxl.styles import Alignment
from openpyxl import load_workbook
from datetime import datetime

# Database setup
def init_db():
    try:
        conn = sqlite3.connect('tournaments.db')
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS tournaments')
        c.execute('''CREATE TABLE tournaments
                     (id INTEGER PRIMARY KEY, name TEXT, created_date TEXT,
                      players TEXT, num_rounds INTEGER, current_round INTEGER DEFAULT 1,
                      matches TEXT, standings TEXT, byes TEXT, pairing_method TEXT)''')
        conn.commit()
        conn.close()
        st.success("Database initialized successfully.")
    except sqlite3.OperationalError as e:
        st.error(f"Database initialization failed: {e}")
        st.stop()

def get_conn():
    return sqlite3.connect('tournaments.db')

# Helper functions
def sort_key(p):
    return (-p['score'], -p['net_hoops'], -p['hoops_scored'])

def generate_pairings(entities, pairing_method="Swiss", modifying=True):
    if pairing_method == "Swiss":
        entity_list = sorted(entities, key=sort_key)
    else:  # Random
        entity_list = entities.copy()
        random.shuffle(entity_list)

    n = len(entity_list)
    best_pairings = []
    best_byes = []
    has_repeat = False
    min_repeats = float('inf')

    if n % 2 == 0:
        players_indices = list(range(n))
        possible_pairings = list(itertools.combinations(players_indices, 2))
        pairing_combinations = []
        for comb in itertools.combinations(possible_pairings, n // 2):
            players_covered = set()
            valid = True
            for p1, p2 in comb:
                if p1 in players_covered or p2 in players_covered:
                    valid = False
                    break
                players_covered.add(p1)
                players_covered.add(p2)
            if valid and len(players_covered) == n:
                pairing_combinations.append(comb)
    else:
        pairing_combinations = []
        for bye_idx in range(n):
            players_indices = [i for i in range(n) if i != bye_idx]
            possible_pairings = list(itertools.combinations(players_indices, 2))
            for comb in itertools.combinations(possible_pairings, (n - 1) // 2):
                players_covered = set()
                valid = True
                for p1, p2 in comb:
                    if p1 in players_covered or p2 in players_covered:
                        valid = False
                        break
                    players_covered.add(p1)
                    players_covered.add(p2)
                if valid and len(players_covered) == n - 1:
                    pairing_combinations.append((comb, bye_idx))

    if not pairing_combinations:
        return [], [], False

    if pairing_method == "Random":
        random.shuffle(pairing_combinations)

    for comb in pairing_combinations:
        if n % 2 == 0:
            pairs = [(entity_list[p1]['name'], entity_list[p2]['name']) for p1, p2 in comb]
            bye = []
        else:
            pairs = [(entity_list[p1]['name'], entity_list[p2]['name']) for p1, p2 in comb[0]]
            bye = [entity_list[comb[1]]['name']]
        
        repeats = 0
        for p1, p2 in pairs:
            pl1 = next(p for p in entity_list if p['name'] == p1)
            if p2 in pl1['opponents']:
                repeats += 1
        if repeats < min_repeats:
            min_repeats = repeats
            best_pairings = pairs
            best_byes = bye
            has_repeat = repeats > 0
        if repeats == 0:
            break

    if modifying and best_pairings:
        for p1, p2 in best_pairings:
            pl1 = next(p for p in entity_list if p['name'] == p1)
            pl2 = next(p for p in entity_list if p['name'] == p2)
            pl1['opponents'].add(p2)
            pl2['opponents'].add(p1)

    return best_pairings, best_byes, has_repeat

def update_player_stats(pl, s_scored, s_conceded, is_win):
    pl['games_played'] += 1
    if is_win:
        pl['wins'] += 1
        pl['score'] += 1.0
    else:
        pl['losses'] += 1
    pl['hoops_scored'] += s_scored
    pl['hoops_conceded'] = s_conceded
    pl['net_hoops'] = pl['hoops_scored'] - pl['hoops_conceded']

def reset_player_stats(players):
    for p in players:
        p['score'] = 0.0
        p['games_played'] = 0
        p['wins'] = 0
        p['losses'] = 0
        p['hoops_scored'] = 0
        p['hoops_conceded'] = 0
        p['net_hoops'] = 0

# Initialize DB
init_db()

# Streamlit App
st.markdown("<br>", unsafe_allow_html=True)
st.title("Croquet Tournament Manager")

# Sidebar
st.sidebar.title("Tournaments")

conn_temp = get_conn()
tournament_list = pd.read_sql("SELECT id, name, created_date FROM tournaments", conn_temp)
conn_temp.close()

if 'selected_id' not in st.session_state:
    st.session_state.selected_id = 0

if not tournament_list.empty:
    options = [0] + list(tournament_list['id'])
    select_index = options.index(st.session_state.selected_id) if st.session_state.selected_id in options else 0
    selected_id = st.sidebar.selectbox(
        "Select Tournament:",
        options=options,
        format_func=lambda x: "New Tournament" if x == 0 else tournament_list[tournament_list['id'] == x]['name'].iloc[0],
        index=select_index,
        key="selectbox_tournament"
    )
    st.session_state.selected_id = selected_id
else:
    selected_id = 0
    st.session_state.selected_id = 0

if selected_id == 0:
    # Single form for tournament creation
    with st.form("create_tournament_form"):
        st.subheader("Create New Tournament")
        col1, col2 = st.columns(2)
        with col1:
            tourney_name = st.text_input("Tournament Name:")
        with col2:
            pairing_method = st.selectbox("Pairing Method:", ["Swiss", "Random"])
        
        col3, col4 = st.columns(2)
        with col3:
            num_players = st.number_input("Number of players:", min_value=2, value=4)
        with col4:
            num_rounds = st.number_input("Number of Rounds:", min_value=1, value=5)
        
        st.subheader("Enter Player Names")
        player_names = []
        for i in range(int(num_players)):
            player_name = st.text_input(f"Player {i+1} name:", key=f"player_{i}")
            player_names.append(player_name)
        
        create_btn = st.form_submit_button("Create Tournament")
        
        if create_btn:
            if not tourney_name:
                st.error("Please enter a tournament name.")
            elif any(not name for name in player_names):
                st.error("Please fill all player names.")
            else:
                # Create players list
                players = []
                for name in player_names:
                    players.append({
                        'name': name, 'score': 0.0, 'games_played': 0, 'wins': 0, 'losses': 0,
                        'hoops_scored': 0, 'hoops_conceded': 0, 'net_hoops': 0, 'opponents': set()
                    })
                
                # Generate initial pairings
                pairings, byes, has_repeat = generate_pairings(players, pairing_method)
                
                # Save to database
                try:
                    conn_temp = get_conn()
                    cur = conn_temp.cursor()
                    cur.execute(
                        "INSERT INTO tournaments (name, created_date, players, num_rounds, current_round, matches, standings, byes, pairing_method) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)",
                        (tourney_name, datetime.now().isoformat(), str(players), num_rounds, str([]), str([]), str([byes]), pairing_method)
                    )
                    new_id = cur.lastrowid
                    conn_temp.commit()
                    conn_temp.close()
                    
                    st.session_state.selected_id = new_id
                    st.session_state.current_pairings = pairings
                    st.session_state.current_byes = byes
                    st.session_state.has_repeat = has_repeat
                    st.session_state.current_round = 1
                    
                    st.success(f"Tournament '{tourney_name}' created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create tournament: {str(e)}")
                    st.stop()
else:
    # Tournament selected - existing code for displaying tournament
    conn_temp = get_conn()
    tourney_data = pd.read_sql("SELECT * FROM tournaments WHERE id=?", conn_temp, params=(selected_id,))
    conn_temp.close()
    
    if not tourney_data.empty:
        tourney = tourney_data.iloc[0].to_dict()
    else:
        st.error("Tournament not found!")
        st.session_state.selected_id = 0
        st.rerun()
        st.stop()
    
    players = eval(tourney['players'])
    num_rounds = tourney['num_rounds']
    current_round = tourney['current_round']
    matches = eval(tourney['matches']) if tourney['matches'] else []
    standings_history = eval(tourney['standings']) if tourney['standings'] else []
    byes_history = eval(tourney['byes']) if tourney['byes'] else []
    pairing_method = tourney.get('pairing_method', 'Swiss')

    if current_round > num_rounds:
        st.header(f"Tournament: {tourney['name']} - Final Standings")
    else:
        st.header(f"Tournament: {tourney['name']} - Round {current_round} of {num_rounds}")

    # Current Standings
    st.subheader("Current Standings")
    if not standings_history:
        sorted_players = sorted(players, key=sort_key)
        current_standings = [
            {
                'rank': i + 1,
                'name': p['name'],
                'games_played': p['games_played'],
                'wins': p['wins'],
                'losses': p['losses'],
                'hoops_scored': p['hoops_scored'],
                'hoops_conceded': p['hoops_conceded'],
                'net_hoops': p['net_hoops'],
                'points': p['score'],
                'win_percentage': 0.00
            } for i, p in enumerate(sorted_players)
        ]
        df_stand = pd.DataFrame(current_standings)
    else:
        df_stand = pd.DataFrame(standings_history[-1])
        df_stand['win_percentage'] = (df_stand['wins'] / df_stand['games_played'] * 100).round(2).fillna(0.00)
    
    st.dataframe(df_stand, use_container_width=True, hide_index=True)

    # Rest of the tournament display code remains the same...
    # (standings, pairings, results form, exports, etc.)

    if current_round <= num_rounds:
        if 'current_pairings' not in st.session_state or current_round != st.session_state.get('current_round', 0):
            pairings, byes, has_repeat = generate_pairings(players, pairing_method)
            st.session_state.current_pairings = pairings
            st.session_state.current_byes = byes
            st.session_state.has_repeat = has_repeat
            st.session_state.current_round = current_round
        else:
            pairings = st.session_state.current_pairings
            byes = st.session_state.current_byes
            has_repeat = st.session_state.has_repeat

        st.subheader(f"Round {current_round} Pairings")
        if has_repeat:
            st.warning("Some repeating pairings this round (unavoidable due to player count).")
        for i, (p1, p2) in enumerate(pairings, 1):
            st.write(f"{i}. {p1} vs {p2}")
        if byes:
            for b in byes:
                st.write(f"{b} gets a bye.")

        with st.form(f"results_round_{current_round}"):
            result_data = {}
            for p1, p2 in pairings:
                col1, col2 = st.columns(2)
                with col1:
                    s1 = st.number_input(f"{p1} hoops:", min_value=0, key=f"s1_{p1}_{p2}_{current_round}")
                with col2:
                    s2 = st.number_input(f"{p2} hoops:", min_value=0, key=f"s2_{p1}_{p2}_{current_round}")
                result_data[(p1, p2)] = (s1, s2)
            submit_results = st.form_submit_button("Submit Results")

            if submit_results:
                # [Rest of results submission logic remains the same]
                pass

    # [Rest of the code for exports, games played, delete tournament remains the same]
    # ... (include all the existing export and games played logic from your original code)

if selected_id != 0:
    if st.sidebar.button("Delete Tournament"):
        conn_temp = get_conn()
        conn_temp.execute("DELETE FROM tournaments WHERE id=?", (selected_id,))
        conn_temp.commit()
        conn_temp.close()
        st.session_state.selected_id = 0
        st.sidebar.success("Tournament deleted!")
        st.rerun()