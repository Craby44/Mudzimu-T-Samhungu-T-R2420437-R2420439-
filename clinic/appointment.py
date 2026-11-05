from enum import Enum
from .errors import ClinicError
from .validation import positive_id, whole_hour

MIN_CANCEL_NOTICE_HOURS = 2     # a CONFIRMED appointment needs >= 2 h notice to cancel
LAST_START_HOUR = 167           # each appointment lasts 1 h and must end by hour 168


class Status(Enum):
    PENDING = 1
    CONFIRMED = 2
    CANCELLED = 3


# Legal transitions. CANCELLED is terminal.
_LEGAL = {
    Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
    Status.CONFIRMED: {Status.CANCELLED},
    Status.CANCELLED: set(),
}


# Invariants of Appointment:
#  1. id is a positive whole number and never changes; start is a whole hour 0..167 and never changes.
#  2. patient and staff are fixed for the life of the appointment.
#  3. status only moves along _LEGAL (PENDING->CONFIRMED, PENDING->CANCELLED, CONFIRMED->CANCELLED).
#  4. CANCELLED never changes again.
#  5. No appointment is confirmed or cancelled once now >= start (it has started).
#  6. A CONFIRMED appointment cannot be cancelled when start - now < 2.
#  7. cancel_reason is set only when status is CANCELLED.
class Appointment:
    def __init__(self, appointment_id, patient, staff, start):
        self._id = positive_id(appointment_id, "appointment id")
        self._start = whole_hour(start, 0, LAST_START_HOUR, "start hour")
        if patient is None or staff is None:
            raise ValueError("an appointment needs a patient and a staff member")
        self._patient = patient
        self._staff = staff
        self._status = Status.PENDING
        self._cancel_reason = ""

    @property
    def id(self):
        return self._id

    @property
    def start(self):
        return self._start

    @property
    def patient(self):
        return self._patient

    @property
    def staff(self):
        return self._staff

    @property
    def status(self):
        return self._status

    @property
    def cancel_reason(self):
        return self._cancel_reason

    def is_active(self):
        return self._status is not Status.CANCELLED

    def confirm(self, now):
        self._require_legal(Status.CONFIRMED)
        if now >= self._start:
            raise ClinicError("already started")
        self._status = Status.CONFIRMED

    def cancel(self, now, reason=""):
        self._require_legal(Status.CANCELLED)
        if now >= self._start:
            raise ClinicError("already started")
        if self._status is Status.CONFIRMED and self._start - now < MIN_CANCEL_NOTICE_HOURS:
            raise ClinicError("too late")
        self._status = Status.CANCELLED
        self._cancel_reason = reason

    def _require_legal(self, target):
        if target in _LEGAL[self._status]:
            return
        if self._status is Status.CANCELLED:
            raise ClinicError("already cancelled")
        if self._status is target:
            raise ClinicError(f"already {target.name.lower()}")
        raise ClinicError(f"illegal transition {self._status.name} -> {target.name}")

    def describe(self):
        return (f"#{self._id} {self._patient.name} with {self._staff.role()} "
                f"{self._staff.name} at hour {self._start} [{self._status.name}]")
