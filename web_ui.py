"""
Web UI for mini-redis.

Browsers can't open raw TCP sockets directly (security restriction), so this
is a small Flask web server that sits in the middle: it takes button clicks
from the browser, translates them into RESP commands, sends them to your
deployed mini-redis server over TCP, and shows the result back on the page.

Run locally:
    pip install flask --break-system-packages
    python3 web_ui.py
Then open http://localhost:5000 in your browser.
"""

import os
import socket

from flask import Flask, render_template_string, request

app = Flask(__name__)

# Where your deployed mini-redis server lives. Can be overridden with
# environment variables if you redeploy elsewhere later.
REDIS_HOST = os.environ.get("REDIS_HOST", "centerbeam.proxy.rlwy.net")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "58534"))


def encode_command(args):
    """Turn ["SET", "name", "Vanshika"] into the RESP wire format mini-redis expects."""
    out = f"*{len(args)}\r\n"
    for arg in args:
        out += f"${len(arg)}\r\n{arg}\r\n"
    return out.encode()


def parse_reply(data: bytes):
    """Turn a raw RESP reply back into a plain Python value for display."""
    if not data:
        return "(no response — is the server reachable?)"
    if data.startswith(b"+"):
        return data[1:].split(b"\r\n")[0].decode()
    if data.startswith(b"-"):
        return "Error: " + data[1:].split(b"\r\n")[0].decode()
    if data.startswith(b":"):
        return data[1:].split(b"\r\n")[0].decode()
    if data.startswith(b"$"):
        lines = data.split(b"\r\n")
        length = int(lines[0][1:])
        if length == -1:
            return "(nil)"
        return lines[1].decode()
    return data.decode(errors="replace")


def send_command(args):
    """Open a fresh TCP connection to mini-redis, send one command, return the reply."""
    with socket.create_connection((REDIS_HOST, REDIS_PORT), timeout=5) as conn:
        conn.sendall(encode_command(args))
        data = conn.recv(4096)
        return parse_reply(data)


PAGE = """
<!doctype html>
<html>
<head>
  <title>mini-redis</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 520px; margin: 60px auto; }
    h1 { font-size: 20px; }
    h2 { font-size: 14px; color: #555; margin-top: 28px; margin-bottom: 8px; }
    form { margin-bottom: 8px; display: flex; gap: 8px; }
    input { padding: 8px; flex: 1; }
    button { padding: 8px 16px; white-space: nowrap; }
    .result { background: #f4f4f4; padding: 12px; border-radius: 6px; font-family: monospace; margin-top: 20px; }
    .last-cmd { color: #888; font-size: 12px; margin-top: -4px; }
  </style>
</head>
<body>
  <h1>mini-redis — live demo</h1>
  <p>Talking to {{ host }}:{{ port }}</p>

  <h2>PING — check the server is alive</h2>
  <form method="POST" action="/ping">
    <button type="submit">PING</button>
  </form>

  <h2>SET — store a value under a key (optionally with expiry)</h2>
  <form method="POST" action="/set">
    <input name="key" placeholder="key" required>
    <input name="value" placeholder="value" required>
    <input name="ex" placeholder="expiry seconds (optional)" style="flex: 0.7">
    <button type="submit">SET</button>
  </form>

  <h2>GET — retrieve a value by key</h2>
  <form method="POST" action="/get">
    <input name="key" placeholder="key" required>
    <button type="submit">GET</button>
  </form>

  <h2>EXISTS — check if a key exists</h2>
  <form method="POST" action="/exists">
    <input name="key" placeholder="key" required>
    <button type="submit">EXISTS</button>
  </form>

  <h2>EXPIRE — set a countdown on an existing key</h2>
  <form method="POST" action="/expire">
    <input name="key" placeholder="key" required>
    <input name="seconds" placeholder="seconds" required style="flex: 0.5">
    <button type="submit">EXPIRE</button>
  </form>

  <h2>DEL — delete a key</h2>
  <form method="POST" action="/del">
    <input name="key" placeholder="key" required>
    <button type="submit">DEL</button>
  </form>

  {% if result is not none %}
  <p class="last-cmd">Last command: {{ last_cmd }}</p>
  <p><strong>Result:</strong></p>
  <div class="result">{{ result }}</div>
  {% endif %}
</body>
</html>
"""


def render(result=None, last_cmd=None):
    return render_template_string(
        PAGE, host=REDIS_HOST, port=REDIS_PORT, result=result, last_cmd=last_cmd
    )


@app.route("/")
def index():
    return render()


@app.route("/ping", methods=["POST"])
def ping():
    result = send_command(["PING"])
    return render(result=result, last_cmd="PING")


@app.route("/set", methods=["POST"])
def set_key():
    key = request.form["key"]
    value = request.form["value"]
    ex = request.form.get("ex", "").strip()

    args = ["SET", key, value]
    if ex:
        args += ["EX", ex]  # matches the optional EX seconds handling in cmd_set

    result = send_command(args)
    return render(result=result, last_cmd=" ".join(args))


@app.route("/get", methods=["POST"])
def get_key():
    key = request.form["key"]
    result = send_command(["GET", key])
    return render(result=result, last_cmd=f"GET {key}")


@app.route("/exists", methods=["POST"])
def exists_key():
    key = request.form["key"]
    result = send_command(["EXISTS", key])
    return render(result=result, last_cmd=f"EXISTS {key}")


@app.route("/expire", methods=["POST"])
def expire_key():
    key = request.form["key"]
    seconds = request.form["seconds"]
    result = send_command(["EXPIRE", key, seconds])
    return render(result=result, last_cmd=f"EXPIRE {key} {seconds}")


@app.route("/del", methods=["POST"])
def del_key():
    key = request.form["key"]
    result = send_command(["DEL", key])
    return render(result=result, last_cmd=f"DEL {key}")


if __name__ == "__main__":
    app.run(debug=True, port=5000)