import os
import math
import struct
import wave
import logging
from typing import Optional, Tuple

logger = logging.getLogger("echosphere.chimes")

STATIC_CHIMES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static",
    "chimes",
)


def ensure_chimes_dir_exists():
    try:
        os.makedirs(STATIC_CHIMES_DIR, exist_ok=True)
    except Exception:
        pass


def resolve_contextual_chime(
    priority: str = "NORMAL",
    category: str = "General",
    emergency_level: str = "NORMAL",
    title: str = "",
    content: str = "",
) -> str:
    """
    AI contextual chime selector:
    - EMERGENCY -> 'emergency' (Sweeping siren pulse)
    - HIGH/URGENT or Examination/Academic/Fee Payment -> 'urgent_academic' (Professional double-beep chime)
    - Event/Sports/Cultural/Placement -> 'events_sports' (Upbeat electronic acoustic ding)
    - Other -> 'standard' (Gentle campus chime)
    """
    p_upper = priority.upper() if priority else "NORMAL"
    e_upper = emergency_level.upper() if emergency_level else "NORMAL"
    c_lower = category.lower() if category else ""
    combined = f"{title} {content}".lower()

    if p_upper == "EMERGENCY" or e_upper in ["CRITICAL", "HIGH"] or "emergency" in combined:
        return "emergency"

    if (
        p_upper in ["URGENT", "HIGH"]
        or any(k in c_lower for k in ["exam", "academic", "fee", "deadline", "circular"])
        or any(k in combined for k in ["deadline", "viva", "hall ticket", "mandatory", "urgent"])
    ):
        return "urgent_academic"

    if (
        any(k in c_lower for k in ["event", "sport", "cultural", "placement", "fest", "workshop", "club"])
        or any(k in combined for k in ["sports day", "hackathon", "symposium", "tournament", "fest"])
    ):
        return "events_sports"

    return "standard"


def synthesize_tone(
    freq: float,
    duration: float,
    sample_rate: int = 24000,
    amplitude: int = 14000,
    attack_sec: float = 0.015,
    decay_exp: float = 4.0,
    harmonics: Tuple[Tuple[float, float], ...] = ((2.0, 0.25), (3.0, 0.1)),
) -> bytes:
    """
    Synthesizes a single high-quality acoustic tone with harmonic overtones and an exponential decay envelope.
    Returns raw 16-bit PCM bytes (mono).
    """
    num_samples = int(sample_rate * duration)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        # Envelope: fast linear attack, exponential decay
        if t < attack_sec:
            envelope = t / attack_sec
        else:
            envelope = math.exp(-decay_exp * (t - attack_sec) / (duration - attack_sec))

        # Fundamental + harmonic overtones
        sample_val = math.sin(2 * math.pi * freq * t)
        for mult, weight in harmonics:
            sample_val += weight * math.sin(2 * math.pi * (freq * mult) * t)

        val = int(amplitude * envelope * sample_val)
        val = max(-32767, min(32767, val))
        samples.append(struct.pack("<h", val))

    return b"".join(samples)


def synthesize_silence(duration: float, sample_rate: int = 24000) -> bytes:
    num_samples = int(sample_rate * duration)
    return b"\x00\x00" * num_samples


def generate_chime_pcm(chime_type: str, sample_rate: int = 24000) -> bytes:
    """
    Generates raw 16-bit mono PCM bytes for the requested chime type:
    - 'urgent_academic': Professional double-beep bell chime (880 Hz / A5 -> 1046.5 Hz / C6)
    - 'events_sports': Upbeat electronic acoustic major arpeggio ding (C5 -> E5 -> G5)
    - 'emergency': Sweeping siren pulse warble (600 Hz to 1200 Hz sweep)
    - 'standard': Gentle campus marimba chime
    """
    c_type = chime_type.lower()

    if c_type in ["urgent_academic", "urgent", "academic"]:
        # Professional double-beep chime
        tone1 = synthesize_tone(880.0, 0.14, sample_rate=sample_rate, amplitude=15000, decay_exp=4.5)
        gap = synthesize_silence(0.06, sample_rate=sample_rate)
        tone2 = synthesize_tone(1046.5, 0.26, sample_rate=sample_rate, amplitude=16000, decay_exp=3.8)
        trailing = synthesize_silence(0.18, sample_rate=sample_rate)
        return tone1 + gap + tone2 + trailing

    elif c_type in ["events_sports", "events", "sports"]:
        # Upbeat electronic acoustic ding: C5 (523.25) -> E5 (659.25) -> G5 (783.99)
        tone1 = synthesize_tone(523.25, 0.12, sample_rate=sample_rate, amplitude=13000, decay_exp=5.0)
        gap1 = synthesize_silence(0.03, sample_rate=sample_rate)
        tone2 = synthesize_tone(659.25, 0.12, sample_rate=sample_rate, amplitude=14000, decay_exp=5.0)
        gap2 = synthesize_silence(0.03, sample_rate=sample_rate)
        tone3 = synthesize_tone(783.99, 0.38, sample_rate=sample_rate, amplitude=16000, decay_exp=3.2)
        trailing = synthesize_silence(0.18, sample_rate=sample_rate)
        return tone1 + gap1 + tone2 + gap2 + tone3 + trailing

    elif c_type == "emergency":
        # Immediate sweeping siren pulse (600Hz -> 1200Hz frequency modulation)
        duration = 0.65
        num_samples = int(sample_rate * duration)
        samples = []
        phase = 0.0

        for i in range(num_samples):
            t = i / sample_rate
            # 3Hz sweep rate between 600 Hz and 1300 Hz
            inst_freq = 950.0 + 350.0 * math.sin(2 * math.pi * 3.5 * t)
            phase += 2 * math.pi * inst_freq / sample_rate
            envelope = min(1.0, t / 0.05) * min(1.0, (duration - t) / 0.05)
            val = int(18000 * envelope * math.sin(phase))
            val = max(-32767, min(32767, val))
            samples.append(struct.pack("<h", val))

        trailing = synthesize_silence(0.25, sample_rate=sample_rate)
        return b"".join(samples) + trailing

    else:
        # Standard campus attention chime: D5 (587.33 Hz) -> A5 (880.0 Hz)
        tone1 = synthesize_tone(587.33, 0.16, sample_rate=sample_rate, amplitude=13000, decay_exp=4.2)
        gap = synthesize_silence(0.06, sample_rate=sample_rate)
        tone2 = synthesize_tone(880.0, 0.28, sample_rate=sample_rate, amplitude=14000, decay_exp=3.5)
        trailing = synthesize_silence(0.18, sample_rate=sample_rate)
        return tone1 + gap + tone2 + trailing


def get_or_create_chime_wav(chime_type: str, sample_rate: int = 24000) -> str:
    """
    Returns absolute path to cached WAV chime file. Generates it if not present.
    """
    ensure_chimes_dir_exists()
    canonical_type = chime_type.lower()
    if canonical_type not in ["urgent_academic", "events_sports", "emergency", "standard"]:
        canonical_type = "standard"

    file_path = os.path.join(STATIC_CHIMES_DIR, f"chime_{canonical_type}_{sample_rate}hz.wav")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 512:
        return file_path

    pcm_data = generate_chime_pcm(canonical_type, sample_rate=sample_rate)
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)

    logger.info(f"Synthesized acoustic chime ({canonical_type}): {file_path}")
    return file_path


def prepend_chime_to_wav_file(
    speech_wav_path: str,
    output_wav_path: str,
    chime_type: str = "standard",
) -> bool:
    """
    Prepends the selected chime onto a speech WAV file and writes output_wav_path.
    Automatically matches speech file sample rate and audio channels.
    """
    if not os.path.exists(speech_wav_path):
        return False

    try:
        with wave.open(speech_wav_path, "rb") as speech_wf:
            channels = speech_wf.getnchannels()
            sampwidth = speech_wf.getsampwidth()
            framerate = speech_wf.getframerate()
            speech_frames = speech_wf.readframes(speech_wf.getnframes())

        # Generate chime matching framerate
        chime_pcm = generate_chime_pcm(chime_type, sample_rate=framerate)

        # If speech is stereo (2 channels), duplicate mono chime to stereo
        if channels == 2 and sampwidth == 2:
            stereo_samples = []
            for i in range(0, len(chime_pcm), 2):
                s = chime_pcm[i:i+2]
                stereo_samples.append(s + s)
            chime_pcm = b"".join(stereo_samples)

        combined_frames = chime_pcm + speech_frames

        with wave.open(output_wav_path, "wb") as out_wf:
            out_wf.setnchannels(channels)
            out_wf.setsampwidth(sampwidth)
            out_wf.setframerate(framerate)
            out_wf.writeframes(combined_frames)

        return True
    except Exception as e:
        logger.error(f"Error prepending chime to WAV: {e}")
        return False
