"""
Local Riot OAuth callback helper.

Riot redirects the browser to:
http://localhost/redirect#access_token=...

The URL fragment (#...) is only accessible inside the browser,
so this server serves a small page that forwards the full URL
to the FastAPI backend.

The backend creates the application session, then this helper
redirects the user back to the React frontend.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.request

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>VALSHOP Login</title>
</head>
<body>
  <p id="status">Finishing Riot login...</p>

  <script>
    const fullUrl = window.location.href;

    fetch("/complete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: fullUrl })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === "success") {
        document.getElementById("status").textContent = "Login successful!";

        window.location.href =
          "http://localhost:5173/?session_token=" +
          encodeURIComponent(data.session_token);
      } else {
        document.body.innerHTML =
          "<h2>Login failed</h2><p>" + data.error + "</p>";
      }
    })
    .catch(error => {
      document.body.innerHTML =
        "<h2>Login failed</h2><p>" + error + "</p>";
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/redirect"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/complete":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        request = urllib.request.Request(
            "http://127.0.0.1:8000/api/auth/token",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request) as response:
                result = response.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result)

        except Exception as error:
            result = json.dumps({
                "status": "error",
                "error": str(error)
            }).encode()

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result)


server = HTTPServer(("127.0.0.1", 80), Handler)

print("Callback server running on http://localhost:80")
server.serve_forever()
