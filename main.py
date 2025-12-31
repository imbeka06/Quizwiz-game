import socketio
import uvicorn
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import C++ Engine
import quiz_engine 

# --- CONFIGURATION ---
game_db = quiz_engine.GameEngine()
current_question_index = 0
game_active = False

# NETFLIX TRIVIA QUESTIONS
QUESTIONS = [
    {
        "q": "In 'Stranger Things', what is the name of the parallel dimension?",
        "options": ["The Other Side", "The Upside Down", "The Dark Place", "Shadow Realm"],
        "correct": 1  # Index of correct answer (0, 1, 2, 3)
    },
    {
        "q": "Which series is based on a chess prodigy?",
        "options": ["The Queen's Gambit", "Checkmate", "Grandmaster", "Pawn Sacrifice"],
        "correct": 0
    },
    {
        "q": "What is the family name in 'Ozark'?",
        "options": ["White", "Byrde", "Smith", "Langmore"],
        "correct": 1
    },
    {
        "q": "In 'Squid Game', what shape is on the workers' masks who are soldiers?",
        "options": ["Circle", "Square", "Triangle", "Star"],
        "correct": 2
    },
    {
        "q": "Who is the lead character in 'The Witcher'?",
        "options": ["Jaskier", "Yennefer", "Geralt of Rivia", "Ciri"],
        "correct": 2
    }
]

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
    print(f"Player connected: {sid}")

@sio.event
async def join_game(sid, data):
    name = data.get('name')
    game_db.add_player(sid, name)
    
    # Send success to player
    await sio.emit('join_success', {'is_admin': name.lower() == 'admin'}, to=sid)
    
    # Update everyone's lobby list
    leaderboard = game_db.get_leaderboard()
    await sio.emit('update_lobby', {'players': leaderboard})

@sio.event
async def start_game(sid):
    global game_active, current_question_index
    game_active = True
    current_question_index = 0
    
    # Broadcast to everyone: "Game Starting!"
    await sio.emit('game_started', {})
    
    # Wait 3 seconds then send first question
    await asyncio.sleep(3)
    await send_question()

async def send_question():
    global current_question_index
    if current_question_index < len(QUESTIONS):
        q_data = QUESTIONS[current_question_index]
        # Send question WITHOUT the answer
        await sio.emit('new_question', {
            'q': q_data['q'],
            'options': q_data['options'],
            'total': len(QUESTIONS),
            'current': current_question_index + 1
        })
    else:
        # Game Over
        leaderboard = game_db.get_leaderboard()
        await sio.emit('game_over', {'leaderboard': leaderboard})

@sio.event
async def submit_answer(sid, data):
    # Data comes from frontend: {'answer_index': 0, 'time_left': 12.5}
    answer_idx = data.get('answer_index')
    time_left = data.get('time_left')
    
    correct_idx = QUESTIONS[current_question_index]['correct']
    is_correct = (answer_idx == correct_idx)
    
    # CALL C++ ENGINE FOR HIGH-SPEED SCORING
    new_score = game_db.update_score(sid, is_correct, float(time_left))
    
    # Tell user if they got it right
    await sio.emit('answer_result', {'correct': is_correct, 'score': new_score}, to=sid)

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