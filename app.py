from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, emit
import random, json, os

app = Flask(__name__)

# Render-safe SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# =========================
# FILE DB
# =========================
ROOM_FILE = "rooms.json"
QUESTION_FILE = "questions.json"

# runtime memory
quiz_sequence = {}
game_state = {}

# =========================
# FILE HELPERS
# =========================
def load_rooms():
    if not os.path.exists(ROOM_FILE):
        return {}
    try:
        with open(ROOM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_rooms(data):
    with open(ROOM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_questions():
    if not os.path.exists(QUESTION_FILE):
        return []
    try:
        with open(QUESTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# =========================
# QUIZ BUILDER (KAHOOT STYLE)
# =========================
def build_quiz():
    q = load_questions()

    easy, med, hard = [], [], []

    for x in q:
        lvl = x.get("difficulty", "").lower()
        if lvl == "easy":
            easy.append(x)
        elif lvl == "moderate":
            med.append(x)
        elif lvl == "hard":
            hard.append(x)

    quiz = []

    if easy:
        quiz += random.sample(easy, min(5, len(easy)))
    if med:
        quiz += random.sample(med, min(5, len(med)))
    if hard:
        quiz += random.sample(hard, min(5, len(hard)))

    random.shuffle(quiz)
    return quiz[:15]

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/host")
def host():
    rooms = load_rooms()

    room = str(random.randint(1000, 9999))
    while room in rooms:
        room = str(random.randint(1000, 9999))

    rooms[room] = {"players": []}
    save_rooms(rooms)

    game_state[room] = {"index": 0}
    quiz_sequence[room] = build_quiz()

    return render_template("host.html", room=room)

@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        rooms = load_rooms()

        name = request.form["name"]
        room = request.form["room"]

        if room not in rooms:
            return "Invalid Room Code"

        return redirect(url_for("lobby", room=room, name=name))

    return render_template("join.html")

@app.route("/lobby/<room>/<name>")
def lobby(room, name):
    return render_template("lobby.html", room=room, name=name)

@app.route("/add_questions", methods=["GET", "POST"])
def add_questions():
    questions = load_questions()

    if request.method == "POST":

        if request.form.get("clear") == "true":
            with open(QUESTION_FILE, "w") as f:
                json.dump([], f)
            return redirect("/add_questions")

        new_q = {
            "question": request.form["question"],
            "A": request.form["A"],
            "B": request.form["B"],
            "C": request.form["C"],
            "D": request.form["D"],
            "correct": request.form["correct"],
            "difficulty": request.form["difficulty"].lower()
        }

        questions.append(new_q)

        with open(QUESTION_FILE, "w") as f:
            json.dump(questions, f, indent=4)

        return redirect("/add_questions")

    return render_template("add_questions.html")

@app.route("/quiz/<room>")
def quiz(room):

    if room not in game_state:
        game_state[room] = {"index": 0}

    if room not in quiz_sequence:
        quiz_sequence[room] = build_quiz()

    idx = game_state[room]["index"]

    if idx >= len(quiz_sequence[room]):
        return "Quiz Finished"

    return render_template(
        "quiz.html",
        question=quiz_sequence[room][idx],
        room=room
    )

# =========================
# SOCKETS
# =========================
@socketio.on("join_room")
def join_socket(data):

    rooms = load_rooms()

    name = data["name"]
    room = data["room"]

    join_room(room)

    if room not in rooms:
        return

    players = rooms[room]["players"]

    if name not in [p["name"] for p in players]:
        players.append({"name": name, "score": 0})

    rooms[room]["players"] = players
    save_rooms(rooms)

    emit("leaderboard", players, to=room)

@socketio.on("start_quiz")
def start_quiz(data):

    room = data["room"]

    if room not in quiz_sequence:
        quiz_sequence[room] = build_quiz()

    game_state[room] = {"index": 0}

    emit("new_question", {
        "question": quiz_sequence[room][0],
        "index": 0
    }, to=room)

@socketio.on("answer_result")
def answer(data):

    rooms = load_rooms()

    room = data["room"]
    name = data["name"]
    score = data["score"]

    if room not in rooms:
        return

    for p in rooms[room]["players"]:
        if p["name"] == name:
            p["score"] += score

    save_rooms(rooms)

    emit("leaderboard", rooms[room]["players"], to=room)

@socketio.on("next_question")
def next_question(data):

    room = data["room"]

    if room not in game_state:
        return

    game_state[room]["index"] += 1
    idx = game_state[room]["index"]

    if idx >= len(quiz_sequence[room]):
        rooms = load_rooms()
        emit("quiz_end", rooms.get(room, {}).get("players", []), to=room)
        return

    emit("new_question", {
        "question": quiz_sequence[room][idx],
        "index": idx
    }, to=room)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)