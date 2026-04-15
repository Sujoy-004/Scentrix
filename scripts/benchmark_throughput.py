import time
import requests
import json
import statistics

# Configuration
API_URL = "http://localhost:8000"
TEST_USER_ID = 1  # Assume exists for local testing
SLA_MS = 300

def run_performance_test():
    """Simulate user discovery requests and track latency."""
    print("[BENCHMARK] Scentrix Elite Infrastructure: Benchmarking Discovery SLA...")
    
    latencies = []
    success_count = 0
    failure_count = 0

    for i in range(10):
        start_time = time.time()
        try:
            # Hit the personalized recommendation endpoint
            # We mock the auth by passing user_id in dependency (if test mode)
            # Or use a real token if available. For local bench, we assume /personalized is reachable.
            response = requests.get(f"{API_URL}/recommendations/personalized", headers={"X-User-ID": "1"})
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            latencies.append(latency)
            
            if response.status_code == 200:
                success_count += 1
                color = "\033[92m" if latency < SLA_MS else "\033[93m"
                print(f"Request {i+1}: {color}{latency:.2f}ms\033[0m")
            else:
                failure_count += 1
                print(f"Request {i+1}: \033[91mFAILED (Status {response.status_code})\033[0m")
        except Exception as e:
            failure_count += 1
            print(f"Request {i+1}: \033[91mCRITICAL ERROR: {e}\033[0m")

    if latencies:
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        
        print("\n--- RESULTS ---")
        print(f"Total Requests: {len(latencies)}")
        print(f"Successes: {success_count} | Failures: {failure_count}")
        print(f"Average Latency: {avg_latency:.2f}ms")
        print(f"P95 Latency: {p95_latency:.2f}ms")
        
        if avg_latency <= SLA_MS:
            print("\033[92m[PASS] SLA VERIFIED: Infrastructure is Elite.\033[0m")
        else:
            print("\033[91m[FAIL] SLA BREACHED: Performance optimization required.\033[0m")

if __name__ == "__main__":
    run_performance_test()
