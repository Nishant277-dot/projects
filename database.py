import sqlite3

DB_NAME = "campus.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            year INTEGER NOT NULL,
            attendance REAL DEFAULT 0,
            cgpa REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            marks REAL NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_student(name, email, department, year, attendance, cgpa):
    conn = get_connection()

    conn.execute("""
        INSERT INTO students
        (name, email, department, year, attendance, cgpa)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, email, department, year, attendance, cgpa))

    conn.commit()
    conn.close()


def get_students():
    conn = get_connection()

    students = conn.execute("""
        SELECT * FROM students
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return students


def get_student(student_id):
    conn = get_connection()

    student = conn.execute("""
        SELECT * FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    conn.close()

    return student


def add_marks(student_id, subject, marks):
    conn = get_connection()

    conn.execute("""
        INSERT INTO marks(student_id, subject, marks)
        VALUES (?, ?, ?)
    """, (student_id, subject, marks))

    conn.commit()
    conn.close()


def get_marks(student_id):
    conn = get_connection()

    marks = conn.execute("""
        SELECT * FROM marks
        WHERE student_id = ?
    """, (student_id,)).fetchall()

    conn.close()

    return marks