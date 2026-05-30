#!/usr/bin/env python3
"""
Vachan Study Bible Chatbot - Mass Scripture Precompiler
This script runs the fetch_api_scripture.py utility for all 66 books of the Bible,
pre-compiling the entire Scripture into structured JSON files inside static_data/
using open-licensed Door43 USFM data (or API.Bible if key is set), ensuring 
full zero-latency scripture viewing for all books on Vercel.
"""

import os
import sys
import subprocess
import time

# Directories relative to this script
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
FETCH_SCRIPT = os.path.join(SCRIPTS_DIR, "fetch_api_scripture.py")

# The 66 standard Protestant Bible book codes in canonical order
BIBLE_BOOKS = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV"
]

def precompile_all():
    print("=" * 75)
    print("VACHAN STUDY BIBLE CHATBOT - MASS SCRIPTURE PRECOMPILER")
    print("=" * 75)
    print(f"[INFO] Initializing mass scripture compilation for {len(BIBLE_BOOKS)} books...")
    
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    # Check if python executable is running inside venv
    python_exe = sys.executable
    
    for i, book in enumerate(BIBLE_BOOKS):
        print(f"\n[{i+1}/{len(BIBLE_BOOKS)}] Precompiling scripture for book: {book}...")
        
        try:
            # Run the scripture fetcher as a subprocess to keep each run isolated
            result = subprocess.run(
                [python_exe, FETCH_SCRIPT, book],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[SUCCESS] Scripture for {book} compiled successfully!")
            success_count += 1
        except subprocess.CalledProcessError as err:
            print(f"[ERROR] Failed to compile scripture for {book}:")
            print(err.stderr or err.stdout)
            fail_count += 1
            
        # Pacing sleep to prevent overloading network/GitHub raw API
        time.sleep(0.5)

    elapsed_time = time.time() - start_time
    print("\n" + "=" * 75)
    print("MASS PRECOMPILATION COMPLETE")
    print(f"   - Total Books Successfully Compiled: {success_count}/{len(BIBLE_BOOKS)}")
    print(f"   - Total Failures: {fail_count}")
    print(f"   - Total Time Elapsed: {elapsed_time:.2f} seconds")
    print("=" * 75)

if __name__ == "__main__":
    precompile_all()
