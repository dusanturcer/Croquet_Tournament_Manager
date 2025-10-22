import sqlite3

# Create a new database with the correct schema
def create_db():
    conn = sqlite3.connect('tournaments.db')
    c = conn.cursor()
    # Drop any existing table to start fresh
    c.execute('DROP TABLE IF EXISTS tournaments')
    # Create table with all required columns
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
    print("Database 'tournaments.db' created successfully with the correct schema.")

if __name__ == "__main__":
    create_db()