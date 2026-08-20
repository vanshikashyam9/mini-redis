# Mini-Redis

A Redis-compatible server built from scratch in Python, over raw TCP sockets — no external Redis libraries used. Speaks real RESP (REdis Serialization Protocol), so it works with the actual `redis-cli` tool.

## Why I built this

Most backend work today is gluing frameworks together. This project goes one layer deeper: implementing the client-server protocol, command parsing, and concurrent connection handling that tools like Redis are built on.

## Supported commands

| Command | Example | What it does |
|---|---|---|
| `PING` | `PING` | Health check, replies `PONG` |
| `SET` | `SET name Vanshika` | Store a value under a key |
| `SET ... EX` | `SET name Vanshika EX 60` | Store with a 60-second expiry |
| `GET` | `GET name` | Retrieve a value by key |
| `DEL` | `DEL name` | Delete a key |
| `EXISTS` | `EXISTS name` | Check if a key exists (and isn't expired) |
| `EXPIRE` | `EXPIRE name 30` | Set a 30-second expiry on an existing key |

## Architecture

```
Client (redis-cli)
      │  raw TCP
      ▼
Socket layer      -> accepts connections, one thread per client
      │
RESP parser        -> turns raw bytes into ["SET", "key", "value"]
      │
Command dispatch   -> routes to cmd_set / cmd_get / etc.
      │
In-memory store    -> a lock-protected dict holding the actual data
```

## Running it

Requires Python 3.9+, no external dependencies.

```bash
python3 mini_redis.py
```

In another terminal, using the real `redis-cli`:

```bash
redis-cli -p 6379 set name Vanshika
redis-cli -p 6379 get name
redis-cli -p 6379 set temp value EX 5
redis-cli -p 6379 expire name 30
redis-cli -p 6379 exists name
redis-cli -p 6379 del name
```

## Running the tests

```bash
python3 -m unittest test_mini_redis.py
```

## What I'd add next

- `TTL` command to check remaining time on a key
- Persistence to disk (snapshotting)
- Docker + a live deployment link
