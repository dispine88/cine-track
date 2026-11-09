from database.db import get_session, init_db, Title, Genre, Review

def seed_data():
    init_db()
    with get_session() as session:
        if session.query(Title).first():
            print("Database already seeded.")
            return

        sci_fi = Genre(name="Sci-Fi")
        drama = Genre(name="Drama")
        action = Genre(name="Action")
        crime = Genre(name="Crime")
        session.add_all([sci_fi, drama, action, crime])
        session.commit()

        interstellar = Title(name="Interstellar", year=2014, type="movie", status="watched", genres=[sci_fi, drama])
        breaking_bad = Title(name="Breaking Bad", year=2008, type="series", status="watched", genres=[crime, drama])
        john_wick = Title(name="John Wick", year=2014, type="movie", status="want", genres=[action])
        
        session.add_all([interstellar, breaking_bad, john_wick])
        session.commit()
        print("Database successfully seeded.")

if __name__ == "__main__":
    seed_data()