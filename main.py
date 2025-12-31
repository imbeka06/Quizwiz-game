import socketio
import uvicorn
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import quiz_engine 

# --- GAME STATE ---
game_db = quiz_engine.GameEngine()
current_question_index = 0
current_category = "netflix"
active_questions = [] 

# --- CONTENT DATABASE ---
CONTENT_DB = {
    "netflix": [
        {"q": "In 'Stranger Things', what is the name of the dimension?", "options": ["Upside Down", "Other Side", "Dark Realm", "Nether"], "correct": 0, "diff": 1},
        {"q": "Who is the 'Mother of Dragons' in Game of Thrones?", "options": ["Cersei", "Sansa", "Daenerys", "Arya"], "correct": 2, "diff": 1},
        {"q": "Which show features a chess prodigy?", "options": ["The Queen's Gambit", "Checkmate", "Pawn Star", "Rook"], "correct": 0, "diff": 2},
    ],
    "kenya": [
        {"q": "What is the meaning of 'Hakuna Matata'?", "options": ["No Food", "No Worries", "Good Morning", "Lets Go"], "correct": 1, "diff": 1},
        {"q": "Who is the fastest marathon runner?", "options": ["Bolt", "Kipchoge", "Rudisha", "Farah"], "correct": 1, "diff": 2},
        {"q": "Which city is known as the 'Green City in the Sun'?", "options": ["Mombasa", "Kisumu", "Nairobi", "Nakuru"], "correct": 2, "diff": 1},
    ],
    "math": [
        {"q": "What is 15 * 15?", "options": ["200", "225", "250", "150"], "correct": 1, "diff": 2},
        {"q": "Solve for x: 2x + 4 = 10", "options": ["2", "4", "3", "5"], "correct": 2, "diff": 2},
        {"q": "What is the square root of 144?", "options": ["10", "11", "12", "14"], "correct": 2, "diff": 1},
    ],
    "romance": [
        {"q": "Where is the 'City of Love'?", "options": ["Rome", "Paris", "London", "Nairobi"], "correct": 1, "diff": 1},
        {"q": "Finish the lyric: 'I will always ____ you'", "options": ["Miss", "Hate", "Love", "Trust"], "correct": 2, "diff": 1},
    ]
}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

@app.get("/")
async def get():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# --- EVENTS ---

@sio.event
async def connect(sid, environ):
    print(f"Connected: {sid}")

@sio.event
async def join_game(sid, data):
    name = data.get('name')
    game_db.add_player(sid, name)
    is_admin = (name.lower() == 'admin')
    
    await sio.emit('join_success', {'is_admin': is_admin}, to=sid)
    
    # If Admin, send them the category list
    if is_admin:
        await sio.emit('admin_init', {'categories': list(CONTENT_DB.keys())}, to=sid)

    leaderboard = game_db.get_leaderboard()
    await sio.emit('update_lobby', {'players': leaderboard})

@sio.event
async def select_category(sid, data):
    # Admin selected a topic
    global current_category, active_questions
    current_category = data.get('category')
    active_questions = CONTENT_DB.get(current_category, [])
    print(f"Category changed to: {current_category}")
    
    # Broadcast THEME CHANGE to all players
    await sio.emit('theme_change', {'theme': current_category})

@sio.event
async def start_game(sid):
    global current_question_index, active_questions
    # If no questions loaded yet, load default
    if not active_questions:
         active_questions = CONTENT_DB["netflix"]

    current_question_index = 0
    await sio.emit('game_started', {})
    await asyncio.sleep(3)
    await send_question()

async def send_question():
    if current_question_index < len(active_questions):
        q_data = active_questions[current_question_index]
        
        # Calculate Time & Points based on Difficulty
        time_limit = 10 + (q_data['diff'] * 5)
        points_val = q_data['diff'] * 1000
        
        await sio.emit('new_question', {
            'q': q_data['q'],
            'options': q_data['options'],
            'current': current_question_index + 1,
            'total': len(active_questions),
            'time': time_limit,
            'points': points_val
        })
    else:
        leaderboard = game_db.get_leaderboard()
        await sio.emit('game_over', {'leaderboard': leaderboard})

@sio.event
async def submit_answer(sid, data):
    idx = data.get('answer_index')
    time_left = float(data.get('time_left'))
    
    q_data = active_questions[current_question_index]
    is_correct = (idx == q_data['correct'])
    
    score = game_db.update_score(sid, is_correct, time_left)
    await sio.emit('answer_result', {'correct': is_correct, 'score': score}, to=sid)

@sio.event
async def admin_next_question(sid):
    global current_question_index
    current_question_index += 1
    await send_question()

@sio.event
async def disconnect(sid):
    game_db.remove_player(sid)
    leaderboard = game_db.get_leaderboard()
    await sio.emit('update_lobby', {'players': leaderboard})

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)