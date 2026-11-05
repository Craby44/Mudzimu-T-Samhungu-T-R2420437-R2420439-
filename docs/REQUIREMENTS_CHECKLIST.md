# Requirements checklist (brief -> where it is answered)

| Brief item | Where | Evidence |
|---|---|---|
| Use Java/Python/C++, pairs | Python 3 | README header lists both student numbers |
| Time = whole hours 0..168, 1-hour appointments | `clinic/clock.py`, `appointment.py` | start must be 0..167; `ManualClock` limits 0..168 |
| Never read the computer clock; use a Clock object `now()` | `clock.py`, `Clinic(clock, log)` | test `test_no_type_checks_in_source` also rejects `import time` / `datetime` |
| **1** Person (abstract: name, id, abstract role()), Patient, Staff (abstract fee()), Doctor, Nurse, Pharmacist, Appointment, Clinic + class diagram | `people.py`, `appointment.py`, `clinic.py`; README section 1 | Mermaid class diagram |
| **2** Hidden fields, no leaked lists | properties, tuple copies | `test_views_are_copies` |
| **2** Status transitions + legal table | `appointment.py` `_LEGAL` | README section 2 |
| **2** Cancelled never returns; confirmed not cancellable < 2 h; none after start | `Appointment.cancel/confirm` | `test_two_hour_rule_boundary`, `test_started_and_terminal` |
| **2** Constructors reject empty names / non-positive ids | `validation.py`, `Person.__init__` | `test_constructors`, demo Part 2 |
| **2** Invariants as comments above Appointment and Clinic | `appointment.py`, `clinic.py` | comment blocks above the classes |
| **3** Fees: doctor 40+5(P%5), nurse 10+(P%3), pharmacist 5; one loop, role + fee | `people.py`, `main.py` | demo Part 3: 40 / 12 / 5 |
| **3** No isinstance / type tags; new Staff subclass without edits | `LabTechnician` in `main.py` | test scans source for `isinstance`/`issubclass` |
| **4** Log opened/closed exactly once even on error | `Clinic.__enter__/__exit__`, `AppointmentLog` | `test_log_closed_once_even_on_error`; demo shows `[log] opened` / `[log] closed` |
| **4** Failed actions logged, e.g. `FAILED cancel #3: too late` | `Clinic._action` | printed in the demo |
| **4** Name the mechanism | README section 4 | context manager (`with`) |
| **5** Lecturer, MedicalLecturer, one Person, role "Doctor and Lecturer" | `people.py` | demo Part 5, `test_diamond` |
| **5** Counter shows Person ran once | `Person.instances_created` | demo prints "ran 1 time(s)" |
| **5** MedicalLecturer.fee() and why | `people.py`, README section 5 | returns Doctor fee 40 |
| **5** Java: Lecturer becomes an interface | README section 5 | explained |
| **6** No double booking (staff and patient), unique ids, clean + logged failure | `Clinic.book`, `_register` | tests + demo |
| **6** Twist P mod 4 (5 % 4 = 1 -> **Emergency**) | `Clinic.book`, `flag_emergency` | `test_emergency_*`, demo |
| **7** D1-D6 | README section 7 | written out |
| **8** 5-minute demo from main with one deliberate failure | `main.py` | `docs/demo_output.txt` |
| **8** Unseen change request live in 10 minutes | `docs/CHANGE_REQUEST_PLAYBOOK.md` | where to edit for likely changes |

Extra (not required by the brief): `dashboard.py`, a browser view that only calls `Clinic`; covered by `tests/test_dashboard.py`.
