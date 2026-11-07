"""server-status: a tiny dashboard with the state of the host it runs on.

Standard library only. Inside a container /proc already reports host-wide
load, uptime, memory and kernel; hostname, OS and disk usage of the host come
from read-only bind mounts of /etc/hostname and /etc/os-release (statvfs on a
bind-mounted file reports the host filesystem that contains it).
"""

import json
import os
import platform
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8000"))
TITLE = os.environ.get("STATUS_TITLE", "server status")
HOST_HOSTNAME = os.environ.get("HOST_HOSTNAME_FILE", "/host/hostname")
HOST_OS_RELEASE = os.environ.get("HOST_OS_RELEASE_FILE", "/host/os-release")
STARTED = time.time()


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def os_name():
    for line in (read(HOST_OS_RELEASE) or read("/etc/os-release")).splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return platform.system()


def cpu_times():
    fields = [int(x) for x in read("/proc/stat").splitlines()[0].split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    return idle, sum(fields)


def cpu_percent(interval=0.2):
    i1, t1 = cpu_times()
    time.sleep(interval)
    i2, t2 = cpu_times()
    dt = t2 - t1
    return round(100.0 * (1 - (i2 - i1) / dt), 1) if dt else 0.0


def meminfo():
    info = {}
    for line in read("/proc/meminfo").splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts:
            info[key] = int(parts[0]) * 1024
    total, avail = info.get("MemTotal", 0), info.get("MemAvailable", 0)
    stotal, sfree = info.get("SwapTotal", 0), info.get("SwapFree", 0)
    return {"total": total, "used": total - avail, "available": avail,
            "swap_total": stotal, "swap_used": stotal - sfree}


def disk():
    path = HOST_HOSTNAME if os.path.exists(HOST_HOSTNAME) else "/"
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return {"total": total, "used": total - free, "free": free, "host": path != "/"}


def status():
    load = read("/proc/loadavg").split()
    return {
        "hostname": read(HOST_HOSTNAME).strip() or socket.gethostname(),
        "os": os_name(),
        "kernel": read("/proc/sys/kernel/osrelease").strip() or platform.release(),
        "arch": platform.machine(),
        "cpus": os.cpu_count(),
        "cpu_percent": cpu_percent(),
        "load": [float(x) for x in load[:3]] if load else [],
        "uptime_seconds": int(float(read("/proc/uptime", "0").split()[0])),
        "memory": meminfo(),
        "disk": disk(),
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "app_uptime_seconds": int(time.time() - STARTED),
    }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --fg:#1d2330; --muted:#6b7280; --bar:#e5e7eb; --ok:#16a34a; --warn:#d97706; --bad:#dc2626; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0f1115; --card:#181b22; --fg:#e6e8ee; --muted:#9aa1ad; --bar:#2a2f3a; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 system-ui, sans-serif; }
  main { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: var(--muted); margin-bottom: 20px; }
  .grid { display:grid; gap:12px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .card { background:var(--card); border-radius:10px; padding:14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
  .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
  .value { font-size:22px; font-weight:600; margin:2px 0 8px; font-variant-numeric: tabular-nums; }
  .bar { height:8px; background:var(--bar); border-radius:4px; overflow:hidden; }
  .bar > div { height:100%; width:0; background:var(--ok); transition: width .4s; }
  .small { color:var(--muted); font-size:13px; margin-top:6px; font-variant-numeric: tabular-nums; }
  footer { color:var(--muted); font-size:12px; margin-top:16px; }
</style>
</head>
<body>
<main>
  <h1 id="host">__TITLE__</h1>
  <div class="sub" id="sys">loading…</div>
  <div class="grid">
    <div class="card"><div class="label">CPU</div><div class="value" id="cpu">–</div>
      <div class="bar"><div id="cpu-bar"></div></div><div class="small" id="load"></div></div>
    <div class="card"><div class="label">Memory</div><div class="value" id="mem">–</div>
      <div class="bar"><div id="mem-bar"></div></div><div class="small" id="mem-d"></div></div>
    <div class="card"><div class="label">Disk</div><div class="value" id="disk">–</div>
      <div class="bar"><div id="disk-bar"></div></div><div class="small" id="disk-d"></div></div>
    <div class="card"><div class="label">Uptime</div><div class="value" id="up">–</div>
      <div class="small" id="time"></div></div>
  </div>
  <footer>refreshes every 5s · <a href="api/status">JSON</a></footer>
</main>
<script>
const $ = id => document.getElementById(id);
const gb = b => (b / 1073741824).toFixed(1) + " GiB";
const dur = s => { const d = Math.floor(s/86400), h = Math.floor(s%86400/3600), m = Math.floor(s%3600/60);
  return (d ? d + "d " : "") + h + "h " + m + "m"; };
function bar(id, pct) { const el = $(id); el.style.width = pct + "%";
  el.style.background = pct > 90 ? "var(--bad)" : pct > 70 ? "var(--warn)" : "var(--ok)"; }
async function refresh() {
  try {
    const s = await (await fetch("api/status", {cache: "no-store"})).json();
    $("host").textContent = s.hostname;
    $("sys").textContent = s.os + " · kernel " + s.kernel + " · " + s.arch + " · " + s.cpus + " CPU";
    $("cpu").textContent = s.cpu_percent + "%"; bar("cpu-bar", s.cpu_percent);
    $("load").textContent = "load " + s.load.map(x => x.toFixed(2)).join(" / ");
    const mp = Math.round(100 * s.memory.used / s.memory.total);
    $("mem").textContent = mp + "%"; bar("mem-bar", mp);
    $("mem-d").textContent = gb(s.memory.used) + " of " + gb(s.memory.total) +
      (s.memory.swap_total ? " · swap " + gb(s.memory.swap_used) : "");
    const dp = Math.round(100 * s.disk.used / s.disk.total);
    $("disk").textContent = dp + "%"; bar("disk-bar", dp);
    $("disk-d").textContent = gb(s.disk.used) + " of " + gb(s.disk.total) + (s.disk.host ? "" : " (container)");
    $("up").textContent = dur(s.uptime_seconds);
    $("time").textContent = s.time;
  } catch (e) { $("sys").textContent = "cannot load status: " + e; }
}
refresh(); setInterval(refresh, 5000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self.send(200, "ok\n", "text/plain")
        elif path == "/api/status":
            self.send(200, json.dumps(status()), "application/json")
        elif path == "/":
            self.send(200, PAGE.replace("__TITLE__", TITLE), "text/html; charset=utf-8")
        else:
            self.send(404, "not found\n", "text/plain")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print("server-status listening on :%d" % PORT, flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
