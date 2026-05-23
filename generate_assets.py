<<<<<<< HEAD
#!/usr/bin/env python3
"""
generate_assets.py
------------------
Membuat aset media dummy untuk Web Kelulusan APTRG Laboratory 2026:
  - assets/victory-dance.mp4   (5 detik, animasi placeholder)
  - assets/celebration-sound.mp3 (3 detik, nada perayaan sintetis)
  - assets/celebration-sound.wav (cadangan jika MP3 gagal)

Jalankan dari root proyek:
  pip install -r requirements.txt
  python generate_assets.py
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
VIDEO_PATH = ASSETS_DIR / "victory-dance.mp4"
AUDIO_MP3_PATH = ASSETS_DIR / "celebration-sound.mp3"
AUDIO_WAV_PATH = ASSETS_DIR / "celebration-sound.wav"

VIDEO_DURATION_SEC = 5
VIDEO_FPS = 30
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 360

AUDIO_DURATION_SEC = 3
AUDIO_SAMPLE_RATE = 44100

# Warna brand APTRG (BGR untuk OpenCV)
COLOR_CYAN = (217, 184, 0)   # #00b8d9
COLOR_RED = (95, 90, 255)    # #ff5a5f
COLOR_NAVY = (47, 25, 10)    # #0a192f
COLOR_WHITE = (255, 255, 255)


def ensure_assets_dir() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Folder assets: {ASSETS_DIR}")


# ---------------------------------------------------------------------------
# Video — dancing shape + teks "LULUS!"
# ---------------------------------------------------------------------------
def draw_star(frame: np.ndarray, cx: int, cy: int, radius: int, angle: float, color: tuple) -> None:
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        a = angle + i * math.pi / 5
        points.append([int(cx + r * math.cos(a)), int(cy + r * math.sin(a))])
    pts = np.array(points, dtype=np.int32)
    cv2.fillPoly(frame, [pts], color)
    cv2.polylines(frame, [pts], True, COLOR_WHITE, 2)


def generate_video() -> None:
    print("[..] Membuat video dummy...")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(VIDEO_PATH),
        fourcc,
        VIDEO_FPS,
        (VIDEO_WIDTH, VIDEO_HEIGHT),
    )

    if not writer.isOpened():
        raise RuntimeError("Gagal membuka VideoWriter. Pastikan codec mp4v tersedia.")

    total_frames = VIDEO_DURATION_SEC * VIDEO_FPS

    for frame_idx in range(total_frames):
        t = frame_idx / VIDEO_FPS
        frame = np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), COLOR_NAVY, dtype=np.uint8)

        # Grid halus
        for x in range(0, VIDEO_WIDTH, 40):
            cv2.line(frame, (x, 0), (x, VIDEO_HEIGHT), (30, 30, 30), 1)
        for y in range(0, VIDEO_HEIGHT, 40):
            cv2.line(frame, (0, y), (VIDEO_WIDTH, y), (30, 30, 30), 1)

        # Bintang berputar + "menari" (geser horizontal sinusoidal)
        angle = t * 4 * math.pi
        bounce = int(25 * math.sin(t * 6 * math.pi))
        sway = int(40 * math.sin(t * 3 * math.pi))
        cx = VIDEO_WIDTH // 2 + sway
        cy = VIDEO_HEIGHT // 2 + bounce
        draw_star(frame, cx, cy, 55, angle, COLOR_CYAN)

        # Lingkaran orbit (merah)
        orbit_x = int(cx + 90 * math.cos(t * 5))
        orbit_y = int(cy + 50 * math.sin(t * 5))
        cv2.circle(frame, (orbit_x, orbit_y), 18, COLOR_RED, -1)
        cv2.circle(frame, (orbit_x, orbit_y), 18, COLOR_WHITE, 2)

        # Teks LULUS!
        scale = 1.0 + 0.08 * math.sin(t * 8 * math.pi)
        font = cv2.FONT_HERSHEY_DUPLEX
        text = "LULUS!"
        text_size, _ = cv2.getTextSize(text, font, 1.4 * scale, 3)
        tx = (VIDEO_WIDTH - text_size[0]) // 2
        ty = VIDEO_HEIGHT - 45
        cv2.putText(
            frame, text, (tx, ty), font,
            1.4 * scale, COLOR_RED, 3, cv2.LINE_AA,
        )
        cv2.putText(
            frame, "APTRG 2026", (tx - 10, ty + 35), font,
            0.55, COLOR_CYAN, 1, cv2.LINE_AA,
        )

        writer.write(frame)

    writer.release()
    print(f"[OK] Video: {VIDEO_PATH} ({VIDEO_DURATION_SEC}s @ {VIDEO_FPS}fps)")


# ---------------------------------------------------------------------------
# Audio — urutan nada perayaan (WAV) lalu konversi ke MP3
# ---------------------------------------------------------------------------
def generate_tone(
    frequency: float,
    duration: float,
    volume: float = 0.35,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> np.ndarray:
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    wave_data = volume * np.sin(2 * np.pi * frequency * t)
    # Envelope attack/release agar tidak "click"
    attack = int(0.02 * sample_rate)
    release = int(0.04 * sample_rate)
    env = np.ones(n_samples)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return wave_data * env


def generate_wav() -> None:
    print("[..] Membuat audio dummy (WAV)...")

    # Melodi singkat naik (nada perayaan)
    notes = [
        (523.25, 0.25),  # C5
        (659.25, 0.25),  # E5
        (783.99, 0.30),  # G5
        (1046.50, 0.45), # C6
        (880.00, 0.35),  # A5
        (1046.50, 0.50), # C6
    ]

    segments = [generate_tone(freq, dur) for freq, dur in notes]
    audio = np.concatenate(segments)

    # Pad / trim ke durasi target
    target_len = int(AUDIO_DURATION_SEC * AUDIO_SAMPLE_RATE)
    if len(audio) < target_len:
        audio = np.pad(audio, (0, target_len - len(audio)))
    else:
        audio = audio[:target_len]

    # Normalisasi ke int16
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)

    with wave.open(str(AUDIO_WAV_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())

    print(f"[OK] Audio WAV: {AUDIO_WAV_PATH}")


def _ffmpeg_executable() -> str | None:
    """Cari ffmpeg: PATH sistem → imageio-ffmpeg bundle → None."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def convert_wav_to_mp3() -> bool:
    """Konversi WAV → MP3 via ffmpeg (sistem atau imageio-ffmpeg)."""
    print("[..] Mengonversi ke MP3...")

    ffmpeg = _ffmpeg_executable()
    if not ffmpeg:
        print(
            "     ffmpeg tidak ditemukan. Jalankan: pip install imageio-ffmpeg\n"
            "     Atau gunakan celebration-sound.wav (fallback di script.js)."
        )
        return False

    try:
        subprocess.run(
            [
                ffmpeg, "-y", "-i", str(AUDIO_WAV_PATH),
                "-codec:a", "libmp3lame", "-b:a", "128k",
                str(AUDIO_MP3_PATH),
            ],
            check=True,
            capture_output=True,
        )
        print(f"[OK] Audio MP3: {AUDIO_MP3_PATH}")
        return True
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode(errors="ignore")[:300] if exc.stderr else str(exc)
        print(f"     ffmpeg gagal: {err}")
        return False
    except FileNotFoundError:
        print("     ffmpeg tidak dapat dijalankan.")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print(" APTRG — Generator Aset Media Dummy")
    print("=" * 60)

    try:
        ensure_assets_dir()
        generate_video()
        generate_wav()
        convert_wav_to_mp3()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1

    print("\nSelesai! File siap dipakai di web:")
    print(f"  - {VIDEO_PATH}")
    if AUDIO_MP3_PATH.exists():
        print(f"  - {AUDIO_MP3_PATH}")
    print(f"  - {AUDIO_WAV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
=======
#!/usr/bin/env python3
"""
generate_assets.py
------------------
Membuat aset media dummy untuk Web Kelulusan APTRG Laboratory 2026:
  - assets/victory-dance.mp4   (5 detik, animasi placeholder)
  - assets/celebration-sound.mp3 (3 detik, nada perayaan sintetis)
  - assets/celebration-sound.wav (cadangan jika MP3 gagal)

Jalankan dari root proyek:
  pip install -r requirements.txt
  python generate_assets.py
"""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
VIDEO_PATH = ASSETS_DIR / "victory-dance.mp4"
AUDIO_MP3_PATH = ASSETS_DIR / "celebration-sound.mp3"
AUDIO_WAV_PATH = ASSETS_DIR / "celebration-sound.wav"

VIDEO_DURATION_SEC = 5
VIDEO_FPS = 30
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 360

AUDIO_DURATION_SEC = 3
AUDIO_SAMPLE_RATE = 44100

# Warna brand APTRG (BGR untuk OpenCV)
COLOR_CYAN = (217, 184, 0)   # #00b8d9
COLOR_RED = (95, 90, 255)    # #ff5a5f
COLOR_NAVY = (47, 25, 10)    # #0a192f
COLOR_WHITE = (255, 255, 255)


def ensure_assets_dir() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Folder assets: {ASSETS_DIR}")


# ---------------------------------------------------------------------------
# Video — dancing shape + teks "LULUS!"
# ---------------------------------------------------------------------------
def draw_star(frame: np.ndarray, cx: int, cy: int, radius: int, angle: float, color: tuple) -> None:
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        a = angle + i * math.pi / 5
        points.append([int(cx + r * math.cos(a)), int(cy + r * math.sin(a))])
    pts = np.array(points, dtype=np.int32)
    cv2.fillPoly(frame, [pts], color)
    cv2.polylines(frame, [pts], True, COLOR_WHITE, 2)


def generate_video() -> None:
    print("[..] Membuat video dummy...")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(VIDEO_PATH),
        fourcc,
        VIDEO_FPS,
        (VIDEO_WIDTH, VIDEO_HEIGHT),
    )

    if not writer.isOpened():
        raise RuntimeError("Gagal membuka VideoWriter. Pastikan codec mp4v tersedia.")

    total_frames = VIDEO_DURATION_SEC * VIDEO_FPS

    for frame_idx in range(total_frames):
        t = frame_idx / VIDEO_FPS
        frame = np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), COLOR_NAVY, dtype=np.uint8)

        # Grid halus
        for x in range(0, VIDEO_WIDTH, 40):
            cv2.line(frame, (x, 0), (x, VIDEO_HEIGHT), (30, 30, 30), 1)
        for y in range(0, VIDEO_HEIGHT, 40):
            cv2.line(frame, (0, y), (VIDEO_WIDTH, y), (30, 30, 30), 1)

        # Bintang berputar + "menari" (geser horizontal sinusoidal)
        angle = t * 4 * math.pi
        bounce = int(25 * math.sin(t * 6 * math.pi))
        sway = int(40 * math.sin(t * 3 * math.pi))
        cx = VIDEO_WIDTH // 2 + sway
        cy = VIDEO_HEIGHT // 2 + bounce
        draw_star(frame, cx, cy, 55, angle, COLOR_CYAN)

        # Lingkaran orbit (merah)
        orbit_x = int(cx + 90 * math.cos(t * 5))
        orbit_y = int(cy + 50 * math.sin(t * 5))
        cv2.circle(frame, (orbit_x, orbit_y), 18, COLOR_RED, -1)
        cv2.circle(frame, (orbit_x, orbit_y), 18, COLOR_WHITE, 2)

        # Teks LULUS!
        scale = 1.0 + 0.08 * math.sin(t * 8 * math.pi)
        font = cv2.FONT_HERSHEY_DUPLEX
        text = "LULUS!"
        text_size, _ = cv2.getTextSize(text, font, 1.4 * scale, 3)
        tx = (VIDEO_WIDTH - text_size[0]) // 2
        ty = VIDEO_HEIGHT - 45
        cv2.putText(
            frame, text, (tx, ty), font,
            1.4 * scale, COLOR_RED, 3, cv2.LINE_AA,
        )
        cv2.putText(
            frame, "APTRG 2026", (tx - 10, ty + 35), font,
            0.55, COLOR_CYAN, 1, cv2.LINE_AA,
        )

        writer.write(frame)

    writer.release()
    print(f"[OK] Video: {VIDEO_PATH} ({VIDEO_DURATION_SEC}s @ {VIDEO_FPS}fps)")


# ---------------------------------------------------------------------------
# Audio — urutan nada perayaan (WAV) lalu konversi ke MP3
# ---------------------------------------------------------------------------
def generate_tone(
    frequency: float,
    duration: float,
    volume: float = 0.35,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> np.ndarray:
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    wave_data = volume * np.sin(2 * np.pi * frequency * t)
    # Envelope attack/release agar tidak "click"
    attack = int(0.02 * sample_rate)
    release = int(0.04 * sample_rate)
    env = np.ones(n_samples)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return wave_data * env


def generate_wav() -> None:
    print("[..] Membuat audio dummy (WAV)...")

    # Melodi singkat naik (nada perayaan)
    notes = [
        (523.25, 0.25),  # C5
        (659.25, 0.25),  # E5
        (783.99, 0.30),  # G5
        (1046.50, 0.45), # C6
        (880.00, 0.35),  # A5
        (1046.50, 0.50), # C6
    ]

    segments = [generate_tone(freq, dur) for freq, dur in notes]
    audio = np.concatenate(segments)

    # Pad / trim ke durasi target
    target_len = int(AUDIO_DURATION_SEC * AUDIO_SAMPLE_RATE)
    if len(audio) < target_len:
        audio = np.pad(audio, (0, target_len - len(audio)))
    else:
        audio = audio[:target_len]

    # Normalisasi ke int16
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)

    with wave.open(str(AUDIO_WAV_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())

    print(f"[OK] Audio WAV: {AUDIO_WAV_PATH}")


def _ffmpeg_executable() -> str | None:
    """Cari ffmpeg: PATH sistem → imageio-ffmpeg bundle → None."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def convert_wav_to_mp3() -> bool:
    """Konversi WAV → MP3 via ffmpeg (sistem atau imageio-ffmpeg)."""
    print("[..] Mengonversi ke MP3...")

    ffmpeg = _ffmpeg_executable()
    if not ffmpeg:
        print(
            "     ffmpeg tidak ditemukan. Jalankan: pip install imageio-ffmpeg\n"
            "     Atau gunakan celebration-sound.wav (fallback di script.js)."
        )
        return False

    try:
        subprocess.run(
            [
                ffmpeg, "-y", "-i", str(AUDIO_WAV_PATH),
                "-codec:a", "libmp3lame", "-b:a", "128k",
                str(AUDIO_MP3_PATH),
            ],
            check=True,
            capture_output=True,
        )
        print(f"[OK] Audio MP3: {AUDIO_MP3_PATH}")
        return True
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode(errors="ignore")[:300] if exc.stderr else str(exc)
        print(f"     ffmpeg gagal: {err}")
        return False
    except FileNotFoundError:
        print("     ffmpeg tidak dapat dijalankan.")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print(" APTRG — Generator Aset Media Dummy")
    print("=" * 60)

    try:
        ensure_assets_dir()
        generate_video()
        generate_wav()
        convert_wav_to_mp3()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1

    print("\nSelesai! File siap dipakai di web:")
    print(f"  - {VIDEO_PATH}")
    if AUDIO_MP3_PATH.exists():
        print(f"  - {AUDIO_MP3_PATH}")
    print(f"  - {AUDIO_WAV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
>>>>>>> 3889ed19acbbe31209042fc52b3d76a5ea2220d5
