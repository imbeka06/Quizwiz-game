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
custom_questions = [] 
previous_leader = None # To track if the leader changes

# --- ROAST DATABASE ---
ROASTS = [
    "Are you still leading? Or just lucky?",
    "Seems he is competing with low key fools. Pick on someone your own size!",
    "You might have thought since you began at the top you will finish at the top... Oops!",
    "Is this a quiz or a nap? Wake up people!",
    "Someone call the police, because [LEADER] is murdering the competition!",
    "Look at the bottom of the list... it's cold down there, wear a sweater.",
    "Are we sure [LEADER] isn't cheating? Just asking for a friend.",
    "A moment of silence for those with 0 points... okay moment over."
]

# --- CONTENT DB (Fallback) ---
CONTENT_DB = {
    "mixed": [
        {"q": "What is the capital of Kenya?", "options": ["Mombasa", "Kisumu", "Nairobi", "Nakuru"], "correct": 2, "diff": 1},
        {"q": "Complete the lyric: 'Wamlambez, ____'", "options": ["Wamnyonyez", "Wamtoboez", "Wamchezez", "Hakuna"], "correct": 0, "diff": 1},
        {"q": "Who is the GOAT of Marathons?", "options": ["Bolt", "Kipchoge", "Bekele", "Farah"], "correct": 1, "diff": 1},
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
    await broadcast_lobby()

@sio.event
async def admin_start_game(sid, data):
    global active_questions, current_question_index, previous_leader
    limit = int(data.get('limit', 5))
    use_custom = data.get('use_custom', False)
    
    if use_custom and len(custom_questions) > 0:
        pool = custom_questions
    else:
        pool = CONTENT_DB['mixed']
        # Add fallback logic if custom is empty but requested? For now just use pool.
    
    random.shuffle(pool)
    active_questions = pool[:limit]
    current_question_index = 0
    previous_leader = None
    
    await sio.emit('game_started', {'total_q': len(active_questions)})
    await asyncio.sleep(4) 
    await send_question()

@sio.event
async def add_custom_question(sid, data):
    new_q = {
        "q": data.get('q'),
        "options": [data.get('o1'), data.get('o2'), data.get('o3'), data.get('o4')],
        "correct": int(data.get('correct')),
        "diff": 2 # Default medium
    }
    custom_questions.append(new_q)
    print(f"Added Q: {new_q['q']}")

# --- GAME LOOP LOGIC ---

async def send_question():
    if current_question_index < len(active_questions):
        q_data = active_questions[current_question_index]
        time_limit = 10 + (q_data['diff'] * 10) # 20s, 30s, 40s
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
        # Final Game Over
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
async def admin_show_scores(sid):
    # 1. Get Leaderboard
    leaderboard = game_db.get_leaderboard()
    
    # 2. Roast Logic
    global previous_leader, current_question_index
    roast_msg = ""
    
    if leaderboard:
        current_leader_name = leaderboard[0][0]
        
        # Every 3 questions, or if leader changed
        if (current_question_index + 1) % 3 == 0: 
            raw_roast = random.choice(ROASTS)
            roast_msg = raw_roast.replace("[LEADER]", current_leader_name)
            
            # Specific check: Same leader?
            if previous_leader and current_leader_name == previous_leader:
                roast_msg = f"Do you think {current_leader_name} is still leading? Yes, unfortunately. Competing with low key fools!"
            elif previous_leader and current_leader_name != previous_leader:
                roast_msg = f"Oops! {previous_leader} fell off! {current_leader_name} is the new captain now!"
        
        previous_leader = current_leader_name

    # 3. Send "Intermediate Results" event
    await sio.emit('show_intermediate_results', {
        'leaderboard': leaderboard,
        'roast': roast_msg
    })

@sio.event
async def admin_next_question(sid):
    global current_question_index
    current_question_index += 1
    await send_question()

async def broadcast_lobby():
    leaderboard = game_db.get_leaderboard()
    await sio.emit('update_lobby', {'players': leaderboard})

@sio.event
async def disconnect(sid):
    game_db.remove_player(sid)
    await broadcast_lobby()

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)