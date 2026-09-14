# 🎬 Online Movie Ticket Booking System

A complete **Flask + MySQL** movie ticket booking web application with customer authentication, admin management, API-backed movie search, seat selection and booking history.

---

## ✨ Features

* 🎨 Responsive dark UI built with Bootstrap, custom CSS and JavaScript
* 🎥 Movie cards, search, genre filters, details pages and poster-first layout
* 🔐 Customer signup/login with hashed passwords and Flask-Login sessions
* 👨‍💼 Admin login with movie, theater, show, booking and user management
* 🗄️ MySQL schema with primary keys, foreign keys and unique seat locking
* 💺 Seat picker that prevents double booking through a database constraint
* ⚡ Flash messages, validation, loading animation and mobile-friendly pages
* 🌐 TMDB integration through environment variables

---

## ⚙️ Backend

The Flask app uses:

* 🚀 `app.py` – Application Factory
* 🔗 `routes.py` – Application Routes
* 🗃️ `models.py` – Database Models
* 🔧 `config.py` – Environment Configuration

SQLAlchemy is used with a MySQL connection string, keeping database access parameterized and protected against SQL injection attacks.

---

## 🎨 Frontend

Frontend resources are organized as:

* 📄 Templates → `templates/`
* 🎨 CSS → `static/css/style.css`
* ⚡ JavaScript → `static/js/`

The UI uses Bootstrap 5 along with custom styling for:

* 🎬 Movie Cards
* ✨ Hover Effects
* 📊 Dashboards
* 💺 Interactive Seat Map

---

## 🗄️ Database

SQL files are located inside `database/`:

* 📜 `schema.sql` – Creates the MySQL database and tables
* 📥 `dummy_data.sql` – Inserts demo users, movies, theaters, shows, and bookings

### Main Tables

* 👤 `users`
* 👨‍💼 `admins`
* 🎬 `movies`
* 🏢 `theaters`
* 🎟️ `shows`
* 📑 `bookings`
* 💺 `booking_seats`

### Seat Protection

`booking_seats` includes a unique constraint on:

```text
(show_id, seat_number)
```

✅ Ensures the same seat cannot be booked twice for the same show.

---

## 🔑 Authentication

* 🔒 Passwords are hashed using Werkzeug
* 🍪 Flask-Login manages user sessions
* 👥 Separate decorators protect customer and admin routes

This prevents a logged-in admin from accidentally booking tickets as a customer.

### Demo Accounts

#### 👤 Customer

Email: `user@moviebook.local`

Password: `User@123`

#### 👨‍💼 Admin

Email: `admin@moviebook.local`

Password: `Admin@123`

---

## 🎟️ Booking System

Customers can:

1. 🎬 Choose a movie
2. 🕒 Select a show
3. 💺 Pick available seats
4. ✅ Confirm booking

The backend validates:

* ✔️ Seat existence
* ✔️ Seat quantity
* ✔️ Seat availability
* ✔️ Duplicate selections

before creating the booking.

---

## 🚀 Setup

### 1️⃣ Create and Activate Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Create MySQL Database

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/dummy_data.sql
```

### 4️⃣ Configure Environment Variables

```bash
copy .env.example .env
```

Update `DATABASE_URL` in `.env` with your MySQL username and password.

### 5️⃣ Run the Application

```bash
flask --app app.py run --debug
```

🌍 Open:

```text
http://127.0.0.1:5000
```

---

## 🌱 Alternative Demo Seeding

You can also create tables and insert demo records directly through Flask:

```bash
flask --app app.py init-db
flask --app app.py seed-demo
```

---

## 🎥 TMDB API Integration

The application works with local demo data by default.

To fetch movie data dynamically, including movie information, search results and posters, add your TMDB API key inside `.env`:

```bash
TMDB_API_KEY=your_tmdb_key
```

---

## 📂 Project Structure

```text
.
├── 📄 app.py
├── ⚙️ config.py
├── 🗃️ models.py
├── 🔗 routes.py
├── 📋 requirements.txt
├── 📖 README.md
├── 📁 database/
│   ├── 📜 schema.sql
│   └── 📥 dummy_data.sql
├── 📁 static/
│   ├── 📁 css/
│   │   └── 🎨 style.css
│   ├── 📁 js/
│   │   ├── ⚡ main.js
│   │   └── ⚡ booking.js
│   └── 📁 images/
└── 📁 templates/
    ├── 📄 base.html
    ├── 🏠 index.html
    ├── 🔑 login.html
    ├── 📝 signup.html
    ├── 🎬 movie_details.html
    ├── 💺 booking.html
    ├── ✅ confirmation.html
    ├── 📊 dashboard.html
    └── 📁 admin/
```

---

## 🛠️ Tech Stack

* 🐍 Python
* 🌶️ Flask
* 🗄️ MySQL
* 🔗 SQLAlchemy
* 🎨 Bootstrap 5
* ⚡ JavaScript
* 🔐 Flask-Login
* 🌐 TMDB API

---

## 👨‍💻 Role & Contributions

**Team Leader & Full-Stack Developer**

* Led the project team throughout the development lifecycle.
* Designed and developed the complete Flask + MySQL application architecture.
* Implemented customer authentication, admin dashboard, movie management and booking workflows.
* Designed the database schema, relationships and seat-booking system.
* Developed responsive frontend interfaces using Bootstrap, CSS and JavaScript.
* Integrated API-based movie search and handled backend business logic.
* Performed testing, debugging and deployment setup.

---

## 🌟 Support

⭐ If you found this project useful, consider giving it a star.

🔗 GitHub Profile: https://github.com/shanusingh-ai
