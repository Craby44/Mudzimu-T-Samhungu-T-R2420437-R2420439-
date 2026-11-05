"""5-minute demo. Run:  python main.py
Authors: R2420439, R2420437 (group 5, P = 5)."""
from pathlib import Path

from clinic.clinic import Clinic
from clinic.clock import ManualClock
from clinic.errors import ClinicError
from clinic.log import AppointmentLog
from clinic.people import (Patient, Doctor, Nurse, Pharmacist, Staff, Lecturer,
                    MedicalLecturer, Person)


class LabTechnician(Staff):
    """A brand-new Staff subclass, defined in main only. Neither Clinic nor the loop is edited."""
    def role(self):
        return "Lab Technician"

    def fee(self):
        return 7


LOG_DIR = Path(__file__).resolve().parent / "logs"


def header(text):
    print(f"\n=== {text} ===")


def attempt(label, action):
    """Run an action; show business-rule refusals without crashing the demo."""
    try:
        result = action()
        print(f"  ok: {label}")
        return result
    except ClinicError as exc:
        print(f"  refused: {label} -> {exc}")


def main():
    LOG_DIR.mkdir(exist_ok=True)
    header("Part 2: constructors reject bad input")
    for label, make in [("empty name", lambda: Doctor(name="   ", person_id=1)),
                        ("id 0", lambda: Nurse(name="Ann", person_id=0))]:
        try:
            make()
        except ValueError as exc:
            print(f"  rejected {label}: {exc}")

    header("Part 3: one loop, no type checks (P = 5)")
    moyo = Doctor(name="Dr Moyo", person_id=1)
    ncube = Nurse(name="Nurse Ncube", person_id=2)
    dube = Pharmacist(name="Dube", person_id=3)
    sibanda = MedicalLecturer(name="Prof Sibanda", person_id=4, module_name="Anatomy")
    tech = LabTechnician(name="Tafara", person_id=5)
    for member in [moyo, ncube, dube, sibanda, tech]:
        print(f"  {member.role():<22} fee {member.fee()}")

    header("Part 5: diamond, Person constructed once")
    before = Person.instances_created
    MedicalLecturer(name="Prof Test", person_id=90, module_name="Physiology")
    print(f"  Person constructor ran {Person.instances_created - before} time(s)")
    print("  MRO:", " -> ".join(c.__name__ for c in MedicalLecturer.__mro__[:5]))
    lec = Lecturer(name="Mr Plain", person_id=91, module_name="Ethics")
    print(f"  plain {lec.role()} teaches {lec.module_name}")

    header("Parts 4 and 6: clinic session (log opened once, closed once)")
    clock = ManualClock(10)
    with Clinic(clock, AppointmentLog(str(LOG_DIR / "appointments.log"))) as clinic:
        for s in (moyo, ncube, dube, sibanda, tech):
            clinic.add_staff(s)
        alice, bob, carol, dan = (Patient(name=n, person_id=i) for n, i in
                                  [("Alice", 101), ("Bob", 102), ("Carol", 103), ("Dan", 104)])
        for p in (alice, bob, carol, dan):
            clinic.add_patient(p)
        attempt("duplicate id 101", lambda: clinic.add_patient(Patient(name="Eve", person_id=101)))

        attempt("Alice-Moyo@20 (#1)", lambda: clinic.book(101, 1, 20))
        attempt("Bob-Ncube@22 (#2)", lambda: clinic.book(102, 2, 22))
        attempt("Bob-Moyo@20 (staff clash)", lambda: clinic.book(102, 1, 20))
        attempt("Alice-Ncube@20 (patient clash)", lambda: clinic.book(101, 2, 20))

        print("  -- twist: emergency --")
        clinic.flag_emergency(103)
        attempt("Carol (emergency)-Moyo@20 bumps pending #1", lambda: clinic.book(103, 1, 20))
        attempt("confirm #3", lambda: clinic.confirm(3))
        clinic.flag_emergency(104)
        attempt("Dan (emergency)-Moyo@20 vs confirmed", lambda: clinic.book(104, 1, 20))

        attempt("Alice-MedicalLecturer@30 (#4)", lambda: clinic.book(101, 4, 30))
        attempt("Dan-LabTechnician@31 (#5, new subclass)", lambda: clinic.book(104, 5, 31))

        print("  -- state rules --")
        clock.set(19)
        print("  DELIBERATE FAILURE: cancel confirmed #3 at hour 19 (1 h before start)")
        attempt("cancel #3", lambda: clinic.cancel(3))
        clock.set(20)
        attempt("cancel #3 after it started", lambda: clinic.cancel(3))
        attempt("cancel pending #2", lambda: clinic.cancel(2, "patient request"))
        attempt("cancel #2 again", lambda: clinic.cancel(2))
        attempt("confirm cancelled #2 (cannot return)", lambda: clinic.confirm(2))

        print("\n  Final appointments:")
        for a in clinic.appointments():
            print("   ", a.describe(), a.cancel_reason)
        print("\n  Week schedule (active appointments only):")
        for line in clinic.schedule():
            print("   ", line)

    header("Part 4: an error mid-operation still closes the log")
    try:
        with Clinic(ManualClock(0), AppointmentLog()) as crashing:
            crashing.add_staff(Doctor(name="Dr Crash", person_id=1))
            raise RuntimeError("simulated crash")
    except RuntimeError as exc:
        print(f"  caught: {exc}")

    header("D5: the log itself fails (unwritable path)")
    with Clinic(ManualClock(0), AppointmentLog("/no_such_dir/clinic.log")) as degraded:
        degraded.add_staff(Doctor(name="Dr Memory", person_id=1))
        print("  clinic kept working")


if __name__ == "__main__":
    main()
