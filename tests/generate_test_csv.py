import csv
import random
import os
from datetime import datetime, timedelta

def generate_csv(filename="test_inventory.csv", num_rows=10000):
    print(f"Generating test inventory CSV with {num_rows} records...")
    
    # Header format
    headers = ["WID", "EAN", "Manufacturing_Date", "Expiry_Date"]
    
    # Anchor date: June 7, 2026 (based on system time)
    anchor_date = datetime(2026, 6, 7)
    
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(1, num_rows + 1):
            # Sequential WID for easy lookups
            wid = f"WID-{i:07d}"
            
            # 13-digit random EAN
            ean = "".join([str(random.randint(0, 9)) for _ in range(13)])
            
            # Manufacturing date between 18 months ago and 1 month ago
            mfg_offset = random.randint(30, 540)
            mfg_date = anchor_date - timedelta(days=mfg_offset)
            
            # Expiry date offset (some expired, some expiring soon, some good)
            # Lifespan: between 90 and 730 days
            lifespan = random.randint(90, 730)
            exp_date = mfg_date + timedelta(days=lifespan)
            
            writer.writerow([
                wid,
                ean,
                mfg_date.strftime("%Y-%m-%d"),
                exp_date.strftime("%Y-%m-%d")
            ])
            
            if i % 100000 == 0:
                print(f"Written {i} rows...")
                
    file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"Successfully generated '{filename}' ({file_size_mb:.2f} MB)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate mock inventory CSV files.")
    parser.add_argument("--rows", type=int, default=10000, help="Number of rows to generate (default: 10000)")
    parser.add_argument("--out", type=str, default="data/test_inventory.csv", help="Output filepath")
    args = parser.parse_args()
    
    generate_csv(args.out, args.rows)
