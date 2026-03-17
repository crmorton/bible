"""Benchmark utilities for exercising the API.

This module is designed to be run as a script via:

    python -m bible_api.benchmark

"""

import csv
import time
import statistics
from urllib.parse import quote

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:  # pragma: no cover
    requests = None


def load_references(filename):
    refs = []
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip():
                refs.append(row[0].strip())
    return refs


def fetch_passage(api_base_url, osis_ref, translation, session):
    encoded_ref = quote(f"osis:{osis_ref}")
    url = f"{api_base_url}?ref={encoded_ref}&translation={translation}"

    start_time = time.time()
    success = False
    error_msg = None

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        if "html" not in data:
            raise ValueError("Response JSON missing 'html' key")

        success = True
    except Exception as e:
        error_msg = str(e)

    duration = time.time() - start_time
    return {"ref": osis_ref, "duration": duration, "success": success, "error": error_msg}


def run_benchmark(
    references,
    api_base_url,
    translation,
    concurrent_requests,
):
    if requests is None:
        raise RuntimeError("requests is required to run the benchmark. Install it via pip.")

    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=concurrent_requests, pool_maxsize=concurrent_requests)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    results = []
    start_total = time.time()

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = {executor.submit(fetch_passage, api_base_url, ref, translation, session): ref for ref in references}
        for count, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if count % 200 == 0 or count == len(references):
                print(f"Progress: {count}/{len(references)} requests completed...")

    total_duration = time.time() - start_total
    return results, total_duration


def print_report(results, total_duration):
    successful = [r["duration"] for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("\n" + "=" * 40)
    print("         BENCHMARK RESULTS")
    print("=" * 40)
    print(f"Total Requests:      {len(results)}")
    print(f"Successful:          {len(successful)}")
    print(f"Failed:              {len(failed)}")
    print(f"Total Elapsed Time:  {total_duration:.2f} seconds")
    if total_duration > 0:
        print(f"Throughput:          {len(results) / total_duration:.2f} req/sec")

    if successful:
        print("\n--- Response Time Metrics (Successes) ---")
        print(f"Average Latency:     {statistics.mean(successful):.4f} seconds")
        print(f"Median Latency:      {statistics.median(successful):.4f} seconds")
        print(f"Min Latency:         {min(successful):.4f} seconds")
        print(f"Max Latency:         {max(successful):.4f} seconds")

    if failed:
        print("\n--- Error Summary ---")
        for f in failed[:5]:
            print(f"Ref: {f['ref']:<20} Error: {f['error']}")
        if len(failed) > 5:
            print(f"... and {len(failed) - 5} more errors.")
    print("=" * 40)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark the Bible API.")
    parser.add_argument("--csv", default="./test/bible_passages_sample2.csv", help="CSV file of OSIS refs")
    parser.add_argument("--url", default="http://localhost:9091/passage", help="API base URL")
    parser.add_argument("--translation", default="LEB", help="Translation acronym")
    parser.add_argument("--concurrency", type=int, default=25, help="Number of concurrent requests")
    parser.add_argument("--iterations", type=int, default=1, help="Repeat list this many times")

    args = parser.parse_args()

    refs = load_references(args.csv)
    refs *= args.iterations

    results, total_duration = run_benchmark(refs, args.url, args.translation, args.concurrency)
    print_report(results, total_duration)


if __name__ == "__main__":
    main()
