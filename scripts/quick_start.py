"""Quick-start helper: boot the server and confirm it responds.

This script starts the API server in a subprocess, waits for it to become
available, then performs a simple HTTP GET against `/` to confirm the UI loads.

If successful, it prints a success message and shuts the server down.

Usage:
    python scripts/quick_start.py

"""

import subprocess
import sys
import time

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def wait_for_server(url: str, timeout: int = 15, interval: float = 0.5) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def main():
    if requests is None:
        raise RuntimeError("The 'requests' package is required. Install with: pip install requests")

    server_url = "http://127.0.0.1:9091/"

    print("Starting Bible API server (this runs in a subprocess)...")

    proc = subprocess.Popen(
        [sys.executable, "-m", "bible_api.api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        print(f"Waiting for server to become available at {server_url}...")
        if not wait_for_server(server_url, timeout=20):
            raise RuntimeError("Server did not respond in time")

        print("Server is up! Verifying UI load...")
        r = requests.get(server_url, timeout=5)
        r.raise_for_status()

        print("✅ Server responded successfully!")
        print(f"Response length: {len(r.text)} bytes")

    except Exception as e:
        print(f"❌ Quick start failed: {e}")
        raise

    finally:
        print("Shutting down server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
