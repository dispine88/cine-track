from sqlalchemy import create_engine, ForeignKey, String, Integer, Text, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

engine = create_engine("sqlite:///cinetrack.db", echo=False)

class Base(DeclarativeBase):
    pass

title_genres = Table(
    "title_genres",
    Base.metadata,
    Column("title_id", ForeignKey("titles.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)

class Title(Base):
    __tablename__ = "titles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="want")
    file_path: Mapped[str] = mapped_column(String(500), nullable=True) 
    poster_url: Mapped[str] = mapped_column(String(500), nullable=True)
    
    genres: Mapped[list["Genre"]] = relationship(secondary=title_genres, back_populates="titles")
    reviews: Mapped[list["Review"]] = relationship(back_populates="title", cascade="all, delete-orphan")

class Genre(Base):
    __tablename__ = "genres"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    
    titles: Mapped[list["Title"]] = relationship(secondary=title_genres, back_populates="genres")

class Review(Base):
    __tablename__ = "reviews"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id"))
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    
    title: Mapped["Title"] = relationship(back_populates="reviews")

def init_db():
    Base.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)
