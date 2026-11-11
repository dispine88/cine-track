from database.db import get_connection, init_db

def seed_data():
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM titles")
        if cursor.fetchone()[0] > 0:
            print("Database already seeded.")
            return

        cursor.execute("INSERT INTO titles (name, year, type, status) VALUES (?, ?, ?, ?)", ("Interstellar", 2014, "movie", "watched"))
        cursor.execute("INSERT INTO titles (name, year, type, status) VALUES (?, ?, ?, ?)", ("Breaking Bad", 2008, "series", "watched"))
        cursor.execute("INSERT INTO titles (name, year, type, status) VALUES (?, ?, ?, ?)", ("John Wick", 2014, "movie", "want"))
        
        conn.commit()
        print("Database successfully seeded.")

if __name__ == "__main__":
    seed_data()