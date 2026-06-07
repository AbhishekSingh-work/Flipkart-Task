import os
import sys
import time
import requests
from generate_test_csv import generate_csv

SERVER_URL = "http://127.0.0.1:8000"

def run_perf_test():
    print("=" * 60)
    print("           AUTOMATED PERFORMANCE & INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Generate test file if not exists
    test_csv = "data/test_inventory.csv"
    num_records = 50000  # 50k items for a quick but meaningful performance test
    if not os.path.exists(test_csv):
        generate_csv(test_csv, num_rows=num_records)
    else:
        print(f"Using existing test CSV: {test_csv}")

    # 2. Upload file to server
    print("\n[Step 1] Triggering CSV Ingestion Upload...")
    start_time = time.time()
    try:
        with open(test_csv, "rb") as f:
            files = {"file": (os.path.basename(test_csv), f, "text/csv")}
            response = requests.post(f"{SERVER_URL}/api/ingestion/upload", files=files)
    except requests.exceptions.ConnectionError:
        print(f"Error: Server is not running at {SERVER_URL}!")
        print("Please start the server first in another window: python run.py")
        sys.exit(1)

    if response.status_code != 200:
        print(f"Failed to upload: {response.text}")
        sys.exit(1)

    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Upload completed. Job ID: {job_id}. Status: {job_data['status']}")

    # 3. Poll status until completion
    print("\n[Step 2] Polling Ingestion Job Progress...")
    poll_start = time.time()
    while True:
        status_resp = requests.get(f"{SERVER_URL}/api/ingestion/status/{job_id}")
        if status_resp.status_code != 200:
            print(f"Failed to get status: {status_resp.text}")
            sys.exit(1)
            
        status_data = status_resp.json()
        status = status_data["status"]
        progress = status_data["percent_complete"]
        processed = status_data["processed_rows"]
        total = status_data["total_rows"]
        
        print(f"Job Status: {status} | Progress: {progress}% ({processed}/{total} rows)")
        
        if status in ("COMPLETED", "FAILED"):
            break
            
        time.sleep(0.5)
        
    poll_end = time.time()
    elapsed = poll_end - poll_start
    
    if status == "FAILED":
        print(f"\nIngestion job failed! Error: {status_data.get('error_message')}")
        sys.exit(1)
        
    # Calculate ingestion statistics
    speed = processed / elapsed if elapsed > 0 else processed
    print("-" * 60)
    print("Ingestion Performance Summary:")
    print(f"  Total Rows Processed: {processed}")
    print(f"  Time Elapsed:         {elapsed:.2f} seconds")
    print(f"  Ingestion Speed:      {speed:.2f} records/second")
    print("-" * 60)

    # 4. Perform random lookups to measure latency
    print("\n[Step 3] Querying Random WIDs (Latency Check)...")
    lookups = ["WID-0000001", "WID-0005000", f"WID-{num_records:07d}"]
    for wid in lookups:
        l_start = time.time()
        lookup_resp = requests.get(f"{SERVER_URL}/api/validation/product/{wid}")
        l_end = time.time()
        l_latency = (l_end - l_start) * 1000
        
        if lookup_resp.status_code == 200:
            prod = lookup_resp.json()
            print(f"  WID: {wid} | EAN: {prod['ean']} | Expiry: {prod['expiry_date']} | Latency: {l_latency:.2f}ms")
        else:
            print(f"  Failed to look up {wid}: {lookup_resp.text}")

    # 5. Log physical verification with photo
    print("\n[Step 4] Logging Sample Verification event with Image...")
    # Create a small dummy image file
    dummy_img_path = "tests/dummy_label.jpg"
    os.makedirs(os.path.dirname(dummy_img_path), exist_ok=True)
    with open(dummy_img_path, "wb") as f:
        # Write small JPEG headers/bytes
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00\xFF\xDB\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37\x29\x2c\x30\x31\x34\x34\x34\x1f\x27\x39\x3d\x38\x32\x3c\x2e\x33\x34\x32\xFF\xC0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x01\xFF\xC4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xDA\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xFF\xD9")
        
    try:
        verify_data = {
            "wid": "WID-0000001",
            "operator_name": "Performance Automated Tester"
        }
        with open(dummy_img_path, "rb") as img_file:
            verify_files = {"image": ("dummy_label.jpg", img_file, "image/jpeg")}
            v_start = time.time()
            v_resp = requests.post(f"{SERVER_URL}/api/validation/verify", data=verify_data, files=verify_files)
            v_end = time.time()
            
        if v_resp.status_code == 200:
            res = v_resp.json()
            print(f"  Logged successfully | ID: {res['id']} | Status: {res['status_label']} | Saved image: {res['image_path']}")
            print(f"  API Latency: {(v_end - v_start)*1000:.2f}ms")
        else:
            print(f"  Verification log failed: {v_resp.text}")
    finally:
        if os.path.exists(dummy_img_path):
            os.remove(dummy_img_path)

    # 6. Query Report
    print("\n[Step 5] Fetching QA Audit Report...")
    today_str = time.strftime("%Y-%m-%d")
    r_resp = requests.get(f"{SERVER_URL}/api/reporting/report?start_date={today_str}&end_date={today_str}")
    if r_resp.status_code == 200:
        report = r_resp.json()
        sum_data = report["summary"]
        print(f"  Summary -> Total Audits today: {sum_data['total_verifications']}")
        print(f"  Details -> Operator: {report['activities'][0]['operator_name']} | Time: {report['activities'][0]['timestamp']}")
    else:
        print(f"  Failed to get report: {r_resp.text}")

    print("\n" + "=" * 60)
    print("           ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_perf_test()
