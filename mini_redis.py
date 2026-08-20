"""
Mini-Redis: A from-scratch Redis-compatible server.

Speaks real RESP (REdis Serialization Protocol) over raw TCP sockets,
so you can test it with the actual `redis-cli` tool.

Supported commands: PING, SET (with optional EX seconds), GET, DEL, EXISTS, EXPIRE
"""

import socket
import threading
import time

# ---------------------------------------------------------------------------
# THE DATA STORE
# ---------------------------------------------------------------------------
# This is the "wall of cubbyholes." Just two plain dicts:
#   store   -> key: value
#   expiry  -> key: unix timestamp after which the key should be treated as gone
# A lock is needed because multiple client threads can touch these at once.
store = {}
expiry = {}
lock = threading.Lock()


def is_expired(key: str) -> bool:
    """True if this key has an expiry set and that time has passed."""
    return key in expiry and time.time() > expiry[key]


# ---------------------------------------------------------------------------
# RESP PROTOCOL: READING INCOMING COMMANDS
# ---------------------------------------------------------------------------
# redis-cli sends commands as a RESP "array of bulk strings", e.g. for `SET foo bar`:
#   *3\r\n          <- 3 arguments follow
#   $3\r\n          <- next argument is 3 bytes long
#   SET\r\n
#   $3\r\n
#   foo\r\n
#   $3\r\n
#   bar\r\n
#
# We read this format line by line and rebuild it into a plain Python list:
# ["SET", "foo", "bar"]
def parse_command(rfile):
    line = rfile.readline()
    if not line:
        return None  # client disconnected

    line = line.strip()
    if not line.startswith(b"*"):
        return None  # not a RESP array; ignore malformed input

    num_args = int(line[1:])
    args = []
    for _ in range(num_args):
        length_line = rfile.readline().strip()   # e.g. b"$3"
        length = int(length_line[1:])
        data = rfile.read(length)                 # the actual argument bytes
        rfile.readline()                          # consume the trailing \r\n
        args.append(data.decode())
    return args


# ---------------------------------------------------------------------------
# RESP PROTOCOL: WRITING RESPONSES
# ---------------------------------------------------------------------------
# RESP has a few reply "types," each starting with a different symbol.
# These helper functions build correctly-formatted replies.
def simple_string(s: str) -> bytes:
    """+OK\\r\\n style reply, used for short status messages."""
    return f"+{s}\r\n".encode()


def error(s: str) -> bytes:
    """-ERR message\\r\\n style reply, used when a command fails."""
    return f"-{s}\r\n".encode()


def integer(n: int) -> bytes:
    """:123\\r\\n style reply, used for counts."""
    return f":{n}\r\n".encode()


def bulk_string(s):
    """
    $<length>\\r\\n<data>\\r\\n style reply, used for actual values.
    None becomes $-1\\r\\n, RESP's way of saying "nil" (key not found).
    """
    if s is None:
        return b"$-1\r\n"
    b = s.encode()
    return f"${len(b)}\r\n".encode() + b + b"\r\n"


# ---------------------------------------------------------------------------
# COMMAND HANDLERS
# ---------------------------------------------------------------------------
# Each handler takes the arguments AFTER the command name
# e.g. for "SET foo bar", args = ["foo", "bar"]

def cmd_ping(args):
    if args:
        return bulk_string(args[0])  # PING <message> echoes the message back
    return simple_string("PONG")


def cmd_set(args):
    if len(args) < 2:
        return error("ERR wrong number of arguments for 'set' command")

    key, value = args[0], args[1]
    with lock:
        store[key] = value
        expiry.pop(key, None)  # a fresh SET always clears any old expiry

        # Optional: SET key value EX <seconds>
        if len(args) >= 4 and args[2].upper() == "EX":
            try:
                seconds = int(args[3])
                expiry[key] = time.time() + seconds
            except ValueError:
                return error("ERR value is not an integer or out of range")

    return simple_string("OK")


def cmd_get(args):
    if len(args) != 1:
        return error("ERR wrong number of arguments for 'get' command")

    key = args[0]
    with lock:
        if key not in store or is_expired(key):
            store.pop(key, None)
            expiry.pop(key, None)
            return bulk_string(None)
        return bulk_string(store[key])


def cmd_del(args):
    count = 0
    with lock:
        for key in args:
            if key in store:
                del store[key]
                expiry.pop(key, None)
                count += 1
    return integer(count)


def cmd_exists(args):
    count = 0
    with lock:
        for key in args:
            if key in store and not is_expired(key):
                count += 1
    return integer(count)


def cmd_expire(args):
    if len(args) != 2:
        return error("ERR wrong number of arguments for 'expire' command")

    key, seconds = args[0], args[1]
    with lock:
        if key in store and not is_expired(key):
            expiry[key] = time.time() + int(seconds)
            return integer(1)  # 1 = expiry was set
        return integer(0)      # 0 = key doesn't exist


# Command name -> handler function. This is the "dispatch table" —
# it's how we go from "the client typed GET" to "run cmd_get."
COMMANDS = {
    "PING": cmd_ping,
    "SET": cmd_set,
    "GET": cmd_get,
    "DEL": cmd_del,
    "EXISTS": cmd_exists,
    "EXPIRE": cmd_expire,
}


# ---------------------------------------------------------------------------
# HANDLING ONE CLIENT CONNECTION
# ---------------------------------------------------------------------------
def handle_client(conn, addr):
    print(f"Connected: {addr}")
    rfile = conn.makefile("rb")  # buffered reader over the raw socket
    try:
        while True:
            args = parse_command(rfile)
            if not args:
                break  # client disconnected or sent something we can't parse

            cmd_name = args[0].upper()
            handler = COMMANDS.get(cmd_name)

            if handler:
                response = handler(args[1:])
            else:
                response = error(f"ERR unknown command '{cmd_name}'")

            conn.sendall(response)
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"Disconnected: {addr}")


# ---------------------------------------------------------------------------
# THE MAIN SERVER LOOP
# ---------------------------------------------------------------------------
def main():
    server_socket = socket.create_server(("0.0.0.0", 6379), reuse_port=True)
    print("Mini-Redis listening on port 6379...")

    while True:
        conn, addr = server_socket.accept()
        # One thread per connection = multiple clients can talk to us
        # at the same time without blocking each other.
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()


if __name__ == "__main__":
    main()
