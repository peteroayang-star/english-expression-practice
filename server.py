#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英语表达练习器 - 本地服务
作用：在 localhost 上托管页面并转发 AI 请求，解决中转站接口不允许浏览器
直连（CORS）导致 "Failed to fetch" 的问题。

注意：中转站启用了 Cloudflare 浏览器特征校验，Python urllib 会被拦截
(403 Error 1010)，因此转发改用 Windows 自带的 curl.exe（实测可通过）。
用法：双击 start.bat，或命令行运行  python server.py
页面地址：http://localhost:8080
"""
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys

PORT = 8080
DEFAULT_UPSTREAM = "https://www.zirocode.com/deepseek/plus"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 浏览器 UA，用于通过 Cloudflare 特征校验
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def find_curl():
    """优先 Windows 自带 curl.exe，其次 PATH 中的 curl"""
    sys32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                         "System32", "curl.exe")
    if os.path.isfile(sys32):
        return sys32
    return shutil.which("curl") or "curl"


CURL = find_curl()


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[server] %s\n" % (fmt % args))

    # ---- 通用响应 ----
    def _send(self, status, ctype, body):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, Authorization, X-Upstream-URL")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    # ---- 跨域预检 ----
    def do_OPTIONS(self):
        self._send(204, "text/plain", b"")

    # ---- 首页 / 模型列表代理 ----
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                    data = f.read()
            except Exception as e:
                self._send(500, "text/plain; charset=utf-8",
                           ("读取 index.html 失败: %s" % e).encode("utf-8"))
                return
            self._send(200, "text/html; charset=utf-8", data)
        elif self.path == "/api/models":
            self._proxy("GET",
                        self.headers.get("X-Upstream-URL") or DEFAULT_UPSTREAM, b"")
        else:
            self._send(404, "text/plain; charset=utf-8", b"404 Not Found")

    # ---- API 转发（用 curl.exe，避免被 Cloudflare 拦截）----
    def do_POST(self):
        if self.path != "/api":
            self._send(404, "text/plain; charset=utf-8", b"404 Not Found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        self._proxy("POST",
                    self.headers.get("X-Upstream-URL") or DEFAULT_UPSTREAM, body)

    def _proxy(self, method, upstream, body):
        if not upstream.startswith("https://"):
            msg = json.dumps({"error": {"message": "非法的上游地址: " + upstream}})
            self._send(400, "application/json", msg.encode("utf-8"))
            return

        cmd = [CURL, "-sS", "-X", method, upstream,
               "-A", BROWSER_UA, "-H", "Accept: application/json"]
        if method == "POST" and body:
            cmd += ["-H", "Content-Type: " +
                    self.headers.get("Content-Type", "application/json")]
        auth = self.headers.get("Authorization")
        if auth:
            cmd += ["-H", "Authorization: " + auth]
        if method == "POST":
            cmd += ["--data-binary", "@-"]
        cmd += ["-w", "HTTPCODE:%{http_code}"]

        try:
            proc = subprocess.run(cmd, input=body if method == "POST" else None,
                                  capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            msg = json.dumps({"error": {"message": "上游响应超时（120 秒）"}})
            self._send(504, "application/json", msg.encode("utf-8"))
            return
        except Exception as e:
            msg = json.dumps({"error": {"message": "本地代理执行失败: %s" % e}})
            self._send(500, "application/json", msg.encode("utf-8"))
            return

        out = proc.stdout.decode("utf-8", "replace")
        marker = "HTTPCODE:"
        if marker in out:
            status = int(out.rsplit(marker, 1)[1][:3])
            out = out.rsplit(marker, 1)[0]
        else:
            status = 502
            out = ("本地代理错误: curl 退出码 %s\n%s"
                   % (proc.returncode, proc.stderr.decode("utf-8", "replace")))
        sys.stderr.write("[server] 转发 %s -> HTTP %s\n" % (upstream, status))
        self._send(status, "application/json", out.encode("utf-8"))


if __name__ == "__main__":
    print("使用转发工具:", CURL)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    print("英语表达练习器已启动，请用浏览器打开: http://localhost:%d" % PORT)
    print("（关闭本窗口即停止服务；按 Ctrl+C 也可停止）")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
