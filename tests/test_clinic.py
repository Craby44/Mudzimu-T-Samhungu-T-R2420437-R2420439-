import pathlib
import unittest
from clinic.appointment import Status
from clinic.clinic import Clinic
from clinic.clock import ManualClock
from clinic.errors import ClinicError
from clinic.log import AppointmentLog
from clinic.people import Patient, Doctor, Nurse, Pharmacist, Lecturer, MedicalLecturer, Person


def make(now=10):
    clock = ManualClock(now)
    log = AppointmentLog(echo=lambda s: None)
    clinic = Clinic(clock, log)
    log.open()
    clinic.add_staff(Doctor(name="Dr A", person_id=1))
    clinic.add_staff(Nurse(name="N B", person_id=2))
    clinic.add_patient(Patient(name="Pat", person_id=101))
    clinic.add_patient(Patient(name="Quin", person_id=102))
    return clock, log, clinic


class Tests(unittest.TestCase):
    def test_constructors(self):
        with self.assertRaises(ValueError): Doctor(name="", person_id=1)
        with self.assertRaises(ValueError): Doctor(name="  ", person_id=1)
        with self.assertRaises(ValueError): Doctor(name="X", person_id=0)
        with self.assertRaises(ValueError): Doctor(name="X", person_id=-3)

    def test_fees_for_p5(self):
        self.assertEqual(Doctor(name="a", person_id=1).fee(), 40)
        self.assertEqual(Nurse(name="a", person_id=1).fee(), 12)
        self.assertEqual(Pharmacist(name="a", person_id=1).fee(), 5)

    def test_diamond(self):
        before = Person.instances_created
        m = MedicalLecturer(name="M", person_id=5, module_name="Anat")
        self.assertEqual(Person.instances_created - before, 1)
        self.assertEqual(m.role(), "Doctor and Lecturer")
        self.assertEqual(m.fee(), 40)
        self.assertEqual(m.module_name, "Anat")

    def test_double_booking_and_unique_ids(self):
        _, _, c = make()
        c.book(101, 1, 20)
        with self.assertRaises(ClinicError): c.book(102, 1, 20)      # staff clash
        with self.assertRaises(ClinicError): c.book(101, 2, 20)      # patient clash
        with self.assertRaises(ClinicError): c.add_patient(Patient(name="Dup", person_id=1))

    def test_cancelled_slot_is_free_again(self):
        _, _, c = make()
        a = c.book(101, 1, 20)
        c.cancel(a.id)
        c.book(102, 1, 20)

    def test_two_hour_rule_boundary(self):
        clock, _, c = make(10)
        a = c.book(101, 1, 20); c.confirm(a.id)
        clock.set(19)
        with self.assertRaises(ClinicError): c.cancel(a.id)           # 1 h notice
        b = c.book(102, 2, 40); c.confirm(b.id)
        clock.set(38)
        c.cancel(b.id)                                                 # exactly 2 h: allowed

    def test_started_and_terminal(self):
        clock, _, c = make(10)
        a = c.book(101, 1, 20)
        clock.set(20)
        with self.assertRaises(ClinicError): c.cancel(a.id)
        with self.assertRaises(ClinicError): c.confirm(a.id)
        clock2, _, c2 = make(10)
        b = c2.book(101, 1, 30); c2.cancel(b.id)
        with self.assertRaises(ClinicError): c2.confirm(b.id)
        with self.assertRaises(ClinicError): c2.cancel(b.id)
        self.assertIs(b.status, Status.CANCELLED)

    def test_emergency_bump(self):
        _, _, c = make()
        first = c.book(101, 1, 20)
        c.flag_emergency(102)
        c.book(102, 1, 20)
        self.assertIs(first.status, Status.CANCELLED)
        self.assertEqual(first.cancel_reason, "bumped")

    def test_emergency_cannot_bump_confirmed_and_is_atomic(self):
        _, _, c = make()
        first = c.book(101, 1, 20); c.confirm(first.id)
        c.flag_emergency(102)
        with self.assertRaises(ClinicError): c.book(102, 1, 20)
        self.assertIs(first.status, Status.CONFIRMED)
        self.assertEqual(len(c.appointments()), 1)

    def test_non_emergency_cannot_bump(self):
        _, _, c = make()
        first = c.book(101, 1, 20)
        with self.assertRaises(ClinicError): c.book(102, 1, 20)
        self.assertIs(first.status, Status.PENDING)

    def test_failures_logged(self):
        clock, log, c = make(10)
        a = c.book(101, 1, 20); c.confirm(a.id)
        clock.set(19)
        with self.assertRaises(ClinicError): c.cancel(a.id)
        self.assertIn("[log] FAILED cancel #1: too late", log.lines())

    def test_log_closed_once_even_on_error(self):
        log = AppointmentLog(echo=lambda s: None)
        with self.assertRaises(RuntimeError):
            with Clinic(ManualClock(0), log):
                raise RuntimeError("boom")
        self.assertEqual((log.opened_count, log.closed_count), (1, 1))
        log.close()
        self.assertEqual(log.closed_count, 1)

    def test_log_failure_does_not_break_clinic(self):
        log = AppointmentLog("/no_such_dir/x.log", echo=lambda s: None)
        with Clinic(ManualClock(0), log) as c:
            c.add_staff(Doctor(name="D", person_id=1))
        self.assertTrue(any("WARNING" in l for l in log.lines()))
        self.assertEqual(log.closed_count, 1)

    def test_views_are_copies(self):
        _, _, c = make()
        self.assertIsInstance(c.appointments(), tuple)
        self.assertIsInstance(c.staff_members(), tuple)

    def test_no_type_checks_in_source(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        for f in list((root / "clinic").glob("*.py")) + [root / "main.py", root / "dashboard.py"]:
            text = f.read_text()
            self.assertNotIn("isinstance", text, f.name)
            self.assertNotIn("issubclass", text, f.name)
            self.assertNotIn("import time", text, f.name)
            self.assertNotIn("datetime", text, f.name)

    def test_schedule_and_hour_format(self):
        from clinic.clock import format_hour
        self.assertEqual(format_hour(20), "Day 1 20:00")
        self.assertEqual(format_hour(30), "Day 2 06:00")
        _, _, c = make()
        a = c.book(101, 1, 30)
        c.book(102, 2, 20)
        c.cancel(a.id)
        lines = c.schedule()
        self.assertEqual(len(lines), 1)
        self.assertIn("Day 1 20:00", lines[0])

    def test_appointment_needs_people(self):
        from clinic.appointment import Appointment
        with self.assertRaises(ValueError): Appointment(1, None, None, 5)
        with self.assertRaises(ValueError): Appointment(1, object(), object(), 168)


if __name__ == "__main__":
    unittest.main()
