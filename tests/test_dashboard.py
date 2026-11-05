import unittest
from clinic.clinic import Clinic
from clinic.clock import ManualClock
from clinic.log import AppointmentLog
import dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.clock = ManualClock(10)
        self.log = AppointmentLog(echo=lambda s: None)
        self.clinic = Clinic(self.clock, self.log)
        self.clinic.__enter__()
        dashboard.seed(self.clinic)

    def tearDown(self):
        self.clinic.__exit__(None, None, None)

    def act(self, **data):
        return dashboard.run_action(self.clinic, self.clock, data)

    def test_book_confirm_cancel_through_actions(self):
        ok, _ = self.act(action="book", patient_id="101", staff_id="1", start="20")
        self.assertTrue(ok)
        self.assertTrue(self.act(action="confirm", id="1")[0])
        self.clock.set(19)
        ok, msg = self.act(action="cancel", id="1")
        self.assertFalse(ok)
        self.assertIn("too late", msg)
        self.assertIn("[log] FAILED cancel #1: too late", self.log.lines())

    def test_rule_refusals_come_from_the_clinic(self):
        self.act(action="book", patient_id="101", staff_id="1", start="20")
        ok, msg = self.act(action="book", patient_id="102", staff_id="1", start="20")
        self.assertFalse(ok)
        self.assertIn("staff already booked", msg)

    def test_emergency_bump_via_dashboard(self):
        self.act(action="book", patient_id="101", staff_id="1", start="20")
        self.act(action="emergency", patient_id="103", flag=True)
        self.assertTrue(self.act(action="book", patient_id="103", staff_id="1", start="20")[0])
        state = dashboard.snapshot(self.clinic, self.clock, self.log)
        self.assertEqual(state["appointments"][0]["reason"], "bumped")

    def test_bad_input_is_reported_not_crashed(self):
        self.assertFalse(self.act(action="book", patient_id="abc", staff_id="1", start="20")[0])
        self.assertFalse(self.act(action="nonsense")[0])
        self.assertFalse(self.act(action="advance", hours="-3")[0])

    def test_snapshot_shape(self):
        state = dashboard.snapshot(self.clinic, self.clock, self.log)
        self.assertEqual(state["now"], 10)
        self.assertEqual(len(state["staff"]), 4)
        self.assertEqual(len(state["patients"]), 4)
        self.assertEqual(state["log_opened"], 1)


if __name__ == "__main__":
    unittest.main()
