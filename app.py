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
        
        # choose number closest to 7000-30000 range (realistic stipend range)
        stipend = min(candidates, key=lambda x: abs(x - 10000))

    
   # -------- FEE --------
    fee = 0
    import re
    
    fee_patterns = [
        r'(fee|registration|payment|charges)[^\d]{0,10}(\d{3,6})',
        r'(\d{3,6})[^\d]{0,10}(fee|registration|payment|charges)'
        ]
    for pattern in fee_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            for group in match.groups():
                if group and group.isdigit():
                    val = int(group)
                    if 500 <= val <= 20000:
                        fee = val
                        break
        if fee != 0:
            break
    print("Final extracted fee:", fee)

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
            name TEXT,   
            phone TEXT,
            password TEXT,
            verified INTEGER
        )
    """)

#------------------HOME----------------
@app.route("/")
def home():
    return redirect("/signup")


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        password = request.form["password"]

        import re
        # -------- MOBILE VALIDATION --------
        if not re.fullmatch(r"[6-9]\d{9}", phone):
            return render_template("signup.html", error="Invalid mobile number")
        
        # -------- EMAIL VALIDATION --------
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            return render_template("signup.html", error="Invalid email format")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        # If user already exists → go to login
        if user:
            return render_template("signup.html", error="User already exists")

        #If new user → insert
        db.execute(
            "INSERT INTO users VALUES (?,?,?,?,?)",
            (email,name ,phone, password, 1)
        )
        db.commit()

        session["user"] = name
        return redirect("/dashboard")

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
            return render_template("login.html", error="Invalid login")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html")

#------------------TEXT PAGE-------------------
@app.route("/form")
def form_page():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")


#Text Prediction
@app.route("/predict", methods=["POST"])
def predict():
    text = request.form["description"]

    import re
    text = re.sub(r'[^a-zA-Z0-9₹.,:/@ \n]+', ' ', text)

    official_email, stipend, fee = extract_details(text)
    print("Extracted stipend:",stipend)
    print("Extracted fee:",fee)

    features = vectorizer.transform([text])
    prediction = model.predict(features)[0]

    fraud_keywords = [
        "pay", "registration fee", "limited seats", "last chance",
        "hurry", "urgent", "final day", "only few", "vacancy left",
        "click link", "rzp.io", "payment", "enroll now"
    ]

    negative_words = ["no", "not", "free", "without"]
    is_fraud_rule = False
    text_lower = text.lower()
    
    for word in fraud_keywords:
        if word in text_lower:
            
            # check if negative word is near it
            for neg in negative_words:
                if neg + " " + word in text_lower:
                    break
                else:
                    is_fraud_rule = True
                    break

    if prediction == 1 or is_fraud_rule:
        result = "Fraud"
    else:
        result = "Legit"

    prob = model.predict_proba(features)[0]
    percentage = str(round(max(prob) * 100, 2)) + "%"

    return render_template(
        "result.html",
        result=result,
        percentage=percentage,
        description=text,
        stipend=stipend,
        fee=fee
    )


#-------------------IMAGE PAGE---------------------
@app.route("/image")
def image_page():
    if "user" not in session:
        return redirect("/login")
    return render_template("image.html")

#Image Prediction
@app.route("/predict_image", methods=["POST"])
def predict_image():
    file = request.files["image"]

    if not file or file.filename =="":
        return "No file uploaded"

    image = Image.open(file)
    image = image.convert('L')

    text = pytesseract.image_to_string(image)
    print("OCR TEXT:\n",text)
    
    import re
    text = re.sub(r'[^a-zA-Z0-9₹.,:/@ \n]+', ' ', text)

    official_email, stipend, fee = extract_details(text)
    print("Extracted stipend:",stipend)
    print("Extracted fee:",fee)

    features = vectorizer.transform([text])
    prediction = model.predict(features)[0]

    fraud_keywords = [
    "pay", "registration fee", "limited seats", "last chance",
    "hurry", "urgent", "final day", "only few", "vacancy left",
    "click link", "rzp.io", "payment", "enroll now", "no extension",
    "closing soon", "apply fast"
    ]
    negative_words = ["no", "not", "free", "without"]
    is_fraud_rule = False
    text_lower = text.lower()
    for word in fraud_keywords:
        if word in text_lower:
            # check if negative word is near it
            for neg in negative_words:
                if neg + " " + word in text_lower:
                    break
                else:
                    is_fraud_rule = True
                    break
                
    if prediction == 1 or is_fraud_rule:
        result = "Fraud"
    else:
        result = "Legit"

    prob = model.predict_proba(features)[0]
    percentage = str(round(max(prob) * 100, 2)) + "%"

    return render_template(
        "result.html",
        result=result,
        percentage=percentage,
        description=text,
        stipend=stipend,
        fee=fee
    )

#-------------------LOGOUT PAGE--------------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

    
if __name__ == "__main__" :
    app.run(debug=True)