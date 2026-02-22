import os
import requests
from flask import Flask, session, request, redirect, render_template, jsonify
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

    # =========================
    # HANDLE REVIEW SUBMISSION
    # =========================
    if request.method == "POST":

        rating = request.form.get("rating")
        review = request.form.get("review")

        existing = db.execute(text("""
            SELECT * FROM reviews
            WHERE user_id = :uid AND isbn = :isbn
        """), {
            "uid": session["user_id"],
            "isbn": isbn
        }).fetchone()

        if existing:
            return "You already reviewed this book"

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

    # =========================
    # GET BOOK FROM DATABASE
    # =========================
    book = db.execute(text("""
        SELECT * FROM books WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchone()

    # =========================
    # GOOGLE BOOKS API
    # =========================
    google_data = None

    res = requests.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": f"isbn:{isbn}"}
    )

    if res.status_code == 200:
        data = res.json()

        if data.get("totalItems", 0) > 0:
            volume = data["items"][0]["volumeInfo"]

            google_data = {
                "publishedDate": volume.get("publishedDate"),
                "description": volume.get("description"),
                "averageRating": volume.get("averageRating"),
                "ratingsCount": volume.get("ratingsCount")
            }

    # =========================
    # GEMINI AI SUMMARY
    # =========================
    summary = None

    text_to_summarize = (
        google_data.get("description")
        if google_data and google_data.get("description")
        else f"{book.title} by {book.author}, published in {book.year}."
    )

    api_key = os.getenv("GEMINI_API_KEY")

    try:
        gemini_response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{
                        "text": f"summarize this text using less than 50 words: {text_to_summarize}"
                    }]
                }]
            }
        )

        print("GEMINI STATUS:", gemini_response.status_code)

        if gemini_response.status_code == 200:
            gemini_json = gemini_response.json()
            summary = gemini_json["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print("Gemini Error:", e)

    print("FINAL SUMMARY:", summary)
    print(gemini_response.status_code, gemini_response.text)

    # =========================
    # GET REVIEWS
    # =========================
    reviews = db.execute(text("""
        SELECT users.username, reviews.rating, reviews.review
        FROM reviews
        JOIN users ON users.id = reviews.user_id
        WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchall()

    return render_template(
        "book.html",
        book=book,
        reviews=reviews,
        google_data=google_data,
        summary=summary
    )
    
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

@app.route("/api/<isbn>")
def book_api(isbn):

    # -------------------------
    # Get book from database
    # -------------------------
    book = db.execute(text("""
        SELECT * FROM books WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchone()

    if not book:
        return jsonify({"error": "Book not found"}), 404

    # -------------------------
    # Get review stats
    # -------------------------
    stats = db.execute(text("""
        SELECT COUNT(*) AS reviewCount,
               AVG(rating) AS averageRating
        FROM reviews
        WHERE isbn = :isbn
    """), {"isbn": isbn}).fetchone()

    review_count = stats.reviewcount if stats.reviewcount else 0
    average_rating = float(stats.averagerating) if stats.averagerating else None

    # -------------------------
    # Google Books API
    # -------------------------
    description = None
    isbn10 = None
    isbn13 = None

    try:
        google_res = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"isbn:{isbn}"}
        )

        if google_res.status_code == 200:
            data = google_res.json()

            if data.get("items"):
                info = data["items"][0]["volumeInfo"]

                description = info.get("description")

                for i in info.get("industryIdentifiers", []):
                    if i["type"] == "ISBN_10":
                        isbn10 = i["identifier"]
                    if i["type"] == "ISBN_13":
                        isbn13 = i["identifier"]

    except Exception as e:
        print("Google API error:", e)

    # -------------------------
    # Gemini summary
    # -------------------------
    summary = None

    if description:
        api_key = os.getenv("GEMINI_API_KEY")

        try:
            gemini_response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{
                            "text": f"Summarize this text in less than 50 words:\n{description}"
                        }]
                    }]
                }
            )

            if gemini_response.status_code == 200:
                gemini_data = gemini_response.json()
                summary = gemini_data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as e:
            print("Gemini error:", e)

    # -------------------------
    # Return JSON
    # -------------------------
    return jsonify({
        "title": book.title,
        "author": book.author,
        "publishedDate": book.year,
        "ISBN_10": isbn10,
        "ISBN_13": isbn13,
        "reviewCount": review_count,
        "averageRating": average_rating,
        "summarizedDescription": summary
    })

