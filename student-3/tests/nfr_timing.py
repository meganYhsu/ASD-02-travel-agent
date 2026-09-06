import time

import requests

URL = "http://127.0.0.1:5003/dashboard/1"
RUNS = 20
LIMIT = 3.0

times = []
for i in range(RUNS):
    start = time.time()
    try:
        requests.get(URL, timeout=10)
    except requests.RequestException as exc:
        print("request failed:", exc)
        raise SystemExit(1)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"run {i + 1:2d}: {elapsed:.3f} s")

passed = 0
for t in times:
    if t <= LIMIT:
        passed += 1

print()
print(f"max {max(times):.3f} s | min {min(times):.3f} s | "
      f"average {sum(times) / len(times):.3f} s")
print(f"{passed}/{RUNS} requests completed within {LIMIT:.1f} s")
