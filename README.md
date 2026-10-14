# BANKING AND FINANCIAL MANAGEMENT SYSTEM

### SDFC Finance — Smart Digital Finance Corporation

**A Python Flask-based Banking and Financial Management System with Admin and Customer dashboards, banking transactions, EMI calculations, loan approvals, repayment tracking, and SQLite database integration.**

**Educational Project:** This application simulates banking operations and does not process real financial transactions.

---

## Project Information

- **Project Title:** Banking and Financial Management System
- **Project Name:** SDFC Finance
- **Developed By:** M. Bvg Shivaramakrishna
- **Registration Number:** 2601150039
- **Course:** 26CS5101E – Computational Thinking and Programming
- **Department:** Artificial Intelligence and Data Science
- **University:** K L University
- **Academic Year:** 2026–2027

## Technologies Used

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Authentication:** PIN/password hashing and Flask sessions
- **Financial Calculations:** Python Decimal
- **Time Zone:** Indian Standard Time (IST)

## Main Features

### 1. Admin Dashboard

- Separate Admin authentication
- Create and manage customer accounts
- Update customer information
- Deactivate eligible customer accounts
- Review loan applications
- Approve or reject loans
- View banking transaction records
- Run basic financial integrity checks

### 2. Customer Dashboard

- Customer authentication using account number and PIN
- Check account balance
- Deposit and withdraw demonstration funds
- Transfer money between customer accounts
- Update account profile
- Calculate monthly loan EMI
- Apply for new loans
- View loan application status
- View repayment schedules
- Pay monthly EMIs
- Track outstanding loan amounts
- View transaction history in IST

## How to Run the Project

**Step 1: Clone the Repository**

`git clone https://github.com/bvgsrkmyneni-png/Banking-and-Financial-Management-System.git`

**Step 2: Open the Project Folder**

`cd Banking-and-Financial-Management-System`

**Step 3: Create a Virtual Environment**

`python -m venv .venv`

**Step 4: Activate the Virtual Environment**

Windows PowerShell:

`.venv\Scripts\Activate.ps1`

Windows Command Prompt:

`.venv\Scripts\activate.bat`

**Step 5: Install Dependencies**

`python -m pip install -r requirements.txt`

**Step 6: Run the Application**

`python app.py`

**Step 7: Open the Dashboard**

http://127.0.0.1:5000

## Application Workflow

1. The user opens the SDFC Finance application.
2. The user selects Admin or Customer Login.
3. Flask validates login credentials.
4. The application displays the appropriate dashboard.
5. Customers perform banking operations or submit loan applications.
6. Admin reviews pending loan applications.
7. Approved loans become active, enabling EMI payments.
8. Each successful EMI payment updates the repayment schedule and customer account balance.
9. SQLite maintains account, loan, installment, and transaction records.
10. The dashboard displays updated information and transaction timestamps in IST.

## Loan EMI Calculation

The system calculates EMI using the fixed-rate reducing-balance formula:

**EMI = P × r × (1 + r)^n / [(1 + r)^n − 1]**

Where:

- P = Principal amount
- r = Monthly interest rate
- n = Number of monthly installments

The system also calculates total interest and total repayment amounts.

## Database Management

The application uses SQLite with the following main tables:

- `accounts` — Customer account details and balances
- `admins` — Administrator authentication records
- `transactions` — Banking operations and EMI payment history
- `loans` — Customer loan applications and approval status
- `loan_installments` — EMI schedules and payment records

A local demonstration database is created automatically when the application starts. The database is excluded from GitHub tracking.

## Six Academic Components

1. **Computational Thinking:** Problem decomposition, banking transaction logic, input validation, and EMI algorithms.
2. **Python and Data Structures:** Python functions, dictionaries, lists, SQLite tables, decorators, and context managers.
3. **Software Design and Engineering:** Flask routes, modular backend functions, authentication, role-based permissions, and database design.
4. **Functional Programming and Concurrency:** Reusable calculations, Decimal arithmetic, SQLite atomic transactions, and thread synchronization.
5. **Software Quality and DevOps:** Input validation, transaction integrity checks, testing, version control, and GitHub Actions configuration.
6. **AI-Assisted Software Engineering:** AI-assisted development, code review, debugging, documentation, and manual verification.

## Testing

The application has been manually tested for major banking, authentication, and loan workflows.

A test suite is included in the repository and can be executed with:

`python -m pytest -q`

The automated tests should be reviewed and updated to match the final Admin/Customer implementation before relying on their results.

## Limitations

- Educational simulation only
- No real bank connectivity or payment gateway
- No real KYC verification
- No actual loan disbursement
- No production-grade fraud detection