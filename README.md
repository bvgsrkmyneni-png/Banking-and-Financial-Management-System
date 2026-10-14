# FinCore — Banking Transaction Management System

**Educational simulator only.** No real bank connectivity, real transfers, KYC, payment rails, or production-grade security.

## Run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5000**. Demo login **10010001 / 1234**; destination **10010002**. Sample accounts are seeded automatically in `bank.db`.

## Tests

```bash
pytest -q
```

## Features

- Account validation with PBKDF2 hashed demo PINs
- Balance enquiry, deposits, withdrawals, transfers
- Account creation, update and zero-balance deactivation
- Transaction history, dashboard metrics, integrity audit
- SQLite `BEGIN IMMEDIATE` atomic transaction boundaries and thread lock
- Decimal-to-integer paise validation; no floating-point money
- Flask JSON API and responsive HTML/CSS/JavaScript interface

## Six academic components

1. **Computational thinking:** decomposition, validation, transaction flow, algorithm complexity.
2. **Python & data structures:** dictionaries, SQLite tables, comprehensions, context managers, decorators.
3. **Software design:** service functions, modular route handlers, abstraction and reusable helpers.
4. **Functional & concurrency:** pure `money`, `display`, `hash_pin`; database atomicity and thread synchronization.
5. **Quality & DevOps:** pytest, CI workflow, integrity checks, linting.
6. **AI-assisted engineering:** specification-first prompts, manual security review, tests and disclosure.

## Important limits

This project is **not** safe for public deployment. It lacks CSRF protection, brute-force throttling, account-level authorization for administrative account creation, strong user identity verification, password reset and production secrets management. Do not expose it on the internet. Do not use real personal or financial data.
