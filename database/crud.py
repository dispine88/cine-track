from database.db import get_session, Title

def get_all_titles():
    with get_session() as session:
        return session.query(Title).order_by(Title.name).all()

def get_title(title_id):
    with get_session() as session:
        return session.get(Title, title_id)

def add_title(name, type="manual", status="want", file_path=None):
    with get_session() as session:
        existing = session.query(Title).filter_by(file_path=file_path).first()
        if existing and file_path:
            return False
        new_title = Title(name=name, type=type, status=status, file_path=file_path)
        session.add(new_title)
        session.commit()
        return True

def delete_title(title_id):
    with get_session() as session:
        title = session.get(Title, title_id)
        if title:
            session.delete(title)
            session.commit()
            return True
        return False

def update_title_info(title_id, year=None, poster_url=None):
    with get_session() as session:
        title = session.get(Title, title_id)
        if title:
            if year is not None:
                title.year = year
            if poster_url is not None:
                title.poster_url = poster_url
            session.commit()
            return True
        return False