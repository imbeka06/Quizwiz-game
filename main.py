# ==============================================================================
#  META-LEVEL TRIVIA OS | ENTERPRISE EDITION v11.0 (ULTIMATE)
#  ARCHITECT: GEMINI | TARGET: PRODUCTION
# ==============================================================================

import eventlet
eventlet.monkey_patch()

import logging
import random
import time
import json
import re
import os
import uuid
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

# --- PDF LIBRARY CHECK ---
# We try to import PyPDF2. If it fails, we warn the user but don't crash.
try:
    import PyPDF2
    PDF_ENABLED = True
except ImportError:
    PyPDF2 = None
    PDF_ENABLED = False
    print("!! SYSTEM WARNING: PyPDF2 not installed. PDF parsing disabled. Run: pip install PyPDF2 !!")

# ==============================================================================
#  1. SYSTEM CONFIGURATION
# ==============================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Meta_Galactic_Secret_Key_Final_X99_Ultra'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB Max Upload for PDFs
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configure Enterprise Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] TRIVIA_OS: %(message)s')
logger = logging.getLogger("TriviaCore")

# ==============================================================================
#  2. DATA & CONTENT LAYER
# ==============================================================================

class ContentManager:
    """ Manages static data, default questions, and dynamic insults. """
    
    ROASTS = {
        'low': [
            "My grandmother types faster than that.", 
            "Did you panic? You looked like you panicked.",
            "Are you playing with your elbows?", 
            "I've seen smarter toast.",
            "Participation trophies for everyone at the bottom!", 
            "System Error: User intelligence not found.",
            "Yikes. Just... yikes."
        ],
        'mid': [
            "Mediocrity achieved. Congratulations.", 
            "Not terrible. Not great. Just... there.",
            "You're the vanilla ice cream of trivia players.", 
            "Safe. Boring. Middle of the pack.",
            "Keep trying, you might reach 'average' soon."
        ],
        'high': [
            "Okay, who is cheating?", 
            "Touch grass, nerd.", 
            "Big brain energy detected.",
            "Don't get cocky, it's just trivia.",
            "Impressive. Most impressive."
        ]
    }

    DEFAULTS = [
        {"q": "Who is the CEO of Meta?", "opts": ["Elon Musk", "Mark Zuckerberg", "Jeff Bezos", "Bill Gates"], "a": 1},
        {"q": "Capital of France?", "opts": ["Berlin", "Madrid", "Paris", "Rome"], "a": 2},
        {"q": "Red Planet?", "opts": ["Earth", "Mars", "Jupiter", "Venus"], "a": 1},
        {"q": "Bits in a Byte?", "opts": ["4", "8", "16", "32"], "a": 1},
        {"q": "Largest Ocean?", "opts": ["Atlantic", "Indian", "Arctic", "Pacific"], "a": 3}
    ]

    @staticmethod
    def get_roast(score_tier):
        """ Returns a random roast based on the score tier. """
        return random.choice(ContentManager.ROASTS.get(score_tier, ContentManager.ROASTS['mid']))

# ==============================================================================
#  3. INTELLIGENT PARSER ENGINE (PDF/TEXT)
# ==============================================================================
class DataParser:
    """ 
    AI-Lite Logic to extract structured data from raw unstructured text.
    Handles regex matching for questions, options (A/B/C/D), and answers.
    """
    
    @staticmethod
    def parse_raw_text(text):
        questions = []
        # Split text into blocks based on double newlines OR numbered lists (1., 2., etc)
        # This regex looks for double newlines OR a digit followed by a dot/paren at the start of a line
        blocks = re.split(r'\n\s*\n|(?=\n\d+[\.)])', text)
        
        for block in blocks:
            if not block.strip(): continue
            
            # Clean up lines
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            
            # We need at least a question and some options
            if len(lines) < 3: continue 

            # 1. Question Parsing (First line usually)
            # Remove leading "1.", "Q1:", etc.
            q_text = re.sub(r'^\d+[\.:\)]\s*|^Q\d+[:\.]\s*', '', lines[0], flags=re.IGNORECASE)
            
            # 2. Options & Answer Parsing
            options = []
            ans_idx = 0 # Default to A if not found
            
            for line in lines[1:]:
                # Check for Answer Key lines like "Answer: A" or "Correct: B"
                if "ANSWER:" in line.upper() or "CORRECT:" in line.upper():
                    # Extract the last character (A, B, C, or D)
                    parts = line.split(':')
                    if len(parts) > 1:
                        char = parts[-1].strip().upper()
                        # Map Letter to Index
                        ans_idx = {'A':0, 'B':1, 'C':2, 'D':3}.get(char[0], 0)
                    continue
                
                # Check for Options (A. B. C. D.)
                # Regex looks for "A." or "a)" at start of line
                if re.match(r'^[A-D][\.\)]', line, re.IGNORECASE):
                    # Remove the "A." part to get just the text
                    val = re.sub(r'^[A-D][\.\)]\s*', '', line, flags=re.IGNORECASE).strip()
                    options.append(val)
            
            # Validation: Ensure we have exactly 4 options for the UI
            # If less, fill with placeholders. If more, slice.
            while len(options) < 4: 
                options.append(f"Option {len(options)+1}")
            
            questions.append({
                "q": q_text, 
                "opts": options[:4], 
                "a": ans_idx
            })
            
        return questions

    @staticmethod
    def parse_pdf(file_storage):
        """ Reads PDF Stream and converts to text for parsing """
        if not PDF_ENABLED: return []
        try:
            reader = PyPDF2.PdfReader(file_storage)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            return DataParser.parse_raw_text(full_text)
        except Exception as e:
            logger.error(f"PDF Parse Error: {e}")
            return []

# ==============================================================================
#  4. GAME LOGIC ARCHITECTURE
# ==============================================================================

class Player:
    """ Represents a single user session """
    def __init__(self, sid, name, avatar, is_admin=False):
        self.sid = sid
        self.name = name
        self.avatar = avatar
        self.score = 0
        self.streak = 0
        self.is_admin = is_admin
        self.has_answered = False

    def to_dict(self):
        # Format for frontend: [Name, Score, Avatar, Streak]
        return [self.name, self.score, self.avatar, self.streak]

class GameEngine:
    """ Singleton Game State Manager """
    def __init__(self):
        self.players = {}
        self.questions = []
        self.q_index = 0
        self.active = False
        self.config = {'limit': 10, 'time': 15}
        self.use_custom = False

    def join(self, sid, name, avatar, force_admin):
        # Logic: If name contains 'Admin' or force_admin is True, grant privileges
        is_admin = force_admin or "ADMIN" in name.upper() or "HOST" in name.upper()
        p = Player(sid, name, avatar, is_admin)
        self.players[sid] = p
        logger.info(f"Player Joined: {name} (Admin: {is_admin})")
        return p

    def leave(self, sid):
        if sid in self.players: 
            logger.info(f"Player Left: {self.players[sid].name}")
            del self.players[sid]

    def add_questions(self, q_list):
        """ Adds bulk questions from PDF/Text import to the FRONT of the queue """
        self.questions = q_list + self.questions
        self.use_custom = True
        logger.info(f"Bulk Import: {len(q_list)} questions added.")

    def start(self, limit, time):
        self.config['limit'] = int(limit)
        self.config['time'] = int(time)
        self.q_index = 0
        self.active = True
        
        # Load Defaults if empty
        if not self.questions:
            self.questions = list(ContentManager.DEFAULTS)
            random.shuffle(self.questions)
            
        # Reset Players stats for new game
        for p in self.players.values(): 
            p.score = 0; p.streak = 0; p.has_answered = False
            
        logger.info("Game Sequence Initiated")

    def submit(self, sid, idx, t_left):
        p = self.players.get(sid)
        if not p or not self.active or p.has_answered: return
        
        q = self.questions[self.q_index] if self.q_index < len(self.questions) else None
        
        if q and idx == q['a']:
            # Scoring Algorithm: 
            # Base(1000) + TimeBonus(0-500) + StreakBonus(50 per streak)
            pts = 1000 + int(float(t_left)*10) + (p.streak*50)
            p.score += pts
            p.streak += 1
        else:
            p.streak = 0 # Reset streak on wrong answer
            
        p.has_answered = True

    def next(self):
        self.q_index += 1
        # Reset answer flags for next round
        for p in self.players.values(): p.has_answered = False
        
        # Check if game should continue
        valid_idx = self.q_index < len(self.questions)
        within_limit = self.q_index < self.config['limit']
        return valid_idx and within_limit

    def get_leaderboard(self):
        # Sort by score descending
        s = sorted(self.players.values(), key=lambda x: x.score, reverse=True)
        return [p.to_dict() for p in s]

# Initialize Global Game Engine
engine = GameEngine()

# ==============================================================================
#  5. ROUTES & API
# ==============================================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_parse', methods=['POST'])
def handle_upload():
    """ 
    AJAX Endpoint for parsing data without reloading page.
    Handles Raw Text or PDF Files.
    """
    data = []
    try:
        # Check 1: Raw Text Paste
        if 'raw_text' in request.form and request.form['raw_text'].strip():
            data = DataParser.parse_raw_text(request.form['raw_text'])
            
        # Check 2: File Upload
        elif 'file' in request.files:
            f = request.files['file']
            if f.filename.endswith('.pdf'):
                data = DataParser.parse_pdf(f)
        
        return jsonify({'status': 'success', 'count': len(data), 'questions': data})
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# ==============================================================================
#  6. SOCKET EVENTS
# ==============================================================================

@socketio.on('join_game')
def on_join(d):
    # Register Player
    p = engine.join(request.sid, d.get('name'), d.get('avatar'), d.get('force_admin'))
    join_room('game_room')
    
    # 1. Private Confirmation (Tells client if they are Admin)
    emit('join_success', {'is_admin': p.is_admin, 'sid': request.sid}, to=request.sid)
    
    # 2. Public Broadcast (Update Lobby for everyone)
    emit('update_lobby', {'players': engine.get_leaderboard()}, to='game_room')

@socketio.on('disconnect')
def on_disconnect():
    engine.leave(request.sid)
    emit('update_lobby', {'players': engine.get_leaderboard()}, to='game_room')

@socketio.on('admin_bulk_import')
def on_import(d):
    # Receive verified questions from frontend and add to engine
    engine.add_questions(d.get('questions', []))
    emit('admin_msg', {'msg': f"DATABASE UPDATED: {len(d['questions'])} QUESTIONS ADDED"}, to=request.sid)

@socketio.on('admin_start_game')
def on_start(d):
    engine.start(d.get('limit'), d.get('time'))
    emit('game_started', {}, to='game_room')
    # Delay for visual effect
    socketio.sleep(1)
    send_q_payload()

@socketio.on('submit_answer')
def on_ans(d):
    engine.submit(request.sid, d['answer_index'], d['time_left'])

@socketio.on('admin_next_question')
def on_next():
    if engine.next():
        send_q_payload()
    else:
        # Game Over
        emit('game_over', {'leaderboard': engine.get_leaderboard()}, to='game_room')

@socketio.on('admin_show_scores')
def on_scores():
    board = engine.get_leaderboard()
    
    # Calculate Roast Tier based on top score
    top = board[0][1] if board else 0
    tier = 'high' if top > 8000 else ('mid' if top > 3000 else 'low')
    roast = ContentManager.get_roast(tier)
    
    emit('show_intermediate_results', {
        'leaderboard': board, 
        'roast': roast,
        'title': "ROUND ANALYSIS"
    }, to='game_room')

def send_q_payload():
    """ Helper to send question data to all clients """
    q = engine.questions[engine.q_index]
    socketio.emit('new_question', {
        'q': q['q'], 
        'options': q['opts'], 
        'time': engine.config['time'],
        'current': engine.q_index + 1, 
        'total': engine.config['limit']
    }, to='game_room')

if __name__ == '__main__':
    print("---------------------------------------------------------")
    print(" META TRIVIA OS [ONLINE] | PORT 5000")
    print(" PDF SUPPORT: " + ("ENABLED" if PDF_ENABLED else "DISABLED"))
    print("---------------------------------------------------------")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)