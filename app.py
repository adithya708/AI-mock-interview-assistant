from io import BytesIO
import json
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from google import genai
from google.genai import types
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
QUESTION_COUNT = 10

questions = {
    "python": [
        {"question": "Which keyword defines a function in Python?", "options": ["func", "def", "function", "define"], "answer": "def"},
        {"question": "Which data type stores an ordered, changeable collection?", "options": ["Tuple", "Set", "List", "String"], "answer": "List"},
        {"question": "How do you access the value for key 'name' in dictionary person?", "options": ["person.name", "person['name']", "person->name", "person(name)"], "answer": "person['name']"},
        {"question": "Which special method initializes a new Python object?", "options": ["__start__", "__new__", "__init__", "__create__"], "answer": "__init__"},
        {"question": "What is the result of len([10, 20, 30])?", "options": ["2", "3", "10", "30"], "answer": "3"},
        {"question": "Which symbol starts a comment in Python?", "options": ["//", "#", "--", "/*"], "answer": "#"},
        {"question": "Which keyword creates a loop over an iterable?", "options": ["repeat", "for", "loop", "iterate"], "answer": "for"},
        {"question": "What does a Python set store?", "options": ["Only duplicate values", "Unique values", "Key-value pairs", "Ordered characters"], "answer": "Unique values"},
        {"question": "Which value represents the absence of a value in Python?", "options": ["null", "undefined", "None", "empty"], "answer": "None"},
        {"question": "Which function displays output in Python?", "options": ["echo()", "write()", "display()", "print()"], "answer": "print()"},
    ],
    "java": [
        {"question": "Which method is the entry point of a Java application?", "options": ["start()", "main()", "run()", "init()"], "answer": "main()"},
        {"question": "Which keyword is used for inheritance in Java?", "options": ["implements", "extends", "inherit", "super"], "answer": "extends"},
        {"question": "What is an object in Java?", "options": ["A class blueprint", "An instance of a class", "A package", "A compiler"], "answer": "An instance of a class"},
        {"question": "Which block handles an exception in Java?", "options": ["catch", "handle", "except", "error"], "answer": "catch"},
        {"question": "Polymorphism allows one interface to have what?", "options": ["Only one implementation", "Many implementations", "No implementation", "Only private methods"], "answer": "Many implementations"},
        {"question": "Which keyword declares a constant-like variable by convention in Java?", "options": ["final", "constant", "static", "fixed"], "answer": "final"},
        {"question": "Which collection does not allow duplicate elements?", "options": ["List", "Queue", "Set", "Array"], "answer": "Set"},
        {"question": "Which operator compares primitive values in Java?", "options": ["=", "==", "equals", "compare"], "answer": "=="},
        {"question": "What does JVM stand for?", "options": ["Java Variable Method", "Java Virtual Machine", "Java Verified Module", "Java Version Manager"], "answer": "Java Virtual Machine"},
        {"question": "Which access modifier makes a member visible from any class?", "options": ["private", "protected", "public", "internal"], "answer": "public"},
    ],
    "sql": [
        {"question": "Which SQL command retrieves data from a database?", "options": ["GET", "SELECT", "FETCH", "RETRIEVE"], "answer": "SELECT"},
        {"question": "Which clause filters rows based on a condition?", "options": ["FILTER", "WHERE", "HAVING", "ORDER BY"], "answer": "WHERE"},
        {"question": "Which JOIN returns matching rows from both tables?", "options": ["FULL JOIN", "LEFT JOIN", "INNER JOIN", "CROSS JOIN"], "answer": "INNER JOIN"},
        {"question": "Which clause groups rows with the same values?", "options": ["GROUP BY", "ORDER BY", "COMBINE BY", "COLLECT BY"], "answer": "GROUP BY"},
        {"question": "Which function counts rows in a query result?", "options": ["TOTAL()", "COUNT()", "SUM()", "NUMBER()"], "answer": "COUNT()"},
        {"question": "Which command adds a new row to a table?", "options": ["ADD", "INSERT", "APPEND", "CREATE"], "answer": "INSERT"},
        {"question": "Which command changes existing rows?", "options": ["MODIFY", "CHANGE", "UPDATE", "ALTER"], "answer": "UPDATE"},
        {"question": "Which command removes rows from a table?", "options": ["REMOVE", "DROP", "DELETE", "CLEAR"], "answer": "DELETE"},
        {"question": "Which keyword sorts query results?", "options": ["SORT BY", "ORDER BY", "GROUP BY", "ARRANGE"], "answer": "ORDER BY"},
        {"question": "Which constraint uniquely identifies each row?", "options": ["FOREIGN KEY", "CHECK", "PRIMARY KEY", "INDEX"], "answer": "PRIMARY KEY"},
    ],
}

subject_names = {"python": "Python", "java": "Java", "sql": "SQL"}


def generate_questions(subject, previous_questions=None):
    """Generate ten MCQs with Gemini, falling back to the built-in set."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("replace-with-"):
        return questions[subject], "fallback"

    previous_questions = previous_questions or []
    previous_text = "\n".join(f"- {item}" for item in previous_questions[-15:]) or "- None"
    prompt = f"""
Create exactly {QUESTION_COUNT} technical multiple-choice interview questions about {subject_names[subject]}.
Cover the subject's basics and common interview topics. Return only valid JSON as an array.
This is a new interview attempt. Use fresh questions and vary the examples from previous attempts.
Do not repeat or rephrase any of these previously used questions:
{previous_text}
Use a mix of beginner, intermediate, and practical interview questions.
Adjust the difficulty and examples for a general interview candidate.
Each array item must have this exact shape:
{{"question": "...", "options": ["...", "...", "...", "..."], "answer": "..."}}
The answer must exactly match one of the four options. Do not include markdown or explanations.
Variation token: {secrets.token_hex(8)}
"""
    client = genai.Client(api_key=api_key)
    last_error = None
    for model in ("gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite"):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9,
                ),
            )
            generated = json.loads(response.text.strip())
            if not isinstance(generated, list) or len(generated) != QUESTION_COUNT:
                raise ValueError(f"Gemini did not return exactly {QUESTION_COUNT} questions")
            for item in generated:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("question"), str)
                    or not isinstance(item.get("options"), list)
                    or len(item["options"]) != 4
                    or not all(isinstance(option, str) for option in item["options"])
                    or item.get("answer") not in item["options"]
                ):
                    raise ValueError("Gemini returned an invalid question format")
            if any(item["question"] in previous_questions for item in generated):
                raise ValueError("Gemini repeated a previous question")
            return generated, "gemini"
        except Exception as error:
            last_error = error
            app.logger.warning("Gemini model %s failed: %s", model, error)

    app.logger.error("Gemini question generation failed: %s", last_error)
    return questions[subject], "fallback"


def current_questions():
    subject = session.get("subject")
    stored_questions = session.get("questions")
    if subject not in questions or not isinstance(stored_questions, list) or len(stored_questions) != QUESTION_COUNT:
        return None
    return stored_questions


def interview_data():
    subject = session.get("subject")
    answers = session.get("answers", {})
    interview_questions = current_questions()
    if subject not in questions or not interview_questions:
        return None

    review = []
    correct = 0
    for index, item in enumerate(interview_questions):
        user_answer = answers.get(str(index + 1), "Not answered")
        is_correct = user_answer == item["answer"]
        correct += int(is_correct)
        review.append({**item, "user_answer": user_answer, "is_correct": is_correct})
    total = len(review)
    percentage = round(correct / total * 100)
    if correct == QUESTION_COUNT:
        feedback = "Excellent Performance 🎉"
    elif correct >= 8:
        feedback = "Very Good Performance 👏"
    elif correct >= 6:
        feedback = "Good Performance 👍"
    else:
        feedback = "Needs More Practice 📚"
    return {
        "subject": subject_names[subject],
        "total": total,
        "correct": correct,
        "incorrect": total - correct,
        "percentage": percentage,
        "feedback": feedback,
        "review": review,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/subjects")
def subjects():
    return render_template("subject.html", selected=session.get("subject"))


@app.route("/start", methods=["POST"])
def start():
    subject = request.form.get("subject", "").lower()
    if subject not in questions:
        return render_template("subject.html", error="Please select a subject before starting.", selected=subject), 400
    previous_questions = session.get("question_history", [])
    session["subject"] = subject
    generated_questions, source = generate_questions(subject, previous_questions)
    session["questions"] = generated_questions
    session["question_source"] = source
    session["answers"] = {}
    session["question_history"] = (previous_questions + [item["question"] for item in generated_questions])[-15:]
    return redirect(url_for("question", number=1))


@app.route("/question/<int:number>", methods=["GET", "POST"])
def question(number):
    subject = session.get("subject")
    interview_questions = current_questions()
    if subject not in questions or not interview_questions:
        return redirect(url_for("subjects"))
    if number < 1 or number > QUESTION_COUNT:
        return redirect(url_for("question", number=1))

    answers = session.setdefault("answers", {})
    if request.method == "POST":
        answer = request.form.get("answer")
        valid_options = interview_questions[number - 1]["options"]
        if answer not in valid_options:
            return render_template("question.html", subject=subject_names[subject], item=interview_questions[number - 1], number=number, total=QUESTION_COUNT, selected_answer=answers.get(str(number)), source=session.get("question_source")), 400
        answers[str(number)] = answer
        session.modified = True
        if request.form.get("action") == "previous":
            return redirect(url_for("question", number=max(1, number - 1)))
        if number == QUESTION_COUNT:
            return redirect(url_for("results"))
        return redirect(url_for("question", number=number + 1))

    return render_template("question.html", subject=subject_names[subject], item=interview_questions[number - 1], number=number, total=QUESTION_COUNT, selected_answer=answers.get(str(number)), source=session.get("question_source"))


@app.route("/results")
def results():
    data = interview_data()
    if not data or len(session.get("answers", {})) != QUESTION_COUNT:
        return redirect(url_for("question", number=1))
    return render_template("results.html", data=data)


@app.route("/download-pdf")
def download_pdf():
    data = interview_data()
    if not data or len(session.get("answers", {})) != QUESTION_COUNT:
        return redirect(url_for("question", number=1))

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.6 * inch, leftMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#17324d"), spaceAfter=16)
    small_style = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=9, leading=12)
    story = [Paragraph("AI Mock Interview Assistant Report", title_style)]
    summary = [["Subject", data["subject"]], ["Final Score", f"{data['correct']} / {data['total']}"], ["Correct Answers", str(data["correct"])], ["Incorrect Answers", str(data["incorrect"])], ["Percentage", f"{data['percentage']}%"]]
    summary_table = Table(summary, colWidths=[1.7 * inch, 4.8 * inch])
    summary_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0f5")), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5df")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (0, -1), 10), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.extend([summary_table, Spacer(1, 18), Paragraph("Detailed Answer Review", styles["Heading2"])])
    rows = [["#", "Question", "User Answer", "Correct Answer", "Status"]]
    for index, item in enumerate(data["review"], 1):
        rows.append([str(index), Paragraph(item["question"], small_style), Paragraph(item["user_answer"], small_style), Paragraph(item["answer"], small_style), "Correct" if item["is_correct"] else "Incorrect"])
    review_table = Table(rows, colWidths=[0.3 * inch, 2.45 * inch, 1.35 * inch, 1.35 * inch, 0.85 * inch], repeatRows=1)
    review_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 10), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f7")])]))
    story.append(review_table)
    document.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{data['subject'].lower()}-mock-interview-report.pdf", mimetype="application/pdf")


@app.route("/restart")
def restart():
    question_history = session.get("question_history", [])
    session.clear()
    session["question_history"] = question_history
    return redirect(url_for("subjects"))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
