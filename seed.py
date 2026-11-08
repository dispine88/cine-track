from db import Genre, Review, Title, get_session, init_db


def seed_data():
    init_db()

    with get_session() as session:
        if session.query(Title).first():
            print("База уже заполнена! Пропускаем.")
            return

        print("Заполняем базу тестовыми данными...")

        sci_fi = Genre(name="Фантастика")
        drama = Genre(name="Драма")
        action = Genre(name="Экшен")
        crime = Genre(name="Криминал")

        session.add_all([sci_fi, drama, action, crime])
        session.commit()

        interstellar = Title(
            name="Интерстеллар",
            year=2014,
            type="movie",
            status="watched",
            genres=[sci_fi, drama],
        )
        breaking_bad = Title(
            name="Во все тяжкие",
            year=2008,
            type="series",
            status="watched",
            genres=[crime, drama],
        )
        john_wick = Title(
            name="Джон Уик", year=2014, type="movie", status="want", genres=[action]
        )

        session.add_all([interstellar, breaking_bad, john_wick])
        session.commit()

        rev1 = Review(
            title_id=interstellar.id, rating=10, text="Плакал над роботом. Нолан гений."
        )
        rev2 = Review(
            title_id=breaking_bad.id, rating=9, text="Хайзенберг творит историю."
        )

        session.add_all([rev1, rev2])
        session.commit()

        print("База успешно заполнена!")


if __name__ == "__main__":
    seed_data()
