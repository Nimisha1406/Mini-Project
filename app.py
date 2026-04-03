# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 17:09:27 2026

@author: nanda
"""

from flask import Flask, render_template, request, redirect, session
import sqlite3, random, pickle, os
import numpy as np
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = "secretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load ML objects (scikit-learn)
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))


def extract_details(text):
    import re

    text = text.lower()

   # -------- STIPEND --------
    stipend = 0
    
    text = text.replace(",", "")
    text_lower = text.lower()
    
    # STEP 1: STRICT pattern (₹ or "get" near stipend)
    strict_patterns = [
        r'₹\s?(\d{3,6})',
        r'get\s*[:\-]?\s*(\d{3,6})',
        r'(\d{3,6})\s*(?:rs|inr)',
        ]
    candidates = []
    for pattern in strict_patterns:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            val = int(m)
            if 1000 <= val <= 100000:
                candidates.append(val)
                
    # STEP 2: If still empty → check near "stipend"
    if not candidates:
        matches = re.findall(r'(.{0,40}stipend.{0,40})', text_lower)
        for block in matches:
            nums = re.findall(r'\d{3,6}', block)
            
            for n in nums:
                val = int(n)
                
                # remove phone numbers
                if len(n) == 5 and n.startswith(('6','7','8','9')):
                    continue
                # remove years
                if val in [2024, 2025, 2026, 2027]:
                    continue
                if 1000 <= val <= 100000:
                    candidates.append(val)
                    
    # STEP 3: Final selection
    if candidates:
        
        # choose number closest to 7000-30000 range (internship realistic)
        stipend = min(candidates, key=lambda x: abs(x - 10000))
    
   # -------- FEE --------
    fee = 0
    
    fee_match = re.search(
        r'(registration fee|application fee|fee|payment)\s*(is|:)?\s*₹?\s*([\d,]{3,6})',
        text,
        re.IGNORECASE
        )
    if fee_match:
        fee = int(fee_match.group(3).replace(",", ""))

    # -------- EMAIL --------
    if "@gmail.com" in text or "@yahoo.com" in text:
        official_email = 0
    else:
        official_email = 1

    return official_email, stipend, fee

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
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if request.method == "POST":

        file = request.files.get("file")
        text_input = request.form.get("text_input")

        text = ""

        # ---------------- TEXT INPUT ----------------
        if text_input and text_input.strip() != "":
            print("Using TEXT input")
            text = text_input
            text = text.replace(",","")

        # ---------------- FILE INPUT ----------------
        elif file and file.filename != "":
            print("Using FILE input")

            filename = file.filename.lower()

            # TEXT FILE
            if filename.endswith(".txt"):
                text = file.read().decode("utf-8")

            # IMAGE FILE
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                image = Image.open(file)

                # OCR improve
                image = image.convert('L')
                custom_config = r'--oem 3 --psm 6'

                text = pytesseract.image_to_string(image, config=custom_config)
                text = text.replace(",","")

            else:
                return "Unsupported file type"

        else:
            return "Please upload a file OR enter text"

        print("FINAL TEXT:", text)

        # ----------- CLEAN TEXT -----------
        import re
        text = re.sub(r'[^a-zA-Z0-9₹.,:/@ \n]+', ' ', text)
        text = "\n".join([line.strip() for line in text.split("\n") if line.strip() != ""])

        # ----------- EXTRACT -----------
        official_email, stipend, fee = extract_details(text)

        # ----------- ML -----------
        features = vectorizer.transform([text])
        prediction = model.predict(features)[0]

        # ----------- RULE BASED -----------
        fraud_keywords = [
            "pay", "registration fee", "limited seats", "last chance",
            "hurry", "urgent", "final day", "only few", "vacancy left",
            "click link", "rzp.io", "payment", "enroll now"
        ]

        is_fraud_rule = any(word in text.lower() for word in fraud_keywords)

        # ----------- FINAL RESULT -----------
        if prediction == 1 or is_fraud_rule:
            result = "FRAUD"
        else:
            result = "LEGIT"

        # ----------- CONFIDENCE -----------
        if hasattr(model, "predict_proba"):
            prob = model.predict_proba(features)[0]
            confidence = round(max(prob) * 100, 2)
        else:
            confidence = 0

        return render_template(
            "dashboard.html",
            result=result,
            confidence=confidence,
            extracted_text=text,
            stipend=stipend,
            fee=fee
        )

    return render_template("dashboard.html")

app.run(debug=True)