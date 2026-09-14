from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from uuid import uuid4

import requests
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import Admin, Booking, BookingSeat, Movie, Show, Theater, User, db


TMDB_GENRES = {
    12: "Adventure",
    14: "Fantasy",
    16: "Animation",
    18: "Drama",
    27: "Horror",
    28: "Action",
    35: "Comedy",
    36: "History",
    37: "Western",
    53: "Thriller",
    80: "Crime",
    99: "Documentary",
    878: "Sci-Fi",
    9648: "Mystery",
    10402: "Music",
    10749: "Romance",
    10751: "Family",
    10752: "War",
    10770: "TV Movie",
}


def register_routes(app):
    """Register all customer, admin, API, and error routes."""

    @app.route("/")
    def index():
        query_text = request.args.get("q", "").strip()
        genre = request.args.get("genre", "").strip()

        movies_query = Movie.query
        if query_text:
            movies_query = movies_query.filter(
                or_(Movie.title.ilike(f"%{query_text}%"), Movie.genre.ilike(f"%{query_text}%"))
            )
        if genre:
            movies_query = movies_query.filter(Movie.genre.ilike(f"%{genre}%"))

        movies = movies_query.order_by(Movie.rating.desc(), Movie.created_at.desc()).limit(18).all()

        # If no local result exists and an API key is configured, pull movies and cache them.
        if query_text and not movies:
            fetched_movies = fetch_movies_from_api(query_text)
            cache_movies(fetched_movies)
            movies = movies_query.order_by(Movie.rating.desc(), Movie.created_at.desc()).limit(18).all()

        genres = get_genres()
        featured = Movie.query.order_by(Movie.rating.desc()).limit(5).all()
        return render_template(
            "index.html",
            movies=movies,
            featured=featured,
            genres=genres,
            query_text=query_text,
            selected_genre=genre,
        )

    @app.route("/movies/<int:movie_id>")
    def movie_details(movie_id):
        movie = Movie.query.get_or_404(movie_id)
        today = date.today()
        shows = (
            Show.query.filter(Show.movie_id == movie.id, Show.show_date >= today, Show.status == "Scheduled")
            .join(Theater)
            .order_by(Show.show_date.asc(), Theater.city.asc(), Show.show_time.asc())
            .all()
        )
        cities = sorted({show.theater.city for show in shows})
        return render_template("movie_details.html", movie=movie, shows=shows, cities=cities)

    @app.route("/api/movies/search")
    def api_movie_search():
        query_text = request.args.get("q", "").strip()
        if len(query_text) < 2:
            return jsonify({"movies": []})

        local_movies = (
            Movie.query.filter(or_(Movie.title.ilike(f"%{query_text}%"), Movie.genre.ilike(f"%{query_text}%")))
            .order_by(Movie.rating.desc())
            .limit(10)
            .all()
        )
        movies = [movie.to_card() for movie in local_movies]
        if not movies:
            movies = fetch_movies_from_api(query_text)
        return jsonify({"movies": movies})

    @app.route("/api/shows/<int:show_id>/booked-seats")
    def api_booked_seats(show_id):
        Show.query.get_or_404(show_id)
        seats = [
            seat.seat_number
            for seat in BookingSeat.query.filter_by(show_id=show_id).order_by(BookingSeat.seat_number.asc()).all()
        ]
        return jsonify({"bookedSeats": seats})

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard" if current_user.auth_type == "user" else "admin_dashboard"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            errors = validate_signup(name, email, password, confirm_password)
            if User.query.filter_by(email=email).first():
                errors.append("An account with this email already exists.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("signup.html", form=request.form)

            user = User(name=name, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Your account is ready. Please log in.", "success")
            return redirect(url_for("login"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard" if current_user.auth_type == "user" else "admin_dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            remember = request.form.get("remember") == "on"
            user = User.query.filter_by(email=email).first()

            if not user or not user.check_password(password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html", form=request.form)
            if not user.active:
                flash("This account is inactive. Please contact support.", "warning")
                return render_template("login.html", form=request.form)

            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))

        return render_template("login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if current_user.is_authenticated and current_user.auth_type == "admin":
            return redirect(url_for("admin_dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            admin = Admin.query.filter_by(email=email).first()

            if not admin or not admin.check_password(password):
                flash("Invalid admin credentials.", "danger")
                return render_template("admin/login.html", form=request.form)

            login_user(admin)
            flash(f"Admin session started for {admin.name}.", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("admin/login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @user_required
    def dashboard():
        bookings = (
            Booking.query.filter_by(user_id=current_user.id)
            .join(Show)
            .order_by(Booking.booked_at.desc())
            .all()
        )
        upcoming_count = sum(1 for booking in bookings if booking.show.show_date >= date.today())
        return render_template("dashboard.html", bookings=bookings, upcoming_count=upcoming_count)

    @app.route("/booking/<int:show_id>", methods=["GET", "POST"])
    @user_required
    def booking(show_id):
        show = Show.query.get_or_404(show_id)
        if show.show_date < date.today() or show.status != "Scheduled":
            flash("This show is no longer available for booking.", "warning")
            return redirect(url_for("movie_details", movie_id=show.movie_id))

        booked_seats = get_booked_seats(show.id)
        seat_matrix = build_seat_matrix(show.theater, booked_seats)

        if request.method == "POST":
            selected_seats = parse_selected_seats(request.form.get("selected_seats", ""))
            all_seats = {seat["number"] for row in seat_matrix for seat in row}
            errors = validate_booking(selected_seats, all_seats, booked_seats)

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "booking.html",
                    show=show,
                    seat_matrix=seat_matrix,
                    booked_seats=booked_seats,
                    selected_seats=selected_seats,
                )

            booking_code = f"MB{uuid4().hex[:10].upper()}"
            total_amount = Decimal(show.price) * len(selected_seats)
            booking_record = Booking(
                booking_code=booking_code,
                user_id=current_user.id,
                show_id=show.id,
                seat_count=len(selected_seats),
                total_amount=total_amount,
            )
            db.session.add(booking_record)
            db.session.flush()

            for seat_number in selected_seats:
                db.session.add(
                    BookingSeat(
                        booking_id=booking_record.id,
                        show_id=show.id,
                        seat_number=seat_number,
                        price=show.price,
                    )
                )

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("One or more selected seats were just booked. Please choose again.", "danger")
                return redirect(url_for("booking", show_id=show.id))

            flash("Booking confirmed.", "success")
            return redirect(url_for("booking_confirmation", booking_code=booking_code))

        return render_template(
            "booking.html",
            show=show,
            seat_matrix=seat_matrix,
            booked_seats=booked_seats,
            selected_seats=[],
        )

    @app.route("/booking/confirmation/<booking_code>")
    @login_required
    def booking_confirmation(booking_code):
        booking_record = Booking.query.filter_by(booking_code=booking_code).first_or_404()
        if current_user.auth_type == "user" and booking_record.user_id != current_user.id:
            abort(403)
        return render_template("confirmation.html", booking=booking_record)

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        stats = {
            "movies": Movie.query.count(),
            "theaters": Theater.query.count(),
            "shows": Show.query.count(),
            "bookings": Booking.query.count(),
            "users": User.query.count(),
        }
        recent_bookings = Booking.query.order_by(Booking.booked_at.desc()).limit(8).all()
        return render_template("admin/dashboard.html", stats=stats, recent_bookings=recent_bookings)

    @app.route("/admin/movies")
    @admin_required
    def admin_movies():
        movies = Movie.query.order_by(Movie.created_at.desc()).all()
        return render_template("admin/movies.html", movies=movies)

    @app.route("/admin/movies/add", methods=["GET", "POST"])
    @admin_required
    def admin_movie_add():
        if request.method == "POST":
            movie, errors = movie_from_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("admin/movie_form.html", movie=movie, mode="Add")

            db.session.add(movie)
            db.session.commit()
            flash("Movie added successfully.", "success")
            return redirect(url_for("admin_movies"))

        return render_template("admin/movie_form.html", movie=None, mode="Add")

    @app.route("/admin/movies/<int:movie_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_movie_edit(movie_id):
        movie = Movie.query.get_or_404(movie_id)
        if request.method == "POST":
            updated_movie, errors = movie_from_form(movie)
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("admin/movie_form.html", movie=updated_movie, mode="Edit")

            db.session.commit()
            flash("Movie updated successfully.", "success")
            return redirect(url_for("admin_movies"))

        return render_template("admin/movie_form.html", movie=movie, mode="Edit")

    @app.route("/admin/movies/<int:movie_id>/delete", methods=["POST"])
    @admin_required
    def admin_movie_delete(movie_id):
        movie = Movie.query.get_or_404(movie_id)
        db.session.delete(movie)
        db.session.commit()
        flash("Movie deleted.", "info")
        return redirect(url_for("admin_movies"))

    @app.route("/admin/theaters")
    @admin_required
    def admin_theaters():
        theaters = Theater.query.order_by(Theater.city.asc(), Theater.name.asc()).all()
        return render_template("admin/theaters.html", theaters=theaters)

    @app.route("/admin/theaters/add", methods=["GET", "POST"])
    @admin_required
    def admin_theater_add():
        if request.method == "POST":
            theater, errors = theater_from_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("admin/theater_form.html", theater=theater, mode="Add")
            db.session.add(theater)
            db.session.commit()
            flash("Theater added successfully.", "success")
            return redirect(url_for("admin_theaters"))

        return render_template("admin/theater_form.html", theater=None, mode="Add")

    @app.route("/admin/theaters/<int:theater_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_theater_edit(theater_id):
        theater = Theater.query.get_or_404(theater_id)
        if request.method == "POST":
            updated_theater, errors = theater_from_form(theater)
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("admin/theater_form.html", theater=updated_theater, mode="Edit")
            db.session.commit()
            flash("Theater updated successfully.", "success")
            return redirect(url_for("admin_theaters"))

        return render_template("admin/theater_form.html", theater=theater, mode="Edit")

    @app.route("/admin/theaters/<int:theater_id>/delete", methods=["POST"])
    @admin_required
    def admin_theater_delete(theater_id):
        theater = Theater.query.get_or_404(theater_id)
        db.session.delete(theater)
        db.session.commit()
        flash("Theater deleted.", "info")
        return redirect(url_for("admin_theaters"))

    @app.route("/admin/shows")
    @admin_required
    def admin_shows():
        shows = Show.query.join(Movie).join(Theater).order_by(Show.show_date.desc(), Show.show_time.desc()).all()
        return render_template("admin/shows.html", shows=shows)

    @app.route("/admin/shows/add", methods=["GET", "POST"])
    @admin_required
    def admin_show_add():
        movies = Movie.query.order_by(Movie.title.asc()).all()
        theaters = Theater.query.order_by(Theater.city.asc(), Theater.name.asc()).all()
        if request.method == "POST":
            show, errors = show_from_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "admin/show_form.html", show=show, movies=movies, theaters=theaters, mode="Add"
                )
            db.session.add(show)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("A show already exists for this movie, theater, date, and time.", "danger")
                return render_template(
                    "admin/show_form.html", show=show, movies=movies, theaters=theaters, mode="Add"
                )
            flash("Show timing added successfully.", "success")
            return redirect(url_for("admin_shows"))

        return render_template("admin/show_form.html", show=None, movies=movies, theaters=theaters, mode="Add")

    @app.route("/admin/shows/<int:show_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_show_edit(show_id):
        show = Show.query.get_or_404(show_id)
        movies = Movie.query.order_by(Movie.title.asc()).all()
        theaters = Theater.query.order_by(Theater.city.asc(), Theater.name.asc()).all()
        if request.method == "POST":
            updated_show, errors = show_from_form(show)
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "admin/show_form.html", show=updated_show, movies=movies, theaters=theaters, mode="Edit"
                )
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("A show already exists for this movie, theater, date, and time.", "danger")
                return render_template(
                    "admin/show_form.html", show=updated_show, movies=movies, theaters=theaters, mode="Edit"
                )
            flash("Show timing updated successfully.", "success")
            return redirect(url_for("admin_shows"))

        return render_template("admin/show_form.html", show=show, movies=movies, theaters=theaters, mode="Edit")

    @app.route("/admin/shows/<int:show_id>/delete", methods=["POST"])
    @admin_required
    def admin_show_delete(show_id):
        show = Show.query.get_or_404(show_id)
        db.session.delete(show)
        db.session.commit()
        flash("Show deleted.", "info")
        return redirect(url_for("admin_shows"))

    @app.route("/admin/bookings")
    @admin_required
    def admin_bookings():
        bookings = Booking.query.order_by(Booking.booked_at.desc()).all()
        return render_template("admin/bookings.html", bookings=bookings)

    @app.route("/admin/users")
    @admin_required
    def admin_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template("admin/users.html", users=users)

    @app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
    @admin_required
    def admin_user_toggle(user_id):
        user = User.query.get_or_404(user_id)
        user.active = not user.active
        db.session.commit()
        flash(f"{user.name}'s account is now {'active' if user.active else 'inactive'}.", "info")
        return redirect(url_for("admin_users"))

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors.html", code=404, title="Page not found"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors.html", code=403, title="Access denied"), 403

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors.html", code=500, title="Something went wrong"), 500


def user_required(view_func):
    """Allow only authenticated customer accounts."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login", next=request.url))
        if current_user.auth_type != "user":
            flash("Please use a customer account for bookings.", "warning")
            return redirect(url_for("admin_dashboard"))
        return view_func(*args, **kwargs)

    return wrapped_view


def admin_required(view_func):
    """Allow only authenticated admin accounts."""

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.auth_type != "admin":
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_login", next=request.url))
        return view_func(*args, **kwargs)

    return wrapped_view


def fetch_movies_from_api(query_text):
    """Fetch movies from TMDb API."""

    tmdb_key = current_app.config.get("TMDB_API_KEY")
    if tmdb_key:
        return fetch_movies_from_tmdb(query_text, tmdb_key)
    return []


def fetch_movies_from_tmdb(query_text, api_key):
    """Search TMDb and normalize results to the local Movie fields.

    Tries the official API first, then falls back to proxy mirrors
    when the ISP blocks api.themoviedb.org.
    """

    # URLs to try — official first, then community proxy mirrors
    base_urls = [
        current_app.config["TMDB_BASE_URL"],            # https://api.themoviedb.org/3
        "https://tmdb-proxy.cubari.moe/3",               # community mirror
        "https://api.tmdb.org/3",                         # alternate official domain
    ]

    params = {"api_key": api_key, "query": query_text, "include_adult": "false"}
    print(f"[TMDB] Searching for: '{query_text}'")

    response = None
    for base in base_urls:
        url = f"{base}/search/movie"
        print(f"[TMDB] Trying: {url}")
        try:
            response = requests.get(url, params=params, timeout=8)
            print(f"[TMDB] Status Code: {response.status_code}")
            response.raise_for_status()
            break  # success — stop trying other URLs
        except requests.RequestException as e:
            print(f"[TMDB] FAILED: {e}")
            response = None
            continue

    if response is None:
        print("[TMDB] All endpoints failed.")
        return []

    data = response.json()
    results = data.get("results", [])
    print(f"[TMDB] Results found: {len(results)}")

    movies = []
    for item in results[:8]:
        release_date = item.get("release_date") or ""
        genres = [TMDB_GENRES.get(genre_id) for genre_id in item.get("genre_ids", [])]
        poster_path = item.get("poster_path")
        movies.append(
            {
                "tmdb_id": item.get("id"),
                "title": item.get("title") or "Untitled",
                "genre": ", ".join(filter(None, genres)) or "Drama",
                "release_year": release_date[:4] or "N/A",
                "language": (item.get("original_language") or "en").upper(),
                "duration": "120 min",
                "rating": round(float(item.get("vote_average") or 0), 1),
                "plot": item.get("overview") or "Plot details are currently unavailable.",
                "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else placeholder_poster(),
            }
        )
    print(f"[TMDB] Movies processed: {len(movies)}")
    return movies




def cache_movies(movie_payloads):
    """Insert API movies that are not already stored locally."""

    created = False
    for payload in movie_payloads:
        existing = None
        if payload.get("tmdb_id"):
            existing = Movie.query.filter_by(tmdb_id=payload["tmdb_id"]).first()
        if not existing and payload.get("imdb_id"):
            existing = Movie.query.filter_by(imdb_id=payload["imdb_id"]).first()
        if not existing:
            db.session.add(Movie(**payload))
            created = True

    if created:
        db.session.commit()


def placeholder_poster():
    return "https://dummyimage.com/500x750/171717/f84464&text=Movie+Poster"


def get_genres():
    """Build a short genre list for filters from stored movies."""

    genres = set()
    for movie in Movie.query.with_entities(Movie.genre).all():
        for genre in movie.genre.split(","):
            clean = genre.strip()
            if clean:
                genres.add(clean)
    return sorted(genres)


def validate_signup(name, email, password, confirm_password):
    errors = []
    if len(name) < 2:
        errors.append("Please enter your full name.")
    if "@" not in email or "." not in email:
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if password != confirm_password:
        errors.append("Passwords do not match.")
    return errors


def parse_selected_seats(raw_value):
    return [seat.strip().upper() for seat in raw_value.split(",") if seat.strip()]


def validate_booking(selected_seats, all_seats, booked_seats):
    errors = []
    if not selected_seats:
        errors.append("Please select at least one seat.")
    if len(selected_seats) > 8:
        errors.append("You can book a maximum of 8 seats at once.")
    if len(set(selected_seats)) != len(selected_seats):
        errors.append("Duplicate seats were selected.")
    invalid = [seat for seat in selected_seats if seat not in all_seats]
    if invalid:
        errors.append("Invalid seat selection detected.")
    unavailable = [seat for seat in selected_seats if seat in booked_seats]
    if unavailable:
        errors.append(f"Seats already booked: {', '.join(unavailable)}.")
    return errors


def get_booked_seats(show_id):
    return {
        seat.seat_number
        for seat in BookingSeat.query.filter_by(show_id=show_id).with_entities(BookingSeat.seat_number).all()
    }


def build_seat_matrix(theater, booked_seats):
    seat_matrix = []
    for row in theater.seat_rows:
        row_seats = []
        for number in range(1, theater.seats_per_row + 1):
            seat_number = f"{row}{number}"
            row_seats.append({"number": seat_number, "booked": seat_number in booked_seats})
        seat_matrix.append(row_seats)
    return seat_matrix


def movie_from_form(movie=None):
    movie = movie or Movie()
    errors = []
    title = request.form.get("title", "").strip()
    genre = request.form.get("genre", "").strip()
    release_year = request.form.get("release_year", "").strip()
    language = request.form.get("language", "").strip() or "English"
    duration = request.form.get("duration", "").strip() or "120 min"
    plot = request.form.get("plot", "").strip()
    poster_url = request.form.get("poster_url", "").strip() or placeholder_poster()

    try:
        rating = float(request.form.get("rating", 0) or 0)
    except ValueError:
        rating = 0
        errors.append("Rating must be a number.")

    if not title:
        errors.append("Movie title is required.")
    if not genre:
        errors.append("Genre is required.")
    if not release_year:
        errors.append("Release year is required.")
    if not plot:
        errors.append("Plot is required.")

    movie.title = title
    movie.genre = genre
    movie.release_year = release_year
    movie.language = language
    movie.duration = duration
    movie.rating = rating
    movie.plot = plot
    movie.poster_url = poster_url
    return movie, errors


def theater_from_form(theater=None):
    theater = theater or Theater()
    errors = []
    name = request.form.get("name", "").strip()
    city = request.form.get("city", "").strip()
    address = request.form.get("address", "").strip()
    rows = request.form.get("rows", "").strip().upper() or "A,B,C,D,E,F,G,H"

    try:
        seats_per_row = int(request.form.get("seats_per_row", 10))
    except ValueError:
        seats_per_row = 10
        errors.append("Seats per row must be a number.")

    if not name:
        errors.append("Theater name is required.")
    if not city:
        errors.append("City is required.")
    if not address:
        errors.append("Address is required.")
    if seats_per_row < 1 or seats_per_row > 30:
        errors.append("Seats per row must be between 1 and 30.")

    theater.name = name
    theater.city = city
    theater.address = address
    theater.rows = rows
    theater.seats_per_row = seats_per_row
    return theater, errors


def show_from_form(show=None):
    show = show or Show()
    errors = []

    try:
        movie_id = int(request.form.get("movie_id", 0))
        theater_id = int(request.form.get("theater_id", 0))
    except ValueError:
        movie_id = 0
        theater_id = 0
        errors.append("Movie and theater are required.")

    try:
        show_date = datetime.strptime(request.form.get("show_date", ""), "%Y-%m-%d").date()
    except ValueError:
        show_date = None
        errors.append("Please enter a valid show date.")

    try:
        show_time = datetime.strptime(request.form.get("show_time", ""), "%H:%M").time()
    except ValueError:
        show_time = None
        errors.append("Please enter a valid show time.")

    try:
        price = Decimal(request.form.get("price", "0"))
    except (InvalidOperation, ValueError):
        price = Decimal("0.00")
        errors.append("Price must be a valid amount.")

    status = request.form.get("status", "Scheduled").strip() or "Scheduled"

    if not Movie.query.get(movie_id):
        errors.append("Selected movie does not exist.")
    if not Theater.query.get(theater_id):
        errors.append("Selected theater does not exist.")
    if price <= 0:
        errors.append("Price must be greater than zero.")

    show.movie_id = movie_id
    show.theater_id = theater_id
    show.show_date = show_date
    show.show_time = show_time
    show.price = price
    show.status = status
    return show, errors