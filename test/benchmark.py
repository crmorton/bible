import csv
import time
import requests
from requests.adapters import HTTPAdapter
import statistics
from urllib.parse import quote
import concurrent.futures

# --- Configuration ---
API_BASE_URL = "http://localhost:9091/passage"
CSV_FILE = "./test/bible_passages_sample.csv"  # has  1,648 rows
CSV_FILE = "./test/bible_passages_sample2.csv" # has 20,089 rows
TRANSLATION = "LEB"

# Set to 1 for sequential testing, or higher (e.g., 5-20) to stress-test concurrency
CONCURRENT_REQUESTS = 25 # This is the sweet-spot with 5 Uvicorn workers
ITERATIONS = 1  # Will multiply the XX,XXX rows by 6

# --- Setup Connection Pooling ---
# This tells Python to keep connections open and reuse them
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=CONCURRENT_REQUESTS, 
    pool_maxsize=CONCURRENT_REQUESTS
)
session.mount('http://', adapter)
session.mount('https://', adapter)

def load_references(filename):
    """Reads OSIS references from the CSV file."""
    refs = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                # Skip empty rows
                if row and row[0].strip():
                    refs.append(row[0].strip())
    except FileNotFoundError:
        print(f"Error: Could not find '{filename}'. Please ensure the file exists.")
        exit(1)
    return refs

def fetch_passage(osis_ref):
    """Makes a single API request and records the time taken."""
    # Properly encode 'osis:Ref' to 'osis%3ARef'
    encoded_ref = quote(f"osis:{osis_ref}")
    url = f"{API_BASE_URL}?ref={encoded_ref}&translation={TRANSLATION}"
    
    start_time = time.time()
    success = False
    error_msg = None

    try:
        # Use the global session instead of requests.get
        # response = requests.get(url, timeout=30)
        response = session.get(url, timeout=30)
        response.raise_for_status() # Raise exception for 4xx/5xx status codes
        
        # Parse JSON and verify the structure matches expectations
        data = response.json()
        if "html" not in data:
            raise ValueError("Response JSON missing 'html' key")
            
        success = True
    except requests.exceptions.RequestException as e:
        error_msg = f"HTTP Error: {e}"
    except ValueError as e:
        error_msg = f"Data Error: {e}"
    except Exception as e:
        error_msg = f"Unexpected Error: {e}"

    duration = time.time() - start_time
    
    return {
        "ref": osis_ref,
        "duration": duration,
        "success": success,
        "error": error_msg
    }

def run_benchmark(refs):
    """Runs the benchmark across all references."""
    results = []
    print(f"Starting benchmark for {len(refs)} passages...")
    print(f"Concurrency level: {CONCURRENT_REQUESTS} concurrent requests\n")
    
    start_total = time.time()

    # Use ThreadPoolExecutor to make requests in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        # Submit all tasks
        futures = {executor.submit(fetch_passage, ref): ref for ref in refs}
        
        # Process results as they complete
        for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            # Print progress every 200 requests or on the last request
            if count % 200 == 0 or count == len(refs):
                print(f"Progress: {count}/{len(refs)} requests completed...")

    total_duration = time.time() - start_total
    return results, total_duration

def print_report(results, total_duration):
    """Calculates and prints performance metrics."""
    successful = [r["duration"] for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("\n" + "="*40)
    print("         BENCHMARK RESULTS")
    print("="*40)
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
        for f in failed[:5]:  # Show up to 5 errors to avoid flooding console
            print(f"Ref: {f['ref']:<20} Error: {f['error']}")
        if len(failed) > 5:
            print(f"... and {len(failed) - 5} more errors.")
    print("="*40)

if __name__ == "__main__":
    base_references = load_references(CSV_FILE)
    if not base_references:
        print("No references found in the CSV. Exiting.")
        exit(1)
        
    # Multiply the list to simulate sustained load
    references_to_test = base_references * ITERATIONS
        
    benchmark_results, elapsed_time = run_benchmark(references_to_test)
    print_report(benchmark_results, elapsed_time)
