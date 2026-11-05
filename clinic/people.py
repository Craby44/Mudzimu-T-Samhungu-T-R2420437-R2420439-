from abc import ABC, abstractmethod
from . import config
from .validation import clean_text, positive_id


class Person(ABC):
    """Invariants: name is non-empty text; id is a positive whole number; both never change.
    instances_created counts how many times this constructor body completed."""
    instances_created = 0

    def __init__(self, *, name, person_id, **kwargs):
        super().__init__(**kwargs)               # cooperative: continues the MRO chain
        self._name = clean_text(name, "name")
        self._id = positive_id(person_id)
        Person.instances_created += 1

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @abstractmethod
    def role(self):
        """Short label such as 'Doctor'."""


class Patient(Person):
    def __init__(self, *, name, person_id, **kwargs):
        super().__init__(name=name, person_id=person_id, **kwargs)
        self._emergency = False

    def role(self):
        return "Patient"

    @property
    def is_emergency(self):
        return self._emergency

    def flag_emergency(self, flag=True):
        self._emergency = bool(flag)


class Staff(Person):
    @abstractmethod
    def fee(self):
        """Fee for one appointment."""


class Doctor(Staff):
    def role(self):
        return "Doctor"

    def fee(self):
        return 40 + 5 * (config.P % 5)


class Nurse(Staff):
    def role(self):
        return "Nurse"

    def fee(self):
        return 10 + (config.P % 3)


class Pharmacist(Staff):
    def role(self):
        return "Pharmacist"

    def fee(self):
        return 5


class Lecturer(Person):
    def __init__(self, *, module_name, **kwargs):
        super().__init__(**kwargs)
        self._module_name = clean_text(module_name, "module name")

    @property
    def module_name(self):
        return self._module_name

    def role(self):
        return "Lecturer"


class MedicalLecturer(Doctor, Lecturer):
    """Diamond: MRO = MedicalLecturer, Doctor, Staff, Lecturer, Person.
    No __init__ of its own is needed: every class passes the keyword arguments up
    with super(), so Person.__init__ runs exactly once."""

    def role(self):
        return "Doctor and Lecturer"

    def fee(self):
        # Explicit choice: the fee is for the clinical service, so the Doctor fee applies.
        # Teaching is not billed to patients. Stated here so it is not left to MRO luck.
        return Doctor.fee(self)
