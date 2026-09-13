"""
╔══════════════════════════════════════════════════════════════╗
║            GestureHUD PRO v2.0  —  by Balkrishan            ║
║   Hand Tracking · Gesture Control · Cyberpunk HUD · AI      ║
╚══════════════════════════════════════════════════════════════╝

Modes:
  M      → Cycle modes (MOUSE / VOLUME / DRAW / MEDIA / GAME)
  D      → Toggle air-drawing canvas
  C      → Clear drawing canvas
  S      → Screenshot
  T      → Train custom gesture (hold 3s)
  Q      → Quit
"""

import cv2
import mediapipe as mp
import numpy as np
import time, math, json, os, platform, random, psutil
from collections import deque
from datetime import datetime

# ── Optional system control (graceful degradation) ────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    MOUSE_OK = True
except Exception:
    MOUSE_OK = False

try:
    if platform.system() == "Windows":
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        VOLUME_OK = True
    elif platform.system() == "Darwin":
        import subprocess
        VOLUME_OK = True
    else:
        import subprocess
        VOLUME_OK = True
except:
    VOLUME_OK = False

# ── MediaPipe ─────────────────────────────────────────────────
mp_hands = mp.solutions.hands
mp_pose  = mp.solutions.pose

# ═══════════════════════════════════════════════════════════════
#  COLOR PALETTE  (BGR)
# ═══════════════════════════════════════════════════════════════
C = {
    "cyan":    (255, 230,  30),
    "blue":    (255, 150,  30),
    "red":     ( 30,  30, 255),
    "green":   ( 30, 220,  80),
    "purple":  (220,  50, 220),
    "yellow":  (  0, 220, 255),
    "white":   (255, 255, 255),
    "dim":     ( 60,  60,  80),
    "orange":  ( 20, 140, 255),
    "pink":    (180,  80, 220),
}

MODES = ["MOUSE", "VOLUME", "DRAW", "MEDIA", "GAME"]
MODE_COLORS = {
    "MOUSE":  C["cyan"],
    "VOLUME": C["green"],
    "DRAW":   C["purple"],
    "MEDIA":  C["yellow"],
    "GAME":   C["red"],
}

PROFILES_PATH = os.path.join(os.path.dirname(__file__), "..", "profiles", "custom_gestures.json")

# ═══════════════════════════════════════════════════════════════
#  GESTURE ENGINE
# ═══════════════════════════════════════════════════════════════
def fingers_up(lm_list, handedness="Right"):
    up = []
    if handedness == "Right":
        up.append(lm_list[4].x < lm_list[3].x)
    else:
        up.append(lm_list[4].x > lm_list[3].x)
    for tip, pip in zip([8,12,16,20],[6,10,14,18]):
        up.append(lm_list[tip].y < lm_list[pip].y)
    return up


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def classify_gesture(up, lm, custom_profiles=None):
    """Returns (gesture_name, confidence_0_to_1)."""
    lm = lm.landmark
    total = sum(up)

    # Check custom trained gestures first
    if custom_profiles:
        for name, profile in custom_profiles.items():
            if profile["fingers"] == up:
                return name, 0.95

    # Built-in gestures
    if total == 0:
        return "FIST", 0.98
    if total == 5:
        return "OPEN PALM", 0.99

    # THUMBS UP: only thumb up, hand oriented upright
    if up[0] and not any(up[1:]):
        return "THUMBS UP", 0.97

    # POINT: only index
    if up[1] and not up[2] and not up[3] and not up[4]:
        return "POINT", 0.98

    # PEACE: index + middle
    if up[1] and up[2] and not up[3] and not up[4]:
        return "PEACE", 0.97

    # ROCK ON
    if up[0] and up[4] and not up[1] and not up[2] and not up[3]:
        return "ROCK ON", 0.96

    # OK SIGN: thumb + index tip close, others spread
    ok_dist = dist(lm[4], lm[8])
    if ok_dist < 0.05 and up[2] and up[3] and up[4]:
        return "OK", 0.94

    # PINCH: thumb + index close, no others
    if ok_dist < 0.06 and not up[2] and not up[3] and not up[4]:
        return "PINCH", 0.93

    # THREE
    if up[1] and up[2] and up[3] and not up[4]:
        return "THREE", 0.95

    # FOUR
    if not up[0] and up[1] and up[2] and up[3] and up[4]:
        return "FOUR", 0.95

    # CALL ME
    if up[0] and up[4] and not up[1] and not up[2] and not up[3]:
        return "CALL ME", 0.94

    # PINKY
    if not any(up[:4]) and up[4]:
        return "PINKY", 0.93

    return "CUSTOM", 0.60


# ═══════════════════════════════════════════════════════════════
#  SYSTEM CONTROL
# ═══════════════════════════════════════════════════════════════
class SystemControl:
    def __init__(self):
        self.screen_w, self.screen_h = 1920, 1080
        if MOUSE_OK:
            self.screen_w, self.screen_h = pyautogui.size()
        self.last_action_time = 0
        self.cooldown = 0.4
        self._volume_cache = 50

    def _can_act(self):
        now = time.time()
        if now - self.last_action_time > self.cooldown:
            self.last_action_time = now
            return True
        return False

    def move_mouse(self, norm_x, norm_y):
        if not MOUSE_OK: return
        sx = int(norm_x * self.screen_w)
        sy = int(norm_y * self.screen_h)
        pyautogui.moveTo(sx, sy, duration=0)

    def left_click(self):
        if MOUSE_OK and self._can_act():
            pyautogui.click()
            return True
        return False

    def right_click(self):
        if MOUSE_OK and self._can_act():
            pyautogui.rightClick()
            return True
        return False

    def set_volume(self, level_0_100):
        level_0_100 = max(0, min(100, level_0_100))
        self._volume_cache = level_0_100
        try:
            if platform.system() == "Darwin":
                os.system(f"osascript -e 'set volume output volume {level_0_100}'")
            elif platform.system() == "Linux":
                os.system(f"amixer -q sset Master {level_0_100}%")
            elif platform.system() == "Windows":
                pass  # pycaw integration
        except: pass
        return level_0_100

    def get_volume(self):
        return self._volume_cache

    def media_action(self, action):
        if not MOUSE_OK or not self._can_act(): return
        actions = {
            "play_pause": "playpause",
            "next": "nexttrack",
            "prev": "prevtrack",
        }
        if action in actions:
            pyautogui.press(actions[action])

    def screenshot(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Desktop/gesture_shot_{ts}.png")
        if MOUSE_OK:
            pyautogui.screenshot(path)
        return path


# ═══════════════════════════════════════════════════════════════
#  PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=6):
        for _ in range(count):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(1, 5)
            self.particles.append({
                "x": float(x), "y": float(y),
                "vx": math.cos(angle)*speed,
                "vy": math.sin(angle)*speed,
                "life": 1.0,
                "decay": random.uniform(0.04, 0.10),
                "size": random.randint(2, 5),
                "color": color,
            })

    def update_draw(self, frame):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.12   # gravity
            p["life"] -= p["decay"]
            if p["life"] > 0:
                alpha = p["life"]
                col = tuple(int(c * alpha) for c in p["color"])
                cx, cy = int(p["x"]), int(p["y"])
                if 0 <= cx < frame.shape[1] and 0 <= cy < frame.shape[0]:
                    cv2.circle(frame, (cx, cy), p["size"], col, -1, cv2.LINE_AA)
                alive.append(p)
        self.particles = alive


# ═══════════════════════════════════════════════════════════════
#  NEON TRAILS
# ═══════════════════════════════════════════════════════════════
class NeonTrail:
    def __init__(self, maxlen=24):
        self.points = deque(maxlen=maxlen)
        self.colors = deque(maxlen=maxlen)

    def add(self, pt, color):
        self.points.append(pt)
        self.colors.append(color)

    def draw(self, frame):
        pts = list(self.points)
        cols = list(self.colors)
        for i in range(1, len(pts)):
            alpha = i / len(pts)
            thickness = max(1, int(alpha * 4))
            col = tuple(int(c * alpha) for c in cols[i])
            cv2.line(frame, pts[i-1], pts[i], col, thickness, cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════
#  HUD RENDERER
# ═══════════════════════════════════════════════════════════════
class HUD:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.radar_angle = 0
        self.alert_msg = ""
        self.alert_timer = 0

    def alert(self, msg, duration=2.0):
        self.alert_msg = msg
        self.alert_timer = time.time() + duration

    # ── Primitives ──────────────────────────────────────────────
    def panel(self, frame, x, y, w, h, color, alpha=0.18, title=""):
        ov = frame.copy()
        cv2.rectangle(ov, (x,y), (x+w,y+h), color, -1)
        cv2.addWeighted(ov, alpha, frame, 1-alpha, 0, frame)
        self._brackets(frame, x, y, w, h, color)
        if title:
            cv2.putText(frame, title, (x+6, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    def _brackets(self, frame, x, y, w, h, col, sz=16, th=2):
        for pts in [
            ((x,y+sz),(x,y),(x+sz,y)),
            ((x+w-sz,y),(x+w,y),(x+w,y+sz)),
            ((x+w,y+h-sz),(x+w,y+h),(x+w-sz,y+h)),
            ((x+sz,y+h),(x,y+h),(x,y+h-sz)),
        ]:
            cv2.polylines(frame, [np.array(pts)], False, col, th)

    def text(self, frame, txt, x, y, color, scale=0.38, thick=1):
        cv2.putText(frame, txt, (x,y), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, thick, cv2.LINE_AA)

    def bar(self, frame, x, y, w, h, pct, fg, bg=(40,40,60)):
        cv2.rectangle(frame, (x,y), (x+w,y+h), bg, -1)
        filled = int(w * max(0, min(1, pct)))
        if filled > 0:
            cv2.rectangle(frame, (x,y), (x+filled,y+h), fg, -1)
        cv2.rectangle(frame, (x,y), (x+w,y+h), fg, 1)

    def dot(self, frame, cx, cy, r, color, label="", active=True):
        if active:
            glow = tuple(min(255,int(c*0.4)) for c in color)
            cv2.circle(frame, (cx,cy), r+4, glow, -1)
        cv2.circle(frame, (cx,cy), r, color if active else C["dim"], -1)
        if label:
            self.text(frame, label, cx+r+5, cy+4, C["white"])

    # ── Radar ───────────────────────────────────────────────────
    def draw_radar(self, frame, cx, cy, r, hand_detected):
        self.radar_angle = (self.radar_angle + 2) % 360
        # Rings
        for ring in [r, r*2//3, r//3]:
            col = C["green"] if hand_detected else C["dim"]
            cv2.circle(frame, (cx,cy), ring, col, 1)
        # Cross
        cv2.line(frame, (cx-r,cy), (cx+r,cy), C["dim"], 1)
        cv2.line(frame, (cx,cy-r), (cx,cy+r), C["dim"], 1)
        # Sweep
        rad = math.radians(self.radar_angle)
        ex = int(cx + r * math.cos(rad))
        ey = int(cy + r * math.sin(rad))
        col = C["green"] if hand_detected else C["dim"]
        cv2.line(frame, (cx,cy), (ex,ey), col, 2, cv2.LINE_AA)
        # Fade trail
        for i in range(1, 60, 4):
            a = math.radians(self.radar_angle - i)
            x2 = int(cx + r * math.cos(a))
            y2 = int(cy + r * math.sin(a))
            alpha = max(0, 1 - i/60)
            trail_col = tuple(int(c*alpha) for c in col)
            cv2.line(frame, (cx,cy), (x2,y2), trail_col, 1)

    # ── Confidence ring ─────────────────────────────────────────
    def conf_ring(self, frame, cx, cy, r, conf, color):
        bg_col = (40,40,60)
        cv2.circle(frame, (cx,cy), r, bg_col, 3)
        angle = int(360 * conf)
        for a in range(-90, -90+angle, 4):
            rad = math.radians(a)
            px = int(cx + r * math.cos(rad))
            py = int(cy + r * math.sin(rad))
            cv2.circle(frame, (px,py), 2, color, -1)

    # ── Scanline ────────────────────────────────────────────────
    def scanline(self, frame, t):
        y = int((t * 80) % self.h)
        cv2.line(frame, (0,y), (self.w,y), (50,50,70), 1)
        cv2.line(frame, (0,(y+2)%self.h), (self.w,(y+2)%self.h), (30,30,50), 1)

    # ── Alert banner ────────────────────────────────────────────
    def draw_alert(self, frame):
        if time.time() < self.alert_timer:
            remaining = self.alert_timer - time.time()
            alpha = min(1.0, remaining)
            ov = frame.copy()
            cv2.rectangle(ov, (self.w//4, self.h//2-30), (self.w*3//4, self.h//2+30),
                          C["yellow"], -1)
            cv2.addWeighted(ov, 0.25*alpha, frame, 1-0.25*alpha, 0, frame)
            self.text(frame, self.alert_msg,
                      self.w//4+10, self.h//2+8, C["yellow"], scale=0.6, thick=2)

    # ── Volume ring ─────────────────────────────────────────────
    def volume_dial(self, frame, cx, cy, r, level, color):
        # Background arc
        for a in range(150, 391):
            rad = math.radians(a)
            px = int(cx + r * math.cos(rad))
            py = int(cy + r * math.sin(rad))
            cv2.circle(frame, (px,py), 2, C["dim"], -1)
        # Filled arc
        filled_end = 150 + int(240 * level / 100)
        for a in range(150, filled_end):
            rad = math.radians(a)
            px = int(cx + r * math.cos(rad))
            py = int(cy + r * math.sin(rad))
            cv2.circle(frame, (px,py), 2, color, -1)
        self.text(frame, f"{level}%", cx-14, cy+6, color, scale=0.5, thick=1)
        self.text(frame, "VOL", cx-12, cy+20, C["dim"], scale=0.32)


# ═══════════════════════════════════════════════════════════════
#  DRAWING CANVAS
# ═══════════════════════════════════════════════════════════════
class DrawCanvas:
    def __init__(self, w, h):
        self.canvas = np.zeros((h, w, 3), dtype=np.uint8)
        self.prev_pt = None
        self.draw_color = C["cyan"]
        self.brush_size = 4
        self.colors_cycle = [C["cyan"], C["red"], C["green"], C["purple"], C["yellow"]]
        self.color_idx = 0

    def draw(self, pt, active):
        if active and self.prev_pt:
            cv2.line(self.canvas, self.prev_pt, pt,
                     self.draw_color, self.brush_size, cv2.LINE_AA)
        self.prev_pt = pt if active else None

    def next_color(self):
        self.color_idx = (self.color_idx + 1) % len(self.colors_cycle)
        self.draw_color = self.colors_cycle[self.color_idx]

    def clear(self):
        self.canvas[:] = 0
        self.prev_pt = None

    def blend(self, frame):
        mask = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, 10, 255, cv2.THRESH_BINARY)
        frame[mask > 0] = self.canvas[mask > 0]


# ═══════════════════════════════════════════════════════════════
#  GAME MODE  (Fruit Ninja style)
# ═══════════════════════════════════════════════════════════════
class GameMode:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.targets = []
        self.score = 0
        self.lives = 3
        self.spawn_timer = 0
        self.spawn_interval = 1.5
        self.particles = ParticleSystem()

    def spawn(self):
        now = time.time()
        if now - self.spawn_timer > self.spawn_interval:
            self.spawn_timer = now
            self.spawn_interval = max(0.6, self.spawn_interval - 0.02)
            x = random.randint(60, self.w - 60)
            color = random.choice(list(C.values()))
            self.targets.append({
                "x": float(x), "y": float(self.h + 30),
                "vy": -random.uniform(6, 12),
                "vx": random.uniform(-2, 2),
                "r": random.randint(25, 45),
                "color": color,
                "sliced": False,
                "birth": now,
            })

    def update(self, frame, finger_tip):
        self.spawn()
        alive = []
        for t in self.targets:
            t["x"] += t["vx"]
            t["y"] += t["vy"]
            t["vy"] += 0.35  # gravity
            cx, cy, r = int(t["x"]), int(t["y"]), t["r"]

            if not t["sliced"]:
                # Draw target
                cv2.circle(frame, (cx,cy), r, t["color"], -1)
                cv2.circle(frame, (cx,cy), r, C["white"], 1)
                # Slice check
                if finger_tip:
                    fx, fy = finger_tip
                    if math.hypot(fx-cx, fy-cy) < r + 10:
                        t["sliced"] = True
                        self.score += 10
                        self.particles.emit(cx, cy, t["color"], count=16)
                        continue

            # Remove off-screen
            if cy > self.h + 60:
                if not t["sliced"]:
                    self.lives -= 1
                continue
            alive.append(t)
        self.targets = alive
        self.particles.update_draw(frame)

    def draw_ui(self, frame, hud):
        hud.text(frame, f"SCORE  {self.score:05d}", 20, 50, C["yellow"], 0.7, 2)
        hud.text(frame, f"LIVES  {'♥ '*self.lives}", 20, 80, C["red"], 0.55, 1)
        hud.text(frame, "GAME MODE — Slice with POINT gesture!", 20, self.h-55,
                 C["yellow"], 0.4, 1)


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════
def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    ret, test = cap.read()
    if not ret:
        print("ERROR: Cannot open webcam.")
        return
    H, W = test.shape[:2]

    # ── Load custom gesture profiles ──────────────────────────
    os.makedirs(os.path.dirname(PROFILES_PATH), exist_ok=True)
    custom_profiles = {}
    if os.path.exists(PROFILES_PATH):
        with open(PROFILES_PATH) as f:
            custom_profiles = json.load(f)

    # ── Init systems ──────────────────────────────────────────
    hud        = HUD(W, H)
    ctrl       = SystemControl()
    canvas     = DrawCanvas(W, H)
    particles  = ParticleSystem()
    game       = GameMode(W, H)
    trail      = NeonTrail(maxlen=30)

    # State
    mode_idx        = 0
    fps_smooth      = 30.0
    prev_time       = time.time()
    gesture_hist    = deque(maxlen=10)
    prev_gesture    = ""
    gesture_conf    = 0.0
    hand_detected   = False
    draw_mode       = False
    pinch_baseline  = None
    swipe_start     = None
    swipe_start_t   = 0
    volume_level    = ctrl.get_volume()
    training_name   = ""
    training_start  = 0
    training_active = False
    last_particle_t = 0
    index_tip_px    = None
    cpu_history     = deque(maxlen=40)
    show_help       = False

    GESTURE_ACTIONS = {
        "MOUSE":  "☝ POINT=Move  ✊ FIST=Hold  ✌ PEACE=Screenshot  👌 OK=Click",
        "VOLUME": "☝ POINT=↑  ✊ FIST=↓  👍 THUMBS=Mute  👌 OK=Confirm",
        "DRAW":   "☝ POINT=Draw  ✌ PEACE=Color  ✊ FIST=Pause  👌 OK=Clear",
        "MEDIA":  "👍 THUMBS=Play/Pause  ☝ POINT=Next  ✌ PEACE=Prev  ✊ FIST=Stop",
        "GAME":   "☝ POINT=Slice  Wave to start",
    }

    with mp_hands.Hands(
        model_complexity=1,
        max_num_hands=2,
        min_detection_confidence=0.72,
        min_tracking_confidence=0.65,
    ) as hands_model:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            t = time.time()

            # FPS
            dt = max(t - prev_time, 1e-5)
            fps_smooth = 0.92*fps_smooth + 0.08*(1/dt)
            prev_time = t

            # CPU
            cpu = psutil.cpu_percent(interval=None)
            cpu_history.append(cpu)

            # ── Dark vignette ──────────────────────────────────
            ov = np.zeros_like(frame)
            cv2.addWeighted(ov, 0.12, frame, 0.88, 0, frame)

            # ── MediaPipe ──────────────────────────────────────
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = hands_model.process(rgb)
            rgb.flags.writeable = True

            gesture       = "NO HAND"
            gesture_conf  = 0.0
            hand_detected = False
            index_tip_px  = None
            cx, cy        = W//2, H//2
            mode          = MODES[mode_idx]
            mode_color    = MODE_COLORS[mode]

            # ── Draw canvas blend ─────────────────────────────
            if draw_mode:
                canvas.blend(frame)

            if results.multi_hand_landmarks:
                # Use first hand as primary
                for hand_idx, (lm_data, hand_info) in enumerate(
                        zip(results.multi_hand_landmarks,
                            results.multi_handedness)):

                    lm  = lm_data
                    side = hand_info.classification[0].label
                    lm_list = lm.landmark

                    # Draw skeleton
                    for conn in mp_hands.HAND_CONNECTIONS:
                        a, b = conn
                        x1 = int(lm_list[a].x*W); y1 = int(lm_list[a].y*H)
                        x2 = int(lm_list[b].x*W); y2 = int(lm_list[b].y*H)
                        cv2.line(frame,(x1,y1),(x2,y2), C["blue"], 2, cv2.LINE_AA)
                    for i, p in enumerate(lm_list):
                        px,py = int(p.x*W), int(p.y*H)
                        col = C["cyan"] if i in [4,8,12,16,20] else C["blue"]
                        cv2.circle(frame,(px,py),5,col,-1,cv2.LINE_AA)
                        cv2.circle(frame,(px,py),8,tuple(c//3 for c in col),1,cv2.LINE_AA)

                    if hand_idx == 0:
                        hand_detected = True
                        xs = [p.x*W for p in lm_list]
                        ys = [p.y*H for p in lm_list]
                        cx = int(np.mean(xs)); cy = int(np.mean(ys))

                        # Index tip
                        index_tip_px = (int(lm_list[8].x*W), int(lm_list[8].y*H))
                        thumb_tip_px = (int(lm_list[4].x*W), int(lm_list[4].y*H))

                        # Classify
                        up = fingers_up(lm_list, side)
                        gesture, gesture_conf = classify_gesture(up, lm, custom_profiles)
                        gesture_hist.append(gesture)
                        gesture = max(set(gesture_hist), key=list(gesture_hist).count)

                        # Neon trail on index tip
                        trail.add(index_tip_px, C["cyan"])

                        # Bounding box
                        bx,by = int(min(xs))-18, int(min(ys))-18
                        bw,bh = int(max(xs)-min(xs))+36, int(max(ys)-min(ys))+36
                        hud._brackets(frame, bx, by, bw, bh, mode_color, sz=12)

                        # Particles on fingertips
                        if t - last_particle_t > 0.08:
                            particles.emit(*index_tip_px, C["cyan"], count=2)
                            last_particle_t = t

                        # ── MODE ACTIONS ──────────────────────
                        if mode == "MOUSE" and MOUSE_OK:
                            if gesture == "POINT":
                                norm_x = lm_list[8].x
                                norm_y = lm_list[8].y
                                ctrl.move_mouse(norm_x, norm_y)
                            elif gesture == "OK":
                                if ctrl.left_click():
                                    hud.alert("LEFT CLICK ✓")
                                    particles.emit(cx, cy, C["green"], 20)
                            elif gesture == "PEACE" and prev_gesture != "PEACE":
                                path = ctrl.screenshot()
                                hud.alert(f"SCREENSHOT SAVED")
                            elif gesture == "ROCK ON":
                                if ctrl.right_click():
                                    hud.alert("RIGHT CLICK ✓")

                        elif mode == "VOLUME":
                            # Pinch to control volume
                            pinch_d = math.hypot(
                                lm_list[8].x - lm_list[4].x,
                                lm_list[8].y - lm_list[4].y
                            )
                            if gesture == "PINCH" or (gesture in ["POINT","OK"]):
                                if pinch_baseline is None:
                                    pinch_baseline = pinch_d
                                else:
                                    delta = (pinch_baseline - pinch_d) * 300
                                    volume_level = max(0, min(100,
                                                              volume_level + delta * 0.1))
                                    ctrl.set_volume(int(volume_level))
                                    pinch_baseline = pinch_d
                            else:
                                pinch_baseline = None
                            if gesture == "THUMBS UP" and prev_gesture != "THUMBS UP":
                                volume_level = ctrl.set_volume(0)
                                hud.alert("MUTED")
                            if gesture == "FIST" and prev_gesture != "FIST":
                                volume_level = ctrl.set_volume(50)
                                hud.alert("VOLUME: 50%")

                        elif mode == "DRAW":
                            drawing = gesture == "POINT"
                            canvas.draw(index_tip_px, drawing)
                            if gesture == "PEACE" and prev_gesture != "PEACE":
                                canvas.next_color()
                                hud.alert(f"COLOR CHANGED")
                            if gesture == "OK" and prev_gesture != "OK":
                                canvas.clear()
                                hud.alert("CANVAS CLEARED")

                        elif mode == "MEDIA" and MOUSE_OK:
                            if gesture == "THUMBS UP" and prev_gesture != "THUMBS UP":
                                ctrl.media_action("play_pause")
                                hud.alert("▶ PLAY / PAUSE")
                            elif gesture == "POINT" and prev_gesture != "POINT":
                                ctrl.media_action("next")
                                hud.alert("⏭ NEXT TRACK")
                            elif gesture == "PEACE" and prev_gesture != "PEACE":
                                ctrl.media_action("prev")
                                hud.alert("⏮ PREV TRACK")

                        # ── Swipe detection ───────────────────
                        if gesture == "OPEN PALM":
                            if swipe_start is None:
                                swipe_start = lm_list[9].x
                                swipe_start_t = t
                            else:
                                if t - swipe_start_t > 0.6:
                                    swipe_start = None
                                else:
                                    delta_x = lm_list[9].x - swipe_start
                                    if abs(delta_x) > 0.18:
                                        if MOUSE_OK:
                                            if delta_x > 0:
                                                pyautogui.hotkey('right')
                                                hud.alert("SWIPE RIGHT →")
                                            else:
                                                pyautogui.hotkey('left')
                                                hud.alert("SWIPE LEFT ←")
                                        swipe_start = None
                        else:
                            swipe_start = None

                        prev_gesture = gesture

            # ── Draw neon trails ──────────────────────────────
            trail.draw(frame)
            particles.update_draw(frame)

            # ── Draw gesture shape / feedback ─────────────────
            if hand_detected:
                draw_gesture_feedback(frame, gesture, cx, cy, t, mode_color)

            # ── Game mode ─────────────────────────────────────
            if mode == "GAME":
                game.update(frame, index_tip_px if gesture=="POINT" else None)
                game.draw_ui(frame, hud)

            # ════════════════════════════════════════════════
            # HUD RENDERING
            # ════════════════════════════════════════════════
            hud.scanline(frame, t)

            # ── TOP LEFT: System Monitor ──────────────────────
            hud.panel(frame, 10, 10, 210, 140, C["blue"], 0.15, "SYS.MONITOR")
            hud.text(frame, f"FPS    {fps_smooth:5.1f}", 18, 36, C["cyan"], 0.40)
            hud.text(frame, f"RES    {W}x{H}",           18, 54, C["cyan"], 0.40)
            hud.text(frame, f"MODE   {mode}",            18, 72, mode_color, 0.40)
            # CPU bar
            hud.text(frame, f"CPU    {cpu:4.1f}%",       18, 90, C["green"], 0.40)
            hud.bar(frame, 18, 96, 170, 5, cpu/100, C["green"])
            # RAM
            ram = psutil.virtual_memory().percent
            hud.text(frame, f"RAM    {ram:4.1f}%",       18, 112, C["yellow"], 0.40)
            hud.bar(frame, 18, 118, 170, 5, ram/100, C["yellow"])
            hud.text(frame, f"AI     MEDIAPIPE",         18, 140, C["green"], 0.40)

            # ── TOP RIGHT: Gesture Engine ──────────────────────
            hud.panel(frame, W-240, 10, 230, 130, C["red"], 0.15, "GESTURE.ENGINE")
            g_label = gesture if hand_detected else "STANDBY"
            g_color = C["white"] if hand_detected else C["dim"]
            hud.text(frame, g_label, W-228, 50, g_color, 0.68, 2)
            conf_pct = int(gesture_conf * 100) if hand_detected else 0
            hud.text(frame, f"CONF   {conf_pct:3d}%", W-228, 72, C["cyan"], 0.42)
            status_str = "ACTIVE" if hand_detected else "SCANNING..."
            hud.text(frame, f"STATUS {status_str}", W-228, 90, C["green"] if hand_detected else C["dim"], 0.38)
            # Confidence ring
            hud.conf_ring(frame, W-38, 38, 26, gesture_conf, mode_color)

            # ── LEFT COLUMN: Status dots ───────────────────────
            dots = [
                ("CAM",  C["green"],  True),
                ("HAND", C["cyan"],   hand_detected),
                ("GEST", C["blue"],   hand_detected),
                ("CTRL", mode_color,  MOUSE_OK),
                ("REC",  C["red"],    hand_detected),
            ]
            for i, (lbl, col, act) in enumerate(dots):
                hud.dot(frame, 18, 180+i*32, 7, col, lbl, act)

            # ── RIGHT SIDE: Radar + Volume ─────────────────────
            hud.draw_radar(frame, W-55, H//2, 45, hand_detected)

            if mode == "VOLUME":
                hud.volume_dial(frame, W-55, H//2+120, 36, int(volume_level), C["green"])

            # ── RIGHT: Gesture legend ──────────────────────────
            legend = ["OPEN PALM","FIST","THUMBS UP","POINT","PEACE",
                      "OK","PINCH","ROCK ON"]
            leg_y = H - len(legend)*22 - 50
            hud.panel(frame, W-185, leg_y-10, 180, len(legend)*22+16, C["blue"], 0.12)
            for i, g in enumerate(legend):
                active = (g == gesture and hand_detected)
                col = C["white"] if active else C["dim"]
                prefix = "▶" if active else " "
                hud.text(frame, f"{prefix} {g}", W-178, leg_y+i*22, col, 0.33)

            # ── BOTTOM: Status bar ────────────────────────────
            hud.panel(frame, 0, H-42, W, 42, C["blue"], 0.18)
            ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
            hud.text(frame, f"GestureHUD PRO v2.0  |  {ts}  |  M=Mode  D=Draw  S=Shot  H=Help  Q=Quit",
                     12, H-14, C["cyan"], 0.36)

            # ── BOTTOM LEFT: mode action hint ──────────────────
            if mode in GESTURE_ACTIONS:
                hud.text(frame, GESTURE_ACTIONS[mode], 12, H-56, mode_color, 0.33)

            # ── HELP overlay ──────────────────────────────────
            if show_help:
                _draw_help(frame, hud, W, H, t)

            # ── Alert banner ──────────────────────────────────
            hud.draw_alert(frame)

            # ── Training UI ───────────────────────────────────
            if training_active:
                elapsed = t - training_start
                remaining = 3.0 - elapsed
                if remaining > 0:
                    hud.panel(frame, W//4, H//3, W//2, 100, C["purple"], 0.35)
                    hud.text(frame, f"HOLD GESTURE: {training_name}",
                             W//4+10, H//3+30, C["white"], 0.55, 2)
                    hud.text(frame, f"Recording in {remaining:.1f}s...",
                             W//4+10, H//3+60, C["yellow"], 0.42)
                    hud.bar(frame, W//4+10, H//3+75, W//2-20, 8,
                            elapsed/3.0, C["purple"])
                else:
                    if hand_detected:
                        up = fingers_up(results.multi_hand_landmarks[0].landmark,
                                        results.multi_handedness[0].classification[0].label)
                        custom_profiles[training_name] = {"fingers": up}
                        with open(PROFILES_PATH, "w") as f:
                            json.dump(custom_profiles, f)
                        hud.alert(f"SAVED: {training_name}")
                    training_active = False

            cv2.imshow("GestureHUD PRO", frame)

            # ── Keyboard controls ─────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('m'):
                mode_idx = (mode_idx + 1) % len(MODES)
                hud.alert(f"MODE → {MODES[mode_idx]}")
            elif key == ord('d'):
                draw_mode = not draw_mode
                hud.alert("DRAW MODE ON" if draw_mode else "DRAW MODE OFF")
            elif key == ord('c'):
                canvas.clear()
                hud.alert("CANVAS CLEARED")
            elif key == ord('s'):
                path = ctrl.screenshot()
                hud.alert("SCREENSHOT SAVED")
            elif key == ord('h'):
                show_help = not show_help
            elif key == ord('t'):
                training_name = f"GESTURE_{len(custom_profiles)+1}"
                training_start = t
                training_active = True

    cap.release()
    cv2.destroyAllWindows()


# ═══════════════════════════════════════════════════════════════
#  GESTURE VISUAL FEEDBACK
# ═══════════════════════════════════════════════════════════════
def draw_gesture_feedback(frame, gesture, cx, cy, t, accent):
    pulse = abs(math.sin(t * 3.5))
    p = int(pulse * 25)

    if gesture == "OPEN PALM":
        r = 65 + p//3
        cv2.circle(frame, (cx,cy), r, C["blue"], 2, cv2.LINE_AA)
        cv2.circle(frame, (cx,cy), r-10, (*C["blue"][:2], 40), 1)

    elif gesture == "FIST":
        s = 52 + p//4
        ov = frame.copy()
        cv2.rectangle(ov,(cx-s,cy-s),(cx+s,cy+s), C["red"], -1)
        cv2.addWeighted(ov, 0.22, frame, 0.78, 0, frame)
        cv2.rectangle(frame,(cx-s,cy-s),(cx+s,cy+s), C["red"], 2)

    elif gesture == "PEACE":
        s = 58 + p//4
        pts = np.array([[cx,cy-s],[cx-s,cy+s//2],[cx+s,cy+s//2]])
        cv2.polylines(frame,[pts],True,C["white"],2,cv2.LINE_AA)

    elif gesture == "THUMBS UP":
        # Upward arrow
        s = 50 + p//4
        pts = np.array([[cx,cy-s],[cx-s//2,cy],[cx+s//2,cy]])
        cv2.fillPoly(frame,[pts], C["green"])
        cv2.rectangle(frame,(cx-s//6,cy),(cx+s//6,cy+s//2), C["green"], -1)

    elif gesture == "POINT":
        r = 52 + p//4
        cv2.circle(frame,(cx,cy),r, C["cyan"], 1, cv2.LINE_AA)
        cv2.line(frame,(cx-r-12,cy),(cx+r+12,cy), C["cyan"],1)
        cv2.line(frame,(cx,cy-r-12),(cx,cy+r+12), C["cyan"],1)
        cv2.circle(frame,(cx,cy),4, C["cyan"],-1)

    elif gesture == "OK":
        r = 55 + p//4
        cv2.circle(frame,(cx,cy),r, C["green"],2, cv2.LINE_AA)
        cv2.circle(frame,(cx,cy),r-8, C["green"],1)
        # Checkmark
        cv2.line(frame,(cx-20,cy),(cx-5,cy+15), C["green"],3)
        cv2.line(frame,(cx-5,cy+15),(cx+22,cy-18), C["green"],3)

    elif gesture == "PINCH":
        for r in [30, 45, 60]:
            alpha_val = max(0, 1 - r/70)
            col = tuple(int(c*alpha_val) for c in C["yellow"])
            cv2.circle(frame,(cx,cy),r+p//5, col, 1, cv2.LINE_AA)

    elif gesture == "ROCK ON":
        s = 52 + p//4
        pts = np.array([[cx,cy-s],[cx+s,cy],[cx,cy+s],[cx-s,cy]])
        cv2.polylines(frame,[pts],True, C["purple"],2,cv2.LINE_AA)

    elif gesture == "CALL ME":
        s = 50 + p//4
        pts = []
        for i in range(6):
            a = math.radians(60*i-30)
            pts.append([int(cx+s*math.cos(a)), int(cy+s*math.sin(a))])
        cv2.polylines(frame,[np.array(pts)],True, C["orange"],2,cv2.LINE_AA)


# ═══════════════════════════════════════════════════════════════
#  HELP OVERLAY
# ═══════════════════════════════════════════════════════════════
def _draw_help(frame, hud, W, H, t):
    ov = frame.copy()
    cv2.rectangle(ov, (W//6, H//8), (W*5//6, H*7//8), (10,10,25), -1)
    cv2.addWeighted(ov, 0.85, frame, 0.15, 0, frame)
    hud._brackets(frame, W//6, H//8, W*2//3, H*3//4, C["cyan"])
    hud.text(frame, "GESTURE HUD PRO  —  HELP", W//6+16, H//8+26, C["cyan"], 0.55, 2)

    lines = [
        ("KEYBOARD", C["yellow"]),
        (" M  — Cycle modes (MOUSE / VOLUME / DRAW / MEDIA / GAME)", C["white"]),
        (" D  — Toggle air-draw canvas", C["white"]),
        (" C  — Clear canvas", C["white"]),
        (" S  — Screenshot", C["white"]),
        (" T  — Train custom gesture (hold 3s)", C["white"]),
        (" H  — Toggle this help", C["white"]),
        (" Q  — Quit", C["white"]),
        ("", C["dim"]),
        ("GESTURES", C["yellow"]),
        (" OPEN PALM   → Swipe left/right to navigate", C["white"]),
        (" POINT       → Mouse move / Draw / Next track", C["white"]),
        (" FIST        → Hold / Pause draw / Volume reset", C["white"]),
        (" PEACE       → Screenshot / Change color / Prev track", C["white"]),
        (" THUMBS UP   → Confirm / Mute / Play-pause", C["white"]),
        (" OK SIGN     → Click / Select / Clear canvas", C["white"]),
        (" PINCH       → Zoom / Volume control", C["white"]),
        (" ROCK ON     → Right click / Special action", C["white"]),
    ]
    for i, (txt, col) in enumerate(lines):
        hud.text(frame, txt, W//6+16, H//8+56+i*22, col, 0.36)


if __name__ == "__main__":
    main()
