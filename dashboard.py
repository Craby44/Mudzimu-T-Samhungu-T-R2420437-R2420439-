"""Optional local dashboard for the clinic.   Run:  python dashboard.py

The dashboard contains NO clinic rules. It only turns button clicks into calls on Clinic
(book / confirm / cancel / flag_emergency) and draws what Clinic and the log report back.
Standard library only. Serves on 127.0.0.1 (this computer) and stops with Ctrl+C,
which also closes the log through the Clinic's with-statement."""
import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from clinic.clinic import Clinic
from clinic.clock import ManualClock, format_hour
from clinic.errors import ClinicError
from clinic.log import AppointmentLog
from clinic.people import Doctor, Nurse, Pharmacist, MedicalLecturer, Patient

LOG_DIR = Path(__file__).resolve().parent / "logs"


def seed(clinic):
    """Starter staff and patients (same people as the console demo)."""
    for member in (Doctor(name="Dr Moyo", person_id=1),
                   Nurse(name="Nurse Ncube", person_id=2),
                   Pharmacist(name="Dube", person_id=3),
                   MedicalLecturer(name="Prof Sibanda", person_id=4, module_name="Anatomy")):
        clinic.add_staff(member)
    for name, pid in (("Alice", 101), ("Bob", 102), ("Carol", 103), ("Dan", 104)):
        clinic.add_patient(Patient(name=name, person_id=pid))


def snapshot(clinic, clock, log):
    """Everything the page needs, built only from Clinic's read-only views."""
    return {
        "now": clock.now(),
        "now_label": format_hour(clock.now()),
        "staff": [{"id": s.id, "name": s.name, "role": s.role(), "fee": s.fee()}
                  for s in clinic.staff_members()],
        "patients": [{"id": p.id, "name": p.name, "emergency": p.is_emergency}
                     for p in clinic.patients()],
        "appointments": [{"id": a.id, "patient": a.patient.name, "staff": a.staff.name,
                          "role": a.staff.role(), "fee": a.staff.fee(), "start": a.start,
                          "when": format_hour(a.start), "status": a.status.name,
                          "reason": a.cancel_reason} for a in clinic.appointments()],
        "schedule": list(clinic.schedule()),
        "log": list(log.lines())[-300:],
        "log_opened": log.opened_count,
        "log_closed": log.closed_count,
    }


def _number(data, key):
    try:
        return int(data[key])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"'{key}' must be a whole number") from None


def run_action(clinic, clock, data):
    """Translate one click into one Clinic call. Returns (ok, message)."""
    try:
        kind = data.get("action")
        if kind == "book":
            a = clinic.book(_number(data, "patient_id"), _number(data, "staff_id"),
                            _number(data, "start"))
            return True, f"Booked {a.describe()}"
        if kind == "confirm":
            clinic.confirm(_number(data, "id"))
            return True, f"Confirmed #{data['id']}"
        if kind == "cancel":
            clinic.cancel(_number(data, "id"), str(data.get("reason", "")))
            return True, f"Cancelled #{data['id']}"
        if kind == "emergency":
            clinic.flag_emergency(_number(data, "patient_id"), bool(data.get("flag", True)))
            return True, "Emergency flag updated"
        if kind == "advance":
            clock.advance(_number(data, "hours"))
            return True, f"Clock is now {format_hour(clock.now())}"
        return False, "Unknown action"
    except ClinicError as exc:
        return False, f"Refused: {exc}"          # already written to the log by Clinic
    except (ValueError, AttributeError) as exc:
        return False, f"Invalid input: {exc}"
    except Exception as exc:                       # keep the dashboard alive, show the problem
        return False, f"Unexpected error: {exc}"


def make_handler(clinic, clock, log):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass                                   # keep the terminal for the [log] lines

        def _send(self, code, body, content_type):
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, code, payload):
            self._send(code, json.dumps(payload), "application/json; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(200, snapshot(clinic, clock, log))
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/action":
                self._json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                self._json(400, {"error": "bad request"})
                return
            ok, message = run_action(clinic, clock, data)
            self._json(200, {"ok": ok, "message": message,
                             "state": snapshot(clinic, clock, log)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Clinic dashboard")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    clock = ManualClock(10)
    log = AppointmentLog(str(LOG_DIR / "dashboard.log"))
    with Clinic(clock, log) as clinic:
        seed(clinic)
        try:
            server = HTTPServer(("127.0.0.1", args.port), make_handler(clinic, clock, log))
        except OSError as exc:
            print(f"Cannot start on port {args.port}: {exc}. Try: python dashboard.py --port 8001")
            return
        url = f"http://127.0.0.1:{args.port}"
        print(f"Dashboard running at {url}  (press Ctrl+C to stop)")
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            server.server_close()


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clinic dashboard</title>
<style>
:root{
  --bg:#f5f6f8; --panel:#ffffff; --text:#1c2430; --muted:#5d6978; --line:#dfe3e8;
  --accent:#0f6f8f; --accent-text:#ffffff;
  --pending-bg:#fff1cc; --pending-tx:#7a5600;
  --ok-bg:#d9f2e3; --ok-tx:#14663a;
  --off-bg:#e6e8eb; --off-tx:#4a5360;
  --bad:#b3261e; --warn:#9a5b00; --logbg:#10161d; --logtx:#d6dde6;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#12171d; --panel:#1b222b; --text:#e6eaef; --muted:#9aa6b4; --line:#2c3541;
    --accent:#4cb4d6; --accent-text:#08202a;
    --pending-bg:#4a3a0a; --pending-tx:#ffd978;
    --ok-bg:#12402a; --ok-tx:#8fe0b2;
    --off-bg:#2d343d; --off-tx:#b4bdc8;
    --bad:#ff8a80; --warn:#ffc266; --logbg:#0a0e13; --logtx:#cfd8e3;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,Segoe UI,Roboto,sans-serif}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;
  padding:14px 20px;background:var(--panel);border-bottom:1px solid var(--line)}
h1{font-size:18px;margin:0}
.sub{color:var(--muted);font-size:13px}
.clock{font-weight:600;font-size:17px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;padding:16px 20px;max-width:1300px;margin:auto}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;min-width:0}
section h2{font-size:14px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.wide{grid-column:1/-1}
label{display:block;font-size:12px;color:var(--muted);margin:8px 0 3px}
select,input{width:100%;padding:8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--text);font:inherit}
button{font:inherit;cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--text);
  border-radius:6px;padding:6px 10px}
button:hover{border-color:var(--accent)}
button.primary{background:var(--accent);color:var(--accent-text);border-color:var(--accent);font-weight:600;margin-top:12px;width:100%}
.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
table{width:100%;border-collapse:collapse;font-size:14px}
.scroll{overflow-x:auto}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:12px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}
.PENDING{background:var(--pending-bg);color:var(--pending-tx)}
.CONFIRMED{background:var(--ok-bg);color:var(--ok-tx)}
.CANCELLED{background:var(--off-bg);color:var(--off-tx)}
.chip{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--line)}
.on{background:var(--bad);color:#fff;border-color:var(--bad)}
.toast{margin:0 20px;padding:10px 14px;border-radius:8px;display:none;font-weight:500}
.toast.good{display:block;background:var(--ok-bg);color:var(--ok-tx)}
.toast.bad{display:block;background:var(--pending-bg);color:var(--bad)}
pre.log{margin:0;background:var(--logbg);color:var(--logtx);padding:12px;border-radius:8px;height:280px;overflow:auto;
  font:12.5px/1.5 ui-monospace,Consolas,monospace;white-space:pre-wrap}
.l-bad{color:#ff8a80}.l-warn{color:#ffc266}
.empty{color:var(--muted);font-style:italic}
</style>
</head>
<body>
<header>
  <div>
    <h1>Clinic Appointment System</h1>
    <div class="sub">Group 5 &middot; P = 5 &middot; Emergency twist &middot; the page only calls Clinic, it has no rules of its own</div>
  </div>
  <div class="row">
    <span class="clock" id="clock">...</span>
    <button data-advance="1">+1 h</button><button data-advance="2">+2 h</button>
    <button data-advance="6">+6 h</button><button data-advance="24">+1 day</button>
  </div>
</header>
<div id="toast" class="toast"></div>
<main>
  <section>
    <h2>Book an appointment</h2>
    <label for="bPatient">Patient</label><select id="bPatient"></select>
    <label for="bStaff">Staff member</label><select id="bStaff"></select>
    <label for="bStart">Start hour (0&ndash;167, must be in the future)</label>
    <input id="bStart" type="number" min="0" max="167" value="13">
    <button class="primary" id="bookBtn">Book</button>
  </section>

  <section>
    <h2>Patients &middot; emergency flag</h2>
    <div id="patients"></div>
    <div class="sub" style="margin-top:8px">An emergency patient may bump a PENDING appointment at the same hour, never a CONFIRMED one.</div>
  </section>

  <section class="wide">
    <h2>Appointments</h2>
    <div class="scroll"><table>
      <thead><tr><th>#</th><th>When</th><th>Patient</th><th>Staff</th><th>Fee</th><th>Status</th><th>Reason</th><th>Actions</th></tr></thead>
      <tbody id="appts"></tbody>
    </table></div>
  </section>

  <section>
    <h2>Week schedule (active only)</h2>
    <pre class="log" id="schedule" style="height:200px"></pre>
  </section>

  <section>
    <h2>Appointment log &middot; <span id="logState"></span></h2>
    <pre class="log" id="log"></pre>
  </section>
</main>
<script>
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let optionsKey = "", startSet = false;

async function call(path, body){
  const res = await fetch(path, body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : {});
  return res.json();
}
function toast(ok, msg){
  const t = $("toast"); t.textContent = msg; t.className = "toast " + (ok ? "good" : "bad");
}
async function act(body){
  const r = await call("/api/action", body);
  toast(r.ok, r.message);
  render(r.state);
}
function render(s){
  $("clock").textContent = s.now_label + " (hour " + s.now + ")";
  const key = JSON.stringify([s.staff.map(x => x.id), s.patients.map(x => x.id)]);
  if (key !== optionsKey){
    $("bPatient").innerHTML = s.patients.map(p => `<option value="${p.id}">${esc(p.name)} (#${p.id})</option>`).join("");
    $("bStaff").innerHTML = s.staff.map(m => `<option value="${m.id}">${esc(m.role)} - ${esc(m.name)} (fee ${m.fee})</option>`).join("");
    optionsKey = key;
  }
  if (!startSet){ $("bStart").value = Math.min(167, s.now + 3); startSet = true; }

  $("patients").innerHTML = s.patients.map(p =>
    `<div class="chip"><span>${esc(p.name)} <span class="sub">#${p.id}</span></span>
     <button class="${p.emergency ? "on" : ""}" data-em="${p.id}" data-flag="${p.emergency ? 0 : 1}">
     Emergency: ${p.emergency ? "ON" : "off"}</button></div>`).join("");

  $("appts").innerHTML = s.appointments.length ? s.appointments.map(a => {
    const buttons =
      (a.status === "PENDING" ? `<button data-confirm="${a.id}">Confirm</button> ` : "") +
      (a.status !== "CANCELLED" ? `<button data-cancel="${a.id}">Cancel</button>` : "");
    return `<tr><td>${a.id}</td><td>${esc(a.when)}</td><td>${esc(a.patient)}</td>
      <td>${esc(a.role)} ${esc(a.staff)}</td><td>${a.fee}</td>
      <td><span class="badge ${a.status}">${a.status}</span></td><td>${esc(a.reason)}</td><td>${buttons}</td></tr>`;
  }).join("") : `<tr><td colspan="8" class="empty">No appointments yet. Book one on the left.</td></tr>`;

  $("schedule").textContent = s.schedule.length ? s.schedule.join("\n") : "Nothing scheduled.";
  const logEl = $("log"), atEnd = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 30;
  logEl.innerHTML = s.log.map(l => {
    const cls = l.includes("FAILED") ? "l-bad" : (l.includes("BUMPED") || l.includes("WARNING")) ? "l-warn" : "";
    return `<div class="${cls}">${esc(l)}</div>`;
  }).join("");
  if (atEnd) logEl.scrollTop = logEl.scrollHeight;
  $("logState").textContent = "opened " + s.log_opened + "x, closed " + s.log_closed + "x";
}

document.addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.id === "bookBtn") act({action:"book", patient_id:$("bPatient").value, staff_id:$("bStaff").value, start:$("bStart").value});
  else if (b.dataset.advance) act({action:"advance", hours:b.dataset.advance});
  else if (b.dataset.confirm) act({action:"confirm", id:b.dataset.confirm});
  else if (b.dataset.cancel) act({action:"cancel", id:b.dataset.cancel, reason:"cancelled from dashboard"});
  else if (b.dataset.em) act({action:"emergency", patient_id:b.dataset.em, flag:b.dataset.flag === "1"});
});
call("/api/state").then(render);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
