# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 17:09:27 2026

@author: nanda
"""

from flask import Flask, render_template, request, redirect, session
import sqlite3, random, pickle, os
import numpy as np
from scipy.sparse import hstack
from PIL import Image
import pytesseract

app = Flask(__name__)
app.secret_key = "secretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load ML objects (scikit-learn)
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))

# Database
def get_db():
    return sqlite3.connect("users.db")

with get_db() as db:
    db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            email TEXT PRIMARY KEY,
            phone TEXT,
            password TEXT,
            verified INTEGER
        )
    """)

# ---------------- SIGNUP ----------------
@app.route("/", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        # If user already exists → go to login
        if user:
            return redirect("/login?msg=User already exists")

        #If new user → insert
        db.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (email, phone, password, 1)
        )
        db.commit()

        return redirect("/login")

    return render_template("signup.html")

# ---------------- LOGIN ----------------
from flask import flash

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email,password)
        ).fetchone()

        if user:
            session["user"] = email
            return redirect("/dashboard")
        else:
            flash("Invalid email or password. Please try again.")
            return redirect("/login")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = risk = None

    if request.method == "POST":
        text = request.form["message"]

        # OCR for images/docs
        if "file" in request.files and request.files["file"].filename != "":
            file = request.files["file"]
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            try:
                img = Image.open(path)
                text += " " + pytesseract.image_to_string(img)
            except:
                pass

        stipend = int(request.form["stipend"])
        fee = int(request.form["fee"])
        official_email = int(request.form["official_email"])

        text_vec = vectorizer.transform([text])
        num_scaled = scaler.transform([[stipend, fee, official_email]])
        final_input = hstack([text_vec, num_scaled])

        pred = model.predict(final_input)[0]
        prob = model.predict_proba(final_input)[0][1]

        result = "FRAUD" if pred == 1 else "LEGIT"
        risk = round(prob * 100, 2)

    return render_template("dashboard.html", result=result, risk=risk)

app.run(debug=True)