import asyncio
import statistics
import time

import httpx


async def test_300ms_sla():
    """Benchmark discovery throughput for 10 concurrent requests at 300ms target."""
    url = "http://localhost:8000/api/v1/recommendations/guest"
    payload = {
        "ratings": [
            {"fragrance_id": "frag_syn_500", "rating": 5.0}  # Seed ID from 24k set
        ]
    }

    print("--- 300ms SLA THROUGHPUT BENCHMARK: 10 CONCURRENT REQUESTS ---")

    async with httpx.AsyncClient() as client:
        durations = []
        tasks = []
        for _ in range(10):
            tasks.append(client.post(url, json=payload, timeout=30.0))

        start = time.perf_counter()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start) * 1000

        for r in responses:
            if isinstance(r, httpx.Response):
                durations.append(r.elapsed.total_seconds() * 1000)
            else:
                print(f"Error: {r}")

        if durations:
            p95 = (
                statistics.quantiles(durations, n=20)[18]
                if len(durations) >= 20
                else max(durations)
            )
            avg = statistics.mean(durations)
            print(f"Total Concurrent Time: {total_time:.2f}ms")
            print(f"Avg Latency: {avg:.2f}ms")
            print(f"P95 Latency: {p95:.2f}ms")

            if p95 <= 300:
                print("SLA STATUS: ACHIEVED 🟢")
            else:
                print("SLA STATUS: BREACHED 🔴")


if __name__ == "__main__":
    # Note: Requires uvicorn running on 8000
    try:
        asyncio.run(test_300ms_sla())
    except Exception as e:
        print(f"Benchmark aborted: {e}")
