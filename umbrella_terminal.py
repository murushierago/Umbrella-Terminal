"""UMBRELLA / secure research network — a fictional Pygame terminal.

PIN: 9876. No ambient music plays before successful authentication.
An incorrect PIN triggers a 10-second warning and siren.
Real Windows shutdown is an OPT-IN setting requiring two confirmations in SECURITY.
Once armed, an incorrect PIN schedules an OS shutdown, cancellable externally via
Windows Win+R -> shutdown /a. The app deliberately has no in-app abort.
CALLS: simulate a call to Mamut Rahal or Albert Wesker, using still portraits;
your local webcam is only enabled after you explicitly press CALL.
No recording, network transfer, or real video calls are performed.
"""
from __future__ import annotations

import json
from functools import lru_cache
import math
import os
import subprocess
import sys
from array import array
from datetime import datetime
from pathlib import Path

import pygame

try:
    import cv2  # Install with: pip install opencv-python
except ImportError:
    cv2 = None

pygame.init()
WIDTH, HEIGHT = 1152, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("UMBRELLA // RESEARCH NETWORK")
clock = pygame.time.Clock()

BG = (8, 10, 14)
SIDEBAR = (12, 14, 19)
CARD = (19, 22, 29)
CARD_HOVER = (25, 29, 38)
BORDER = (42, 46, 55)
RED = (214, 37, 49)
RED_BRIGHT = (247, 64, 76)
WHITE = (238, 238, 240)
MUTED = (144, 150, 162)
DIM = (91, 98, 113)
GREEN = (87, 198, 151)
YELLOW = (237, 178, 88)

FONT = pygame.font.SysFont("segoeui", 18)
FONT_BOLD = pygame.font.SysFont("segoeui", 18, bold=True)
SMALL = pygame.font.SysFont("consolas", 14)
MEDIUM = pygame.font.SysFont("consolas", 16)
BIG = pygame.font.SysFont("segoeui", 36, bold=True)
HUGE = pygame.font.SysFont("segoeui", 48, bold=True)

PAGES = ("OVERVIEW", "PROJECTS", "PERSONNEL", "SECURITY", "CALLS", "SECRET FILES")
ICONS = ("01", "02", "03", "04", "05", "06")
PROJECTS = [
    ("PROJECT T", "CLASSIFIED RESEARCH", "RESTRICTED", 0.78, "ARCHIVE // R-001"),
    ("NEMESIS PROGRAM", "SPECIAL DEVELOPMENT", "SEALED", 0.45, "ARCHIVE // R-002"),
    ("ARKLAY FACILITY", "FIELD OPERATIONS", "INACTIVE", 0.26, "ARCHIVE // R-003"),
    ("RACCOON DIVISION", "SITE ADMINISTRATION", "RESTRICTED", 0.63, "ARCHIVE // R-004"),
]
PERSONNEL = [
    ("DR. E. HART", "RESEARCH DIRECTOR", "A-1139", "ACTIVE"),
    ("A. MORGAN", "SECURITY OFFICER", "S-2044", "ACTIVE"),
    ("DR. S. VALE", "PROJECT ANALYST", "R-0812", "OFFLINE"),
    ("M. REYES", "SYSTEMS OPERATOR", "T-4091", "ACTIVE"),
]

page = 0
selected_project = 0
mode = "login"   # login / terminal / alarm / demo_offline
pin = ""
alarm_started = 0
real_shutdown_scheduled = False
shutdown_error = ""
shutdown_confirmation_pending = False
vault_step = 0
vault_entry = ""
vault_message = "LEVEL 1 / IDENTIFICATION REQUIRED"
vault_unlocked = False
vault_folder = None
vault_file = None
vault_scroll = 0
call_partner = None  # None / 0 (Mamut Rahal) / 1 (Albert Wesker)
call_started = 0
local_camera_enabled = True
diag_started = 0
notice = "WELCOME TO THE UMBRELLA INTERNAL NETWORK"
notice_time = pygame.time.get_ticks()

# Camera is started ONLY on an explicit CALL click. It is never recorded,
# transmitted, or saved, and is released on hang-up / tab change / exit.
camera = None
camera_error = "CAMERA DISCONNECTED"
camera_surface = None
last_camera_read = 0

# Contact portraits (local files only). Mamut's picture is a generated stylization
# based on the reference photo supplied by the user.
# In a bundled Windows EXE, editable files live beside the executable.
app_dir = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
           else Path(__file__).resolve().parent)
asset_dir = app_dir / "assets"
vault_dir = app_dir / "secret_files"
vault_dir.mkdir(parents=True, exist_ok=True)
for folder_name in ("Ada Wong", "Jill Valentine", "Claire Redfield", "Ashley Graham", "####"):
    (vault_dir / folder_name).mkdir(exist_ok=True)
CONFIG_PATH = app_dir / "settings.json"
DEFAULT_VAULT_CODES = ["1998", "RACCOON", "T-VIRUS", "ALPHA", "REDQUEEN"]
try:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        config = {}
except (OSError, ValueError):
    config = {}
real_shutdown_enabled = config.get("real_shutdown_enabled") is True
vault_codes = config.get("vault_codes")
if not (isinstance(vault_codes, list) and len(vault_codes) == 5
        and all(isinstance(s, str) and 1 <= len(s) <= 28 for s in vault_codes)):
    vault_codes = DEFAULT_VAULT_CODES.copy()


def save_config():
    try:
        CONFIG_PATH.write_text(json.dumps({
            "real_shutdown_enabled": real_shutdown_enabled,
            "vault_codes": vault_codes,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except OSError:
        return False


def load_portrait(filename):
    try:
        return pygame.image.load(str(asset_dir / filename)).convert()
    except (pygame.error, OSError, FileNotFoundError):
        return None

wesker_photo = load_portrait("wesker.png")
mamut_photo = load_portrait("mamut_rahal.png")
CONTACTS = (
    ("MAMUT RAHAL", "SPECIAL RESEARCH ADVISOR", "MR-081", mamut_photo),
    ("ALBERT WESKER", "EXECUTIVE COMMAND", "AW-001", wesker_photo),
)

# Music must be silent at initial login. It begins only AFTER a correct PIN.
# The siren has a separate local file and plays only after an incorrect PIN.
soundtrack = next((p for ext in ("mp3", "ogg", "wav")
                   if (p := asset_dir / f"ambience.{ext}").is_file()), None)
siren_file = next((p for ext in ("mp3", "ogg", "wav")
                   if (p := asset_dir / f"siren.{ext}").is_file()), None)
audio_ready = False
music_on = True  # preference (not 'currently playing')
alarm_sound = None
try:
    pygame.mixer.init()
    audio_ready = True
except (pygame.error, OSError):
    pass


def stop_audio():
    global alarm_sound
    if not audio_ready:
        return
    try:
        pygame.mixer.music.stop()
        if alarm_sound is not None:
            alarm_sound.stop()
    except pygame.error:
        pass


def start_ambient():
    if not (audio_ready and soundtrack and music_on and mode == "terminal"):
        return
    try:
        pygame.mixer.music.load(str(soundtrack))
        pygame.mixer.music.set_volume(0.28)
        pygame.mixer.music.play(-1)
    except (pygame.error, OSError):
        pass


def fallback_siren():
    """Generate a short looping alarm tone when assets/siren.mp3 is absent."""
    try:
        frequency, fmt, channels = pygame.mixer.get_init()
        if fmt != -16:
            return None
        duration = 1.1
        wave = array('h')
        frames = int(frequency * duration)
        for i in range(frames):
            s = i / frequency
            pitch = 490 + 350 * (0.5 - 0.5 * math.cos(2 * math.pi * s / duration))
            amplitude = int(9200 * math.sin(2 * math.pi * pitch * s))
            for _ in range(channels):
                wave.append(amplitude)
        return pygame.mixer.Sound(buffer=wave.tobytes())
    except (pygame.error, TypeError, ValueError, OverflowError):
        return None


def start_siren():
    global alarm_sound
    stop_audio()
    if not audio_ready:
        return
    if siren_file:
        try:
            pygame.mixer.music.load(str(siren_file))
            pygame.mixer.music.set_volume(0.85)
            pygame.mixer.music.play(-1)
            return
        except (pygame.error, OSError):
            pass
    if alarm_sound is None:
        alarm_sound = fallback_siren()
    if alarm_sound is not None:
        alarm_sound.set_volume(0.55)
        alarm_sound.play(-1)


def enter_terminal():
    global mode, pin, page
    mode = "terminal"
    pin = ""
    page = 0
    start_ambient()
    set_notice("ACCESS GRANTED // WELCOME, OPERATOR")


def schedule_real_shutdown():
    """Ask Windows to shut down in 10 seconds (can be aborted via shutdown /a)."""
    if sys.platform != "win32":
        return False, "REAL SHUTDOWN REQUIRES WINDOWS"
    exe = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "shutdown.exe")
    try:
        result = subprocess.run(
            [exe, "/s", "/t", "10", "/c", "Umbrella terminal: invalid access code"],
            capture_output=True, text=True, timeout=4, shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            return True, "WINDOWS SHUTDOWN SCHEDULED"
        return False, "SHUTDOWN FAILED: " + (result.stderr or "UNKNOWN ERROR")[:90]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "SHUTDOWN FAILED: " + str(exc)[:90]


def start_alarm():
    global mode, pin, alarm_started, real_shutdown_scheduled, shutdown_error
    pin = ""
    mode = "alarm"
    alarm_started = pygame.time.get_ticks()
    real_shutdown_scheduled = False
    shutdown_error = ""
    if real_shutdown_enabled:
        real_shutdown_scheduled, shutdown_error = schedule_real_shutdown()
    start_siren()


def restart_demo():
    global mode, pin
    stop_audio()
    mode = "login"
    pin = ""


def reset_vault():
    global vault_step, vault_entry, vault_message, vault_unlocked, vault_folder, vault_file, vault_scroll
    vault_step = 0
    vault_entry = ""
    vault_message = "LEVEL 1 / IDENTIFICATION REQUIRED"
    vault_unlocked = False
    vault_folder = None
    vault_file = None
    vault_scroll = 0


def verify_vault():
    global vault_step, vault_entry, vault_message, vault_unlocked
    if vault_entry.upper().strip() == vault_codes[vault_step].upper():
        vault_step += 1
        vault_entry = ""
        if vault_step >= 5:
            vault_unlocked = True
            vault_message = "ACCESS GRANTED // ARCHIVE DECRYPTED (SIMULATED)"
            set_notice("SECRET FILES // LEVEL 5 CLEARANCE GRANTED")
        else:
            vault_message = f"LEVEL {vault_step} VERIFIED // PROCEED TO LEVEL {vault_step + 1}"
    else:
        vault_step = 0
        vault_entry = ""
        vault_message = "AUTHENTICATION FAILED // RESET TO LEVEL 1"


def verify_pin():
    if pin == "9876":
        enter_terminal()
    elif pin:
        start_alarm()


def terminate_session():
    global mode, pin, call_partner
    stop_audio()
    stop_camera()
    call_partner = None
    pin = ""
    mode = "login"
    reset_vault()



def txt(text, x, y, font=FONT, color=WHITE):
    screen.blit(font.render(str(text), True, color), (int(x), int(y)))


def right_txt(text, x, y, font=SMALL, color=MUTED):
    surf = font.render(str(text), True, color)
    screen.blit(surf, (int(x - surf.get_width()), int(y)))


def box(x, y, w, h, fill=CARD, radius=12, border=BORDER, width=1):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, fill, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(screen, border, rect, width, border_radius=radius)
    return rect


def line(x1, y1, x2, y2, color=BORDER, w=1):
    pygame.draw.line(screen, color, (x1, y1), (x2, y2), w)


def logo(cx, cy, radius):
    """Draw a geometric umbrella emblem using Pygame; no image file needed."""
    for i in range(8):
        angle0 = math.radians(-90 + 45 * i + 3)
        angle1 = math.radians(-90 + 45 * (i + 1) - 3)
        p0 = (cx + radius * math.cos(angle0), cy + radius * math.sin(angle0))
        p1 = (cx + radius * math.cos(angle1), cy + radius * math.sin(angle1))
        inset = radius * 0.12
        mid = math.radians(-90 + 45 * (i + 0.5))
        center = (cx + inset * math.cos(mid), cy + inset * math.sin(mid))
        pygame.draw.polygon(screen, RED if i % 2 == 0 else WHITE, (center, p0, p1))


def set_notice(message):
    global notice, notice_time
    notice = message
    notice_time = pygame.time.get_ticks()


def button(label, rect, mouse, fill=RED, hover=RED_BRIGHT):
    x, y, w, h = rect
    is_hover = pygame.Rect(rect).collidepoint(mouse)
    box(x, y, w, h, hover if is_hover else fill, radius=8, border=None)
    surf = FONT_BOLD.render(label, True, WHITE)
    screen.blit(surf, (x + (w - surf.get_width()) / 2, y + (h - surf.get_height()) / 2 - 1))
    return pygame.Rect(rect)


def panel_header(title, label, x, y, width):
    txt(title, x, y, FONT_BOLD)
    right_txt(label, x + width, y + 3)
    line(x, y + 31, x + width, y + 31)


def stop_camera():
    """Release local webcam immediately when leaving camera mode."""
    global camera, camera_surface, last_camera_read
    if camera is not None:
        camera.release()
        camera = None
    camera_surface = None
    last_camera_read = 0


def start_camera():
    """Open webcam without allowing a missing camera to crash the terminal."""
    global camera, camera_error
    if camera is not None:
        return
    if cv2 is None:
        camera_error = "OPENCV NOT INSTALLED"
        return
    camera_error = "CONNECTING ..."
    attempts = [(0, cv2.CAP_DSHOW), (0, cv2.CAP_ANY)] if sys.platform.startswith("win") else [(0, cv2.CAP_ANY)]
    for index, backend in attempts:
        candidate = None
        try:
            candidate = cv2.VideoCapture(index, backend)
            if candidate.isOpened():
                candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                camera = candidate
                camera_error = ""
                return
        except Exception:
            pass
        if candidate is not None:
            candidate.release()
    camera_error = "NO CAMERA / ACCESS DENIED"


def end_call():
    global call_partner
    stop_camera()
    call_partner = None


def begin_call(index):
    global call_partner, call_started, local_camera_enabled
    call_partner = index
    call_started = pygame.time.get_ticks()
    local_camera_enabled = True
    start_camera()
    set_notice(f"CONNECTING TO {CONTACTS[index][0]} // DEMO")


def set_page(index):
    global page, shutdown_confirmation_pending
    if index != page and page == 3:
        shutdown_confirmation_pending = False
    if index != page and page == 4:
        end_call()
    if index != page and page == 5:
        reset_vault()  # the classified archive locks when you switch tabs
    page = index
    set_notice(f"OPENED {PAGES[index]}")


def update_camera_frame():
    global camera_surface, last_camera_read, camera_error
    if camera is None:
        return
    now = pygame.time.get_ticks()
    if now - last_camera_read < 55:
        return
    last_camera_read = now
    try:
        ok, image = camera.read()
        if not ok:
            camera_error = "VIDEO SIGNAL LOST"
            stop_camera()
            return
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]
        # frombuffer plus bytes copy prevents OpenCV frame buffer lifetime issues.
        camera_surface = pygame.image.frombuffer(image.tobytes(), (width, height), "RGB").copy()
    except Exception:
        camera_error = "VIDEO SIGNAL LOST"
        stop_camera()


def blit_cover(surface, rect):
    """Draw an image filling a rectangle while keeping aspect ratio."""
    x, y, w, h = rect
    sw, sh = surface.get_size()
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale + .5), int(sh * scale + .5)
    scaled = pygame.transform.smoothscale(surface, (max(w, nw), max(h, nh)))
    crop = pygame.Rect((scaled.get_width() - w) // 2, (scaled.get_height() - h) // 2, w, h)
    screen.blit(scaled, (x, y), crop)


def camera_frame_border(rect, time):
    x, y, w, h = rect
    pygame.draw.rect(screen, BORDER, rect, width=1)
    for corner_x in (x, x + w):
        for corner_y in (y, y + h):
            x_dir = 1 if corner_x == x else -1
            y_dir = 1 if corner_y == y else -1
            line(corner_x, corner_y, corner_x + x_dir * 17, corner_y, RED_BRIGHT, 2)
            line(corner_x, corner_y, corner_x, corner_y + y_dir * 17, RED_BRIGHT, 2)
    # Very subtle scanline effect, applied only to the on-screen display.
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    for j in range(4, h, 5):
        pygame.draw.line(overlay, (5, 8, 12, 34), (0, j), (w, j))
    screen.blit(overlay, (x, y))


def draw_calls(mouse, t):
    if call_partner is None:
        box(282, 126, 834, 523)
        panel_header("SECURE COMMUNICATIONS", "CONTACT DIRECTORY / DEMO", 302, 147, 794)
        txt("SELECT AN INTERNAL CONTACT TO INITIATE A SIMULATED VIDEO CALL", 304, 194, SMALL, MUTED)
        for index, (name, title, code, portrait) in enumerate(CONTACTS):
            y = 234 + index * 177
            box(304, y, 793, 151, (22, 26, 34), 10, (49, 53, 66))
            portrait_rect = pygame.Rect(318, y + 12, 148, 126)
            pygame.draw.rect(screen, (8, 10, 16), portrait_rect)
            if portrait is not None:
                blit_cover(portrait, portrait_rect)
            camera_frame_border(portrait_rect, t)
            txt(name, 490, y + 23, FONT_BOLD, WHITE)
            txt(title, 490, y + 57, MEDIUM, MUTED)
            txt("INTERNAL ID // " + code, 490, y + 94, SMALL, DIM)
            button("CALL", (894, y + 49, 174, 51), mouse)
        txt("CALLS ARE FICTIONAL. REMOTE FEEDS ARE STILL IMAGES.", 306, 611, SMALL, DIM)
        return

    name, title, code, portrait = CONTACTS[call_partner]
    connected = pygame.time.get_ticks() - call_started >= 1500
    box(282, 126, 546, 523)
    panel_header("ENCRYPTED VIDEO CALL", "UMBRELLA / NETWORK", 302, 147, 505)
    txt("CH 01 // " + name, 304, 193, MEDIUM, WHITE)
    right_txt("CONNECTED" if connected else "DIALING ...", 804, 194, SMALL,
              GREEN if connected else YELLOW)
    remote = pygame.Rect(304, 219, 502, 323)
    pygame.draw.rect(screen, (5, 7, 11), remote)
    if connected and portrait is not None:
        blit_cover(portrait, remote)
        # A gentle red tint ties the still feed into the terminal UI.
        shade = pygame.Surface(remote.size, pygame.SRCALPHA)
        shade.fill((20, 2, 6, 33))
        screen.blit(shade, remote.topleft)
        txt("SECURE CHANNEL / SIMULATED FEED", 316, 515, SMALL, WHITE)
    elif connected:
        txt("REMOTE PORTRAIT MISSING", 385, 360, MEDIUM, YELLOW)
    else:
        logo(554, 339, 45)
        txt("ESTABLISHING SECURE CONNECTION ...", 355, 433, SMALL, MUTED)
    camera_frame_border(remote, t)
    txt(name, 304, 561, FONT_BOLD, WHITE)
    txt(title + "   /   " + code, 304, 590, SMALL, MUTED)
    txt("CH 01: STILL PHOTO / NOT A REAL CONNECTION", 304, 622, SMALL, DIM)

    box(846, 126, 270, 523)
    panel_header("LOCAL OPERATOR", "CH 02", 864, 147, 231)
    txt("YOUR WEBCAM PREVIEW", 865, 200, SMALL, MUTED)
    local = pygame.Rect(864, 227, 232, 169)
    pygame.draw.rect(screen, (5, 7, 11), local)
    if camera is not None and camera_surface is not None:
        blit_cover(camera_surface, local)
        pygame.draw.circle(screen, RED_BRIGHT, (884, 247), 4)
        txt("LIVE", 894, 237, SMALL, WHITE)
    else:
        txt("CAMERA OFFLINE", 912, 281, SMALL, YELLOW)
        txt(camera_error, 874, 310, SMALL, MUTED)
    camera_frame_border(local, t)
    txt("LOCAL ONLY // NO RECORDING", 865, 414, SMALL, DIM)
    button("END CALL", (864, 457, 232, 50), mouse)
    button("CAMERA OFF" if camera is not None else "CAMERA ON",
           (864, 521, 232, 46), mouse, (62, 67, 79), (81, 86, 101))
    txt("C: TOGGLE CAMERA", 864, 607, SMALL, DIM)
    txt("ESC: EXIT TERMINAL", 864, 625, SMALL, DIM)


def draw_sidebar(mouse):
    pygame.draw.rect(screen, SIDEBAR, (0, 0, 250, HEIGHT))
    line(249, 0, 249, HEIGHT)
    logo(52, 57, 24)
    txt("UMBRELLA", 85, 36, FONT_BOLD)
    txt("CORPORATION", 85, 59, SMALL, MUTED)
    line(24, 108, 225, 108)
    txt("INTERNAL SYSTEMS", 26, 136, SMALL, DIM)

    for i, label in enumerate(PAGES):
        ry = 166 + i * 56
        hovered = pygame.Rect(15, ry, 220, 46).collidepoint(mouse)
        if i == page or hovered:
            box(15, ry, 220, 46, (44, 27, 33) if i == page else CARD_HOVER,
                radius=9, border=None)
        if i == page:
            pygame.draw.rect(screen, RED, (15, ry + 7, 3, 31), border_radius=2)
        txt(ICONS[i], 31, ry + 11, MEDIUM, RED_BRIGHT if i == page else DIM)
        txt(label, 78, ry + 12, FONT_BOLD if i == page else FONT,
            WHITE if i == page else MUTED)

    line(24, 567, 225, 567)
    txt("ACCESS LEVEL", 26, 589, SMALL, DIM)
    txt("AUTHORIZED // L-04", 26, 614, MEDIUM, GREEN)
    txt("SIMULATED TERMINAL", 26, 671, SMALL, RED_BRIGHT)


def draw_header():
    txt("U M B R E L L A   / /   I N T R A N E T", 282, 25, SMALL, RED_BRIGHT)
    right_txt(datetime.now().strftime("%d %b %Y  %H:%M:%S").upper(), 1115, 24, SMALL)
    txt(PAGES[page].title(), 282, 49, BIG)
    line(282, 103, 1116, 103)


def draw_overview(mouse, t):
    cards = [
        ("FACILITY STATUS", "NOMINAL", "SIMULATION ONLINE", GREEN),
        ("RESEARCH FILES", "04", "CLASSIFIED ENTRIES", WHITE),
        ("SECURITY LEVEL", "01", "GUEST SESSION", YELLOW),
    ]
    for i, (label, value, sub, color) in enumerate(cards):
        x = 282 + i * 285
        box(x, 126, 265, 136)
        txt(label, x + 18, 143, SMALL, MUTED)
        txt(value, x + 18, 170, BIG, color)
        txt(sub, x + 18, 229, SMALL, DIM)

    box(282, 280, 546, 327)
    panel_header("NETWORK ACTIVITY", "LIVE VISUALIZATION", 302, 300, 505)
    for row in range(4):
        yy = 363 + row * 53
        line(310, yy, 803, yy, (32, 37, 47))
    for col in range(9):
        xx = 312 + col * 61
        line(xx, 350, xx, 574, (27, 32, 40))
    pts = []
    for i in range(220):
        x = 311 + i * 2.22
        val = math.sin(i * 0.115 + t * 1.7) * 23 + math.sin(i * 0.038 - t * 0.62) * 19
        val += math.sin(i * 0.55 + t * 3.1) * 5
        pts.append((int(x), int(471 - val)))
    pygame.draw.lines(screen, RED_BRIGHT, False, pts, 2)
    txt("RESEARCH NETWORK / SIGNAL TRACE", 312, 573, SMALL, DIM)

    box(848, 280, 268, 327)
    panel_header("SYSTEM LOG", "AUTO", 866, 300, 232)
    logs = [
        ("13:40", "SESSION INITIALIZED"),
        ("13:39", "ARCHIVE LINK READY"),
        ("13:38", "SECURITY CHECK OK"),
        ("13:37", "NODE SYNC COMPLETE"),
        ("13:36", "CHANNEL ENCRYPTED"),
    ]
    for i, (time, entry) in enumerate(logs):
        y = 360 + i * 45
        txt(time, 866, y, SMALL, RED_BRIGHT)
        txt(entry, 866, y + 18, SMALL, MUTED)

    txt("AUTHORIZED PERSONNEL ONLY    •    ALL OPERATIONS ARE FICTIONAL", 283, 638, SMALL, DIM)


def draw_projects(mouse, t):
    box(282, 126, 834, 473)
    panel_header("RESTRICTED PROJECT DIRECTORY", "4 FILES", 302, 146, 793)
    for i, (name, department, status, progress, _) in enumerate(PROJECTS):
        y = 202 + i * 93
        is_hover = pygame.Rect(302, y, 794, 80).collidepoint(mouse)
        if i == selected_project or is_hover:
            box(302, y, 794, 80, (38, 27, 33) if i == selected_project else CARD_HOVER,
                radius=8, border=None)
        txt(f"0{i + 1}", 318, y + 24, MEDIUM, RED_BRIGHT)
        txt(name, 372, y + 12, FONT_BOLD)
        txt(department, 372, y + 40, SMALL, MUTED)
        right_txt(status, 1077, y + 14, SMALL,
                  YELLOW if status == "SEALED" else RED_BRIGHT if status == "RESTRICTED" else DIM)
        pygame.draw.rect(screen, BORDER, (899, y + 52, 177, 4), border_radius=2)
        pygame.draw.rect(screen, RED, (899, y + 52, int(177 * progress), 4), border_radius=2)
    txt("SELECT A FILE TO INSPECT ITS ARCHIVE RECORD", 303, 622, SMALL, DIM)
    name, dept, status, _, code = PROJECTS[selected_project]
    txt(f"SELECTED: {name}     /     {code}     /     {status}", 303, 653, SMALL, RED_BRIGHT)


def draw_personnel(mouse, t):
    box(282, 126, 834, 472)
    panel_header("PERSONNEL RECORDS", "ACCESS: READ ONLY", 302, 146, 793)
    txt("EMPLOYEE", 326, 206, SMALL, DIM)
    txt("DEPARTMENT", 570, 206, SMALL, DIM)
    txt("IDENTIFIER", 812, 206, SMALL, DIM)
    txt("STATUS", 990, 206, SMALL, DIM)
    line(302, 238, 1096, 238)
    for i, (name, job, ident, status) in enumerate(PERSONNEL):
        y = 253 + i * 79
        if i % 2 == 0:
            box(303, y, 794, 66, (24, 27, 34), radius=6, border=None)
        txt(name, 326, y + 21, FONT_BOLD)
        txt(job, 570, y + 22, SMALL, MUTED)
        txt(ident, 812, y + 22, SMALL, MUTED)
        txt(status, 990, y + 22, SMALL, GREEN if status == "ACTIVE" else DIM)
    txt("ALL PERSONNEL PROFILES ARE FICTIONAL", 302, 629, SMALL, DIM)


def draw_security(mouse, t):
    box(282, 126, 834, 225)
    panel_header("CONTAINMENT MONITOR", "TRAINING ENVIRONMENT", 302, 146, 793)
    sectors = [
        ("SECTOR A", "RESEARCH WING", "NOMINAL", GREEN),
        ("SECTOR B", "DOCUMENT ARCHIVE", "RESTRICTED", YELLOW),
        ("SECTOR C", "SECURE STORAGE", "NOMINAL", GREEN),
    ]
    for i, (name, desc, status, color) in enumerate(sectors):
        y = 200 + i * 46
        pygame.draw.circle(screen, color, (318, y + 9), 4)
        txt(name, 338, y, MEDIUM)
        txt(desc, 478, y + 1, SMALL, MUTED)
        right_txt(status, 1075, y + 1, MEDIUM, color)

    box(282, 370, 834, 276)
    panel_header("SECURITY CONTROLS", "LOCAL CONFIGURATION", 302, 389, 793)
    button("RUN DIAGNOSTICS", (304, 446, 235, 44), mouse)
    button("LOCK TERMINAL", (554, 446, 223, 44), mouse, (65, 69, 81), (80, 84, 97))
    elapsed = pygame.time.get_ticks() - diag_started
    msg = ("RUNNING SECURITY DIAGNOSTICS ..." if diag_started and elapsed < 1900
           else "DIAGNOSTICS OK // 0 ANOMALIES (DEMO)" if diag_started
           else "STANDBY // NO DIAGNOSTICS REQUESTED")
    txt(msg, 304, 498, SMALL, YELLOW if diag_started and elapsed < 1900 else MUTED)
    line(304, 522, 1095, 522)
    txt("REAL WINDOWS SHUTDOWN", 304, 538, FONT_BOLD)
    txt("WRONG PIN -> 10 SEC; CANCEL VIA WIN+R: shutdown /a", 304, 568, SMALL, MUTED)
    if real_shutdown_enabled:
        label, fill = "DISABLE", (72, 77, 89)
    elif shutdown_confirmation_pending:
        label, fill = "CONFIRM ENABLE", RED
    else:
        label, fill = "ENABLE (OPT-IN)", (72, 77, 89)
    button(label, (876, 540, 218, 47), mouse, fill, RED_BRIGHT)
    state = "ARMED / REAL SHUTDOWN" if real_shutdown_enabled else ("CONFIRM TO ARM REAL SHUTDOWN" if shutdown_confirmation_pending else "SAFE DEMO / NO OS SHUTDOWN")
    txt(state, 304, 607, SMALL, RED_BRIGHT if real_shutdown_enabled else YELLOW)


def vault_folders():
    try:
        return sorted([p for p in vault_dir.iterdir() if p.is_dir() and not p.is_symlink()], key=lambda p: p.name.lower())
    except OSError:
        return []


def vault_files():
    if vault_folder is None:
        return []
    folder = vault_dir / vault_folder
    if not folder.is_dir() or folder.is_symlink() or folder.parent != vault_dir:
        return []
    try:
        return sorted([p for p in folder.iterdir() if p.is_file() and not p.is_symlink()], key=lambda p: p.name.lower())
    except OSError:
        return []


def fit_name(name, length=27):
    return name if len(name) <= length else name[:length - 3] + "..."


@lru_cache(maxsize=10)
def cached_archive_image(image_path, modified_time):
    return pygame.image.load(image_path).convert_alpha()


def draw_vault(mouse, t):
    if not vault_unlocked:
        box(282, 126, 834, 531, (18, 20, 27), 12, (75, 40, 48))
        panel_header("TOP SECRET // PERSONNEL ARCHIVES", "CLEARANCE 5 / BLACK FILES", 303, 146, 793)
        centered("FIVE-TIER SECURITY SYSTEM", 700, 213, BIG, WHITE)
        centered("ENTER EACH LEVEL'S ACCESS PHRASE TO CONTINUE", 700, 257, SMALL, MUTED)
        for level in range(5):
            x = 350 + level * 142
            box(x, 301, 125, 55, (39, 29, 35) if level == vault_step else (18, 22, 29), 7,
                RED if level == vault_step else GREEN if level < vault_step else BORDER)
            centered("LVL " + str(level + 1), x + 62, 318, MEDIUM,
                     GREEN if level < vault_step else RED_BRIGHT if level == vault_step else DIM)
        centered(f"SECURITY GATE  {vault_step + 1} / 5", 700, 386, FONT_BOLD, WHITE)
        box(371, 423, 476, 59, (8, 9, 13), 8, (97, 47, 57))
        centered("*" * len(vault_entry) + "_", 609, 436, BIG, RED_BRIGHT)
        button("VERIFY", (862, 424, 194, 57), mouse)
        centered(fit_name(vault_message, 61), 700, 507, SMALL,
                 RED_BRIGHT if "FAILED" in vault_message else YELLOW)
        centered("ESC: BACK   /   FILES STAY LOCAL   /   DISPLAY LOCK ONLY", 700, 608, SMALL, DIM)
        return

    # Explorer: choose folder, then choose a file; PNG/JPEG/WEBP/BMP/GIF are previewed.
    box(282, 126, 834, 531)
    panel_header("BLACK ARCHIVE // CLASSIFIED", "L5 CLEARANCE VERIFIED", 302, 146, 794)
    txt("ARCHIVE ROOT / " + (vault_folder if vault_folder else "SELECT DIRECTORY"), 304, 191, MEDIUM, YELLOW)
    button("BACK", (996, 181, 100, 40), mouse, (60, 64, 76), (78, 83, 97))
    box(302, 237, 315, 389, (11, 14, 19), 8, BORDER)
    box(637, 237, 458, 389, (9, 11, 16), 8, BORDER)
    items = vault_folders() if vault_folder is None else vault_files()
    title = "SUBJECT DOSSIERS" if vault_folder is None else "FILES / " + vault_folder.upper()
    txt(fit_name(title, 29), 319, 254, SMALL, RED_BRIGHT)
    line(317, 282, 597, 282)
    if not items:
        txt("EMPTY DIRECTORY", 329, 311, MEDIUM, DIM)
        if vault_folder is not None:
            txt("ADD FILES TO THIS FOLDER", 327, 341, SMALL, DIM)
    for index in range(vault_scroll, min(len(items), vault_scroll + 8)):
        entry = items[index]
        y = 293 + (index - vault_scroll) * 38
        rect = pygame.Rect(316, y, 284, 34)
        selected = (vault_folder == entry.name) if vault_folder is None else (vault_file == entry.name)
        if selected or rect.collidepoint(mouse):
            box(rect.x, rect.y, rect.w, rect.h, (62, 34, 44) if selected else CARD_HOVER, 6, None)
        txt("DIR" if vault_folder is None else "DOC", 323, y + 8, SMALL, RED_BRIGHT)
        txt(fit_name(entry.name, 25), 371, y + 8, SMALL, WHITE)
    if len(items) > 8:
        txt(f"SCROLL: {vault_scroll + 1}-{min(len(items), vault_scroll + 8)} / {len(items)}", 323, 608, SMALL, DIM)

    if vault_folder is None:
        logo(865, 358, 42)
        centered("SELECT SUBJECT DIRECTORY", 867, 450, MEDIUM, WHITE)
        centered("ALL DATA STORED ON THIS COMPUTER", 867, 481, SMALL, DIM)
        return

    files = vault_files()
    selected = next((p for p in files if p.name == vault_file), None)
    if selected is None:
        centered("SELECT FILE TO PREVIEW", 866, 406, MEDIUM, MUTED)
        centered("PNG / JPG / WEBP / BMP / GIF SUPPORTED", 866, 437, SMALL, DIM)
        return
    extension = selected.suffix.lower()
    if extension in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
        try:
            photo = cached_archive_image(str(selected), selected.stat().st_mtime_ns)
            region = pygame.Rect(654, 252, 426, 316)
            pygame.draw.rect(screen, (5, 6, 9), region)
            sw, sh = photo.get_size()
            scale = min(region.width / sw, region.height / sh)
            scaled = pygame.transform.smoothscale(photo, (max(1, int(sw * scale)), max(1, int(sh * scale))))
            screen.blit(scaled, (region.centerx - scaled.get_width() // 2,
                                region.centery - scaled.get_height() // 2))
        except (pygame.error, OSError, ValueError):
            centered("UNABLE TO DECODE IMAGE", 868, 401, MEDIUM, YELLOW)
    else:
        logo(867, 361, 35)
        centered("DOCUMENT / EXTERNAL VIEWER", 867, 430, MEDIUM, MUTED)
        if extension in (".pdf", ".txt", ".md", ".mp4", ".avi", ".mkv", ".mp3", ".wav"):
            button("OPEN WITH WINDOWS", (711, 477, 314, 44), mouse, (66, 70, 83), (82, 86, 98))
    txt(fit_name(selected.name, 47), 656, 582, SMALL, WHITE)
    try:
        size_kb = selected.stat().st_size // 1024
    except OSError:
        size_kb = 0
    txt(f"FILE SIZE: {size_kb} KB", 656, 605, SMALL, DIM)


def draw_footer():
    line(282, 684, 1116, 684)
    txt("UMBRELLA RESEARCH NETWORK    /    BUILD 3.0", 283, 695, SMALL, DIM)
    audio_label = "AUDIO: ON" if soundtrack and music_on and audio_ready else "AUDIO: OFF" if soundtrack else "AUDIO: NO TRACK"
    right_txt(f"{audio_label}   /   M: SOUND   /   ESC: EXIT", 1115, 695, SMALL, MUTED)


def centered(text, cx, y, font=FONT, color=WHITE):
    surface = font.render(text, True, color)
    screen.blit(surface, (cx - surface.get_width() // 2, y))


def draw_access_background(t):
    screen.fill(BG)
    for x in range(0, WIDTH, 45):
        line(x, 0, x, HEIGHT, (19, 21, 29))
    for y in range(0, HEIGHT, 45):
        line(0, y, WIDTH, y, (19, 21, 29))
    pygame.draw.rect(screen, (56, 18, 25), (0, 0, WIDTH, 5))
    txt("UMBRELLA // INTERNAL SECURITY GATE", 38, 33, SMALL, RED_BRIGHT)
    right_txt("RESEARCH NETWORK / CLASSIFIED", WIDTH - 40, 33, SMALL, MUTED)
    logo(WIDTH // 2, 154, 52)
    centered("U M B R E L L A   C O R P O R A T I O N", WIDTH // 2, 215, MEDIUM, WHITE)
    line(320, 252, 832, 252, (85, 35, 47))
    txt("SECURE ACCESS PROTOCOL", 39, 671, SMALL, DIM)
    right_txt(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"), WIDTH - 39, 671, SMALL, DIM)


def draw_login(mouse, t):
    draw_access_background(t)
    box(331, 277, 490, 303, (17, 19, 26), 12, (92, 42, 54))
    centered("IDENTITY VERIFICATION", WIDTH // 2, 305, BIG, WHITE)
    centered("PERSONNEL ACCESS CODE REQUIRED", WIDTH // 2, 359, SMALL, MUTED)
    box(389, 401, 374, 62, (7, 9, 14), 8, (79, 43, 54))
    centered("* " * len(pin) + "_ " * (4 - len(pin)), WIDTH // 2, 415, BIG, RED_BRIGHT)
    button("AUTHENTICATE", (422, 492, 309, 49), mouse)
    centered("TYPE 4 DIGITS  /  ENTER: VERIFY", WIDTH // 2, 557, SMALL, DIM)


def draw_alarm(mouse, t):
    draw_access_background(t)
    flash = int(t * 5) % 2 == 0
    box(256, 274, 640, 323, (42, 15, 21) if flash else (23, 16, 21), 12,
        RED_BRIGHT if flash else (95, 30, 39), 2)
    centered("SECURITY BREACH DETECTED", WIDTH // 2, 303, BIG, RED_BRIGHT)
    centered("INVALID ACCESS CODE / INTRUSION ALARM ACTIVE", WIDTH // 2, 368, SMALL, WHITE)
    elapsed = pygame.time.get_ticks() - alarm_started
    remaining = max(0, math.ceil((10000 - elapsed) / 1000))
    centered(f"YOUR COMPUTER WILL SHUT DOWN IN {remaining:02d} SECONDS", WIDTH // 2, 416,
             FONT_BOLD, YELLOW)
    centered("NO IN-APP CANCEL // THIS IS A TEST TERMINAL", WIDTH // 2, 481, MEDIUM, WHITE)
    if real_shutdown_scheduled:
        centered("WINDOWS: WIN+R  ->  shutdown /a  -> ENTER", WIDTH // 2, 535, SMALL, YELLOW)
    elif real_shutdown_enabled:
        centered(fit_name(shutdown_error, 74), WIDTH // 2, 535, SMALL, YELLOW)
    else:
        centered("DEMO MODE // WINDOWS IS NOT SHUTTING DOWN", WIDTH // 2, 535, SMALL, DIM)


def draw_demo_offline(mouse, t):
    draw_access_background(t)
    box(332, 293, 488, 258, (13, 15, 21), 12, (80, 34, 43))
    centered("SYSTEM OFFLINE", WIDTH // 2, 326, BIG, RED_BRIGHT)
    centered("SESSION TERMINATED", WIDTH // 2, 392, SMALL, MUTED)
    if real_shutdown_scheduled:
        centered("WINDOWS SHUTDOWN WAS SCHEDULED", WIDTH // 2, 438, SMALL, YELLOW)
        centered("IF ABORTED EXTERNALLY, PRESS R TO RESET", WIDTH // 2, 470, SMALL, DIM)
    else:
        button("RESTART TERMINAL  [R]", (420, 444, 314, 54), mouse)
    centered("SECURITY INCIDENT // TERMINAL OFFLINE", WIDTH // 2, 522, SMALL, DIM)


def mouse_click(pos):
    global selected_project, diag_started, shutdown_confirmation_pending
    global real_shutdown_enabled, vault_folder, vault_file, vault_scroll
    if mode == "login":
        if pygame.Rect(422, 492, 309, 49).collidepoint(pos):
            verify_pin()
        return
    if mode in ("alarm", "demo_offline"):
        if mode == "demo_offline" and not real_shutdown_scheduled and pygame.Rect(420, 444, 314, 54).collidepoint(pos):
            restart_demo()
        return

    for i in range(len(PAGES)):
        if pygame.Rect(15, 166 + i * 56, 220, 46).collidepoint(pos):
            set_page(i)
            return
    if page == 1:
        for i in range(len(PROJECTS)):
            if pygame.Rect(302, 202 + i * 93, 794, 80).collidepoint(pos):
                selected_project = i
                set_notice(f"SELECTED {PROJECTS[i][0]}")
                return
    elif page == 3:
        if pygame.Rect(304, 446, 235, 44).collidepoint(pos):
            diag_started = pygame.time.get_ticks()
            set_notice("SECURITY DIAGNOSTICS INITIATED (SIMULATION)")
        elif pygame.Rect(554, 446, 223, 44).collidepoint(pos):
            terminate_session()
        elif pygame.Rect(876, 540, 218, 47).collidepoint(pos):
            if real_shutdown_enabled:
                real_shutdown_enabled = False
                shutdown_confirmation_pending = False
                save_config()
                set_notice("REAL SHUTDOWN DISABLED // SAFE DEMO")
            elif not shutdown_confirmation_pending:
                shutdown_confirmation_pending = True
                set_notice("WARNING: CLICK CONFIRM AGAIN TO ARM REAL SHUTDOWN")
            else:
                real_shutdown_enabled = True
                shutdown_confirmation_pending = False
                if save_config():
                    set_notice("REAL SHUTDOWN ARMED // WIN+R: shutdown /a")
                else:
                    set_notice("SETTING ARMED TEMPORARILY // SETTINGS NOT SAVED")
    elif page == 4:
        if call_partner is None:
            for i in range(len(CONTACTS)):
                if pygame.Rect(894, 234 + i * 177 + 49, 174, 51).collidepoint(pos):
                    begin_call(i)
                    break
        else:
            if pygame.Rect(864, 457, 232, 50).collidepoint(pos):
                end_call()
                set_notice("CALL ENDED // CHANNEL DISCONNECTED")
            elif pygame.Rect(864, 521, 232, 46).collidepoint(pos):
                if camera is None:
                    start_camera()
                    set_notice("LOCAL CAMERA ENABLED" if camera else camera_error)
                else:
                    stop_camera()
                    set_notice("LOCAL CAMERA DISABLED")
    elif page == 5:
        if not vault_unlocked:
            if pygame.Rect(862, 424, 194, 57).collidepoint(pos):
                verify_vault()
            return
        if pygame.Rect(996, 181, 100, 40).collidepoint(pos):
            vault_folder = None
            vault_file = None
            vault_scroll = 0
            return
        if pygame.Rect(316, 293, 284, 304).collidepoint(pos):
            row = (pos[1] - 293) // 38
            idx = vault_scroll + row
            items = vault_folders() if vault_folder is None else vault_files()
            if 0 <= idx < len(items):
                if vault_folder is None:
                    vault_folder = items[idx].name
                    vault_file = None
                    vault_scroll = 0
                else:
                    vault_file = items[idx].name
            return
        if vault_file is not None and pygame.Rect(711, 477, 314, 44).collidepoint(pos):
            selected = next((p for p in vault_files() if p.name == vault_file), None)
            if (selected is not None and selected.suffix.lower() in
                    (".pdf", ".txt", ".md", ".mp4", ".avi", ".mkv", ".mp3", ".wav")
                    and sys.platform == "win32"):
                try:
                    os.startfile(str(selected))
                except OSError:
                    set_notice("COULD NOT OPEN FILE WITH WINDOWS")


running = True
while running:
    t = pygame.time.get_ticks() / 1000.0
    mouse = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if mode == "alarm":
                pass  # Closing the app DOES NOT cancel an already scheduled OS shutdown.
            elif mode == "demo_offline":
                if (event.key in (pygame.K_r, pygame.K_RETURN)) and not real_shutdown_scheduled:
                    restart_demo()
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif mode == "login":
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    pin = pin[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    verify_pin()
                elif event.unicode and event.unicode in "0123456789" and len(pin) < 4:
                    pin += event.unicode
            elif mode == "terminal":
                if page == 5 and not vault_unlocked:
                    if event.key == pygame.K_ESCAPE:
                        set_page(0)
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                        vault_entry = vault_entry[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        verify_vault()
                    elif event.unicode and (event.unicode.isascii() and (event.unicode.isalnum() or event.unicode in "-_")) and len(vault_entry) < 28:
                        vault_entry += event.unicode.upper()
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m and soundtrack and audio_ready:
                    if music_on:
                        pygame.mixer.music.stop()
                        music_on = False
                    else:
                        music_on = True
                        start_ambient()
                elif event.key == pygame.K_c and page == 4 and call_partner is not None:
                    if camera is None:
                        start_camera()
                    else:
                        stop_camera()
                elif pygame.K_1 <= event.key <= pygame.K_6:
                    set_page(event.key - pygame.K_1)
        elif event.type == pygame.MOUSEWHEEL and mode == "terminal" and page == 5 and vault_unlocked:
            items = vault_folders() if vault_folder is None else vault_files()
            vault_scroll = max(0, min(max(0, len(items) - 8), vault_scroll - event.y))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_click(event.pos)

    if mode == "alarm" and pygame.time.get_ticks() - alarm_started >= 10000:
        stop_audio()
        mode = "demo_offline"  # the Windows OS handles the scheduled shutdown when armed

    if mode == "terminal" and page == 4 and call_partner is not None:
        update_camera_frame()

    if mode == "terminal":
        screen.fill(BG)
        draw_sidebar(mouse)
        draw_header()
        if page == 0:
            draw_overview(mouse, t)
        elif page == 1:
            draw_projects(mouse, t)
        elif page == 2:
            draw_personnel(mouse, t)
        elif page == 3:
            draw_security(mouse, t)
        elif page == 4:
            draw_calls(mouse, t)
        else:
            draw_vault(mouse, t)
        draw_footer()
    elif mode == "login":
        draw_login(mouse, t)
    elif mode == "alarm":
        draw_alarm(mouse, t)
    else:
        draw_demo_offline(mouse, t)

    pygame.display.flip()
    clock.tick(60)

stop_camera()
stop_audio()
pygame.quit()
