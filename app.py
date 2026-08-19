from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

import sqlite3
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Change this before deploying online
app.secret_key = "change-this-secret-key"

DATABASE = "campus.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():

    connection = get_db()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT NOT NULL DEFAULT 'student'

        )
    """)

    # --------------------------------------------------------
    # STUDENTS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            department TEXT NOT NULL,

            year INTEGER NOT NULL,

            attendance REAL DEFAULT 0,

            cgpa REAL DEFAULT 0,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
    """)

    # --------------------------------------------------------
    # MARKS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            subject TEXT NOT NULL,

            marks REAL NOT NULL,

            FOREIGN KEY(student_id)
            REFERENCES students(id)

        )
    """)

    # --------------------------------------------------------
    # ATTENDANCE TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            student_id INTEGER NOT NULL,

            subject TEXT NOT NULL,

            attended INTEGER NOT NULL,

            total INTEGER NOT NULL,

            FOREIGN KEY(student_id)
            REFERENCES students(id)

        )
    """)

    # --------------------------------------------------------
    # EVENTS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT,

            event_date TEXT NOT NULL

        )
    """)

    # --------------------------------------------------------
    # NOTICES TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            content TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
    """)

    # ========================================================
    # CREATE ADMIN ACCOUNT
    # ========================================================

    admin = cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        cursor.execute(
            """
            INSERT INTO users
            (username, password, role)

            VALUES (?, ?, ?)
            """,
            (
                "admin",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    # ========================================================
    # CREATE DEMO STUDENT
    # ========================================================

    student_user = cursor.execute(
        "SELECT id FROM users WHERE username = ?",
        ("student",)
    ).fetchone()

    if student_user is None:

        student_user_id = cursor.execute(
            """
            INSERT INTO users
            (username, password, role)

            VALUES (?, ?, ?)
            """,
            (
                "student",
                generate_password_hash("student123"),
                "student"
            )
        ).lastrowid

        cursor.execute(
            """
            INSERT INTO students
            (
                user_id,
                name,
                email,
                department,
                year,
                attendance,
                cgpa
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_user_id,
                "Demo Student",
                "student@campus.local",
                "Artificial Intelligence & Data Science",
                1,
                87.5,
                8.6
            )
        )

        student_id = cursor.lastrowid

        # Sample marks

        sample_marks = [

            ("Python", 88),

            ("Data Science", 82),

            ("Mathematics", 91),

            ("Programming", 86),

            ("Communication", 78)

        ]

        for subject, marks in sample_marks:

            cursor.execute(
                """
                INSERT INTO marks
                (student_id, subject, marks)

                VALUES (?, ?, ?)
                """,
                (
                    student_id,
                    subject,
                    marks
                )
            )

        # Sample attendance

        sample_attendance = [

            ("Python", 18, 20),

            ("Data Science", 17, 20),

            ("Mathematics", 19, 20),

            ("Programming", 18, 20)

        ]

        for subject, attended, total in sample_attendance:

            cursor.execute(
                """
                INSERT INTO attendance
                (
                    student_id,
                    subject,
                    attended,
                    total
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    student_id,
                    subject,
                    attended,
                    total
                )
            )

    # ========================================================
    # SAMPLE EVENTS
    # ========================================================

    event_exists = cursor.execute(
        "SELECT id FROM events LIMIT 1"
    ).fetchone()

    if event_exists is None:

        events = [

            (
                "AI & Innovation Hackathon",
                "Build practical AI solutions for campus problems.",
                "2026-09-05"
            ),

            (
                "Freshers Orientation",
                "Orientation program for new students.",
                "2026-08-28"
            ),

            (
                "Coding Contest",
                "Competitive programming contest.",
                "2026-09-15"
            )

        ]

        cursor.executemany(
            """
            INSERT INTO events
            (
                title,
                description,
                event_date
            )

            VALUES (?, ?, ?)
            """,
            events
        )

    # ========================================================
    # SAMPLE NOTICES
    # ========================================================

    notice_exists = cursor.execute(
        "SELECT id FROM notices LIMIT 1"
    ).fetchone()

    if notice_exists is None:

        notices = [

            (
                "Welcome to Smart Campus",
                "The Smart Campus portal is now live.",
                datetime.now().isoformat(
                    timespec="minutes"
                )
            ),

            (
                "Library Reminder",
                "Return overdue books before the end of the week.",
                datetime.now().isoformat(
                    timespec="minutes"
                )
            )

        ]

        cursor.executemany(
            """
            INSERT INTO notices
            (
                title,
                content,
                created_at
            )

            VALUES (?, ?, ?)
            """,
            notices
        )

    connection.commit()

    connection.close()


# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# ADMIN REQUIRED DECORATOR
# ============================================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if session.get("role") != "admin":

            flash(
                "Admin access required.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# GET CURRENT STUDENT
# ============================================================

def get_current_student():

    connection = get_db()

    student = connection.execute(
        """
        SELECT *
        FROM students

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    connection.close()

    return student


# ============================================================
# PERFORMANCE PREDICTION
# ============================================================

def predict_performance(attendance, cgpa):

    score = (
        attendance * 0.4
        +
        cgpa * 10 * 0.6
    )

    if score >= 85:

        level = "Excellent"

        advice = (
            "Keep maintaining your consistency "
            "and consider advanced projects."
        )

    elif score >= 70:

        level = "Good"

        advice = (
            "Your fundamentals are strong. "
            "Focus on improving weaker subjects."
        )

    elif score >= 55:

        level = "Average"

        advice = (
            "Increase study consistency and "
            "attendance to improve your performance."
        )

    else:

        level = "Needs Attention"

        advice = (
            "A structured study plan and "
            "faculty support are recommended."
        )

    return {

        "score": round(score, 1),

        "level": level,

        "advice": advice

    }


# ============================================================
# GLOBAL TEMPLATE VARIABLES
# ============================================================

@app.context_processor
def global_variables():

    return {

        "current_user":
            session.get("username"),

        "role":
            session.get("role")

    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if "user_id" in session:

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form[
            "username"
        ].strip()

        password = request.form[
            "password"
        ]

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users

            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["role"] = user["role"]

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

    connection = get_db()

    if session["role"] == "admin":

        total_students = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM students
            """
        ).fetchone()["total"]

        average_attendance = connection.execute(
            """
            SELECT COALESCE(
                AVG(attendance),
                0
            ) AS average

            FROM students
            """
        ).fetchone()["average"]

        average_cgpa = connection.execute(
            """
            SELECT COALESCE(
                AVG(cgpa),
                0
            ) AS average

            FROM students
            """
        ).fetchone()["average"]

        students = connection.execute(
            """
            SELECT *
            FROM students

            ORDER BY id DESC

            LIMIT 8
            """
        ).fetchall()

    else:

        student = get_current_student()

        total_students = 1

        average_attendance = (
            student["attendance"]
            if student
            else 0
        )

        average_cgpa = (
            student["cgpa"]
            if student
            else 0
        )

        students = (
            [student]
            if student
            else []
        )

    events = connection.execute(
        """
        SELECT *
        FROM events

        ORDER BY event_date

        LIMIT 5
        """
    ).fetchall()

    notices = connection.execute(
        """
        SELECT *
        FROM notices

        ORDER BY id DESC

        LIMIT 5
        """
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",

        total=total_students,

        avg_att=round(
            average_attendance,
            2
        ),

        avg_cgpa=round(
            average_cgpa,
            2
        ),

        students=students,

        events=events,

        notices=notices
    )


# ============================================================
# STUDENTS
# ============================================================

@app.route("/students")
@login_required
@admin_required
def students():

    search = request.args.get(
        "q",
        ""
    ).strip()

    connection = get_db()

    if search:

        students = connection.execute(
            """
            SELECT *
            FROM students

            WHERE name LIKE ?
            OR email LIKE ?
            OR department LIKE ?

            ORDER BY name
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        students = connection.execute(
            """
            SELECT *
            FROM students

            ORDER BY name
            """
        ).fetchall()

    connection.close()

    return render_template(
        "students.html",

        students=students,

        q=search
    )


# ============================================================
# ADD STUDENT
# ============================================================

@app.route(
    "/students/add",
    methods=["POST"]
)
@login_required
@admin_required
def add_student():

    name = request.form[
        "name"
    ].strip()

    email = request.form[
        "email"
    ].strip()

    department = request.form[
        "department"
    ].strip()

    year = int(
        request.form["year"]
    )

    attendance = float(
        request.form.get(
            "attendance",
            0
        )
    )

    cgpa = float(
        request.form.get(
            "cgpa",
            0
        )
    )

    username = request.form[
        "username"
    ].strip()

    password = request.form[
        "password"
    ]

    connection = get_db()

    try:

        user_id = connection.execute(
            """
            INSERT INTO users
            (
                username,
                password,
                role
            )

            VALUES (?, ?, ?)
            """,
            (
                username,
                generate_password_hash(
                    password
                ),
                "student"
            )
        ).lastrowid

        connection.execute(
            """
            INSERT INTO students
            (
                user_id,
                name,
                email,
                department,
                year,
                attendance,
                cgpa
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                email,
                department,
                year,
                attendance,
                cgpa
            )
        )

        connection.commit()

        flash(
            "Student created successfully.",
            "success"
        )

    except sqlite3.IntegrityError:

        connection.rollback()

        flash(
            "Username or email already exists.",
            "error"
        )

    finally:

        connection.close()

    return redirect(
        url_for("students")
    )


# ============================================================
# STUDENT PROFILE
# ============================================================

@app.route(
    "/student/<int:student_id>"
)
@login_required
def student_profile(student_id):

    connection = get_db()

    student = connection.execute(
        """
        SELECT *
        FROM students

        WHERE id = ?
        """,
        (student_id,)
    ).fetchone()

    if not student:

        connection.close()

        return "Student not found", 404

    # Student can only view own profile

    if (
        session["role"] != "admin"
        and
        student["user_id"]
        != session["user_id"]
    ):

        connection.close()

        return "Unauthorized", 403

    marks = connection.execute(
        """
        SELECT *
        FROM marks

        WHERE student_id = ?

        ORDER BY subject
        """,
        (student_id,)
    ).fetchall()

    attendance = connection.execute(
        """
        SELECT *
        FROM attendance

        WHERE student_id = ?

        ORDER BY subject
        """,
        (student_id,)
    ).fetchall()

    connection.close()

    if marks:

        average_marks = round(
            sum(
                mark["marks"]
                for mark in marks
            )
            /
            len(marks),
            2
        )

    else:

        average_marks = 0

    performance = predict_performance(
        student["attendance"],
        student["cgpa"]
    )

    return render_template(
        "student.html",

        student=student,

        marks=marks,

        attendance=attendance,

        avg_marks=average_marks,

        prediction=performance
    )


# ============================================================
# ADD MARKS
# ============================================================

@app.route(
    "/student/<int:student_id>/marks",
    methods=["POST"]
)
@login_required
@admin_required
def add_marks(student_id):

    subject = request.form[
        "subject"
    ]

    marks = float(
        request.form["marks"]
    )

    connection = get_db()

    connection.execute(
        """
        INSERT INTO marks
        (
            student_id,
            subject,
            marks
        )

        VALUES (?, ?, ?)
        """,
        (
            student_id,
            subject,
            marks
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for(
            "student_profile",
            student_id=student_id
        )
    )


# ============================================================
# ADD ATTENDANCE
# ============================================================

@app.route(
    "/student/<int:student_id>/attendance",
    methods=["POST"]
)
@login_required
@admin_required
def add_attendance(student_id):

    subject = request.form[
        "subject"
    ]

    attended = int(
        request.form["attended"]
    )

    total = int(
        request.form["total"]
    )

    connection = get_db()

    connection.execute(
        """
        INSERT INTO attendance
        (
            student_id,
            subject,
            attended,
            total
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            student_id,
            subject,
            attended,
            total
        )
    )

    records = connection.execute(
        """
        SELECT attended, total
        FROM attendance

        WHERE student_id = ?
        """,
        (student_id,)
    ).fetchall()

    total_classes = sum(
        row["total"]
        for row in records
    )

    attended_classes = sum(
        row["attended"]
        for row in records
    )

    if total_classes > 0:

        percentage = round(
            attended_classes
            /
            total_classes
            * 100,
            2
        )

    else:

        percentage = 0

    connection.execute(
        """
        UPDATE students

        SET attendance = ?

        WHERE id = ?
        """,
        (
            percentage,
            student_id
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for(
            "student_profile",
            student_id=student_id
        )
    )


# ============================================================
# EVENTS
# ============================================================

@app.route("/events")
@login_required
def events():

    connection = get_db()

    events_list = connection.execute(
        """
        SELECT *
        FROM events

        ORDER BY event_date
        """
    ).fetchall()

    connection.close()

    return render_template(
        "events.html",
        events=events_list
    )


# ============================================================
# ADD EVENT
# ============================================================

@app.route(
    "/events/add",
    methods=["POST"]
)
@login_required
@admin_required
def add_event():

    title = request.form[
        "title"
    ]

    description = request.form[
        "description"
    ]

    event_date = request.form[
        "event_date"
    ]

    connection = get_db()

    connection.execute(
        """
        INSERT INTO events
        (
            title,
            description,
            event_date
        )

        VALUES (?, ?, ?)
        """,
        (
            title,
            description,
            event_date
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("events")
    )


# ============================================================
# NOTICES
# ============================================================

@app.route("/notices")
@login_required
def notices():

    connection = get_db()

    notices_list = connection.execute(
        """
        SELECT *
        FROM notices

        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "notices.html",
        notices=notices_list
    )


# ============================================================
# ADD NOTICE
# ============================================================

@app.route(
    "/notices/add",
    methods=["POST"]
)
@login_required
@admin_required
def add_notice():

    title = request.form[
        "title"
    ]

    content = request.form[
        "content"
    ]

    created_at = datetime.now().isoformat(
        timespec="minutes"
    )

    connection = get_db()

    connection.execute(
        """
        INSERT INTO notices
        (
            title,
            content,
            created_at
        )

        VALUES (?, ?, ?)
        """,
        (
            title,
            content,
            created_at
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("notices")
    )


# ============================================================
# DASHBOARD API
# ============================================================

@app.route(
    "/api/dashboard"
)
@login_required
def dashboard_api():

    connection = get_db()

    total_students = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM students
        """
    ).fetchone()["total"]

    average_cgpa = connection.execute(
        """
        SELECT COALESCE(
            AVG(cgpa),
            0
        ) AS average

        FROM students
        """
    ).fetchone()["average"]

    average_attendance = connection.execute(
        """
        SELECT COALESCE(
            AVG(attendance),
            0
        ) AS average

        FROM students
        """
    ).fetchone()["average"]

    connection.close()

    return jsonify({

        "students":
            total_students,

        "average_cgpa":
            round(
                average_cgpa,
                2
            ),

        "average_attendance":
            round(
                average_attendance,
                2
            )

    })


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    init_database()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )