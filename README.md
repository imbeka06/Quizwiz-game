# 🧠 QuizWiz: Enterprise Edition (v14.0)
### * Trivia Operating System*

> **"Not just a game. A high-performance, real-time event engine."**

QuizWiz is a production-grade, WebSocket-based trivia platform designed for seamless multiplayer experiences. It features a reactive 3D visual engine, intelligent AI-lite data parsing for question generation, and a robust admin command center. Built for speed, scale, and visual impact.

---

## ✨ Key Features

### 🚀 **Core Technology**
* **Real-Time Latency:** Powered by `Flask-SocketIO` and `Eventlet` for instant state synchronization across hundreds of clients.
* **Intelligent Data Uplink:** Drag-and-drop a **PDF** or paste raw text, and the system auto-parses questions, options, and answers using Regex and Logic patterns.
* **Security:** 4-Character Room Codes and dynamic QR Code generation to secure game lobbies.

### 🎨 **Visual & Audio Engine**
* **Reactive 3D Backgrounds:** A `Three.js` particle system that shifts states (Idle → Matrix Rain → Warp Speed → Gold Dust) based on game events.
* **Cyberpunk/Netflix Aesthetic:** Glassmorphism UI, Neon glows, and "glitch" typography.
* **Adaptive Audio:** Background music cross-fading and SFX triggers for a cinematic feel.
* **Mobile-Perfect:** Fully responsive design with `viewport-fit=cover` for native-app feel on phones.

### 🎮 **Gamification**
* **Advanced Scoring:** Algorithms calculate points based on **Speed + Accuracy + Streak Multipliers**.
* **Dynamic Roasts:** The system analyzes score tiers and delivers sassy, context-aware insults to players on the leaderboard.
* **Identity System:** Avatar selector with persistent session tracking.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.10+, Flask, Socket.IO, PyPDF2, Qrcode
* **Architecture:** C++ (Core Logic Design & Performance Patterns)
* **Frontend:** HTML5, CSS3 (Variables + Animations), Vanilla JavaScript
* **Visuals:** Three.js (WebGL), Canvas Confetti
* **Server:** Gunicorn with Eventlet Workers

---

## 📂 Project Structure

```text
/QuizWiz_Project
├── main.py                 # The Brain (Game Engine, Socket Logic, PDF Parser)
├── requirements.txt        # Dependency Manifest
├── Procfile                # Production Start Command (Gunicorn)
├── README.md               # Documentation
└── static/
    ├── audio/              # SFX & Music Assets (tadum.mp3, game.mp3, etc.)
    └── templates/
        └── index.html      # The Client (Visual State Machine)
⚡ Quick Start (Local)
Clone the Repository

Bash

git clone [https://github.com/yourusername/quizwiz.git](https://github.com/yourusername/quizwiz.git)
cd quizwiz
Install Dependencies

Bash

pip install -r requirements.txt
Launch the System

Bash

python main.py
Access the Uplink at: http://localhost:5000

☁️ Deployment (Render/Railway)
This project is configured for cloud deployment.

Build Command:

Bash

pip install -r requirements.txt
Start Command:

Bash

gunicorn --worker-class eventlet -w 1 main:app
(Note: Ensure your main python file is named main.py)

🕹️ User Manual
For the Host (Admin)
Login: Check the "HOST OVERRIDE" box on the login screen.

Lobby: You will see the Command Center.

Config Tab: Set question limits and timer duration.

Data Uplink Tab: Upload a PDF or paste text to auto-generate questions.

QR Code: Display the QR code on a big screen for players to scan.

Control: Use the floating "Live Control" buttons to advance questions or show scores.

For Players
Join: Scan the QR code or enter the 4-letter Room Code.

Identity: Pick a Sci-Fi Avatar and enter a Codename.

Play: Answer questions before the timer bar depletes to maximize points.

📜 Credits
Architect & Developer: [Imbeka Musa]

UI/UX Concept: Cyberpunk & Streaming aesthetics.

Visual Engines: Powered by Three.js & Canvas-Confetti.

"System Online. Waiting for input..."
