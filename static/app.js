
/*
 SDFC FINANCE
 Banking and Financial Management System

 Admin and Customer Dashboard
 Transaction History in Indian Standard Time (IST)
 Educational Demonstration
*/

// ================= BASIC HELPERS =================

const $ = (id) => document.getElementById(id);

let userRole = null;
let customerAccount = null;

const headings = {
    overview: "Overview Dashboard",
    emi: "EMI Calculator",
    loans: "My Loans",
    schedule: "Repayment Schedule",
    transfer: "Transfer Money",
    cash: "Deposit / Withdraw",
    profile: "My Account Profile",
    history: "My Transactions",
    accounts: "Manage Customer Accounts",
    adminLoans: "Manage Loan Applications",
    adminHistory: "All Transactions",
    audit: "Financial Integrity Check"
};

function rupees(value) {
    return "₹" + Number(value || 0).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// ================= UTC TO IST CONVERSION =================

function formatIST(utcTime) {
    if (!utcTime) {
        return "—";
    }

    const date = new Date(utcTime);

    if (Number.isNaN(date.getTime())) {
        return String(utcTime);
    }

    return new Intl.DateTimeFormat("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
    }).format(date);
}

// Change table heading UTC to IST.
function updateTimeHeaders() {
    document.querySelectorAll(
        "#history th:last-child, #adminHistory th:last-child"
    ).forEach((heading) => {
        heading.textContent = "Date & Time (IST)";
    });
}

function setText(id, value) {
    const element = $(id);

    if (element) {
        element.textContent = value;
    }
}

async function api(path, method = "GET", data = undefined) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "same-origin"
    };

    if (data !== undefined) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch("/api/" + path, options);

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error("Unable to read server response");
    }

    if (!response.ok) {
        throw new Error(
            result.error || "Request failed"
        );
    }

    return result;
}

function notify(message, error = false) {
    const status = $("status");

    if (!status) return;

    status.textContent = message;
    status.style.color = error ? "#ff8080" : "#30d5c8";
}

function loginMessage(message, error = false) {
    let box = $("loginMessage");

    if (!box) {
        box = document.createElement("p");
        box.id = "loginMessage";
        $("loginForm").after(box);
    }

    box.textContent = message;
    box.style.marginTop = "12px";
    box.style.color = error ? "#ff8080" : "#30d5c8";
}


// ================= LOGIN ROLE SELECTION =================

function selectLoginRole(role) {
    if (role !== "ADMIN" && role !== "CUSTOMER") {
        return;
    }

    $("loginRole").value = role;

    $("customerLoginFields").hidden = role !== "CUSTOMER";
    $("adminLoginFields").hidden = role !== "ADMIN";

    $("customerRoleBtn").classList.toggle(
        "selected",
        role === "CUSTOMER"
    );

    $("adminRoleBtn").classList.toggle(
        "selected",
        role === "ADMIN"
    );

    loginMessage("");
}


// ================= ROLE VISIBILITY =================

function updateRoleVisibility() {
    document.querySelectorAll("[data-role]").forEach((element) => {
        element.hidden = element.dataset.role !== userRole;
    });

    $("roleLabel").hidden = !userRole;

    if (userRole === "ADMIN") {
        setText("roleLabel", "BANK ADMIN");
        setText("balanceLabel", "Total Customer Funds");
        setText(
            "balanceDescription",
            "Combined demo account balances"
        );
        setText(
            "welcomeTitle",
            "Welcome, Bank Administrator"
        );
        setText(
            "welcomeDescription",
            "Manage customer accounts, review loan applications, approve or reject loans, monitor transactions and verify financial records."
        );
    } else if (userRole === "CUSTOMER") {
        setText("roleLabel", "CUSTOMER");
        setText("balanceLabel", "Available Balance");
        setText(
            "balanceDescription",
            "Your demo account balance"
        );
        setText(
            "welcomeTitle",
            "Welcome to SDFC Finance"
        );
        setText(
            "welcomeDescription",
            "Access banking services, calculate EMIs, apply for loans, track repayment schedules and pay installments."
        );
    }
}


// ================= PAGE NAVIGATION =================

function show(id, skipLoad = false) {
    if (!userRole) return;

    const target = $(id);

    if (!target || !target.classList.contains("view")) {
        return;
    }

    const requiredRole = target.dataset.role;

    if (requiredRole && requiredRole !== userRole) {
        notify("You do not have permission to open this page", true);
        return;
    }

    document.querySelectorAll(".view").forEach((view) => {
        view.hidden = view.id !== id;
    });

    setText("heading", headings[id] || "SDFC Finance");

    document.querySelectorAll(".nav button").forEach((button) => {
        const action = button.getAttribute("onclick") || "";

        button.classList.toggle(
            "active",
            action === `show('${id}')`
        );
    });

    notify("");

    if (skipLoad) return;

    if (id === "overview") refreshOverview();
    if (id === "loans") loadLoans();
    if (id === "schedule") loadLoanOptions();
    if (id === "history") loadHistory();
    if (id === "accounts") loadAdminAccounts();
    if (id === "adminLoans") loadAdminLoans();
    if (id === "adminHistory") loadAdminHistory();
}


// ================= AUTHENTICATION =================

$("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = Object.fromEntries(
        new FormData(event.target)
    );

    try {
        loginMessage("Signing in...");

        await api("login", "POST", data);
        await refresh();

        loginMessage("");
    } catch (error) {
        loginMessage(error.message, true);
    }
});

async function refresh() {
    try {
        const result = await api("me");

        userRole = result.role;
        customerAccount = result.account || null;

        $("login").hidden = true;
        $("private").hidden = false;

        if (userRole === "ADMIN") {
            setText(
                "user",
                "Admin: " + result.admin.username
            );
        } else {
            setText(
                "user",
                result.account.name + " • " +
                result.account.number
            );

            setText("profileNumber", result.account.number);
            setText("profileName", result.account.name);
        }

        updateRoleVisibility();
        updateTimeHeaders();
        show("overview");

    } catch {
        userRole = null;
        customerAccount = null;

        $("login").hidden = false;
        $("private").hidden = true;
        $("roleLabel").hidden = true;

        setText("heading", "Welcome to SDFC Finance");
        setText("user", "Welcome");
    }
}

async function logout() {
    try {
        await api("logout", "POST");

        userRole = null;
        customerAccount = null;

        $("private").hidden = true;
        $("login").hidden = false;
        $("roleLabel").hidden = true;

        setText("user", "Welcome");
        setText("heading", "Welcome to SDFC Finance");

        loginMessage("Signed out successfully");
    } catch (error) {
        notify(error.message, true);
    }
}


// ================= DASHBOARD OVERVIEW =================

async function refreshOverview() {
    try {
        const result = await api("overview");

        setText("balance", rupees(result.total_funds));
        setText("totalLoans", result.total_loans);
        setText("activeLoans", result.active_loans);
        setText("txcount", result.transactions);
    } catch (error) {
        notify(error.message, true);
    }
}


// ================= FORM HELPER =================

function setupForm(id, path, method = "POST", after = null) {
    const form = $(id);

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const data = Object.fromEntries(
            new FormData(form)
        );

        try {
            const result = await api(path, method, data);

            if (after) {
                await after(result);
            } else {
                await refreshOverview();
            }

            notify("Operation completed successfully");

            if (id === "createForm") {
                form.reset();
                notify(
                    "Customer account created: " + result.number
                );
            }
        } catch (error) {
            notify(error.message, true);
        }
    });
}


// ================= CUSTOMER BANKING =================

setupForm("transferForm", "transfer");
setupForm("depositForm", "deposit");
setupForm("withdrawForm", "withdraw");

setupForm(
    "updateForm",
    "account",
    "PATCH",
    async () => {
        const result = await api("me");

        customerAccount = result.account;

        setText(
            "user",
            result.account.name + " • " +
            result.account.number
        );

        setText("profileName", result.account.name);
    }
);


// ================= EMI CALCULATOR =================

$("emiForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = Object.fromEntries(
        new FormData(event.target)
    );

    try {
        const result = await api(
            "emi/calculate",
            "POST",
            data
        );

        setText("emiMonthly", rupees(result.monthly_emi));
        setText("emiPrincipal", rupees(result.loan_amount));
        setText("emiInterest", rupees(result.total_interest));
        setText("emiTotal", rupees(result.total_payment));

        notify("EMI calculated successfully");
    } catch (error) {
        notify(error.message, true);
    }
});


// ================= TABLE HELPERS =================

function clearTable(id) {
    const table = $(id);

    if (table) {
        table.replaceChildren();
    }

    return table;
}

function cell(row, value) {
    const td = document.createElement("td");

    td.textContent =
        value === null || value === undefined
            ? "—"
            : String(value);

    row.appendChild(td);
    return td;
}

function createButton(label, action, danger = false) {
    const button = document.createElement("button");

    button.type = "button";
    button.textContent = label;

    if (danger) {
        button.classList.add("danger");
    }

    button.addEventListener("click", action);

    return button;
}

function emptyRow(table, columns, message) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");

    td.colSpan = columns;
    td.textContent = message;
    td.style.textAlign = "center";
    td.style.padding = "20px";

    tr.appendChild(td);
    table.appendChild(tr);
}


// ================= APPLY FOR LOAN =================

$("loanForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = Object.fromEntries(
        new FormData(event.target)
    );

    try {
        const result = await api("loans", "POST", data);

        await loadLoans();
        await refreshOverview();

        notify(
            "Loan #" + result.loan_id +
            " submitted successfully. Waiting for Admin approval."
        );
    } catch (error) {
        notify(error.message, true);
    }
});


// ================= CUSTOMER LOAN RECORDS =================

async function loadLoans() {
    if (userRole !== "CUSTOMER") return;

    try {
        const result = await api("loans");
        const table = clearTable("loanRows");

        if (!result.items.length) {
            emptyRow(table, 8, "No loan applications found");
            return;
        }

        result.items.forEach((loan) => {
            const tr = document.createElement("tr");

            cell(tr, "#" + loan.id);
            cell(tr, rupees(loan.principal));
            cell(tr, loan.interest_rate + "%");
            cell(tr, rupees(loan.monthly_emi));

            cell(
                tr,
                loan.paid_installments +
                " / " +
                loan.total_installments
            );

            cell(
                tr,
                rupees(loan.outstanding_principal)
            );

            const status = cell(tr, loan.status);
            status.classList.add("status-pill");

            if (loan.status === "ACTIVE") {
                status.style.color = "#30d5c8";
            } else if (loan.status === "PENDING") {
                status.style.color = "#ffcb70";
            } else if (loan.status === "REJECTED") {
                status.style.color = "#ff8080";
            }

            const actions = document.createElement("td");
            actions.classList.add("admin-actions");

            actions.appendChild(
                createButton(
                    "Schedule",
                    () => openSchedule(loan.id)
                )
            );

            if (loan.status === "ACTIVE") {
                actions.appendChild(
                    createButton(
                        "Pay EMI",
                        () => payEmi(loan.id)
                    )
                );
            }

            tr.appendChild(actions);
            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= LOAN REPAYMENT SCHEDULE =================

async function loadLoanOptions(selectedId = "") {
    if (userRole !== "CUSTOMER") return;

    try {
        const result = await api("loans");
        const select = $("scheduleLoanSelect");
        const previous = selectedId || select.value;

        select.replaceChildren();

        const placeholder = document.createElement("option");

        placeholder.value = "";
        placeholder.textContent = "Choose a loan";

        select.appendChild(placeholder);

        result.items.forEach((loan) => {
            const option = document.createElement("option");

            option.value = loan.id;

            option.textContent =
                "Loan #" + loan.id +
                " • " + rupees(loan.principal) +
                " • " + loan.status;

            select.appendChild(option);
        });

        if (
            previous &&
            [...select.options].some(
                (option) => option.value === String(previous)
            )
        ) {
            select.value = String(previous);
        }

    } catch (error) {
        notify(error.message, true);
    }
}

async function openSchedule(loanId) {
    show("schedule", true);

    await loadLoanOptions(loanId);
    await loadSelectedSchedule();
}

async function loadSelectedSchedule() {
    if (userRole !== "CUSTOMER") return;

    const loanId = $("scheduleLoanSelect").value;

    if (!loanId) {
        notify("Please select a loan", true);
        return;
    }

    try {
        const result = await api(
            "loans/" + loanId + "/schedule"
        );

        const table = clearTable("scheduleRows");

        setText(
            "scheduleTitle",
            "Repayment Schedule — Loan #" + loanId
        );

        if (!result.items.length) {
            emptyRow(table, 6, "No installments found");
            return;
        }

        result.items.forEach((item) => {
            const tr = document.createElement("tr");

            cell(tr, item.number);
            cell(tr, item.due_date);
            cell(tr, rupees(item.amount));
            cell(tr, rupees(item.principal));
            cell(tr, rupees(item.interest));

            const status = cell(
                tr,
                item.paid ? "✓ PAID" : "PENDING"
            );

            status.style.color =
                item.paid ? "#30d5c8" : "#ffcb70";

            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= PAY EMI =================

async function payEmi(loanId) {
    if (userRole !== "CUSTOMER") return;

    if (!confirm(
        "Pay the next EMI for Loan #" + loanId + "?"
    )) {
        return;
    }

    try {
        const result = await api(
            "loans/" + loanId + "/pay",
            "POST"
        );

        await loadLoans();
        await refreshOverview();

        if (result.completed) {
            notify(
                "EMI paid successfully. Loan completed!"
            );
        } else {
            notify(
                "EMI #" + result.installment +
                " paid successfully: " +
                rupees(result.amount)
            );
        }

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= CUSTOMER TRANSACTION HISTORY =================

async function loadHistory() {
    if (userRole !== "CUSTOMER") return;

    try {
        const result = await api("history");
        const table = clearTable("historyRows");

        if (!result.items.length) {
            emptyRow(table, 6, "No transactions found");
            return;
        }

        result.items.forEach((item) => {
            const tr = document.createElement("tr");

            cell(tr, item.id);
            cell(tr, item.kind);
            cell(tr, item.source);
            cell(tr, item.destination);
            cell(tr, rupees(item.amount));

            // Display UTC timestamp as Indian Standard Time.
            cell(tr, formatIST(item.created));

            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: MANAGE ACCOUNTS =================

async function loadAdminAccounts() {
    if (userRole !== "ADMIN") return;

    try {
        const result = await api("admin/accounts");
        const table = clearTable("accountRows");

        if (!result.items.length) {
            emptyRow(table, 5, "No customer accounts found");
            return;
        }

        result.items.forEach((account) => {
            const tr = document.createElement("tr");

            cell(tr, account.number);
            cell(tr, account.name);
            cell(tr, rupees(account.balance));

            const status = cell(
                tr,
                account.active ? "ACTIVE" : "INACTIVE"
            );

            status.style.color =
                account.active ? "#30d5c8" : "#ff8080";

            cell(tr, account.created);

            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: CREATE ACCOUNT =================

setupForm(
    "createForm",
    "accounts",
    "POST",
    async () => {
        await loadAdminAccounts();
        await refreshOverview();
    }
);


// ================= ADMIN: UPDATE ACCOUNT =================

$("adminUpdateForm").addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const data = Object.fromEntries(
            new FormData(event.target)
        );

        const number = data.number.trim();

        try {
            await api(
                "admin/accounts/" + encodeURIComponent(number),
                "PATCH",
                { name: data.name }
            );

            await loadAdminAccounts();

            notify(
                "Customer account updated successfully"
            );

        } catch (error) {
            notify(error.message, true);
        }
    }
);


// ================= ADMIN: DEACTIVATE ACCOUNT =================

$("adminDeactivateForm").addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const data = Object.fromEntries(
            new FormData(event.target)
        );

        const number = data.number.trim();

        if (!confirm(
            "Deactivate customer account " + number + "?"
        )) {
            return;
        }

        try {
            await api(
                "deactivate",
                "POST",
                { number }
            );

            await loadAdminAccounts();
            await refreshOverview();

            notify(
                "Customer account deactivated successfully"
            );

        } catch (error) {
            notify(error.message, true);
        }
    }
);


// ================= ADMIN: VIEW LOANS =================

async function loadAdminLoans() {
    if (userRole !== "ADMIN") return;

    try {
        const result = await api("admin/loans");
        const table = clearTable("adminLoanRows");

        if (!result.items.length) {
            emptyRow(table, 8, "No loan applications found");
            return;
        }

        result.items.forEach((loan) => {
            const tr = document.createElement("tr");

            cell(tr, "#" + loan.id);
            cell(tr, loan.customer_name);
            cell(tr, loan.account_number);
            cell(tr, rupees(loan.principal));
            cell(tr, loan.interest_rate + "%");
            cell(tr, rupees(loan.monthly_emi));

            const status = cell(tr, loan.status);

            if (loan.status === "PENDING") {
                status.style.color = "#ffcb70";
            } else if (loan.status === "ACTIVE") {
                status.style.color = "#30d5c8";
            } else if (loan.status === "REJECTED") {
                status.style.color = "#ff8080";
            }

            const actions = document.createElement("td");
            actions.classList.add("admin-actions");

            if (loan.status === "PENDING") {
                actions.appendChild(
                    createButton(
                        "Approve",
                        () => approveLoan(loan.id)
                    )
                );

                actions.appendChild(
                    createButton(
                        "Reject",
                        () => rejectLoan(loan.id),
                        true
                    )
                );
            } else {
                actions.textContent = "—";
            }

            tr.appendChild(actions);
            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: APPROVE LOAN =================

async function approveLoan(loanId) {
    if (userRole !== "ADMIN") return;

    if (!confirm("Approve Loan #" + loanId + "?")) {
        return;
    }

    try {
        await api(
            "admin/loans/" + loanId + "/approve",
            "POST"
        );

        await loadAdminLoans();
        await refreshOverview();

        notify(
            "Loan #" + loanId + " approved successfully"
        );

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: REJECT LOAN =================

async function rejectLoan(loanId) {
    if (userRole !== "ADMIN") return;

    if (!confirm("Reject Loan #" + loanId + "?")) {
        return;
    }

    try {
        await api(
            "admin/loans/" + loanId + "/reject",
            "POST"
        );

        await loadAdminLoans();
        await refreshOverview();

        notify(
            "Loan #" + loanId + " rejected"
        );

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: TRANSACTIONS =================

async function loadAdminHistory() {
    if (userRole !== "ADMIN") return;

    try {
        const result = await api("admin/history");
        const table = clearTable("adminHistoryRows");

        if (!result.items.length) {
            emptyRow(table, 6, "No transaction records found");
            return;
        }

        result.items.forEach((item) => {
            const tr = document.createElement("tr");

            cell(tr, item.id);
            cell(tr, item.kind);
            cell(tr, item.source);
            cell(tr, item.destination);
            cell(tr, rupees(item.amount));

            // Display UTC timestamp as Indian Standard Time.
            cell(tr, formatIST(item.created));

            table.appendChild(tr);
        });

    } catch (error) {
        notify(error.message, true);
    }
}


// ================= ADMIN: INTEGRITY CHECK =================

async function runAudit() {
    if (userRole !== "ADMIN") {
        notify("Admin access required", true);
        return;
    }

    const container = $("auditResult");

    container.textContent = "Running integrity checks...";

    try {
        const result = await api("audit");

        const checks = [
            {
                title: "Account Balance Check",
                description: "No negative account balances",
                count: result.negative_balances
            },
            {
                title: "Transaction Reference Check",
                description: "No orphan transaction references",
                count: result.orphan_references
            },
            {
                title: "Loan Reference Check",
                description: "No invalid loan account references",
                count: result.invalid_loans
            }
        ];

        const lines = [
            "SDFC FINANCE",
            "FINANCIAL INTEGRITY REPORT",
            "----------------------------------------",
            ""
        ];

        checks.forEach((check, index) => {
            const passed = check.count === 0;

            lines.push(
                (index + 1) + ". " + check.title
            );

            lines.push(
                "   " + (passed ? "✓ PASS" : "✗ FAIL")
            );

            lines.push(
                "   " + check.description
            );

            lines.push(
                "   Issues found: " + check.count
            );

            lines.push("");
        });

        const passed =
            result.passed === true &&
            checks.every((check) => check.count === 0);

        lines.push("----------------------------------------");

        lines.push(
            "OVERALL STATUS: " +
            (passed ? "PASSED" : "FAILED")
        );

        lines.push(
            passed
                ? "All implemented integrity checks passed."
                : "One or more integrity checks failed."
        );

        container.textContent = lines.join("\n");
        container.style.whiteSpace = "pre-wrap";
        container.style.fontFamily = "inherit";
        container.style.lineHeight = "1.9";
        container.style.color =
            passed ? "#30d5c8" : "#ff8080";

        notify(
            passed
                ? "Integrity checks completed successfully"
                : "Integrity issues detected",
            !passed
        );

    } catch (error) {
        container.textContent =
            "Unable to run integrity check";

        notify(error.message, true);
    }
}


// ================= START APPLICATION =================

updateTimeHeaders();
selectLoginRole("CUSTOMER");
refresh();
