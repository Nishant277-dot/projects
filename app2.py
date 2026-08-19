from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader

from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.metrics.pairwise import cosine_similarity

import os
import re


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "resume-analyzer-secret-key"

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# SKILL DATABASE
# ============================================================

SKILLS = {

    "Programming": [
        "python",
        "java",
        "c++",
        "c",
        "javascript",
        "typescript",
        "sql"
    ],

    "Data Science": [
        "data science",
        "machine learning",
        "deep learning",
        "artificial intelligence",
        "pandas",
        "numpy",
        "scikit-learn",
        "tensorflow",
        "pytorch",
        "matplotlib",
        "seaborn"
    ],

    "Web Development": [
        "html",
        "css",
        "javascript",
        "react",
        "node.js",
        "flask",
        "django",
        "bootstrap"
    ],

    "Tools": [
        "git",
        "github",
        "docker",
        "linux",
        "aws",
        "azure",
        "vs code"
    ],

    "Soft Skills": [
        "communication",
        "leadership",
        "teamwork",
        "problem solving",
        "time management",
        "presentation"
    ]

}


# ============================================================
# JOB ROLES
# ============================================================

JOB_ROLES = {

    "Python Developer": [

        "python",
        "flask",
        "django",
        "sql",
        "git",
        "api"

    ],

    "Data Scientist": [

        "python",
        "pandas",
        "numpy",
        "machine learning",
        "statistics",
        "sql",
        "scikit-learn"

    ],

    "Machine Learning Engineer": [

        "python",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch",
        "numpy",
        "scikit-learn"

    ],

    "Web Developer": [

        "html",
        "css",
        "javascript",
        "react",
        "node.js",
        "git"

    ],

    "AI Engineer": [

        "python",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "tensorflow",
        "pytorch"

    ],

    "Data Analyst": [

        "python",
        "sql",
        "excel",
        "pandas",
        "statistics",
        "data analysis"

    ]

}


# ============================================================
# CHECK FILE EXTENSION
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# EXTRACT PDF TEXT
# ============================================================

def extract_pdf_text(filepath):

    text = ""

    try:

        reader = PdfReader(filepath)

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"

    except Exception as error:

        print(
            "PDF extraction error:",
            error
        )

    return text


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT SKILLS
# ============================================================

def extract_skills(text):

    text = clean_text(text)

    found_skills = {}

    for category, skills in SKILLS.items():

        found_skills[category] = []

        for skill in skills:

            if skill.lower() in text:

                found_skills[category].append(
                    skill
                )

    return found_skills


# ============================================================
# FLATTEN SKILLS
# ============================================================

def flatten_skills(skill_dictionary):

    result = []

    for category in skill_dictionary:

        result.extend(
            skill_dictionary[category]
        )

    return result


# ============================================================
# CALCULATE ATS SCORE
# ============================================================

def calculate_ats_score(
    resume_text,
    job_description
):

    resume_text = clean_text(
        resume_text
    )

    job_description = clean_text(
        job_description
    )

    if not resume_text:

        return 0

    if not job_description:

        return 0

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english"
        )

        vectors = vectorizer.fit_transform(
            [
                resume_text,
                job_description
            ]
        )

        similarity = cosine_similarity(
            vectors[0:1],
            vectors[1:2]
        )[0][0]

        score = round(
            similarity * 100,
            2
        )

        return min(
            score,
            100
        )

    except Exception:

        return 0


# ============================================================
# KEYWORD MATCHING
# ============================================================

def keyword_match(
    resume_text,
    job_description
):

    resume_text = clean_text(
        resume_text
    )

    job_description = clean_text(
        job_description
    )

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9+#.-]*\b",
        job_description
    )

    words = list(
        set(words)
    )

    matched = []

    missing = []

    ignored_words = {

        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "are",
        "you",
        "your",
        "our",
        "from",
        "have",
        "will",
        "work",
        "years",
        "using",
        "into",
        "job",
        "role"

    }

    for word in words:

        if word in ignored_words:

            continue

        if len(word) < 3:

            continue

        if word in resume_text:

            matched.append(word)

        else:

            missing.append(word)

    total = len(
        matched
    ) + len(
        missing
    )

    if total:

        percentage = round(
            len(matched)
            /
            total
            * 100,
            2
        )

    else:

        percentage = 0

    return (
        matched,
        missing,
        percentage
    )


# ============================================================
# JOB ROLE RECOMMENDATION
# ============================================================

def recommend_roles(resume_text):

    resume_text = clean_text(
        resume_text
    )

    scores = []

    for role, required_skills in JOB_ROLES.items():

        matched = 0

        for skill in required_skills:

            if skill.lower() in resume_text:

                matched += 1

        percentage = round(
            matched
            /
            len(required_skills)
            * 100,
            2
        )

        scores.append(
            {
                "role": role,
                "score": percentage
            }
        )

    scores.sort(
        key=lambda item:
        item["score"],
        reverse=True
    )

    return scores


# ============================================================
# RESUME QUALITY ANALYSIS
# ============================================================

def analyze_resume_quality(text):

    text_lower = clean_text(
        text
    )

    suggestions = []

    positive_points = []

    # --------------------------------------------------------
    # LENGTH
    # --------------------------------------------------------

    word_count = len(
        text_lower.split()
    )

    if word_count < 250:

        suggestions.append(
            "Your resume appears too short. "
            "Add relevant projects, achievements "
            "and technical experience."
        )

    elif word_count > 1200:

        suggestions.append(
            "Your resume may be too long. "
            "Remove unnecessary information."
        )

    else:

        positive_points.append(
            "Resume length appears reasonable."
        )

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    if re.search(
        email_pattern,
        text
    ):

        positive_points.append(
            "Email address detected."
        )

    else:

        suggestions.append(
            "Add a professional email address."
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    phone_pattern = r"\b\d{10}\b"

    if re.search(
        phone_pattern,
        text
    ):

        positive_points.append(
            "Phone number detected."
        )

    else:

        suggestions.append(
            "Consider adding a professional contact number."
        )

    # --------------------------------------------------------
    # LINKEDIN
    # --------------------------------------------------------

    if "linkedin" in text_lower:

        positive_points.append(
            "LinkedIn profile detected."
        )

    else:

        suggestions.append(
            "Add your LinkedIn profile."
        )

    # --------------------------------------------------------
    # GITHUB
    # --------------------------------------------------------

    if "github" in text_lower:

        positive_points.append(
            "GitHub profile detected."
        )

    else:

        suggestions.append(
            "Add your GitHub profile if you have projects."
        )

    # --------------------------------------------------------
    # PROJECTS
    # --------------------------------------------------------

    if "project" in text_lower:

        positive_points.append(
            "Projects section detected."
        )

    else:

        suggestions.append(
            "Add 2-4 relevant projects."
        )

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if (
        "experience" in text_lower
        or
        "internship" in text_lower
    ):

        positive_points.append(
            "Experience information detected."
        )

    else:

        suggestions.append(
            "Add internships, practical experience "
            "or relevant academic work."
        )

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    if "education" in text_lower:

        positive_points.append(
            "Education section detected."
        )

    else:

        suggestions.append(
            "Add an education section."
        )

    return {

        "word_count":
            word_count,

        "suggestions":
            suggestions,

        "positive":
            positive_points

    }


# ============================================================
# RESUME SCORE
# ============================================================

def calculate_resume_score(
    quality,
    skill_count,
    ats_score,
    keyword_score
):

    score = 0

    # ATS = 40%
    score += ats_score * 0.40

    # Keywords = 30%
    score += keyword_score * 0.30

    # Skills = 20%

    skill_score = min(
        skill_count * 5,
        100
    )

    score += skill_score * 0.20

    # Quality = 10%

    quality_score = min(
        (
            len(
                quality["positive"]
            )
            /
            7
        )
        *
        100,
        100
    )

    score += quality_score * 0.10

    return round(
        min(score, 100),
        2
    )


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# ANALYZE RESUME
# ============================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # --------------------------------------------------------
    # CHECK PDF
    # --------------------------------------------------------

    if "resume" not in request.files:

        flash(
            "Please upload a resume.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    file = request.files[
        "resume"
    ]

    job_description = request.form.get(
        "job_description",
        ""
    ).strip()

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if file.filename == "":

        flash(
            "Please select a PDF file.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only PDF files are supported.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    if not job_description:

        flash(
            "Please enter a job description.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # --------------------------------------------------------
    # SAVE FILE
    # --------------------------------------------------------

    filename = secure_filename(
        file.filename
    )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    # --------------------------------------------------------
    # EXTRACT TEXT
    # --------------------------------------------------------

    resume_text = extract_pdf_text(
        filepath
    )

    if not resume_text.strip():

        flash(
            "Could not extract text from the PDF. "
            "Use a text-based PDF rather than a scanned image.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    # --------------------------------------------------------
    # SKILLS
    # --------------------------------------------------------

    skills = extract_skills(
        resume_text
    )

    all_skills = flatten_skills(
        skills
    )

    # --------------------------------------------------------
    # ATS SCORE
    # --------------------------------------------------------

    ats_score = calculate_ats_score(
        resume_text,
        job_description
    )

    # --------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------

    (
        matched_keywords,
        missing_keywords,
        keyword_score
    ) = keyword_match(
        resume_text,
        job_description
    )

    # --------------------------------------------------------
    # QUALITY
    # --------------------------------------------------------

    quality = analyze_resume_quality(
        resume_text
    )

    # --------------------------------------------------------
    # JOB ROLES
    # --------------------------------------------------------

    recommended_roles = recommend_roles(
        resume_text
    )

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    final_score = calculate_resume_score(

        quality,

        len(all_skills),

        ats_score,

        keyword_score

    )

    # --------------------------------------------------------
    # SCORE CATEGORY
    # --------------------------------------------------------

    if final_score >= 80:

        score_label = "Excellent"

    elif final_score >= 65:

        score_label = "Good"

    elif final_score >= 50:

        score_label = "Average"

    else:

        score_label = "Needs Improvement"

    # --------------------------------------------------------
    # DELETE UPLOADED FILE
    # --------------------------------------------------------

    try:

        os.remove(filepath)

    except OSError:

        pass

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return render_template(

        "result.html",

        filename=filename,

        resume_text=resume_text,

        skills=skills,

        all_skills=all_skills,

        ats_score=ats_score,

        matched_keywords=matched_keywords,

        missing_keywords=missing_keywords,

        keyword_score=keyword_score,

        quality=quality,

        recommended_roles=recommended_roles,

        final_score=final_score,

        score_label=score_label

    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )