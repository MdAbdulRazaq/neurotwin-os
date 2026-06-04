"""
lip_sync.py — Rule-based text-to-viseme cue generator.
Produces timed viseme cues for Three.js avatar lip-sync.
No external dependencies required.
"""
import re
from typing import List, Dict, Any

# Phoneme → viseme class mapping (simplified English rules)
VISEME_MAP = {
    # Bilabials
    'p': 'PP', 'b': 'PP', 'm': 'PP',
    # Labiodentals
    'f': 'FF', 'v': 'FF',
    # Dentals / alveolars
    'th': 'TH', 'dh': 'TH',
    't': 'DD', 'd': 'DD', 'n': 'DD', 'l': 'DD',
    # Sibilants
    's': 'SS', 'z': 'SS', 'sh': 'SS', 'zh': 'SS',
    'ch': 'CH', 'jh': 'CH',
    # Velars
    'k': 'kk', 'g': 'kk', 'ng': 'kk',
    # Glottals / approximants
    'h': 'PP', 'r': 'RR', 'w': 'OO', 'y': 'I',
    # Vowels
    'aa': 'aa', 'ae': 'aa', 'ah': 'aa',
    'ao': 'O', 'aw': 'O', 'oy': 'O',
    'ow': 'OO', 'uw': 'OO', 'uh': 'OO',
    'eh': 'E', 'ey': 'E', 'er': 'E',
    'ih': 'I', 'iy': 'I',
    'silence': 'sil',
}

VOWELS = set('aeiouAEIOU')

def _char_to_viseme(char: str) -> str:
    """Map a single character to a viseme class."""
    if char in VOWELS:
        v = char.lower()
        if v in ('a',): return 'aa'
        if v in ('e',): return 'E'
        if v in ('i',): return 'I'
        if v in ('o',): return 'O'
        if v in ('u',): return 'OO'
    c = char.lower()
    if c in ('p', 'b', 'm'): return 'PP'
    if c in ('f', 'v'): return 'FF'
    if c in ('t', 'd', 'n', 'l'): return 'DD'
    if c in ('s', 'z'): return 'SS'
    if c in ('k', 'g'): return 'kk'
    if c in ('r',): return 'RR'
    if c in ('w',): return 'OO'
    if c in ('y',): return 'I'
    return 'sil'


def text_to_viseme_cues(text: str, duration: float) -> List[Dict[str, Any]]:
    """
    Convert text to a list of timed viseme cues for avatar lip-sync.

    Args:
        text: The spoken text string.
        duration: Total speech duration in seconds.

    Returns:
        List of cue dicts with keys: time (float, seconds), viseme (str), weight (float 0-1)
    """
    # Strip punctuation, split into characters
    clean = re.sub(r'[^a-zA-Z ]', '', text).strip()
    if not clean or duration <= 0:
        return [{"time": 0.0, "viseme": "sil", "weight": 0.0}]

    chars = [c for c in clean if c != ' ']
    if not chars:
        return [{"time": 0.0, "viseme": "sil", "weight": 0.0}]

    cues: List[Dict[str, Any]] = []
    n = len(chars)
    # Add leading silence
    cues.append({"time": 0.0, "viseme": "sil", "weight": 0.0})

    for i, char in enumerate(chars):
        t = (i / n) * duration
        viseme = _char_to_viseme(char)
        weight = 1.0 if char.lower() in 'aeioupbmfv' else 0.6
        cues.append({"time": round(t, 3), "viseme": viseme, "weight": weight})

    # Add trailing silence
    cues.append({"time": round(duration, 3), "viseme": "sil", "weight": 0.0})
    return cues
