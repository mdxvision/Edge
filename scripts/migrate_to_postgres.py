#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

Usage:
    python scripts/migrate_to_postgres.py --sqlite ./sports_betting.db --postgres postgresql://user:pass@localhost:5432/edge_db

This script:
1. Reads all data from SQLite
2. Creates tables in PostgreSQL (via SQLAlchemy)
3. Migrates all data preserving relationships
"""

import argparse
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.db import Base

# Tables in order of dependencies (parents before children)
TABLE_ORDER = [
    'teams',
    'competitors',
    'players',
    'games',
    'markets',
    'lines',
    'clients',
    'users',
    'user_sessions',
    'bet_recommendations',
    'historical_game_results',
    'tracked_bets',
    'alerts',
    'webhooks',
    'audit_logs',
    'currency_rates',
    'odds_snapshots',
    'tracked_picks',
    'bankroll_snapshots',
]


def get_table_data(engine, table_name):
    """Fetch all data from a table."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            columns = result.keys()
            rows = result.fetchall()
            return columns, rows
        except Exception as e:
            print(f"  Warning: Could not read {table_name}: {e}")
            return None, []


def insert_data(engine, table_name, columns, rows):
    """Insert data into PostgreSQL table."""
    if not rows:
        return 0

    # Build INSERT statement
    col_list = ', '.join(columns)
    placeholders = ', '.join([f':{col}' for col in columns])

    with engine.begin() as conn:
        for row in rows:
            row_dict = dict(zip(columns, row))
            try:
                conn.execute(
                    text(f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"),
                    row_dict
                )
            except Exception as e:
                print(f"  Error inserting row: {e}")
                continue

    return len(rows)


def reset_sequences(pg_engine):
    """Reset PostgreSQL sequences to max ID + 1."""
    with pg_engine.begin() as conn:
        # Get all tables with serial/identity columns
        result = conn.execute(text("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND column_default LIKE 'nextval%'
        """))

        for table_name, column_name in result:
            try:
                # Get max ID
                max_result = conn.execute(text(f"SELECT MAX({column_name}) FROM {table_name}"))
                max_id = max_result.scalar() or 0

                # Reset sequence
                conn.execute(text(f"""
                    SELECT setval(pg_get_serial_sequence('{table_name}', '{column_name}'), {max_id + 1}, false)
                """))
                print(f"  Reset sequence for {table_name}.{column_name} to {max_id + 1}")
            except Exception as e:
                print(f"  Warning: Could not reset sequence for {table_name}: {e}")


def migrate(sqlite_url: str, postgres_url: str, drop_existing: bool = False):
    """Migrate data from SQLite to PostgreSQL."""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)

    # Connect to databases
    print(f"\nConnecting to SQLite: {sqlite_url}")
    sqlite_engine = create_engine(sqlite_url)

    print(f"Connecting to PostgreSQL: {postgres_url.split('@')[1] if '@' in postgres_url else postgres_url}")
    pg_engine = create_engine(postgres_url)

    # Create tables in PostgreSQL
    print("\nCreating tables in PostgreSQL...")
    if drop_existing:
        print("  Dropping existing tables...")
        Base.metadata.drop_all(pg_engine)
    Base.metadata.create_all(pg_engine)
    print("  Tables created.")

    # Migrate each table
    print("\nMigrating data...")
    total_rows = 0

    for table_name in TABLE_ORDER:
        columns, rows = get_table_data(sqlite_engine, table_name)
        if columns is None:
            continue

        if rows:
            count = insert_data(pg_engine, table_name, columns, rows)
            print(f"  {table_name}: {count} rows migrated")
            total_rows += count
        else:
            print(f"  {table_name}: 0 rows (empty)")

    # Reset sequences
    print("\nResetting PostgreSQL sequences...")
    reset_sequences(pg_engine)

    print("\n" + "=" * 60)
    print(f"Migration complete! {total_rows} total rows migrated.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite to PostgreSQL')
    parser.add_argument('--sqlite', required=True, help='SQLite database path or URL')
    parser.add_argument('--postgres', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--drop', action='store_true', help='Drop existing tables before migration')

    args = parser.parse_args()

    # Normalize SQLite URL
    sqlite_url = args.sqlite
    if not sqlite_url.startswith('sqlite'):
        sqlite_url = f'sqlite:///{sqlite_url}'

    migrate(sqlite_url, args.postgres, args.drop)


if __name__ == '__main__':
    main()
