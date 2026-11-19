"""Illustrative multi-signal accident candidate detector. NOT a trained model."""
from collections import deque

class CandidateDetector:
    def __init__(self, window=10, minimum_hits=7, threshold=0.75):
        self.scores = deque(maxlen=window)
        self.window = window
        self.minimum_hits = minimum_hits
        self.threshold = threshold
        self.triggered = False

    def update(self, vision: float, impact: float, speed_drop: float) -> bool:
        """All inputs are normalized [0,1]. Returns once per sustained event."""
        if not all(0 <= x <= 1 for x in (vision, impact, speed_drop)):
            raise ValueError('All signals must be in [0, 1]')
        score = 0.5 * vision + 0.3 * impact + 0.2 * speed_drop
        self.scores.append(score)
        hits = sum(x >= self.threshold for x in self.scores)
        candidate = len(self.scores) == self.window and hits >= self.minimum_hits
        if not candidate:
            self.triggered = False
        elif not self.triggered:
            self.triggered = True
            return True
        return False
