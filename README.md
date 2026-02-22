# Book Review Website – Project 1-2 (ENGO 651)

## Overview

This project is a Flask-based web application that allows users to register, log in, search for books, view detailed book information, and submit reviews. The application uses PostgreSQL as the backend database and SQLAlchemy for database queries.

Users can:

* Create an account and log in securely
* Search for books by ISBN, title, or author
* View individual book pages
* Submit ratings and written reviews
* See reviews from other users
* View AI-generated summaries for books
* Access a JSON API endpoint for book data

The application also integrates Google Books API for additional metadata and Gemini AI for automatic text summarization.

---

## Project Structure

### application.py

Main Flask application file that manages routing, authentication, session handling, searching, book pages, review submission, external API integration, and JSON API responses.

### import.py

Script used to create database tables and import book data from `books.csv` into PostgreSQL.

Run with:

python import.py

### Templates/

HTML templates rendered by Flask:

* login.html – login page
* register.html – registration page
* search.html – book search interface
* book.html – individual book detail and review page

### books.csv

Dataset containing ISBN, title, author, and publication year information for books.

### requirements.txt

Python dependencies required to run the project.

---

## Database Design

Tables used:

* users – stores usernames and hashed passwords
* books – stores book information
* reviews – stores ratings and written reviews linked to users and books

SQL queries are executed using SQLAlchemy’s execute() method.

---

## Setup Instructions

Install dependencies:

pip install -r requirements.txt

Set database environment variable (PowerShell example):

$env:DATABASE_URL="postgresql://postgres:<password>@localhost/<dbname>"

Set Gemini API key:

$env:GEMINI_API_KEY="<your_api_key>"

Import book data:

python import.py

Run the application:

python -m flask --app application run

Open in browser:

http://127.0.0.1:5000

---

## Notes

This application demonstrates user authentication, database integration, dynamic searching, external API usage, AI-powered text summarization, and JSON API functionality built with Flask and PostgreSQL.
