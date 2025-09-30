from flask import Flask, request, jsonify, render_template, g, redirect, url_for
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")

app = Flask(__name__, template_folder="templates")

def get_db():
    db = getattr(g, "db", None)
    if db is None:
        db = g.db = sqlite3.connect(DB_PATH)
    return db

@app.teardown_appcontext
def close_db(error):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/questions')
def questions():
    # Return 10 ready-made questions (mixed MCQ / true-false style)
    qs = [
            {"id": "q01", "text": "What is 7 + 5?", "type": "mcq", "options": ["10", "11", "12"]},
            {"id": "q02", "text": "Which planet is known as the Red Planet?", "type": "mcq", "options": ["Earth", "Mars", "Venus"]},
            {"id": "q03", "text": "What is the square root of 81?", "type": "mcq", "options": ["7", "8", "9"]},
            {"id": "q04", "text": "Which gas do plants primarily absorb for photosynthesis?", "type": "mcq", "options": ["Oxygen", "Carbon dioxide", "Nitrogen"]},
            {"id": "q05", "text": "Is water composed of hydrogen and oxygen?", "type": "mcq", "options": ["yes", "no"]},
            {"id": "q06", "text": "What is 15 × 3?", "type": "mcq", "options": ["40", "45", "50"]},
            {"id": "q07", "text": "Which shape has 4 equal sides and 4 right angles?", "type": "mcq", "options": ["Rectangle", "Square", "Rhombus"]},
            {"id": "q08", "text": "Which instrument measures temperature?", "type": "mcq", "options": ["Barometer", "Thermometer", "Ammeter"]},
            {"id": "q09", "text": "Which one is a prime number?", "type": "mcq", "options": ["21", "23", "25"]},
            {"id": "q10", "text": "Is the statement 'The Sun rises in the West' true or false?", "type": "mcq", "options": ["true", "false"]},
        ]
    return jsonify(qs)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "invalid json"}), 400
    user = data.get('user', 'anonymous')
    answers = data.get('answers', [])
    ts = datetime.utcnow().isoformat()
    db = get_db()
    cur = db.cursor()
    for a in answers:
        qid = a.get('qid')
        ans = a.get('answer')
        cur.execute('INSERT INTO responses(timestamp, user, qid, answer) VALUES (?,?,?,?)', (ts, user, qid, ans))
    db.commit()
    return jsonify({"status": "ok", "saved": len(answers)})

@app.route('/submissions')
def submissions():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, timestamp, user, qid, answer FROM responses ORDER BY id DESC LIMIT 200')
    rows = cur.fetchall()
    return render_template('submissions.html', rows=rows)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port)
