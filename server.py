"""
เว็บเล็กๆ สำหรับกรอกรหัสแล้วส่งเข้า Discord
- ไม่ต้องติดตั้งอะไรเพิ่ม (ใช้ไลบรารีมาตรฐานของ Python ล้วนๆ)
- รันทดสอบบนเครื่องตัวเอง: python server.py แล้วเปิด http://localhost:8000
- เอาไป deploy ขึ้นเว็บจริงได้เลย (เช่น Render) เพื่อเอาลิงก์ไปส่งให้คนอื่นเปิด
"""

import os
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "ใส่ WEBHOOK URL ตรงนี้")

PORT = int(os.environ.get("PORT", 8000))
HOST = "0.0.0.0"

HTML_PAGE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>ส่งรหัสเข้า Discord</title>
<style>
  body { font-family: sans-serif; max-width: 420px; margin: 60px auto; padding: 0 16px; }
  input { width: 100%; padding: 10px; font-size: 16px; box-sizing: border-box; }
  button { margin-top: 12px; padding: 10px 16px; font-size: 16px; cursor: pointer; }
  #result { margin-top: 16px; font-weight: bold; }
</style>
</head>
<body>
  <h2>ใส่รหัส</h2>
  <input id="code" type="text" placeholder="ใส่รหัสตรงนี้" autofocus>
  <button onclick="sendCode()">ส่งเข้า Discord</button>
  <div id="result"></div>

<script>
async function sendCode() {
  const code = document.getElementById('code').value.trim();
  const result = document.getElementById('result');
  if (!code) {
    result.textContent = 'ยังไม่ได้พิมพ์อะไรเลย';
    result.style.color = 'red';
    return;
  }
  result.textContent = 'กำลังส่ง...';
  result.style.color = 'black';
  try {
    const res = await fetch('/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const data = await res.json();
    result.textContent = data.ok ? '✅ ' + data.message : '❌ ' + data.message;
    result.style.color = data.ok ? 'green' : 'red';
    if (data.ok) {
      document.getElementById('code').value = '';
    }
  } catch (e) {
    result.textContent = '❌ เชื่อมต่อเซิร์ฟเวอร์ไม่ได้';
    result.style.color = 'red';
  }
}

document.getElementById('code').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendCode();
});
</script>
</body>
</html>
"""


def send_to_discord(code):
    payload = {
        "username": "บอทรับรหัส",
        "embeds": [
            {
                "title": "มีรหัสใหม่เข้ามา",
                "description": f"รหัส: `{code}`",
                "color": 5814783,
            }
        ],
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (webhook-script)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status in (200, 204):
                return True, "ส่งสำเร็จ"
            return False, f"ผิดพลาด (status {res.status})"
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            detail = "(อ่านรายละเอียดไม่ได้)"
        print(f"[DISCORD ERROR] HTTP {e.code} | headers: {dict(e.headers)} | body: {detail}")
        if e.code == 404:
            return False, "ไม่พบ Webhook (URL ผิด หรือถูกลบไปแล้ว)"
        if e.code == 429:
            return False, "ส่งเร็วเกินไป รอแป๊บนึงแล้วลองใหม่"
        return False, f"ผิดพลาด (HTTP {e.code})"
    except urllib.error.URLError as e:
        return False, f"เชื่อมต่อไม่ได้ ลองเช็กอินเทอร์เน็ต ({e.reason})"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาด: {e}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/send":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw)
            code = str(payload.get("code", "")).strip()
        except Exception:
            code = ""

        if not code:
            ok, msg = False, "ไม่พบรหัสที่ส่งมา"
        else:
            ok, msg = send_to_discord(code)

        body = json.dumps({"ok": ok, "message": msg}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if not WEBHOOK_URL.startswith(
        ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")
    ):
        print("ยังไม่ได้ใส่ Webhook URL ที่ถูกต้อง")
        print("เปิดไฟล์นี้ แล้วแก้บรรทัด WEBHOOK_URL ก่อนนะ")
        return

    server = HTTPServer((HOST, PORT), Handler)
    print(f"เซิร์ฟเวอร์กำลังทำงานที่พอร์ต {PORT}")
    print(f"ทดสอบบนเครื่องตัวเอง: http://localhost:{PORT}")
    print("กด Ctrl+C เพื่อปิดเซิร์ฟเวอร์")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nปิดเซิร์ฟเวอร์แล้ว")


if __name__ == "__main__":
    main()
