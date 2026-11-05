"""Time is a whole number of hours 0..168. Nothing else in the project reads the computer clock."""
from abc import ABC, abstractmethod
from .validation import whole_hour

MAX_HOUR = 168

class Clock(ABC):
    @abstractmethod
    def now(self):
        """Current hour, 0..168."""

class ManualClock(Clock):
    """Clock driven by the program/tests. Time only moves forward."""
    def __init__(self, start=0):
        self._now = whole_hour(start, 0, MAX_HOUR, "time")

    def now(self):
        return self._now

    def set(self, hour):
        new = whole_hour(hour, 0, MAX_HOUR, "time")
        if new < self._now:
            raise ValueError("time cannot go backwards")
        self._now = new

    def advance(self, hours):
        self.set(self._now + hours)


def format_hour(hour):
    """Readable label for an hour 0..168, e.g. 20 -> 'Day 1 20:00'."""
    return f"Day {hour // 24 + 1} {hour % 24:02d}:00"
