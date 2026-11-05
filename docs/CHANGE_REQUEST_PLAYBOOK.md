# Live change-request playbook (practise these)

Always: make the change, add one test in `tests/test_clinic.py`, run the tests, run `python main.py`.

| Possible request | Where to edit | Notes |
|---|---|---|
| Change the 2-hour notice to N hours | `MIN_CANCEL_NOTICE_HOURS` in `clinic/appointment.py` | one constant; update the test boundary |
| New Staff type (e.g. Receptionist, fee 3) | new class in `clinic/people.py` with `role()` and `fee()` | Clinic and the loop stay untouched (like `LabTechnician`) |
| Staff-specific buffer between appointments | add `buffer_hours()` to `Staff` (default 0), override in subclasses; in `Clinic.book` compare `abs(a.start - start) <= buffer` using `a.staff.buffer_hours()` | ask the staff object, no type checks |
| Limit appointments per patient per week | check count of active appointments in `Clinic.book`, raise `ClinicError("limit reached")` | failure is logged automatically by `_action` |
| Reschedule an appointment | new `Clinic.reschedule(id, new_start)`: cancel + book inside one `_action`, validate first | do all checks before cancelling |
| List appointments for a patient / day | add a tuple-returning query in `Clinic`, like `appointments_for_staff` | return copies, never internal lists |
| Discount by patient type | add `discount_percent()` to Patient subclasses; `price = staff.fee() * (100 - patient.discount_percent()) // 100` | polymorphism, no type tests |
| Another status (e.g. COMPLETED) | add to `Status` and `_LEGAL` in `appointment.py` | `CANCELLED` stays terminal |
