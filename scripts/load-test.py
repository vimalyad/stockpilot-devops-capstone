"""Bounded concurrent read-only traffic for metrics and HPA demonstrations."""
import argparse
import concurrent.futures
import time
import urllib.request
parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://localhost:3000/api/dashboard')
parser.add_argument('--requests', type=int, default=500)
parser.add_argument('--workers', type=int, default=8)
args = parser.parse_args()
if not 1 <= args.requests <= 100000 or not 1 <= args.workers <= 64:
    parser.error('requests must be 1..100000 and workers 1..64')
def request(_):
    started = time.monotonic()
    try:
        with urllib.request.urlopen(args.url, timeout=10) as response:
            response.read()
            return response.status, time.monotonic() - started
    except Exception:
        return 0, time.monotonic() - started
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    results = list(pool.map(request, range(args.requests)))
latencies = sorted(duration for _, duration in results)
failed = sum(status != 200 for status, _ in results)
print(f'requests={len(results)} failed={failed} p95_seconds={latencies[min(len(latencies)-1,int(len(latencies)*0.95))]:.3f}')
raise SystemExit(bool(failed))
