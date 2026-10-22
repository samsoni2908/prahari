"""Non-clinical output terminology contract, shared by runtime and offline evaluation."""
from typing import List

BANNED_PHRASES: List[str] = [
    "depressed",
    "depression",
    "mentally unstable",
    "mentally weak",
    "unfit",
    "psychologically unsafe",
    "clinical stress",
    "burnout",
    "ptsd",
    "suicide",
    "self-harm",
    "mental health disorder",
    "psychiatric",
]
