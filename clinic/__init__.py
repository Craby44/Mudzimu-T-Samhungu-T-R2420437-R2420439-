"""Clinic Appointment System (group 5, P = 5, Emergency twist)."""
from .appointment import Appointment, Status
from .clinic import Clinic
from .clock import Clock, ManualClock
from .errors import ClinicError
from .log import AppointmentLog
from .people import (Person, Patient, Staff, Doctor, Nurse, Pharmacist,
                     Lecturer, MedicalLecturer)
