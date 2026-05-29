#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import re
from dotenv import load_dotenv

# Load environments
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")

# Resolution of credentials
BIBLE_API_URL = os.environ.get("BIBLE_API_URL", "https://rest.api.bible").rstrip('/')
BIBLE_API_KEY = os.environ.get("BIBLE_API_KEY")
BIBLE_ID = os.environ.get("BIBLE_ID") or os.environ.get("BIBLE_VERSION_ID") or "de4e12af7af57f50-02"

USFM_BOOK_MAPPING = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy",
    "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth", "1SA": "1 Samuel", "2SA": "2 Samuel",
    "1KI": "1 Kings", "2KI": "2 Kings", "1CH": "1 Chronicles", "2CH": "2 Chronicles",
    "EZR": "Ezra", "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms",
    "PRO": "Proverbs", "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea",
    "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah", "MIC": "Micah",
    "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah",
    "MAL": "Malachi", "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
    "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy", "2TI": "2 Timothy",
    "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews", "JAS": "James", "1PE": "1 Peter",
    "2PE": "2 Peter", "1JN": "1 John", "2JN": "2 John", "3JN": "3 John", "JUD": "Jude",
    "REV": "Revelation"
}

# Systematic mapping to double-digit USFM prefix numbers
USFM_BOOK_NUMBERS = {
    "GEN": "01", "EXO": "02", "LEV": "03", "NUM": "04", "DEU": "05",
    "JOS": "06", "JDG": "07", "RUT": "08", "1SA": "09", "2SA": "10",
    "1KI": "11", "2KI": "12", "1CH": "13", "2CH": "14", "EZR": "15",
    "NEH": "16", "EST": "17", "JOB": "18", "PSA": "19", "PRO": "20",
    "ECC": "21", "SNG": "22", "ISA": "23", "JER": "24", "LAM": "25",
    "EZK": "26", "DAN": "27", "HOS": "28", "JOL": "29", "AMO": "30",
    "OBA": "31", "JON": "32", "MIC": "33", "NAM": "34", "HAB": "35",
    "ZEP": "36", "HAG": "37", "ZEC": "38", "MAL": "39",
    "MAT": "41", "MRK": "42", "LUK": "43", "JHN": "44", "ACT": "45",
    "ROM": "46", "1CO": "47", "2CO": "48", "GAL": "49", "EPH": "50",
    "PHP": "51", "COL": "52", "1TH": "53", "2TH": "54", "1TI": "55",
    "2TI": "56", "TIT": "57", "PHM": "58", "HEB": "59", "JAS": "60",
    "1PE": "61", "2PE": "62", "1JN": "63", "2JN": "64", "3JN": "65",
    "JUD": "66", "REV": "67"
}

def parse_html_to_verses(html: str) -> list:
    """Splits API.Bible HTML into verse objects, matching backend parsing logic."""
    matches = list(re.finditer(r'<span[^>]*data-number="(\d+)"[^>]*>.*?</span>', html))
    
    if not matches:
        matches = list(re.finditer(r'<span[^>]*class="v"[^>]*>(\d+)</span>', html))
        
    verses = []
    if not matches:
        clean_text = re.sub(r'<[^>]+>', ' ', html).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        if clean_text:
            verses.append({"verse": 1, "text": clean_text})
        return verses
        
    for i, match in enumerate(matches):
        verse_num = int(match.group(1))
        start_pos = match.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(html)
        
        verse_html = html[start_pos:end_pos]
        verse_text = re.sub(r'<[^>]+>', ' ', verse_html).strip()
        verse_text = re.sub(r'\s+', ' ', verse_text)
        
        if verse_text:
            verses.append({"verse": verse_num, "text": verse_text})
            
    return verses

def clean_usfm_text(text: str) -> str:
    """Removes USFM alignment attributes, footnotes, cross-references, and formats to plain English."""
    # 1. Clean footnotes and cross-references
    text = re.sub(r'\\f\s+.*?\s*\\f\*', '', text)
    text = re.sub(r'\\x\s+.*?\s*\\x\*', '', text)
    
    # 2. Clean word alignment tags specifically: \w Word|attributes\w* -> Word
    text = re.sub(r'\\w\s+([^|\\*]+)(?:\|[^\\*]*)?\\w\*', r'\1', text)
    
    # 3. Clean milestone tags: \zaln-s ... \* and \zaln-e\*
    text = re.sub(r'\\zaln-s[^*]*\*', '', text)
    text = re.sub(r'\\zaln-e\*', '', text)
    
    # 4. Clean any other formatting ending tags like \ts\*
    text = re.sub(r'\\[a-z0-9-]+\*', '', text)
    
    # 5. Clean any other formatting start tags like \p, \q, \b, \s1, \ip, \m
    text = re.sub(r'\\[a-z0-9-*]+\+?', '', text)
    
    # 6. Clean translator braces (e.g. { was } -> was)
    text = re.sub(r'\{\s*([^}]+)\s*\}', r'\1', text)
    
    # 7. Normalize whitespaces and remove space before punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    return text

def parse_usfm_to_chapters(usfm_text: str, book_name: str) -> list:
    """Parses USFM text into structured chapters and verses by line processing."""
    chapters = []
    current_chapter = None
    current_verses = []
    current_verse_num = None
    current_verse_text_chunks = []
    
    ignore_tags = {
        'id', 'usfm', 'ide', 'h', 'toc1', 'toc2', 'toc3', 'mt1', 'mt2', 'c', 's1', 's2', 's3', 'sr', 'r'
    }
    
    for line in usfm_text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('\\'):
            parts = line.split(maxsplit=2)
            tag = parts[0][1:]
            
            if tag == 'c':
                if current_verse_num is not None:
                    full_text = " ".join(current_verse_text_chunks)
                    current_verses.append({
                        "verse": current_verse_num,
                        "text": clean_usfm_text(full_text)
                    })
                    current_verse_num = None
                    current_verse_text_chunks = []
                
                if current_chapter is not None and current_verses:
                    chapters.append({
                        "chapter": current_chapter,
                        "reference": f"{book_name} {current_chapter}",
                        "verses": current_verses
                    })
                
                current_chapter = int(parts[1])
                current_verses = []
                continue
                
            elif tag == 'v':
                if current_verse_num is not None:
                    full_text = " ".join(current_verse_text_chunks)
                    current_verses.append({
                        "verse": current_verse_num,
                        "text": clean_usfm_text(full_text)
                    })
                
                current_verse_num = int(parts[1])
                if len(parts) > 2:
                    current_verse_text_chunks = [parts[2]]
                else:
                    current_verse_text_chunks = []
                continue
                
            elif tag in ignore_tags or any(tag.startswith(t) for t in ['s', 'mt', 'toc', 'id', 'usfm', 'ide', 'h']):
                continue
                
            else:
                if current_verse_num is not None:
                    current_verse_text_chunks.append(line)
        else:
            if current_verse_num is not None:
                current_verse_text_chunks.append(line)
                
    if current_verse_num is not None:
        full_text = " ".join(current_verse_text_chunks)
        current_verses.append({
            "verse": current_verse_num,
            "text": clean_usfm_text(full_text)
        })
        
    if current_chapter is not None and current_verses:
        chapters.append({
            "chapter": current_chapter,
            "reference": f"{book_name} {current_chapter}",
            "verses": current_verses
        })
        
    return chapters

def make_api_request(endpoint: str):
    """Utility to perform authentic requests to API.Bible."""
    url = f"{BIBLE_API_URL}/v1{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "api-key": BIBLE_API_KEY,
            "User-Agent": "VachanStudyScriptureFetcher/1.0"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

def fetch_from_door43_usfm(book_code: str, book_name: str) -> list:
    """Fallback engine that fetches USFM from the official unfoldingWord Door43 repository."""
    book_num = USFM_BOOK_NUMBERS.get(book_code)
    if not book_num:
        raise ValueError(f"Book number mapping not found for USFM code: {book_code}")
        
    usfm_url = f"https://git.door43.org/unfoldingWord/en_ult/raw/branch/master/{book_num}-{book_code}.usfm"
    print(f"[FALLBACK] Fetching open-licensed USFM from Door43: {usfm_url}...")
    
    req = urllib.request.Request(
        usfm_url,
        headers={'User-Agent': 'VachanStudyScriptureFetcher/1.0'}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        usfm_text = response.read().decode("utf-8")
        
    print("[FALLBACK] USFM downloaded successfully. Commencing parsing...")
    chapters = parse_usfm_to_chapters(usfm_text, book_name)
    return chapters

def main():
    book_code = sys.argv[1].upper().strip() if len(sys.argv) > 1 else "COL"
    
    print("=" * 70)
    print("VACHAN STUDY BIBLE STUDY CHATBOT - DUAL-ENGINE SCRIPTURE PRECOMPILER UTILITY")
    print("=" * 70)
    
    book_name = USFM_BOOK_MAPPING.get(book_code, book_code.capitalize())
    print(f"[INFO] Target Book: {book_name} ({book_code})")
    
    compiled_chapters = []
    engine_used = "API.Bible"

    # Engine 1: Try API.Bible if credentials are present
    if BIBLE_API_KEY:
        try:
            print(f"[INFO] Engine 1: Trying API.Bible (Version: {BIBLE_ID})...")
            chapters_endpoint = f"/bibles/{BIBLE_ID}/books/{book_code}/chapters"
            chapters_data = make_api_request(chapters_endpoint)
            
            raw_chapters = chapters_data.get("data", [])
            chapters_to_fetch = []
            for rc in raw_chapters:
                ch_num_str = rc.get("number")
                if ch_num_str and ch_num_str.isdigit():
                    chapters_to_fetch.append({
                        "id": rc.get("id"),
                        "number": int(ch_num_str)
                    })
                    
            chapters_to_fetch.sort(key=lambda x: x["number"])
            print(f"[SUCCESS] Discovered {len(chapters_to_fetch)} active chapters via API.")
            
            for ch in chapters_to_fetch:
                ch_id = ch["id"]
                ch_num = ch["number"]
                print(f"   Fetching Chapter {ch_num}...")
                
                detail_endpoint = f"/bibles/{BIBLE_ID}/chapters/{ch_id}?content-type=html&include-notes=false&include-titles=false"
                ch_data = make_api_request(detail_endpoint)
                
                payload = ch_data.get("data", {})
                html_content = payload.get("content", "")
                reference = payload.get("reference", f"{book_name} {ch_num}")
                
                parsed_verses = parse_html_to_verses(html_content)
                compiled_chapters.append({
                    "chapter": ch_num,
                    "reference": reference,
                    "verses": parsed_verses
                })
        except Exception as api_err:
            print(f"[WARNING] API.Bible engine failed ({api_err}). Shifting to Engine 2...")
            compiled_chapters = [] # Clear any partial fetches
            
    # Engine 2: Failsafe Fallback to unfoldingWord USFM
    if not compiled_chapters:
        try:
            print("[INFO] Engine 2: Trying unfoldingWord ULT USFM fallback...")
            compiled_chapters = fetch_from_door43_usfm(book_code, book_name)
            engine_used = "unfoldingWord ULT USFM"
        except Exception as fallback_err:
            print(f"[ERROR] unfoldingWord fallback engine failed: {fallback_err}")
            sys.exit(1)
            
    if not compiled_chapters:
        print("[ERROR] Failed to fetch scripture using both Engines. Exiting.")
        sys.exit(1)
        
    # Write output payload
    output_payload = {
        "book": book_name,
        "chapters": compiled_chapters
    }
    
    os.makedirs(STATIC_DATA_DIR, exist_ok=True)
    out_file = os.path.join(STATIC_DATA_DIR, f"bible_{book_code}.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=4)
        
    print("=" * 70)
    print(f"[SUCCESS] Scripture precompiled using: {engine_used.upper()}")
    print(f"[SUCCESS] Output file saved to: {out_file}")
    print(f"[SUCCESS] Book: {book_name}")
    print(f"[SUCCESS] Chapters Precompiled: {len(compiled_chapters)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
