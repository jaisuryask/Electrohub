"""Request logging + a small per-IP rate limiter for the AI endpoints."""
import logging
import time
from collections import defaultdict, deque

from django.http import JsonResponse

log = logging.getLogger("electrolab.request")

STARTED = time.time()
stats = {"total": 0, "2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "recent": deque(maxlen=20)}

RATE_LIMIT = 20       # requests ...
RATE_WINDOW = 60      # ... per this many seconds, per client IP, on /api/ai/
_hits = defaultdict(deque)


def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "-")) or "-"


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        ip = client_ip(request)
        limited = request.path.startswith("/api/ai/") and request.method == "POST" and self._limited(ip)
        if limited:
            response = JsonResponse({"error": "Too many requests - please wait a minute.", "code": "429"}, status=429)
            response["Retry-After"] = str(RATE_WINDOW)
        else:
            response = self.get_response(request)
        ms = (time.perf_counter() - start) * 1000
        # Only method, path and status are logged - never bodies, queries or cookies.
        log.info("%s %s -> %s %.0fms ip=%s", request.method, request.path, response.status_code, ms, ip)
        stats["total"] += 1
        stats[f"{response.status_code // 100}xx"] = stats.get(f"{response.status_code // 100}xx", 0) + 1
        stats["recent"].appendleft(
            {"t": time.strftime("%H:%M:%S"), "m": request.method, "p": request.path[:60], "s": response.status_code, "ms": round(ms)})
        return response

    @staticmethod
    def _limited(ip):
        now = time.time()
        q = _hits[ip]
        while q and q[0] < now - RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return True
        q.append(now)
        return False
