"""
In-process request metrics, exposed in the Prometheus text format.

Deliberately dependency-free: one process, one dict, one lock. That is enough
for a single-container deployment and keeps the image unchanged. Paths are
recorded by their *route template* (`/api/tasks/{task_id}`), never the raw URL,
so the label set stays bounded and no id or query string ever lands in a metric.
"""
import threading
import time
import uuid
import logging
import re
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("koshi.access")

# Upper bounds in seconds; the last bucket is +Inf.
BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

_SAFE_ID = re.compile(r"[A-Za-z0-9-]{1,64}")

_lock = threading.Lock()
_started = time.time()
_requests = defaultdict(int)       # (method, route, status) -> count
_latency_sum = defaultdict(float)  # (method, route) -> seconds
_latency_count = defaultdict(int)
_latency_buckets = defaultdict(lambda: [0] * (len(BUCKETS) + 1))
_ai_tiers = defaultdict(int)       # (feature, tier) -> count


def record_request(method: str, route: str, status: int, seconds: float) -> None:
    with _lock:
        _requests[(method, route, status)] += 1
        _latency_sum[(method, route)] += seconds
        _latency_count[(method, route)] += 1
        buckets = _latency_buckets[(method, route)]
        for i, bound in enumerate(BUCKETS):
            if seconds <= bound:
                buckets[i] += 1
        buckets[-1] += 1


def record_ai_tier(feature: str, tier: str) -> None:
    """Which cascade tier answered — the signal that a silent AI outage shows up in."""
    with _lock:
        _ai_tiers[(feature, tier)] += 1


def reset() -> None:
    with _lock:
        for d in (_requests, _latency_sum, _latency_count, _latency_buckets, _ai_tiers):
            d.clear()


def _route_of(request: Request) -> str:
    route = request.scope.get("route")
    # Unmatched paths collapse into one label rather than one per probe URL.
    return getattr(route, "path", None) or "unmatched"


def render() -> str:
    lines = [
        "# HELP koshi_uptime_seconds Seconds since the API process started.",
        "# TYPE koshi_uptime_seconds gauge",
        f"koshi_uptime_seconds {time.time() - _started:.0f}",
        "# HELP koshi_http_requests_total HTTP requests by route template and status.",
        "# TYPE koshi_http_requests_total counter",
    ]
    with _lock:
        for (m, r, s), n in sorted(_requests.items()):
            lines.append(f'koshi_http_requests_total{{method="{m}",route="{r}",status="{s}"}} {n}')
        lines += [
            "# HELP koshi_http_request_duration_seconds Request latency.",
            "# TYPE koshi_http_request_duration_seconds histogram",
        ]
        for (m, r), buckets in sorted(_latency_buckets.items()):
            labels = f'method="{m}",route="{r}"'
            for bound, n in zip(BUCKETS, buckets):
                lines.append(f'koshi_http_request_duration_seconds_bucket{{{labels},le="{bound}"}} {n}')
            lines.append(f'koshi_http_request_duration_seconds_bucket{{{labels},le="+Inf"}} {buckets[-1]}')
            lines.append(f"koshi_http_request_duration_seconds_sum{{{labels}}} {_latency_sum[(m, r)]:.4f}")
            lines.append(f"koshi_http_request_duration_seconds_count{{{labels}}} {_latency_count[(m, r)]}")
        lines += [
            "# HELP koshi_ai_answers_total AI answers by feature and the cascade tier that produced them.",
            "# TYPE koshi_ai_answers_total counter",
        ]
        for (f, t), n in sorted(_ai_tiers.items()):
            lines.append(f'koshi_ai_answers_total{{feature="{f}",tier="{t}"}} {n}')
    return "\n".join(lines) + "\n"


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Times every request, tags it with an id, and writes one access-log line."""

    async def dispatch(self, request: Request, call_next):
        # A caller-supplied id is kept only if it is short and plain: it is
        # echoed into a header and a log line, so anything else is replaced.
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _SAFE_ID.fullmatch(supplied) else uuid.uuid4().hex[:12]
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = _route_of(request)
            record_request(request.method, route, status, elapsed)
            # The route template, not the URL: no ids, tokens or query strings in logs.
            logger.info("%s %s %s %.1fms rid=%s", request.method, route, status, elapsed * 1000, request_id)
