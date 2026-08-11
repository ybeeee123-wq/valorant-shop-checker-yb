import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


CALLBACK_HTML = b"""<!doctype html><meta charset='utf-8'><title>VALSHOP</title>
<style>body{font-family:Segoe UI,sans-serif;background:#111;color:#eee;display:grid;place-items:center;height:100vh;margin:0}div{text-align:center}b{color:#ff6572}</style>
<div><h1>VAL<b>SHOP</b></h1><p id='s'>Finishing Riot connection...</p></div>
<script>fetch('/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:location.href})}).then(r=>r.json()).then(()=>{document.getElementById('s').textContent='Connected. You can close this tab.'}).catch(()=>{document.getElementById('s').textContent='VALSHOP could not finish the connection.'})</script>"""


class CallbackError(RuntimeError):
    pass


class LocalCallback:
    def __init__(self, port: int = 80) -> None:
        self.port = port
        self.urls: queue.Queue[str] = queue.Queue(maxsize=1)
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                return

            def do_GET(self) -> None:
                if self.path.startswith("/redirect"):
                    self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(CALLBACK_HTML)
                else:
                    self.send_error(404)

            def do_POST(self) -> None:
                if self.path != "/complete": self.send_error(404); return
                try:
                    size = min(int(self.headers.get("Content-Length", "0")), 20000)
                    url = json.loads(self.rfile.read(size))["url"]
                    owner.urls.put_nowait(url)
                    body = b'{"status":"ok"}'
                    self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
                except Exception:
                    self.send_error(400)

        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
            self.port = self.server.server_port
        except OSError as exc:
            raise CallbackError("VALSHOP could not start the Riot login callback because port 80 is already in use.") from exc
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="riot-callback")
        self.thread.start()

    def wait(self, timeout: float = 240) -> str:
        try:
            return self.urls.get(timeout=timeout)
        except queue.Empty as exc:
            raise CallbackError("Riot sign-in timed out. Please try connecting again.") from exc
        finally:
            self.stop()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown(); self.server.server_close(); self.server = None
