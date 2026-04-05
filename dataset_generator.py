# -*- coding: utf-8 -*-
"""
Created on Sun Apr  5 18:50:38 2026

@author: nanda
"""

import csv
import random

# Templates
legit_templates = [
    "We are offering a {} internship with training and no registration fee",
    "Join our {} internship program with mentorship and real projects",
    "Internship opportunity for students with stipend and certificate",
    "Work on real world {} projects with guidance",
    "Apply now for {} internship with flexible timings",
]

fraud_templates = [
    "Pay {} rupees to confirm your internship seat immediately",
    "Limited seats! Pay now to secure your internship",
    "Urgent hiring pay registration fee before deadline",
    "Click link and pay {} to get internship instantly",
    "Final chance pay now or lose internship opportunity",
]

skills = ["Python", "Web Development", "AI", "Data Science", "Cyber Security"]

# Create CSV
with open("dataset.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    # Header
    writer.writerow([
        "message_text","fee_required","stipend","urgency_payment",
        "valid_email","seat_urgency","has_link","suspicious_domain",
        "grammar_score","company_verified","label"
    ])

    # Generate 1000 rows
    for i in range(1000):
        if random.random() > 0.5:
            # Legit
            skill = random.choice(skills)
            msg = random.choice(legit_templates).format(skill)

            row = [
                msg,
                0,
                random.randint(5000, 10000),
                0,
                1,
                0,
                0,
                0,
                round(random.uniform(0.8, 1.0), 2),
                1,
                0
            ]
        else:
            # Fraud
            amount = random.randint(500, 5000)
            msg = random.choice(fraud_templates).format(amount)

            row = [
                msg,
                1,
                0,
                1,
                0,
                1,
                1,
                1,
                round(random.uniform(0.2, 0.5), 2),
                0,
                1
            ]

        writer.writerow(row)

print("✅ dataset.csv with 1000 rows created!")