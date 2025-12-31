import socketio
import uvicorn
import asyncio
import random
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import quiz_engine 

# --- GAME STATE ---
game_db = quiz_engine.GameEngine()
current_question_index = 0
active_questions = [] 
custom_questions = [] # Store user-created questions here

# --- CONTENT DATABASE (Static fallback) ---
CONTENT_DB = {
    "mixed": [
        {"q": "In 'Stranger Things', what is the name of the dimension?", "options": ["Upside Down", "Other Side", "Dark Realm", "Nether"], "correct": 0, "diff": 1},
        {"q": "Who is the 'Mother of Dragons' in Game of Thrones?", "options": ["Cersei", "Sansa", "Daenerys", "Arya"], "correct": 2, "diff": 1},
        {"q": "What is 15 * 15?", "options": ["200", "225", "250", "150"], "correct": 1, "diff": 2},
        {"q": "Which country is home to the Maasai Mara?", "options": ["Tanzania", "Uganda", "Kenya", "Rwanda"], "correct": 2, "diff": 1},
        {"q": "What is the largest planet in our solar system?", "options": ["Earth", "Mars", "Jupiter", "Saturn"], "correct": 2, "diff": 1},
        {"q": "Who wrote 'Romeo and Juliet'?", "options": ["Dickens", "Shakespeare", "Hemingway", "Orwell"], "correct": 1, "diff": 2},
        {"q": "What is the chemical symbol for Gold?", "options": ["Ag", "Fe", "Au", "Pb"], "correct": 2, "diff": 3},
        {"q": "Which African city is known as the 'Green City in the Sun'?", "options": ["Nairobi", "Lagos", "Cape Town", "Accra"], "correct": 0, "diff": 2},
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
    leaderboard = game_db.get_leaderboard()
    await sio.emit('update_lobby', {'players': leaderboard})

@sio.event
async def admin_start_game(sid, data):
    global active_questions, current_question_index
    
    # 1. GET SETTINGS
    limit = int(data.get('limit', 5))
    use_custom = data.get('use_custom', False)
    
    # 2. SELECT QUESTIONS
    if use_custom and len(custom_questions) > 0:
        pool = custom_questions
    else:
        pool = CONTENT_DB['mixed']
    
    # Shuffle and slice
    random.shuffle(pool)
    active_questions = pool[:limit]
    
    current_question_index = 0
    
    # 3. START
    await sio.emit('game_started', {'total_q': len(active_questions)})
    await asyncio.sleep(4) # Waiting for "Are you ready?" music
    await send_question()

@sio.event
async def add_custom_question(sid, data):
    # Admin sent a new question
    new_q = {
        "q": data.get('q'),
        "options": [data.get('o1'), data.get('o2'), data.get('o3'), data.get('o4')],
        "correct": int(data.get('correct')),
        "diff": int(data.get('diff'))
    }
    custom_questions.append(new_q)
    print(f"Added Question: {new_q['q']}")
    await sio.emit('admin_msg', {'msg': f"Question Added! Total Custom: {len(custom_questions)}"}, to=sid)

async def send_question():
    if current_question_index < len(active_questions):
        q_data = active_questions[current_question_index]
        
        # DYNAMIC TIME: Easy(1)=15s, Med(2)=25s, Hard(3)=35s
        time_limit = 10 + (q_data['diff'] * 10)
        points_val = q_data['diff'] * 1000
        
        await sio.emit('new_question', {
            'q': q_data['q'],
            'options': q_data['options'],
            'current': current_question_index + 1,
            'total': len(active_questions),
            'time': time_limit,
            'points': points_val,
            'diff': q_data['diff']
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