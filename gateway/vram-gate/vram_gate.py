"""
VRAM Gate — HTTP health check for GPU memory pressure.
Returns 200 if GPU VRAM < 90%, 503 if overloaded.
Deploy to Host A LXC 101, port 11435.

Usage:
    python3 vram_gate.py

Systemd unit: /etc/systemd/system/vram-gate.service
"""

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

THRESHOLD = 0.90  # 90% VRAM usage triggers 503
PORT = 11435


class VRAMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                self._respond(500, {"error": "nvidia-smi failed", "stderr": result.stderr.strip()})
                return

            used, total = [int(x.strip()) for x in result.stdout.strip().split(",")]
            ratio = used / total
            status = "ok" if ratio < THRESHOLD else "overloaded"
            code = 200 if ratio < THRESHOLD else 503

            self._respond(code, {
                "vram_used_mb": used,
                "vram_total_mb": total,
                "vram_pct": round(ratio, 3),
                "threshold": THRESHOLD,
                "status": status,
            })
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        pass  # Silence request logs


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), VRAMHandler)
    print(f"VRAM gate listening on :{PORT} (threshold: {THRESHOLD:.0%})")
    server.serve_forever()
