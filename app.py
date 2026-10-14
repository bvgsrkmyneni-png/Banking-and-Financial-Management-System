
"""SDFC Finance - Banking and Financial Management System.

Educational simulation only. Do not use real banking data.
"""

from __future__ import annotations

import os
import sqlite3
import secrets
import hashlib
import hmac
import threading

from pathlib import Path
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timezone, date
from calendar import monthrange
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Flask, jsonify, render_template, request, session


# ================= CONFIGURATION =================

DB = os.getenv(
    "BTMS_DB",
    str(Path(__file__).with_name("bank.db"))
)

LOCK = threading.RLock()

app = Flask(__name__)
app.secret_key = os.getenv("BTMS_SECRET", secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)


# ================= HELPERS =================

@contextmanager
def connection():
    db = sqlite3.connect(DB, timeout=15, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode(), bytes.fromhex(salt), 180000
    ).hex()


def display(cents):
    return f"{Decimal(cents) / 100:.2f}"


def money(value):
    try:
        amount = Decimal(str(value))
        if (
            not amount.is_finite()
            or amount <= 0
            or amount > Decimal("100000000")
            or amount != amount.quantize(Decimal("0.01"))
        ):
            raise ValueError()

        return int(amount * 100)

    except (ValueError, InvalidOperation, TypeError):
        raise ValueError(
            "Enter a valid positive amount with at most 2 decimals"
        )


def failure(message, code=400):
    return jsonify(error=message), code


def current():
    if session.get("role") == "CUSTOMER":
        return session.get("account")
    return None


def is_admin():
    return (
        session.get("role") == "ADMIN"
        and bool(session.get("admin_username"))
    )


def require_customer(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not current():
            return failure("Customer sign-in required", 403)

        with connection() as db:
            account = get_account(db, current())

        if account is None or not account["active"]:
            session.clear()
            return failure(
                "Customer account is inactive or unavailable", 401
            )

        return fn(*args, **kwargs)

    return inner


def require_admin(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not is_admin():
            return failure("Admin access required", 403)

        with connection() as db:
            found = db.execute(
                "SELECT 1 FROM admins WHERE username=?",
                (session["admin_username"],)
            ).fetchone()

        if not found:
            session.clear()
            return failure("Admin account unavailable", 401)

        return fn(*args, **kwargs)

    return inner


def require_login(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not current() and not is_admin():
            return failure("Sign in first", 401)

        return fn(*args, **kwargs)

    return inner


def get_account(db, number):
    return db.execute(
        "SELECT * FROM accounts WHERE number=?", (number,)
    ).fetchone()


def row_account(row):
    return {
        "number": row["number"],
        "name": row["name"],
        "balance": display(row["balance"]),
        "active": bool(row["active"]),
        "created": row["created"]
    }


# ================= DATABASE =================

def init_db():
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            number TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            pin_salt TEXT NOT NULL,
            pin_hash TEXT NOT NULL,
            balance INTEGER NOT NULL CHECK(balance >= 0),
            active INTEGER NOT NULL DEFAULT 1,
            created TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            source TEXT,
            destination TEXT,
            amount INTEGER NOT NULL CHECK(amount > 0),
            created TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT NOT NULL,
            principal INTEGER NOT NULL CHECK(principal > 0),
            annual_rate TEXT NOT NULL,
            tenure_months INTEGER NOT NULL,
            monthly_emi INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created TEXT NOT NULL,
            FOREIGN KEY(account_number) REFERENCES accounts(number)
        );

        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS loan_installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            installment_number INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK(amount > 0),
            principal_component INTEGER NOT NULL,
            interest_component INTEGER NOT NULL,
            paid INTEGER NOT NULL DEFAULT 0,
            paid_at TEXT,
            UNIQUE(loan_id, installment_number),
            FOREIGN KEY(loan_id) REFERENCES loans(id)
        );
        """)

        if not db.execute(
            "SELECT 1 FROM accounts LIMIT 1"
        ).fetchone():
            demo = [
                ("10010001", "Aarav Sharma", "1234", 2500000),
                ("10010002", "Diya Reddy", "2345", 1850000),
                ("10010003", "Rahul Kumar", "3456", 720000),
                ("10010004", "Ananya Rao", "4567", 3100000)
            ]

            for number, name, pin, balance in demo:
                salt = secrets.token_hex(16)

                db.execute(
                    "INSERT INTO accounts VALUES(?,?,?,?,?,?,?)",
                    (
                        number,
                        name,
                        salt,
                        hash_pin(pin, salt),
                        balance,
                        1,
                        now()
                    )
                )

        # Create demo Admin without altering existing customers.
        if not db.execute(
            "SELECT 1 FROM admins LIMIT 1"
        ).fetchone():
            username = os.getenv(
                "SDFC_ADMIN_USERNAME", "admin"
            ).strip()

            password = os.getenv(
                "SDFC_ADMIN_PASSWORD", "Admin@1234"
            )

            if not username or not password:
                raise ValueError(
                    "Admin username/password must not be empty"
                )

            salt = secrets.token_hex(16)

            db.execute(
                "INSERT INTO admins VALUES(?,?,?,?)",
                (
                    username,
                    salt,
                    hash_pin(password, salt),
                    now()
                )
            )


# ================= LOGIN =================

@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    role = str(
        data.get("role", "CUSTOMER")
    ).upper().strip()

    if role == "ADMIN":
        username = str(
            data.get("username", "")
        ).strip()

        password = str(data.get("password", ""))

        with connection() as db:
            row = db.execute(
                "SELECT * FROM admins WHERE username=?",
                (username,)
            ).fetchone()

        if not row or not hmac.compare_digest(
            hash_pin(password, row["password_salt"]),
            row["password_hash"]
        ):
            return failure(
                "Invalid admin username or password", 401
            )

        session.clear()
        session["role"] = "ADMIN"
        session["admin_username"] = username

        return jsonify(
            role="ADMIN",
            admin={"username": username}
        )

    if role != "CUSTOMER":
        return failure("Unknown login role")

    number = str(
        data.get("number", "")
    ).strip()

    pin = str(data.get("pin", ""))

    with connection() as db:
        row = get_account(db, number)

    if (
        not row
        or not row["active"]
        or not hmac.compare_digest(
            hash_pin(pin, row["pin_salt"]),
            row["pin_hash"]
        )
    ):
        return failure(
            "Invalid account number or PIN", 401
        )

    session.clear()
    session["role"] = "CUSTOMER"
    session["account"] = number

    return jsonify(
        role="CUSTOMER",
        account=row_account(row)
    )


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
@require_login
def me():
    if is_admin():
        with connection() as db:
            admin = db.execute(
                "SELECT username FROM admins WHERE username=?",
                (session["admin_username"],)
            ).fetchone()

        if admin is None:
            session.clear()
            return failure("Admin no longer exists", 401)

        return jsonify(
            role="ADMIN",
            admin={"username": admin["username"]}
        )

    with connection() as db:
        row = get_account(db, current())

    if not row or not row["active"]:
        session.clear()
        return failure("Account inactive", 401)

    return jsonify(
        role="CUSTOMER",
        account=row_account(row)
    )


# ================= DASHBOARD =================

@app.get("/api/overview")
@require_login
def overview():
    with connection() as db:
        if is_admin():
            stats = db.execute("""
                SELECT
                    COUNT(*) total,
                    COALESCE(SUM(active),0) active,
                    COALESCE(SUM(balance),0) funds
                FROM accounts
            """).fetchone()

            count = db.execute(
                "SELECT COUNT(*) FROM transactions"
            ).fetchone()[0]

            loan_stats = db.execute("""
                SELECT
                    COUNT(*) total,
                    COALESCE(SUM(
                        CASE WHEN status='ACTIVE'
                        THEN 1 ELSE 0 END
                    ),0) active,
                    COALESCE(SUM(
                        CASE WHEN status='PENDING'
                        THEN 1 ELSE 0 END
                    ),0) pending
                FROM loans
            """).fetchone()

            return jsonify(
                accounts=stats["total"],
                active=stats["active"],
                total_funds=display(stats["funds"]),
                transactions=count,
                total_loans=loan_stats["total"],
                active_loans=loan_stats["active"],
                pending_loans=loan_stats["pending"]
            )

        account = get_account(db, current())

        if account is None or not account["active"]:
            return failure("Account unavailable", 401)

        count = db.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE source=? OR destination=?
        """, (
            current(),
            current()
        )).fetchone()[0]

        loan_stats = db.execute("""
            SELECT
                COUNT(*) total,
                COALESCE(SUM(
                    CASE WHEN status='ACTIVE'
                    THEN 1 ELSE 0 END
                ),0) active
            FROM loans
            WHERE account_number=?
        """, (current(),)).fetchone()

    return jsonify(
        accounts=1,
        active=1,
        total_funds=display(account["balance"]),
        transactions=count,
        total_loans=loan_stats["total"],
        active_loans=loan_stats["active"]
    )


# ================= ACCOUNTS =================

@app.post("/api/accounts")
@require_admin
def create_account():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    pin = str(data.get("pin", ""))

    if not 2 <= len(name) <= 80 or not (
        pin.isdigit() and len(pin) == 4
    ):
        return failure(
            "Name 2-80 characters and four-digit PIN required"
        )

    with LOCK, connection() as db:
        db.execute("BEGIN IMMEDIATE")

        last = db.execute(
            "SELECT MAX(CAST(number AS INTEGER)) FROM accounts"
        ).fetchone()[0]

        number = str(int(last or 10010000) + 1)
        salt = secrets.token_hex(16)

        db.execute(
            "INSERT INTO accounts VALUES(?,?,?,?,?,?,?)",
            (
                number,
                name,
                salt,
                hash_pin(pin, salt),
                0,
                1,
                now()
            )
        )

        db.commit()

    return jsonify(
        number=number,
        name=name
    ), 201


@app.patch("/api/account")
@require_customer
def update_account():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()

    if not 2 <= len(name) <= 80:
        return failure(
            "Name must contain 2-80 characters"
        )

    with connection() as db:
        db.execute(
            """
            UPDATE accounts
            SET name=?
            WHERE number=? AND active=1
            """,
            (name, current())
        )

    return jsonify(ok=True)


@app.get("/api/admin/accounts")
@require_admin
def admin_accounts():
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM accounts ORDER BY number DESC"
        ).fetchall()

    return jsonify(
        items=[row_account(row) for row in rows]
    )


@app.patch("/api/admin/accounts/<number>")
@require_admin
def admin_update_account(number):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()

    if not 2 <= len(name) <= 80:
        return failure(
            "Name must contain 2-80 characters"
        )

    with connection() as db:
        cursor = db.execute(
            """
            UPDATE accounts SET name=?
            WHERE number=? AND active=1
            """,
            (name, number)
        )

    if not cursor.rowcount:
        return failure(
            "Active customer account not found", 404
        )

    return jsonify(ok=True)


@app.post("/api/deactivate")
@require_admin
def deactivate():
    data = request.get_json(silent=True) or {}
    number = str(
        data.get("number", "")
    ).strip()

    if not number:
        return failure(
            "Customer account number required"
        )

    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            account = get_account(db, number)

            if not account or not account["active"]:
                raise ValueError(
                    "Customer account missing or inactive"
                )

            if account["balance"] != 0:
                raise ValueError(
                    "Customer balance must be zero before deactivation"
                )

            active_loans = db.execute("""
                SELECT COUNT(*) FROM loans
                WHERE account_number=?
                AND status IN ('ACTIVE','PENDING')
            """, (number,)).fetchone()[0]

            if active_loans:
                raise ValueError(
                    "Resolve active/pending loans before deactivation"
                )

            db.execute(
                """
                UPDATE accounts SET active=0
                WHERE number=?
                """,
                (number,)
            )

            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(ok=True)


# ================= TRANSACTIONS =================

def transact(kind, destination=None):
    data = request.get_json(silent=True) or {}

    try:
        amount = money(data.get("amount"))
    except ValueError as e:
        return failure(str(e))

    source = current()

    if kind == "transfer" and (
        not destination or destination == source
    ):
        return failure(
            "Choose a different destination account"
        )

    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            account = get_account(db, source)

            if not account or not account["active"]:
                raise ValueError("Source account inactive")

            if kind == "transfer":
                target = get_account(db, destination)

                if not target or not target["active"]:
                    raise ValueError(
                        "Destination account inactive or missing"
                    )

            if kind in ("withdraw", "transfer"):
                if account["balance"] < amount:
                    raise ValueError("Insufficient balance")

            if kind == "deposit":
                db.execute(
                    """
                    UPDATE accounts
                    SET balance=balance+?
                    WHERE number=?
                    """,
                    (amount, source)
                )
            else:
                db.execute(
                    """
                    UPDATE accounts
                    SET balance=balance-?
                    WHERE number=?
                    """,
                    (amount, source)
                )

            if kind == "transfer":
                db.execute(
                    """
                    UPDATE accounts
                    SET balance=balance+?
                    WHERE number=?
                    """,
                    (amount, destination)
                )

            cursor = db.execute("""
                INSERT INTO transactions
                (
                    kind,
                    source,
                    destination,
                    amount,
                    created,
                    note
                )
                VALUES(?,?,?,?,?,?)
            """, (
                kind,
                source,
                destination,
                amount,
                now(),
                "Educational demo"
            ))

            tid = cursor.lastrowid
            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(
        ok=True,
        transaction_id=tid,
        amount=display(amount)
    )


@app.post("/api/deposit")
@require_customer
def deposit():
    return transact("deposit")


@app.post("/api/withdraw")
@require_customer
def withdraw():
    return transact("withdraw")


@app.post("/api/transfer")
@require_customer
def transfer():
    data = request.get_json(silent=True) or {}

    return transact(
        "transfer",
        str(data.get("destination", "")).strip()
    )


@app.get("/api/history")
@require_customer
def history():
    with connection() as db:
        rows = db.execute("""
            SELECT * FROM transactions
            WHERE source=? OR destination=?
            ORDER BY id DESC LIMIT 100
        """, (
            current(),
            current()
        )).fetchall()

    return jsonify(items=[
        {
            "id": row["id"],
            "kind": row["kind"],
            "source": row["source"],
            "destination": row["destination"],
            "amount": display(row["amount"]),
            "created": row["created"]
        }
        for row in rows
    ])


@app.get("/api/admin/history")
@require_admin
def admin_history():
    with connection() as db:
        rows = db.execute(
            """
            SELECT *
            FROM transactions
            ORDER BY id DESC LIMIT 200
            """
        ).fetchall()

    return jsonify(items=[
        {
            "id": row["id"],
            "kind": row["kind"],
            "source": row["source"],
            "destination": row["destination"],
            "amount": display(row["amount"]),
            "created": row["created"]
        }
        for row in rows
    ])


# ================= INTEGRITY CHECK =================

@app.get("/api/audit")
@require_admin
def audit():
    with connection() as db:
        bad = db.execute(
            "SELECT COUNT(*) FROM accounts WHERE balance<0"
        ).fetchone()[0]

        orphan = db.execute("""
            SELECT COUNT(*) FROM transactions t
            WHERE (
                t.source IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM accounts a
                    WHERE a.number=t.source
                )
            ) OR (
                t.destination IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM accounts a
                    WHERE a.number=t.destination
                )
            )
        """).fetchone()[0]

        invalid_loans = db.execute("""
            SELECT COUNT(*) FROM loans l
            WHERE NOT EXISTS (
                SELECT 1 FROM accounts a
                WHERE a.number=l.account_number
            )
        """).fetchone()[0]

    return jsonify(
        passed=(
            bad == 0
            and orphan == 0
            and invalid_loans == 0
        ),
        negative_balances=bad,
        orphan_references=orphan,
        invalid_loans=invalid_loans
    )


# ================= EMI CALCULATOR =================

def parse_loan_details(data):
    try:
        principal = Decimal(
            str(data.get("principal"))
        )
        annual_rate = Decimal(
            str(data.get("interest_rate"))
        )
        tenure = Decimal(
            str(data.get("months"))
        )

        if (
            not principal.is_finite()
            or not annual_rate.is_finite()
            or not tenure.is_finite()
            or principal < Decimal("0.01")
            or principal > Decimal("100000000")
            or annual_rate < 0
            or annual_rate > 100
            or tenure != tenure.to_integral_value()
            or tenure < 1
            or tenure > 600
        ):
            raise ValueError()

        return principal, annual_rate, int(tenure)

    except (ValueError, TypeError, InvalidOperation):
        raise ValueError(
            "Enter valid loan amount, rate and tenure"
        )


def emi_value(principal, annual_rate, months):
    rate = annual_rate / Decimal("1200")

    if rate == 0:
        return principal / months

    factor = (1 + rate) ** months

    return principal * rate * factor / (factor - 1)


def rounded(value):
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


@app.post("/api/emi/calculate")
@require_login
def emi_calculator():
    data = request.get_json(silent=True) or {}

    try:
        principal, annual_rate, months = parse_loan_details(data)
        emi = emi_value(
            principal,
            annual_rate,
            months
        )
        total = emi * months

        return jsonify(
            loan_amount=str(rounded(principal)),
            interest_rate=str(annual_rate),
            tenure_months=months,
            monthly_emi=str(rounded(emi)),
            total_interest=str(rounded(total - principal)),
            total_payment=str(rounded(total))
        )

    except ValueError as e:
        return failure(str(e))


# ================= REPAYMENT SCHEDULE =================

def create_schedule(principal_cents, annual_rate, months):
    rate = annual_rate / Decimal("1200")

    exact_emi = emi_value(
        Decimal(principal_cents),
        annual_rate,
        months
    )

    emi_cents = int(
        exact_emi.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )

    remaining = principal_cents
    today = date.today()
    schedule = []

    for number in range(1, months + 1):
        interest = int(
            (Decimal(remaining) * rate).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

        if number == months:
            principal_part = remaining
        else:
            principal_part = min(
                remaining,
                max(0, emi_cents - interest)
            )

        payment = principal_part + interest
        remaining -= principal_part

        month_index = today.month - 1 + number
        year = today.year + month_index // 12
        month = month_index % 12 + 1
        day = min(today.day, monthrange(year, month)[1])

        schedule.append({
            "number": number,
            "due_date": date(year, month, day).isoformat(),
            "amount": payment,
            "principal": principal_part,
            "interest": interest,
            "remaining": remaining
        })

    return emi_cents, schedule


# ================= CREATE LOAN =================

@app.post("/api/loans")
@require_customer
def create_loan():
    data = request.get_json(silent=True) or {}

    try:
        principal, rate, months = parse_loan_details(data)
        principal_cents = money(principal)

        emi, schedule = create_schedule(
            principal_cents,
            rate,
            months
        )

        if emi <= 0 or any(
            item["amount"] <= 0 for item in schedule
        ):
            raise ValueError(
                "Loan too small for selected tenure"
            )

    except ValueError as e:
        return failure(str(e))

    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            account = get_account(db, current())

            if not account or not account["active"]:
                raise ValueError("Account inactive")

            cursor = db.execute("""
                INSERT INTO loans
                (
                    account_number,
                    principal,
                    annual_rate,
                    tenure_months,
                    monthly_emi,
                    status,
                    created
                )
                VALUES(?,?,?,?,?,'PENDING',?)
            """, (
                current(),
                principal_cents,
                str(rate),
                months,
                emi,
                now()
            ))

            loan_id = cursor.lastrowid

            for item in schedule:
                db.execute("""
                    INSERT INTO loan_installments
                    (
                        loan_id,
                        installment_number,
                        due_date,
                        amount,
                        principal_component,
                        interest_component
                    )
                    VALUES(?,?,?,?,?,?)
                """, (
                    loan_id,
                    item["number"],
                    item["due_date"],
                    item["amount"],
                    item["principal"],
                    item["interest"]
                ))

            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(
        ok=True,
        loan_id=loan_id,
        monthly_emi=display(emi),
        installments=months
    ), 201


# ================= LIST CUSTOMER LOANS =================

@app.get("/api/loans")
@require_customer
def list_loans():
    with connection() as db:
        rows = db.execute("""
            SELECT
                l.*,
                COUNT(i.id) AS total_installments,
                COALESCE(SUM(
                    CASE WHEN i.paid=1
                    THEN 1 ELSE 0 END
                ),0) AS paid_installments,
                COALESCE(SUM(
                    CASE WHEN i.paid=0
                    THEN i.principal_component
                    ELSE 0 END
                ),0) AS outstanding_principal
            FROM loans l
            LEFT JOIN loan_installments i
                ON i.loan_id=l.id
            WHERE l.account_number=?
            GROUP BY l.id
            ORDER BY l.id DESC
        """, (current(),)).fetchall()

    return jsonify(items=[
        {
            "id": row["id"],
            "principal": display(row["principal"]),
            "interest_rate": row["annual_rate"],
            "tenure_months": row["tenure_months"],
            "monthly_emi": display(row["monthly_emi"]),
            "status": row["status"],
            "total_installments": row["total_installments"],
            "paid_installments": row["paid_installments"],
            "outstanding_principal": display(
                row["outstanding_principal"]
            )
        }
        for row in rows
    ])


# ================= CUSTOMER LOAN SCHEDULE =================

@app.get("/api/loans/<int:loan_id>/schedule")
@require_customer
def get_loan_schedule(loan_id):
    with connection() as db:
        loan = db.execute("""
            SELECT id FROM loans
            WHERE id=? AND account_number=?
        """, (
            loan_id,
            current()
        )).fetchone()

        if not loan:
            return failure("Loan not found", 404)

        rows = db.execute("""
            SELECT *
            FROM loan_installments
            WHERE loan_id=?
            ORDER BY installment_number
        """, (loan_id,)).fetchall()

    return jsonify(items=[
        {
            "id": row["id"],
            "number": row["installment_number"],
            "due_date": row["due_date"],
            "amount": display(row["amount"]),
            "principal": display(row["principal_component"]),
            "interest": display(row["interest_component"]),
            "paid": bool(row["paid"]),
            "paid_at": row["paid_at"]
        }
        for row in rows
    ])


# ================= PAY EMI =================

@app.post("/api/loans/<int:loan_id>/pay")
@require_customer
def pay_loan_emi(loan_id):
    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")

            loan = db.execute("""
                SELECT *
                FROM loans
                WHERE id=? AND account_number=?
            """, (
                loan_id,
                current()
            )).fetchone()

            if not loan:
                raise ValueError("Loan not found")

            if loan["status"] != "ACTIVE":
                raise ValueError("Loan is not active")

            installment = db.execute("""
                SELECT *
                FROM loan_installments
                WHERE loan_id=? AND paid=0
                ORDER BY installment_number
                LIMIT 1
            """, (loan_id,)).fetchone()

            if not installment:
                raise ValueError(
                    "No pending installments"
                )

            account = get_account(db, current())

            if not account or not account["active"]:
                raise ValueError("Account inactive")

            if account["balance"] < installment["amount"]:
                raise ValueError(
                    "Insufficient balance to pay EMI"
                )

            db.execute("""
                UPDATE accounts
                SET balance=balance-?
                WHERE number=?
            """, (
                installment["amount"],
                current()
            ))

            db.execute("""
                UPDATE loan_installments
                SET paid=1, paid_at=?
                WHERE id=?
            """, (
                now(),
                installment["id"]
            ))

            db.execute("""
                INSERT INTO transactions
                (
                    kind,
                    source,
                    destination,
                    amount,
                    created,
                    note
                )
                VALUES(?,?,?,?,?,?)
            """, (
                "emi_payment",
                current(),
                None,
                installment["amount"],
                now(),
                f"Loan #{loan_id}, EMI "
                f"{installment['installment_number']}"
            ))

            pending = db.execute("""
                SELECT COUNT(*)
                FROM loan_installments
                WHERE loan_id=? AND paid=0
            """, (loan_id,)).fetchone()[0]

            if pending == 0:
                db.execute(
                    """
                    UPDATE loans
                    SET status='COMPLETED'
                    WHERE id=?
                    """,
                    (loan_id,)
                )

            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(
        ok=True,
        loan_id=loan_id,
        installment=installment["installment_number"],
        amount=display(installment["amount"]),
        completed=(pending == 0)
    )


# ================= ADMIN LOAN MANAGEMENT =================

@app.get("/api/admin/loans")
@require_admin
def admin_loans():
    with connection() as db:
        rows = db.execute("""
            SELECT
                l.*,
                a.name AS customer_name,
                COUNT(i.id) AS total_installments,
                COALESCE(SUM(
                    CASE WHEN i.paid=1
                    THEN 1 ELSE 0 END
                ),0) AS paid_installments
            FROM loans l
            JOIN accounts a
                ON a.number=l.account_number
            LEFT JOIN loan_installments i
                ON i.loan_id=l.id
            GROUP BY l.id
            ORDER BY l.id DESC
        """).fetchall()

    return jsonify(items=[
        {
            "id": row["id"],
            "account_number": row["account_number"],
            "customer_name": row["customer_name"],
            "principal": display(row["principal"]),
            "interest_rate": row["annual_rate"],
            "tenure_months": row["tenure_months"],
            "monthly_emi": display(row["monthly_emi"]),
            "status": row["status"],
            "total_installments": row["total_installments"],
            "paid_installments": row["paid_installments"]
        }
        for row in rows
    ])


@app.post("/api/admin/loans/<int:loan_id>/approve")
@require_admin
def approve_loan(loan_id):
    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")

            loan = db.execute(
                "SELECT * FROM loans WHERE id=?",
                (loan_id,)
            ).fetchone()

            if not loan or loan["status"] != "PENDING":
                raise ValueError(
                    "Pending loan not found"
                )

            account = get_account(
                db,
                loan["account_number"]
            )

            if not account or not account["active"]:
                raise ValueError(
                    "Customer account is not active"
                )

            _, schedule = create_schedule(
                loan["principal"],
                Decimal(loan["annual_rate"]),
                loan["tenure_months"]
            )

            for item in schedule:
                db.execute("""
                    UPDATE loan_installments
                    SET due_date=?
                    WHERE loan_id=?
                    AND installment_number=?
                """, (
                    item["due_date"],
                    loan_id,
                    item["number"]
                ))

            db.execute(
                """
                UPDATE loans
                SET status='ACTIVE'
                WHERE id=?
                """,
                (loan_id,)
            )

            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(
        ok=True,
        loan_id=loan_id,
        status="ACTIVE"
    )


@app.post("/api/admin/loans/<int:loan_id>/reject")
@require_admin
def reject_loan(loan_id):
    with LOCK, connection() as db:
        try:
            db.execute("BEGIN IMMEDIATE")

            cursor = db.execute("""
                UPDATE loans
                SET status='REJECTED'
                WHERE id=?
                AND status='PENDING'
            """, (loan_id,))

            if not cursor.rowcount:
                raise ValueError(
                    "Pending loan not found"
                )

            db.commit()

        except (ValueError, sqlite3.Error) as e:
            db.rollback()
            return failure(str(e))

    return jsonify(
        ok=True,
        loan_id=loan_id,
        status="REJECTED"
    )


# ================= START APPLICATION =================

init_db()

if __name__ == "__main__":
    app.run(debug=False, port=5000)
