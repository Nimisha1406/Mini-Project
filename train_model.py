# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 16:56:04 2026

@author: nanda
"""

import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from scipy.sparse import hstack

# Load dataset
data = pd.read_csv("dataset.csv")

X_text = data["description"]
X_num = data[["stipend", "fee_required", "official_email"]]
y = data["label"]

# Scale numeric data
scaler = StandardScaler()
X_num_scaled = scaler.fit_transform(X_num)

# TF-IDF Vectorizer
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1,2),
    max_features=5000
)

X_text_vec = vectorizer.fit_transform(X_text)

X_final = hstack([X_text_vec, X_num_scaled])

X_train, X_test, y_train, y_test = train_test_split(
    X_final, y, test_size=0.2, random_state=42
)

# Train model
model = LogisticRegression(max_iter=2000, class_weight="balanced")
model.fit(X_train, y_train)

# Accuracy
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))

# Save model
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))
pickle.dump(scaler, open("scaler.pkl", "wb"))