from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from websockets.sync.client import connect


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "submission" / "evidence" / "04-dashboard-runtime.png"
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
REQUIRED_TEXT = {
    "Latency percentiles",
    "Request traffic",
    "Error rate and breakdown",
    "Cost over time",
    "Input and output tokens",
    "Quality proxy",
}


class CdpSession:
    def __init__(self, websocket_url: str) -> None:
        self.websocket = connect(websocket_url, open_timeout=10)
        self.message_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.message_id += 1
        message_id = self.message_id
        self.websocket.send(
            json.dumps({"id": message_id, "method": method, "params": params or {}})
        )
        while True:
            message = json.loads(self.websocket.recv(timeout=15))
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})

    def close(self) -> None:
        self.websocket.close()


def wait_for_debugger(port: int, timeout: float = 15) -> str:
    deadline = time.monotonic() + timeout
    endpoint = f"http://127.0.0.1:{port}/json/new?http://127.0.0.1:8501"
    while time.monotonic() < deadline:
        try:
            response = httpx.put(endpoint, timeout=2)
            response.raise_for_status()
            return response.json()["webSocketDebuggerUrl"]
        except (httpx.HTTPError, KeyError):
            time.sleep(0.25)
    raise RuntimeError("Chrome DevTools endpoint did not become ready")


def wait_for_dashboard(session: CdpSession, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = session.call(
            "Runtime.evaluate",
            {
                "expression": (
                    "({text: document.body ? document.body.innerText : '', "
                    "charts: document.querySelectorAll('[data-testid=stVegaLiteChart]').length, "
                    "skeletons: document.querySelectorAll('[data-testid=stSkeleton]').length})"
                ),
                "returnByValue": True,
            },
        )
        state = result.get("result", {}).get("value", {})
        body_text = state.get("text", "")
        if (
            REQUIRED_TEXT.issubset(set(body_text.splitlines()))
            and state.get("charts", 0) >= 6
            and state.get("skeletons", 0) == 0
        ):
            return
        time.sleep(0.5)
    raise RuntimeError("Dashboard did not render all six panels before timeout")


def capture(output: Path, port: int = 9222) -> None:
    if not CHROME_PATH.exists():
        raise FileNotFoundError(f"Chrome not found: {CHROME_PATH}")

    temp_root = REPO_ROOT / "tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="dashboard-chrome-", dir=temp_root, ignore_cleanup_errors=True
    ) as profile:
        process = subprocess.Popen(
            [
                str(CHROME_PATH),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={profile}",
                "--window-size=1920,1500",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        session: CdpSession | None = None
        try:
            session = CdpSession(wait_for_debugger(port))
            session.call("Page.enable")
            session.call("Runtime.enable")
            session.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1920, "height": 1500, "deviceScaleFactor": 1, "mobile": False},
            )
            wait_for_dashboard(session)
            time.sleep(2)
            layout = session.call("Page.getLayoutMetrics")
            content = layout["cssContentSize"]
            result = session.call(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "captureBeyondViewport": True,
                    "fromSurface": True,
                    "clip": {
                        "x": 0,
                        "y": 0,
                        "width": min(float(content["width"]), 1920),
                        "height": float(content["height"]),
                        "scale": 1,
                    },
                },
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(base64.b64decode(result["data"]))
        finally:
            if session is not None:
                session.close()
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Chụp dashboard Streamlit sau khi render đủ 6 panel")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        capture(args.output.resolve())
    except Exception as exc:
        print(f"LỖI: {type(exc).__name__}: {exc}")
        return 1
    print(f"Đã lưu dashboard evidence: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
