"""Appointment log. Opened exactly once and closed exactly once (see Clinic.__enter__/__exit__).
Failures of the log itself never break the clinic: it degrades to memory-only and warns (design D5)."""

class AppointmentLog:
    def __init__(self, path=None, echo=print, opener=open):
        self._path = path
        self._echo = echo
        self._opener = opener
        self._file = None
        self._lines = []
        self._is_open = False
        self._opened_count = 0
        self._closed_count = 0

    @property
    def is_open(self):
        return self._is_open

    @property
    def opened_count(self):
        return self._opened_count

    @property
    def closed_count(self):
        return self._closed_count

    def lines(self):
        return tuple(self._lines)          # copy: callers cannot touch our list

    def open(self):
        if self._opened_count:
            raise RuntimeError("log can only be opened once")
        self._opened_count = 1
        self._is_open = True
        if self._path is not None:
            try:
                self._file = self._opener(self._path, "a", encoding="utf-8")
            except OSError as exc:
                self._warn(f"cannot open {self._path}: {exc}; logging to memory only")
        self._emit("[log] opened")

    def write(self, text):
        if not self._is_open:
            raise RuntimeError("log is not open")
        self._emit(f"[log] {text}")

    def close(self):
        if not self._is_open:              # idempotent: second call does nothing
            return
        self._is_open = False
        self._closed_count += 1
        try:
            self._emit("[log] closed")
        finally:
            if self._file is not None:
                try:
                    self._file.close()
                except OSError as exc:
                    self._warn(f"close failed: {exc}")
                self._file = None

    def _emit(self, line):
        self._lines.append(line)
        self._echo(line)
        if self._file is not None:
            try:
                self._file.write(line + "\n")
                self._file.flush()
            except (OSError, ValueError) as exc:
                self._file = None
                self._warn(f"write failed: {exc}; continuing in memory only")

    def _warn(self, message):
        line = f"[log] WARNING: {message}"
        self._lines.append(line)
        self._echo(line)
