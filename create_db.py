import sqlite3

def create_db():
    conn = sqlite3.connect('tournaments.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS tournaments')
    c.execute('''CREATE TABLE tournaments
                 (id INTEGER PRIMARY KEY, 
                  name TEXT, 
                  created_date TEXT,
                  players TEXT, 
                  num_rounds INTEGER, 
                  current_round INTEGER DEFAULT 1,
                  matches TEXT, 
                  standings TEXT, 
                  byes TEXT, 
                  pairing_method TEXT)''')
    conn.commit()
    conn.close()
    print("Database 'tournaments.db' created successfully.")

if __name__ == "__main__":
    create_db()