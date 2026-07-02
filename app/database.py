import sqlite3
import os
import json
import uuid
from datetime import datetime
from typing import Any

DATABASE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "momo.db")

def get_connection():
    """Returns a sqlite3 connection to the local database file."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite tables for MoMo Ledger database structure."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Merchants Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        id TEXT PRIMARY KEY,
        business_name TEXT NOT NULL,
        owner_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Transactions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        merchant_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        amount REAL NOT NULL CHECK (amount >= 0),
        direction TEXT NOT NULL CHECK (direction IN ('inflow', 'outflow')),
        counterparty TEXT NOT NULL,
        category TEXT NOT NULL,
        confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
        reviewed_flag INTEGER NOT NULL DEFAULT 0,
        raw_payload TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
    );
    """)

    # 3. Financial Summaries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_summaries (
        id TEXT PRIMARY KEY,
        merchant_id TEXT NOT NULL,
        revenue REAL NOT NULL DEFAULT 0.00 CHECK (revenue >= 0),
        expenses REAL NOT NULL DEFAULT 0.00 CHECK (expenses >= 0),
        profit REAL NOT NULL DEFAULT 0.00,
        cash_flow REAL NOT NULL DEFAULT 0.00,
        average_balance REAL NOT NULL DEFAULT 0.00 CHECK (average_balance >= 0),
        credit_score INTEGER NOT NULL DEFAULT 0 CHECK (credit_score >= 0 AND credit_score <= 100),
        calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
    );
    """)

    # 4. Credit Profiles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS credit_profiles (
        id TEXT PRIMARY KEY,
        merchant_id TEXT NOT NULL,
        credit_score INTEGER NOT NULL CHECK (credit_score >= 0 AND credit_score <= 100),
        readiness_level TEXT NOT NULL,
        indicator TEXT NOT NULL CHECK (indicator IN ('RED', 'AMBER', 'GREEN')),
        assessment_details TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
    );
    """)

    # 5. Audit Logs Table (immutable record of mutations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        merchant_id TEXT,
        action TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        old_data TEXT,
        new_data TEXT,
        performed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE SET NULL
    );
    """)

    conn.commit()
    conn.close()

def log_audit(conn, merchant_id: str, action: str, table_name: str, record_id: str, old_data: dict | None = None, new_data: dict | None = None):
    """Inserts a record into the audit_logs table."""
    cursor = conn.cursor()
    log_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO audit_logs (id, merchant_id, action, table_name, record_id, old_data, new_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        merchant_id,
        action,
        table_name,
        record_id,
        json.dumps(old_data) if old_data else None,
        json.dumps(new_data) if new_data else None
    ))

def save_transaction(merchant_id: str, timestamp: str, amount: float, direction: str, counterparty: str, category: str, confidence: float, raw_payload: str | None = None) -> str:
    """Inserts a transaction and triggers audit logging."""
    conn = get_connection()
    cursor = conn.cursor()
    txn_id = str(uuid.uuid4())
    
    try:
        cursor.execute("""
            INSERT INTO transactions (id, merchant_id, timestamp, amount, direction, counterparty, category, confidence, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (txn_id, merchant_id, timestamp, amount, direction, counterparty, category, confidence, raw_payload))
        
        # Log mutation (mimics Postgres trigger)
        new_data = {
            "id": txn_id, "merchant_id": merchant_id, "timestamp": timestamp, "amount": amount,
            "direction": direction, "counterparty": counterparty, "category": category, "confidence": confidence
        }
        log_audit(conn, merchant_id, "INSERT", "transactions", txn_id, new_data=new_data)
        
        conn.commit()
        return txn_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_merchant_transactions(merchant_id: str) -> list:
    """Retrieves all transaction rows for a merchant."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE merchant_id = ? ORDER BY timestamp DESC", (merchant_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_merchant(merchant_id: str, business_name: str, owner_name: str, phone: str) -> None:
    """Saves or updates a merchant profile."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO merchants (id, business_name, owner_name, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                business_name = excluded.business_name,
                owner_name = excluded.owner_name,
                phone = excluded.phone
        """, (merchant_id, business_name, owner_name, phone))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_merchant(merchant_id: str) -> dict[str, Any] | None:
    """Retrieves merchant profile data."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_financial_summary(merchant_id: str, revenue: float, expenses: float, profit: float, cash_flow: float, average_balance: float, credit_score: int) -> str:
    """Saves a financial summary record."""
    conn = get_connection()
    cursor = conn.cursor()
    summary_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO financial_summaries (id, merchant_id, revenue, expenses, profit, cash_flow, average_balance, credit_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (summary_id, merchant_id, revenue, expenses, profit, cash_flow, average_balance, credit_score))
        conn.commit()
        return summary_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_financial_summary(merchant_id: str) -> dict[str, Any] | None:
    """Gets the latest financial summary for a merchant."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financial_summaries WHERE merchant_id = ? ORDER BY calculated_at DESC LIMIT 1", (merchant_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_credit_profile(merchant_id: str, credit_score: int, readiness_level: str, indicator: str, assessment_details: str) -> str:
    """Saves a credit profile rating."""
    conn = get_connection()
    cursor = conn.cursor()
    profile_id = str(uuid.uuid4())
    try:
        cursor.execute("""
            INSERT INTO credit_profiles (id, merchant_id, credit_score, readiness_level, indicator, assessment_details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (profile_id, merchant_id, credit_score, readiness_level, indicator, assessment_details))
        conn.commit()
        return profile_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_credit_profile(merchant_id: str) -> dict[str, Any] | None:
    """Gets the latest credit profile for a merchant."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credit_profiles WHERE merchant_id = ? ORDER BY created_at DESC LIMIT 1", (merchant_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_transaction_category(transaction_id: str, merchant_id: str, category: str) -> bool:
    """Updates a transaction's category (user review override) and logs the action."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get old data for audit log
        cursor.execute("SELECT * FROM transactions WHERE id = ? AND merchant_id = ?", (transaction_id, merchant_id))
        row = cursor.fetchone()
        if not row:
            return False
        old_data = dict(row)
        
        cursor.execute("""
            UPDATE transactions
            SET category = ?, reviewed_flag = 1
            WHERE id = ? AND merchant_id = ?
        """, (category, transaction_id, merchant_id))
        
        # Log mutation (mimics Postgres trigger)
        new_data = old_data.copy()
        new_data["category"] = category
        new_data["reviewed_flag"] = 1
        log_audit(conn, merchant_id, "UPDATE", "transactions", transaction_id, old_data=old_data, new_data=new_data)
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
