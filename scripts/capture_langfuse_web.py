from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import httpx
from websockets.sync.client import connect


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "submission" / "evidence" / "06-prompt-versions-web.png"


class CdpSession:
    def __init__(self, websocket_url: str) -> None:
        self.websocket = connect(websocket_url, open_timeout=10, proxy=None)
        self.message_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.message_id += 1
        message_id = self.message_id
        self.websocket.send(
            json.dumps({"id": message_id, "method": method, "params": params or {}})
        )
        while True:
            message = json.loads(self.websocket.recv(timeout=20))
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})

    def close(self) -> None:
        self.websocket.close()


def langfuse_page(port: int) -> dict:
    client = httpx.Client(trust_env=False, timeout=5)
    tabs = client.get(f"http://127.0.0.1:{port}/json").json()
    for tab in tabs:
        if tab.get("type") == "page" and tab.get("url", "").startswith(
            "https://cloud.langfuse.com/"
        ):
            return tab
    raise RuntimeError("Không tìm thấy tab Langfuse đã đăng nhập")


def evaluate(session: CdpSession, expression: str):
    result = session.call(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
    )
    return result.get("result", {}).get("value")


def wait_for_page(session: CdpSession, expected_text: str, timeout: float = 35) -> None:
    deadline = time.monotonic() + timeout
    stable_since: float | None = None
    state: dict = {}
    while time.monotonic() < deadline:
        state = evaluate(
            session,
            """({
              ready: document.readyState,
              text: document.body ? document.body.innerText : '',
              busy: document.querySelectorAll('[aria-busy=true]').length
            })""",
        ) or {}
        text = state.get("text", "")
        ready = state.get("ready") == "complete"
        found = not expected_text or expected_text.lower() in text.lower()
        if ready and found and len(text) > 100 and state.get("busy", 0) == 0:
            if stable_since is None:
                stable_since = time.monotonic()
            if time.monotonic() - stable_since >= 1.5:
                return
        else:
            stable_since = None
        time.sleep(0.4)
    summary = {
        "ready": state.get("ready"),
        "text_length": len(state.get("text", "")),
        "busy": state.get("busy"),
    }
    raise RuntimeError(
        f"Trang chưa render nội dung mong đợi: {expected_text!r}; state={summary}"
    )


def capture(
    output: Path,
    url: str | None,
    expected_text: str,
    click_text: str,
    no_wait: bool,
    port: int,
) -> None:
    tab = langfuse_page(port)
    session = CdpSession(tab["webSocketDebuggerUrl"])
    try:
        session.call("Page.enable")
        session.call("Runtime.enable")
        session.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1600, "height": 1000, "deviceScaleFactor": 1, "mobile": False},
        )
        if url:
            session.call("Page.navigate", {"url": url})
        if not no_wait:
            wait_for_page(session, "" if click_text else expected_text)
        if click_text:
            clicked = evaluate(
                session,
                """(() => {
                  const needle = %s.toLowerCase();
                  const nodes = [...document.querySelectorAll('a, button')];
                  const node = nodes.find((item) =>
                    (item.innerText || '').trim().toLowerCase().includes(needle));
                  if (!node) return false;
                  node.click();
                  return true;
                })()""" % json.dumps(click_text),
            )
            if not clicked:
                raise RuntimeError(f"Không tìm thấy liên kết/nút: {click_text!r}")
            time.sleep(2)
            wait_for_page(session, expected_text)
        time.sleep(1)
        if no_wait:
            width, height = 1600, 1000
        else:
            layout = session.call("Page.getLayoutMetrics")
            content = layout["cssContentSize"]
            width = min(max(float(content["width"]), 1600), 2000)
            height = min(max(float(content["height"]), 1000), 6000)
        result = session.call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "fromSurface": True,
                "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
            },
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(base64.b64decode(result["data"]))
    finally:
        session.close()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Chụp trang Langfuse từ Chrome đã đăng nhập")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--url")
    parser.add_argument("--wait-text", default="")
    parser.add_argument("--click-text", default="")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--port", type=int, default=9223)
    args = parser.parse_args()
    try:
        capture(
            args.output.resolve(),
            args.url,
            args.wait_text,
            args.click_text,
            args.no_wait,
            args.port,
        )
    except Exception as exc:
        print(f"LỖI: {type(exc).__name__}: {exc}")
        return 1
    print(f"Đã lưu ảnh Langfuse web: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
