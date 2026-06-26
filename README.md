# 🖐️ GestureHUD PRO v2.0

> **Real-time hand tracking · Gesture recognition · System control · Cyberpunk HUD**  
> Built with OpenCV + MediaPipe — runs on your laptop webcam, zero GPU required.

![Python](https://img.shields.io/badge/Python-3.8–3.11-blue?style=flat-square&logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-green?style=flat-square)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Win%20%7C%20Mac%20%7C%20Linux-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## ✨ What's New in v2.0

| Feature | v1 | v2 |
|---|:---:|:---:|
| Basic gesture recognition | ✅ | ✅ |
| Cyberpunk HUD panels | ✅ | ✅ |
| **Gesture-controlled mouse** | ❌ | ✅ |
| **Volume / brightness control** | ❌ | ✅ |
| **Air drawing canvas** | ❌ | ✅ |
| **Media controls** | ❌ | ✅ |
| **Fruit Ninja game mode** | ❌ | ✅ |
| **Neon finger trails** | ❌ | ✅ |
| **Particle effects** | ❌ | ✅ |
| **Animated radar scanner** | ❌ | ✅ |
| **Confidence % display** | ❌ | ✅ |
| **CPU / RAM overlay** | ❌ | ✅ |
| **Custom gesture training** | ❌ | ✅ |
| **Swipe left/right detection** | ❌ | ✅ |
| **Screenshot with gesture** | ❌ | ✅ |

---

## 🎮 Gesture Reference

| Gesture | Symbol | Mouse | Volume | Draw | Media | Game |
|---|:---:|---|---|---|---|---|
| Open Palm | ✋ | Swipe slides | — | Pause | — | — |
| Point | ☝️ | Move cursor | Vol ↑ | **Draw** | Next track | Slice |
| Fist | ✊ | Hold | Vol ↓ | Pause draw | Stop | — |
| Peace | ✌️ | Screenshot | — | Change color | Prev track | — |
| Thumbs Up | 👍 | — | Mute | — | Play/Pause | — |
| OK Sign | 👌 | Left click | Confirm | Clear canvas | — | — |
| Pinch | 🤏 | — | Fine volume | — | — | — |
| Rock On | 🤘 | Right click | — | Special | — | — |
| Swipe Left | 👋← | ← Arrow | — | — | — | — |
| Swipe Right | 👋→ | → Arrow | — | — | — | — |

---

## 🖥️ Modes

Switch modes with **`M`** key:

```
MOUSE  →  VOLUME  →  DRAW  →  MEDIA  →  GAME  →  MOUSE  →  ...
```

### 🖱️ MOUSE Mode
Control your entire computer with gestures:
- **POINT** — Move cursor (index finger = mouse pointer)
- **OK** — Left click
- **ROCK ON** — Right click
- **PEACE** — Take screenshot
- **OPEN PALM + swipe** — Arrow keys (slide navigation)

### 🔊 VOLUME Mode
- **PINCH** — Fine-tune volume (pinch distance = volume level)
- **POINT** — Volume up
- **FIST** — Volume down
- **THUMBS UP** — Mute/unmute

### 🎨 DRAW Mode
Air-draw on screen with your finger:
- **POINT** — Draw (index finger = brush)
- **PEACE** — Cycle brush color (Cyan → Red → Green → Purple → Yellow)
- **FIST** — Lift brush (pause drawing)
- **OK** — Clear canvas

### 🎵 MEDIA Mode
Control Spotify, YouTube, VLC, anything:
- **THUMBS UP** — Play / Pause
- **POINT** — Next track
- **PEACE** — Previous track
- **FIST** — Stop

### 🎮 GAME Mode
Fruit Ninja–style gesture game:
- **POINT** — Slice falling targets
- Targets fall faster over time
- Score tracked live on HUD

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/gesture-hud.git
cd gesture-hud
```

### 2. Install

```bash
pip install -r requirements.txt
```

> **Python 3.8–3.11 required.** MediaPipe does not yet support 3.12+.

> **macOS users:** If pyautogui fails, grant Terminal accessibility permissions in  
> System Settings → Privacy & Security → Accessibility.

### 3. Run

```bash
python src/main.py
```

---

## 🌐 React Web Application (New Air-Drawing Canvas)

In addition to the Python application, we have introduced a brand new **React-based Air-Drawing Canvas** built with Vite and MediaPipe Tasks Vision. It runs directly in your browser with a sleek Cyberpunk UI!

### Running the Web App

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open the `localhost` URL in your browser and allow webcam access.

### Web Features
- **Pure JavaScript Hand Tracking** using `@mediapipe/tasks-vision`.
- **Cyberpunk UI** with neon colors and monospace typography.
- **Real-time drawing** by holding up your index finger.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|---|---|
| `M` | Cycle modes |
| `D` | Toggle air-draw canvas |
| `C` | Clear canvas |
| `S` | Screenshot |
| `T` | Train custom gesture (hold 3s) |
| `H` | Toggle help overlay |
| `Q` | Quit |

---

## 🧠 Custom Gesture Training

Train your own gestures:

1. Press **`T`** to start training
2. Hold your custom hand pose for **3 seconds**
3. The gesture is saved to `profiles/custom_gestures.json`
4. It will be detected automatically next run

```json
// profiles/custom_gestures.json (auto-generated)
{
  "GESTURE_1": { "fingers": [true, false, true, false, true] },
  "GESTURE_2": { "fingers": [false, true, true, true, false] }
}
```

---

## 📁 Project Structure

```
gesture-hud/
├── src/
│   └── main.py              # Full application (single file)
├── profiles/
│   └── custom_gestures.json # Auto-generated custom gestures
├── docs/
│   └── demo.gif             # Add your demo here
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛠️ How It Works

```
Webcam Frame
     │
     ▼
MediaPipe Hands ──► 21 Landmarks (x, y, z)
     │
     ├──► fingers_up()       ──► bool[5] finger states
     │
     ├──► classify_gesture() ──► (label, confidence %)
     │         │
     │         └──► Custom profiles checked first
     │
     ├──► Mode dispatcher    ──► Mouse / Volume / Draw / Media / Game
     │
     └──► HUD renderer       ──► Panels + Radar + Trails + Particles
```

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `mediapipe` | 21-point hand landmark detection |
| `opencv-python` | Camera capture + rendering |
| `numpy` | Array math, shape drawing |
| `pyautogui` | Mouse, keyboard, screenshot control |
| `psutil` | CPU / RAM monitoring |

---

## 🔧 Tuning

In `src/main.py`:

```python
mp_hands.Hands(
    model_complexity=1,           # 0=fast, 1=accurate
    max_num_hands=2,              # support two hands
    min_detection_confidence=0.72,
    min_tracking_confidence=0.65,
)
```

```python
# Gesture smoothing window
gesture_hist = deque(maxlen=10)   # increase = smoother, slower
```

---

## 🤝 Contributing

Pull requests welcome! Ideas for v3:

- [ ] Eye tracking (MediaPipe FaceMesh)
- [ ] Full body pose gestures (MediaPipe Pose)
- [ ] Voice + gesture combined commands
- [ ] AR holographic overlays
- [ ] Multi-user tracking
- [ ] Gesture password unlock

---

## 📄 License

MIT © Balkrishan — SBMPCE Mumbai
