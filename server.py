# -*- coding: utf-8 -*-
"""
FF14 中文维基（灰机wiki）MCP 启动器

背景：ff14.huijiwiki.com 由 Cloudflare 保护，Node/axios 等普通客户端的 TLS 指纹
会被拦截（403 人机验证），因此这里在本机起一个明文代理，用 curl_cffi 模拟
Chrome 指纹把请求转发过去。启动器随后拉起
@professional-wiki/mediawiki-mcp-server，stdio 原样透传给 MCP 客户端。

仅监听 127.0.0.1，只读（config.json 中 readOnly: true）。
"""

import os
import sys
import time
import threading
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:
    from curl_cffi import requests as creq
except ImportError:
    sys.stderr.write("缺少依赖 curl_cffi，请先执行: python -m pip install curl_cffi\n")
    raise

TARGET = os.environ.get("FF14_WIKI_TARGET", "https://ff14.huijiwiki.com")
PORT = int(os.environ.get("FF14_PROXY_PORT", "8787"))
LOG_PATH = os.path.join(os.environ.get("TEMP", "/tmp"), "ff14-wiki-mcp-proxy.log")
CONFIG_PATH = os.environ.get(
    "FF14_WIKI_CONFIG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
)
MAX_RETRIES = 5
CACHE_TTL = 5 * 60

session = creq.Session(impersonate="chrome")
session_lock = threading.Lock()
cache = {}
cache_lock = threading.Lock()


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        self._handle("GET")

    def do_HEAD(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _handle(self, method):
        raw = self.path
        if raw.startswith("http://") or raw.startswith("https://"):
            u = urlparse(raw)
            path_q = u.path + ("?" + u.query if u.query else "")
        else:
            path_q = raw
        url = TARGET + path_q

        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""

        key = (method, url)
        now = time.time()
        if method == "GET":
            with cache_lock:
                hit = cache.get(key)
                if hit and now - hit[0] < CACHE_TTL:
                    _, status, ctype, data = hit
                    self._respond(status, ctype, data)
                    return

        status, ctype, data = 502, "text/plain", b"proxy error"
        for attempt in range(MAX_RETRIES + 1):
            try:
                with session_lock:
                    if method == "POST":
                        r = session.post(url, data=body, timeout=60)
                    else:
                        r = session.get(url, timeout=60)
                status = r.status_code
                ctype = r.headers.get("content-type", "application/json")
                data = r.content
            except Exception as e:
                status, ctype, data = 502, "text/plain", ("proxy error: %s" % e).encode()
            if status == 200 and b"challenge-platform" not in data[:2000]:
                break
            log("blocked (%s), retry %s" % (status, attempt + 1))
            time.sleep(0.6 * (attempt + 1))

        if method == "GET" and status == 200:
            with cache_lock:
                if len(cache) > 300:
                    cache.clear()
                cache[key] = (time.time(), status, ctype, data)

        log("%s %s -> %s (%dB)" % (method, path_q, status, len(data)))
        self._respond(status, ctype, data)

    def _respond(self, status, ctype, data):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass


def start_mcp():
    env = dict(os.environ)
    env.update({
        "CONFIG": CONFIG_PATH,
        "MCP_TRUSTED_HOSTS": "127.0.0.1:%d" % PORT,
        "MCP_LOG_LEVEL": "warning",
        "MCP_CONTENT_MAX_BYTES": "75000",
    })
    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [npx, "-y", "@professional-wiki/mediawiki-mcp-server@latest"]
    log("starting mcp: %s" % " ".join(cmd))
    proc = subprocess.Popen(cmd, env=env)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    log("mcp exited: %s" % proc.returncode)


def main():
    if os.environ.get("FF14_PROXY_ONLY") == "1":
        log("proxy-only mode on 127.0.0.1:%d -> %s" % (PORT, TARGET))
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
        return
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        log("proxy port %d unavailable (%s), assuming another instance is running" % (PORT, e))
        httpd = None
    if httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        log("proxy listening on 127.0.0.1:%d -> %s" % (PORT, TARGET))
    start_mcp()


if __name__ == "__main__":
    main()
