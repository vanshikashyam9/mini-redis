# Start from a small, official Python image instead of a full OS.
# "slim" keeps the final container small and fast to deploy.
FROM python:3.11-slim

# This is the folder inside the container where our code will live.
WORKDIR /app

# Copy our server code and tests into the container's /app folder.
# (We don't have any external dependencies to install, since mini_redis.py
# only uses Python's built-in socket/threading/time libraries.)
COPY mini_redis.py .
COPY test_mini_redis.py .

# Tell Docker (and anyone reading this file) that the container listens on
# port 6379 — the standard Redis port. This line is documentation; it
# doesn't actually open the port by itself (the next step handles that).
EXPOSE 6379

# The command that runs when the container starts.
CMD ["python3", "mini_redis.py"]
