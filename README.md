# GestureHUD

GestureHUD is a webcam-based hand-gesture controller built with **Python + OpenCV + MediaPipe**.
It lets you control system actions (mouse, media, volume), draw in the air, and use a HUD-based game mode.

## Features

- Real-time hand landmark tracking (MediaPipe Hands)
- Gesture classification with confidence display
- Multiple modes: **Mouse**, **Volume**, **Draw**, **Media**, **Game**
- Air-drawing canvas with color switching and clear gesture
- Gesture-triggered screenshot capture
- Custom gesture training saved to local profile
- Optional React web canvas in `/frontend`

## Repository Structure

```
Gesture-hud/
├── src/
│   └── main.py
├── frontend/
│   ├── src/
│   └── package.json
├── requirements.txt
└── README.md
```

## Python App Setup

### 1) Clone and enter the repository

```bash
git clone https://github.com/balkrishan99/Gesture-hud.git
cd Gesture-hud
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run

```bash
python src/main.py
```

## Keyboard Shortcuts

- `M` → Cycle modes
- `D` → Toggle draw canvas
- `C` → Clear canvas
- `S` → Take screenshot
- `T` → Train custom gesture (hold pose)
- `H` → Toggle help panel
- `Q` → Quit

## Frontend (React Canvas)

See `/home/runner/work/Gesture-hud/Gesture-hud/frontend/README.md` for web app setup and usage.

## Dependencies

Core Python dependencies are listed in `/home/runner/work/Gesture-hud/Gesture-hud/requirements.txt`:

- `mediapipe`
- `opencv-python`
- `numpy`
- `pyautogui`
- `psutil`

## License

MIT
