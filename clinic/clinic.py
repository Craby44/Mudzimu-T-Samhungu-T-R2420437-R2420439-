import operator
from contextlib import contextmanager
from .appointment import Appointment, Status, LAST_START_HOUR
from .clock import format_hour
from .errors import ClinicError


# Invariants of Clinic:
#  1. Every person id (patients and staff share one namespace) is unique.
#  2. Appointment ids are unique, assigned by the Clinic, and never reused.
#  3. No staff member and no patient has two non-cancelled appointments at the same hour.
#  4. Every appointment starts in the future when it is booked.
#  5. A failed operation changes nothing, and is written to the log as FAILED <action>: <reason>.
#  6. EMERGENCY twist: only a patient flagged emergency may bump, only a PENDING appointment,
#     and a bumped appointment is cancelled with reason "bumped". CONFIRMED is never bumped.
#  7. The log is opened once and closed once per Clinic, by the with-statement.
# The Clinic never tests what kind of staff or patient it holds; it only calls their methods.
class Clinic:
    def __init__(self, clock, log):
        self._clock = clock
        self._log = log
        self._patients = {}
        self._staff = {}
        self._appointments = {}
        self._used_ids = set()
        self._next_appointment_id = 1

    # ---- log lifecycle: with Clinic(...) as clinic: ... ----
    def __enter__(self):
        self._log.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._log.close()          # always runs, even if the body raised
        return False               # never swallow the error

    @contextmanager
    def _action(self, label):
        try:
            yield
        except ClinicError as exc:
            self._log_failure(label, exc)
            raise
        except Exception as exc:
            self._log_failure(label, f"unexpected error: {exc}")
            raise

    def _log_failure(self, label, reason):
        if self._log.is_open:
            self._log.write(f"FAILED {label}: {reason}")

    # ---- registration ----
    def add_patient(self, patient):
        self._register(patient, self._patients, "patient")

    def add_staff(self, staff):
        self._register(staff, self._staff, "staff")

    def _register(self, person, table, kind):
        with self._action(f"register {kind} #{person.id}"):
            if person.id in self._used_ids:
                raise ClinicError(f"id {person.id} already in use")
            self._used_ids.add(person.id)
            table[person.id] = person
            self._log.write(f"REGISTERED {person.role()} {person.name} #{person.id}")

    def flag_emergency(self, patient_id, flag=True):
        with self._action(f"flag emergency patient #{patient_id}"):
            patient = self._find(self._patients, patient_id, "patient")
            patient.flag_emergency(flag)
            self._log.write(f"EMERGENCY {'on' if flag else 'off'} for {patient.name}")

    # ---- booking ----
    def book(self, patient_id, staff_id, start):
        now = self._clock.now()
        with self._action(f"book patient #{patient_id} with staff #{staff_id} at hour {start}"):
            patient = self._find(self._patients, patient_id, "patient")
            staff = self._find(self._staff, staff_id, "staff")
            try:
                start = operator.index(start)
            except TypeError:
                raise ClinicError("start hour must be a whole number") from None
            if not 0 <= start <= LAST_START_HOUR:
                raise ClinicError(f"start hour must be 0-{LAST_START_HOUR}")
            if start <= now:
                raise ClinicError("start is not in the future")

            active = [a for a in self._appointments.values() if a.is_active() and a.start == start]
            if any(a.patient is patient for a in active):
                raise ClinicError("patient already booked at that hour")
            staff_clash = [a for a in active if a.staff is staff]

            if staff_clash:
                if not patient.is_emergency:
                    raise ClinicError("staff already booked at that hour")
                if any(a.status is Status.CONFIRMED for a in staff_clash):
                    raise ClinicError("cannot bump a confirmed appointment")
                # every check passed: bumping cannot fail now, so nothing is half-done
                for victim in staff_clash:
                    victim.cancel(now, "bumped")
                    self._log.write(f"BUMPED #{victim.id} ({victim.patient.name}) "
                                    f"for emergency patient {patient.name}")

            appointment = Appointment(self._next_appointment_id, patient, staff, start)
            self._next_appointment_id += 1
            self._appointments[appointment.id] = appointment
            self._log.write(f"BOOKED {appointment.describe()} fee {staff.fee()}")
            return appointment

    def confirm(self, appointment_id):
        with self._action(f"confirm #{appointment_id}"):
            appointment = self._find(self._appointments, appointment_id, "appointment")
            appointment.confirm(self._clock.now())
            self._log.write(f"CONFIRMED #{appointment_id}")

    def cancel(self, appointment_id, reason=""):
        with self._action(f"cancel #{appointment_id}"):
            appointment = self._find(self._appointments, appointment_id, "appointment")
            appointment.cancel(self._clock.now(), reason)
            self._log.write(f"CANCELLED #{appointment_id}" + (f" ({reason})" if reason else ""))

    # ---- read-only views: always copies ----
    def appointments(self):
        return tuple(self._appointments.values())

    def appointments_for_staff(self, staff_id):
        return tuple(a for a in self._appointments.values() if a.staff.id == staff_id)

    def schedule(self):
        """Week plan of non-cancelled appointments, earliest first (a tuple of text lines)."""
        rows = sorted((a for a in self._appointments.values() if a.is_active()),
                      key=lambda a: (a.start, a.id))
        return tuple(f"{format_hour(a.start)}  {a.staff.role():<20} {a.staff.name:<13}"
                     f" <- {a.patient.name} [{a.status.name}]" for a in rows)

    def staff_members(self):
        return tuple(self._staff.values())

    def patients(self):
        return tuple(self._patients.values())

    @staticmethod
    def _find(table, key, what):
        try:
            return table[key]
        except KeyError:
            raise ClinicError(f"unknown {what} #{key}") from None
