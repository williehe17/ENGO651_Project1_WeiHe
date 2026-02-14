import csv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

# Check DATABASE_URL
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Connect to database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

print("Importing books...")

# Create books table if it doesn't exist
db.execute(text("""
CREATE TABLE IF NOT EXISTS books (
    isbn VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    author VARCHAR NOT NULL,
    year INTEGER NOT NULL
);
"""))

# Create reviews table
db.execute(text("""
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    isbn VARCHAR NOT NULL,
    rating INTEGER NOT NULL,
    review TEXT
)
"""))


# Read CSV and insert rows
with open("books.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        db.execute(
            text("""
            INSERT INTO books (isbn, title, author, year)
            VALUES (:isbn, :title, :author, :year)
            ON CONFLICT DO NOTHING;
            """),
            {
                "isbn": row["isbn"],
                "title": row["title"],
                "author": row["author"],
                "year": int(row["year"])
            }
        )

db.commit()
print("Books imported successfully.")
