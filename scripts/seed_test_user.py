#!/usr/bin/env python3
"""Seed script to create a test user for EdgeBet app."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, Client
from app.services.auth import hash_password
from sqlalchemy import text
from datetime import datetime

def create_test_user():
    """Create a test user with the specified credentials using raw SQL."""

    with engine.connect() as conn:
        # Check if user already exists
        result = conn.execute(text(
            "SELECT id, email, username FROM users WHERE email = :email OR username = :username"
        ), {"email": "test@edgebet.com", "username": "testuser"})
        existing = result.fetchone()

        if existing:
            print(f"Test user already exists (id={existing[0]}, email={existing[1]}, username={existing[2]})")
            print("=" * 50)
            print("Login credentials:")
            print(f"  Email:    test@edgebet.com")
            print(f"  Username: testuser")
            print(f"  Password: TestPass123!")
            print("=" * 50)
            return

        # Create client profile first
        result = conn.execute(text("""
            INSERT INTO clients (name, bankroll, risk_profile, created_at)
            VALUES (:name, :bankroll, :risk_profile, :created_at)
            RETURNING id
        """), {
            "name": "testuser",
            "bankroll": 10000.0,
            "risk_profile": "balanced",
            "created_at": datetime.utcnow()
        })
        client_id = result.fetchone()[0]

        # Create user - using columns that exist in actual DB
        password_hash = hash_password("TestPass123!")
        conn.execute(text("""
            INSERT INTO users (email, username, password_hash, client_id, is_active, is_verified, created_at, updated_at)
            VALUES (:email, :username, :password_hash, :client_id, :is_active, :is_verified, :created_at, :updated_at)
        """), {
            "email": "test@edgebet.com",
            "username": "testuser",
            "password_hash": password_hash,
            "client_id": client_id,
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        conn.commit()

        print("=" * 50)
        print("Test user created successfully!")
        print("=" * 50)
        print(f"Email:        test@edgebet.com")
        print(f"Username:     testuser")
        print(f"Password:     TestPass123!")
        print(f"Client ID:    {client_id}")
        print("=" * 50)
        print()
        print("Note: is_age_verified column doesn't exist in DB yet.")
        print("You may need to run migrations to add it.")

if __name__ == "__main__":
    create_test_user()
