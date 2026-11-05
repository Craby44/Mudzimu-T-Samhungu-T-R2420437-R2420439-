"""Project constant. P is our group number (group 5).
Fees depend on it: doctor 40 + 5*(P % 5), nurse 10 + (P % 3), pharmacist 5.
P % 4 == 1  ->  the EMERGENCY twist (implemented in clinic.py)."""
P = 5
