"""Shared argument checks. Uses duck typing (strip / operator.index), never type tests."""
import operator

def clean_text(value, label):
    try:
        cleaned = value.strip()
    except AttributeError:
        raise ValueError(f"{label} must be text") from None
    if not cleaned:
        raise ValueError(f"{label} must not be empty")
    return cleaned

def positive_id(value, label="id"):
    try:
        number = operator.index(value)
    except TypeError:
        raise ValueError(f"{label} must be a whole number") from None
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number

def whole_hour(value, low, high, label="hour"):
    try:
        hour = operator.index(value)
    except TypeError:
        raise ValueError(f"{label} must be a whole number") from None
    if not low <= hour <= high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return hour
