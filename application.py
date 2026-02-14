import os
from flask import Flask, session, request, redirect, render_template
from flask_session import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Create users table if not exists
db.execute(text("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL
);
"""))
db.commit()

@app.route("/")
def index():

    # Require login
    if session.get("user_id") is None:
        return redirect("/login")

    return "Project 1: TODO"

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Missing username or password"

        hash_pw = generate_password_hash(password)

        try:
            db.execute(
                text("INSERT INTO users (username, password) VALUES (:u, :p)"),
                {"u": username, "p": hash_pw}
            )
            db.commit()
        except:
            return "Username already exists"

        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = db.execute(
            text("SELECT * FROM users WHERE username = :u"),
            {"u": username}
        ).fetchone()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect("/search")

        return "Invalid login"

    return render_template("login.html")

# ====================
# SEARCH PAGE
# ====================
@app.route("/search", methods=["GET", "POST"])
def search():

    if not session.get("user_id"):
        return redirect("/login")

    if request.method == "POST":

        query = request.form.get("query")

        results = db.execute(
            text("""
                SELECT * FROM books
                WHERE isbn ILIKE :q
                OR title ILIKE :q
                OR author ILIKE :q
                LIMIT 20
            """),
            {"q": f"%{query}%"}
        ).fetchall()

        return render_template("search.html", books=results)

    return render_template("search.html")


# =========================
# BOOK PAGE
# =========================
@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):

    if "user_id" not in session:
        return redirect("/login")

    # If user submits a review
    if request.method == "POST":

        rating = request.form.get("rating")
        review = request.form.get("review")

        db.execute(text("""
            INSERT INTO reviews (user_id, isbn, rating, review)
            VALUES (:user_id, :isbn, :rating, :review)
        """), {
            "user_id": session["user_id"],
            "isbn": isbn,
            "rating": rating,
            "review": review
        })

        db.commit()

        return redirect(f"/book/{isbn}")

    # Get book info
    book = db.execute(text("""
        SELECT * FROM books WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchone()

    # Get reviews
    reviews = db.execute(text("""
        SELECT users.username, reviews.rating, reviews.review
        FROM reviews
        JOIN users ON users.id = reviews.user_id
        WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchall()

    return render_template("book.html", book=book, reviews=reviews)

# =========================
# ADD REVIEW
# =========================
@app.route("/review", methods=["POST"])
def review():

    if not session.get("user_id"):
        return redirect("/login")

    isbn = request.form.get("isbn")
    rating = request.form.get("rating")
    review = request.form.get("review")

    db.execute(
        text("""
            INSERT INTO reviews (user_id, isbn, rating, review)
            VALUES (:user_id, :isbn, :rating, :review)
        """),
        {
            "user_id": session["user_id"],
            "isbn": isbn,
            "rating": rating,
            "review": review
        }
    )

    db.commit()

    return redirect(f"/book/{isbn}")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

