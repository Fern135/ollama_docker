#!/usr/bin/env python3
"""
    entrypoint.py
        Starts Ollama, pulls the deepseek-r1 model once, prints the LAN URL,
        then waits in the foreground (docker friendly).
"""
import os
import socket
import subprocess
import time
import sys
import signal
import urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1")
PORT  = os.getenv("OLLAMA_PORT", "11434")


def get_lan_ip() -> str:
    """Return best-guess LAN IP for friendly logging."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def wait_for_server(url: str, timeout: int = 1) -> None:
    """Block until Ollama responds (use /api/version for 200)."""
    while True:
        try:
            with urllib.request.urlopen(url, timeout=timeout):
                return
        except Exception:
            time.sleep(1)


def model_already_cached(model: str) -> bool:
    """Return True if model already exists in the Ollama store."""
    res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    return any(line.startswith(model) for line in res.stdout.splitlines())


def main() -> None:
    # 1) Launch Ollama in the background
    server = subprocess.Popen(["ollama", "serve"])

    try:
        # 2) Wait for API to be ready
        wait_for_server(f"http://localhost:{PORT}/api/version")

        # 3) Pull model on first run
        if not model_already_cached(MODEL):
            print(f"► First-time setup: downloading {MODEL} …", flush=True)
            subprocess.check_call(["ollama", "pull", MODEL])
            print("✓ Model ready.", flush=True)

        # 4) Show friendly LAN URL
        print(f"Ollama API is ready →  http://{get_lan_ip()}:{PORT}/api/generate", flush=True)

        # 5) Keep container alive
        server.wait()

    except KeyboardInterrupt:
        server.send_signal(signal.SIGINT)
        server.wait()
    finally:
        sys.exit(server.returncode or 0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"")
