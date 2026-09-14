from datetime import datetime
from decimal import Decimal

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Registered customer who can book movie tickets."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    bookings = db.relationship("Booking", back_populates="user", lazy=True)

    auth_type = "user"

    def get_id(self):
        return f"user:{self.id}"

    @property
    def is_active(self):
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Admin(UserMixin, db.Model):
    """Administrator account for managing movies, theaters, shows, and users."""

    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    auth_type = "admin"

    def get_id(self):
        return f"admin:{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Movie(db.Model):
    """Movie metadata fetched from TMDb or entered by an admin."""

    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True)
    imdb_id = db.Column(db.String(30), unique=True)
    title = db.Column(db.String(180), nullable=False, index=True)
    genre = db.Column(db.String(160), nullable=False)
    release_year = db.Column(db.String(10), nullable=False)
    language = db.Column(db.String(80), default="English")
    duration = db.Column(db.String(40), default="120 min")
    rating = db.Column(db.Float, default=0.0)
    plot = db.Column(db.Text, nullable=False)
    poster_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    shows = db.relationship(
        "Show",
        back_populates="movie",
        cascade="all, delete-orphan"
    )

    def to_card(self):
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "release_year": self.release_year,
            "rating": self.rating,
            "poster_url": self.poster_url,
        }


class Theater(db.Model):
    """Physical cinema location with a simple fixed seat layout."""

    __tablename__ = "theaters"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(160),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    address = db.Column(
        db.String(255),
        nullable=False
    )

    rows_data = db.Column(
        db.String(100),
        default="A,B,C,D,E,F,G,H",
        nullable=False
    )

    seats_per_row = db.Column(
        db.Integer,
        default=10,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    shows = db.relationship(
        "Show",
        back_populates="theater",
        cascade="all, delete-orphan"
    )

    @property
    def seat_rows(self):
        return [
            row.strip()
            for row in self.rows_data.split(",")
            if row.strip()
        ]

    @property
    def total_seats(self):
        return len(self.seat_rows) * self.seats_per_row


class Show(db.Model):
    """A scheduled movie screening in a theater."""

    __tablename__ = "shows"

    __table_args__ = (
        db.UniqueConstraint(
            "movie_id",
            "theater_id",
            "show_date",
            "show_time",
            name="uq_show_movie_theater_time",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )

    theater_id = db.Column(
        db.Integer,
        db.ForeignKey("theaters.id", ondelete="CASCADE"),
        nullable=False
    )

    show_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    show_time = db.Column(
        db.Time,
        nullable=False
    )

    price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("180.00")
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Scheduled"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    movie = db.relationship("Movie", back_populates="shows")
    theater = db.relationship("Theater", back_populates="shows")

    bookings = db.relationship(
        "Booking",
        back_populates="show",
        cascade="all, delete-orphan"
    )

    seats = db.relationship(
        "BookingSeat",
        back_populates="show",
        cascade="all, delete-orphan"
    )

    @property
    def available_seat_count(self):
        booked = BookingSeat.query.filter_by(show_id=self.id).count()
        return max(self.theater.total_seats - booked, 0)


class Booking(db.Model):
    """Customer booking header. Individual seats live in BookingSeat."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    booking_code = db.Column(
        db.String(30),
        nullable=False,
        unique=True,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    show_id = db.Column(
        db.Integer,
        db.ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=False
    )

    seat_count = db.Column(
        db.Integer,
        nullable=False
    )

    total_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Confirmed"
    )

    booked_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = db.relationship("User", back_populates="bookings")
    show = db.relationship("Show", back_populates="bookings")

    seats = db.relationship(
        "BookingSeat",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    @property
    def seat_numbers(self):
        return [seat.seat_number for seat in self.seats]

    @property
    def seat_label(self):
        return ", ".join(self.seat_numbers)


class BookingSeat(db.Model):
    """One reserved seat. The unique constraint blocks double booking."""

    __tablename__ = "booking_seats"

    __table_args__ = (
        db.UniqueConstraint(
            "show_id",
            "seat_number",
            name="uq_show_seat"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    show_id = db.Column(
        db.Integer,
        db.ForeignKey("shows.id", ondelete="CASCADE"),
        nullable=False
    )

    seat_number = db.Column(
        db.String(10),
        nullable=False
    )

    price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    booking = db.relationship(
        "Booking",
        back_populates="seats"
    )

    show = db.relationship(
        "Show",
        back_populates="seats"
    )