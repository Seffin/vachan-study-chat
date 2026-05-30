#!/usr/bin/env python3
"""
Vachan Study Bible Chatbot - Offline CSV Fallback Generator
This script reads all book TSV files locally and exports them as cleaned CSV files
to static_data/ without making any external API calls, ensuring a full set of 
offline fallbacks on Vercel with zero rate-limit risks.
"""

import os
import pandas as pd

# Directories relative to this script's location (backend/scripts/generate_csv_fallbacks.py)
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, "data")
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")
TQ_DIR = os.path.join(DATA_DIR, "en_tq")

def generate_fallbacks():
    print("=" * 75)
    print("VACHAN STUDY BIBLE CHATBOT - OFFLINE CSV FALLBACK GENERATOR")
    print("=" * 75)

    os.makedirs(STATIC_DATA_DIR, exist_ok=True)

    if not os.path.exists(TQ_DIR):
        print(f"[ERROR] unfoldingWord en_tq source directory not found at {TQ_DIR}.")
        print("        Please run build_vector_db.py once first to fetch the TSV data.")
        return

    # Find all TSV files
    tsv_files = [f for f in os.listdir(TQ_DIR) if f.startswith("tq_") and f.endswith(".tsv")]
    if not tsv_files:
        print("[ERROR] No tq_*.tsv files found in backend/data/en_tq/. Exiting.")
        return

    print(f"[INFO] Found {len(tsv_files)} book TSV datasets. Commencing CSV conversion...")
    
    success_count = 0
    fail_count = 0

    for filename in sorted(tsv_files):
        book_code = filename.replace("tq_", "").replace(".tsv", "").upper().strip()
        tsv_path = os.path.join(TQ_DIR, filename)
        csv_path = os.path.join(STATIC_DATA_DIR, f"tq_{book_code}.csv")

        try:
            # Load TSV
            df = pd.read_csv(tsv_path, sep='\t')
            
            # Normalize column names
            df.rename(columns={
                'reference': 'Reference',
                'Reference': 'Reference',
                'question': 'Question',
                'Question': 'Question',
                'response': 'Response',
                'Response': 'Response'
            }, inplace=True)
            
            df.columns = df.columns.str.strip()
            
            # Fill missing values
            df['Reference'] = df['Reference'].fillna('1:1').astype(str)
            df['Question'] = df['Question'].fillna('').astype(str)
            df['Response'] = df['Response'].fillna('').astype(str)

            # Save as CSV in static_data
            df.to_csv(csv_path, index=False)
            success_count += 1
            print(f"[SUCCESS] Cleaned and exported fallback CSV for '{book_code}'")
        except Exception as e:
            print(f"[ERROR] Failed to convert '{book_code}' ({filename}): {e}")
            fail_count += 1

    print("\n" + "=" * 75)
    print("CONVERSION SUMMARY")
    print(f"   - Total CSV Fallbacks Successfully Generated: {success_count}")
    print(f"   - Total Failures: {fail_count}")
    print(f"   - CSV assets saved under: {STATIC_DATA_DIR}")
    print("=" * 75)

if __name__ == "__main__":
    generate_fallbacks()
