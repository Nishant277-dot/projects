from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    Response
)

import sqlite3
import pandas as pd
import csv
import io

from functools import wraps
from datetime import datetime
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from sklearn.linear_model import LinearRegression


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "smart-finance-secret-key"

DATABASE = "finance.db"


# ============================================================
# DATABASE
# ============================================================

def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_database():

    db = get_db()

    cursor = db.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)

    # --------------------------------------------------------
    # TRANSACTIONS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            transaction_type TEXT NOT NULL,

            category TEXT NOT NULL,

            amount REAL NOT NULL,

            description TEXT,

            transaction_date TEXT NOT NULL,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)

    # --------------------------------------------------------
    # BUDGETS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            category TEXT NOT NULL,

            amount REAL NOT NULL,

            month TEXT NOT NULL,

            FOREIGN KEY(user_id)
            REFERENCES users(id),

            UNIQUE(
                user_id,
                category,
                month
            )

        )
    """)

    db.commit()

    db.close()


# ============================================================
# LOGIN DECORATOR
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# CURRENT USER
# ============================================================

def current_user():

    if "user_id" not in session:

        return None

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users

        WHERE id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    db.close()

    return user


# ============================================================
# MONTH
# ============================================================

def current_month():

    return datetime.now().strftime(
        "%Y-%m"
    )


# ============================================================
# GET USER TRANSACTIONS
# ============================================================

def get_transactions():

    db = get_db()

    rows = db.execute(
        """
        SELECT *
        FROM transactions

        WHERE user_id = ?

        ORDER BY
            transaction_date DESC,
            id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    db.close()

    return rows


# ============================================================
# ANALYTICS
# ============================================================

def calculate_analytics():

    transactions = get_transactions()

    if not transactions:

        return {

            "income": 0,

            "expense": 0,

            "balance": 0,

            "categories": {},

            "monthly": {},

            "prediction": 0,

            "advice": []

        }

    data = [

        {

            "type":
                row["transaction_type"],

            "category":
                row["category"],

            "amount":
                row["amount"],

            "date":
                row["transaction_date"]

        }

        for row in transactions

    ]

    df = pd.DataFrame(data)

    # --------------------------------------------------------
    # INCOME
    # --------------------------------------------------------

    income = df.loc[
        df["type"] == "income",
        "amount"
    ].sum()

    # --------------------------------------------------------
    # EXPENSE
    # --------------------------------------------------------

    expense = df.loc[
        df["type"] == "expense",
        "amount"
    ].sum()

    # --------------------------------------------------------
    # BALANCE
    # --------------------------------------------------------

    balance = income - expense

    # --------------------------------------------------------
    # CATEGORY ANALYSIS
    # --------------------------------------------------------

    expense_df = df[
        df["type"] == "expense"
    ]

    categories = (

        expense_df
        .groupby("category")["amount"]
        .sum()
        .sort_values(
            ascending=False
        )
        .to_dict()

    )

    # --------------------------------------------------------
    # MONTHLY ANALYSIS
    # --------------------------------------------------------

    df["month"] = pd.to_datetime(
        df["date"]
    ).dt.strftime(
        "%Y-%m"
    )

    monthly_expense = (

        expense_df
        .assign(
            month=pd.to_datetime(
                expense_df["date"]
            ).dt.strftime(
                "%Y-%m"
            )
        )
        .groupby("month")["amount"]
        .sum()
        .sort_index()

    )

    monthly = {

        month: round(
            amount,
            2
        )

        for month, amount
        in monthly_expense.items()

    }

    # --------------------------------------------------------
    # EXPENSE PREDICTION
    # --------------------------------------------------------

    prediction = 0

    if len(monthly_expense) >= 2:

        values = monthly_expense.values

        X = pd.DataFrame(
            {
                "month_number":
                    range(
                        1,
                        len(values) + 1
                    )
            }
        )

        y = values

        model = LinearRegression()

        model.fit(
            X,
            y
        )

        next_month = model.predict(
            [
                [
                    len(values) + 1
                ]
            ]
        )[0]

        prediction = max(
            0,
            round(
                float(next_month),
                2
            )
        )

    elif len(monthly_expense) == 1:

        prediction = round(
            float(
                monthly_expense.iloc[0]
            ),
            2
        )

    # --------------------------------------------------------
    # FINANCIAL ADVICE
    # --------------------------------------------------------

    advice = []

    if income > 0:

        saving_rate = (
            balance
            /
            income
            *
            100
        )

    else:

        saving_rate = 0

    if saving_rate < 10:

        advice.append(
            "Your saving rate is low. "
            "Try reducing unnecessary expenses."
        )

    elif saving_rate >= 30:

        advice.append(
            "Excellent saving rate. "
            "Continue maintaining this habit."
        )

    else:

        advice.append(
            "Your saving rate is moderate. "
            "Look for areas where you can save more."
        )

    if categories:

        highest_category = max(
            categories,
            key=categories.get
        )

        advice.append(
            f"Your highest spending category "
            f"is {highest_category}."
        )

    if prediction > 0:

        advice.append(
            f"Estimated next-month spending "
            f"is approximately ₹{prediction:,.0f}."
        )

    return {

        "income":
            round(
                float(income),
                2
            ),

        "expense":
            round(
                float(expense),
                2
            ),

        "balance":
            round(
                float(balance),
                2
            ),

        "categories":
            categories,

        "monthly":
            monthly,

        "prediction":
            prediction,

        "advice":
            advice

    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    if "user_id" in session:

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=[
        "GET",
        "POST"
    ]
)
def register():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        email = request.form[
            "email"
        ].strip()

        password = request.form[
            "password"
        ]

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        db = get_db()

        try:

            db.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password
                )

                VALUES (?, ?, ?)
                """,
                (
                    username,
                    email,
                    generate_password_hash(
                        password
                    )
                )
            )

            db.commit()

            flash(
                "Account created successfully.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Username or email already exists.",
                "error"
            )

        finally:

            db.close()

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=[
        "GET",
        "POST"
    ]
)
def login():

    if request.method == "POST":

        username = request.form[
            "username"
        ]

        password = request.form[
            "password"
        ]

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users

            WHERE username = ?
            """,
            (
                username,
            )
        ).fetchone()

        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session[
                "user_id"
            ] = user["id"]

            session[
                "username"
            ] = user["username"]

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    analytics = calculate_analytics()

    return render_template(

        "dashboard.html",

        analytics=analytics,

        username=session[
            "username"
        ]

    )


# ============================================================
# ADD TRANSACTION
# ============================================================

@app.route(
    "/transaction/add",
    methods=["POST"]
)
@login_required
def add_transaction():

    transaction_type = request.form[
        "transaction_type"
    ]

    category = request.form[
        "category"
    ]

    amount = float(
        request.form[
            "amount"
        ]
    )

    description = request.form.get(
        "description",
        ""
    )

    transaction_date = request.form[
        "transaction_date"
    ]

    if amount <= 0:

        flash(
            "Amount must be greater than zero.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    db = get_db()

    db.execute(
        """
        INSERT INTO transactions
        (
            user_id,
            transaction_type,
            category,
            amount,
            description,
            transaction_date
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            transaction_type,
            category,
            amount,
            description,
            transaction_date
        )
    )

    db.commit()

    db.close()

    flash(
        "Transaction added.",
        "success"
    )

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# TRANSACTIONS
# ============================================================

@app.route("/transactions")
@login_required
def transactions():

    rows = get_transactions()

    return render_template(
        "transactions.html",
        transactions=rows
    )


# ============================================================
# DELETE TRANSACTION
# ============================================================

@app.route(
    "/transaction/delete/<int:transaction_id>"
)
@login_required
def delete_transaction(
    transaction_id
):

    db = get_db()

    db.execute(
        """
        DELETE FROM transactions

        WHERE id = ?

        AND user_id = ?
        """,
        (
            transaction_id,
            session["user_id"]
        )
    )

    db.commit()

    db.close()

    flash(
        "Transaction deleted.",
        "success"
    )

    return redirect(
        url_for("transactions")
    )


# ============================================================
# BUDGET PAGE
# ============================================================

@app.route("/budget")
@login_required
def budget():

    db = get_db()

    month = current_month()

    budgets = db.execute(
        """
        SELECT *
        FROM budgets

        WHERE user_id = ?

        AND month = ?

        ORDER BY category
        """,
        (
            session["user_id"],
            month
        )
    ).fetchall()

    db.close()

    # --------------------------------------------------------
    # CURRENT MONTH EXPENSES
    # --------------------------------------------------------

    transactions = get_transactions()

    category_spending = {}

    for transaction in transactions:

        if (
            transaction["transaction_type"]
            == "expense"
            and
            transaction["transaction_date"]
            .startswith(month)
        ):

            category = transaction[
                "category"
            ]

            category_spending[
                category
            ] = (
                category_spending.get(
                    category,
                    0
                )
                +
                transaction["amount"]
            )

    return render_template(

        "budget.html",

        budgets=budgets,

        category_spending=
            category_spending,

        month=month

    )


# ============================================================
# ADD BUDGET
# ============================================================

@app.route(
    "/budget/add",
    methods=["POST"]
)
@login_required
def add_budget():

    category = request.form[
        "category"
    ]

    amount = float(
        request.form[
            "amount"
        ]
    )

    month = request.form[
        "month"
    ]

    db = get_db()

    try:

        db.execute(
            """
            INSERT INTO budgets
            (
                user_id,
                category,
                amount,
                month
            )

            VALUES (?, ?, ?, ?)

            ON CONFLICT(
                user_id,
                category,
                month
            )

            DO UPDATE SET
                amount = excluded.amount
            """,
            (
                session["user_id"],
                category,
                amount,
                month
            )
        )

        db.commit()

        flash(
            "Budget saved.",
            "success"
        )

    except sqlite3.Error as error:

        flash(
            f"Could not save budget: {error}",
            "error"
        )

    finally:

        db.close()

    return redirect(
        url_for("budget")
    )


# ============================================================
# EXPORT CSV
# ============================================================

@app.route("/export")
@login_required
def export_csv():

    rows = get_transactions()

    output = io.StringIO()

    writer = csv.writer(
        output
    )

    writer.writerow(
        [
            "Date",
            "Type",
            "Category",
            "Amount",
            "Description"
        ]
    )

    for row in rows:

        writer.writerow(
            [
                row["transaction_date"],
                row["transaction_type"],
                row["category"],
                row["amount"],
                row["description"]
            ]
        )

    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )

    response.headers[
        "Content-Disposition"
    ] = (
        "attachment; "
        "filename=transactions.csv"
    )

    return response


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    init_database()

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )