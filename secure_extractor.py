import os
import re
import json
import time
import sys
import hashlib
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from supabase import create_client

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================
IS_GITHUB = os.environ.get('GITHUB_ACTIONS') == 'true'
SLEEP_TIME = 90 if IS_GITHUB else 2
LIMIT = None if IS_GITHUB else 3

# --- TIME GUARDRAIL (Naya Feature) ---
def check_time_guardrail():
    if IS_GITHUB:
        utc_now = datetime.utcnow()
        ist_now = utc_now + timedelta(hours=5, minutes=30)
        # Limit reset 12:30 par hoti hai, hum 12:40 ka safety buffer le rahe hain
        target_time = ist_now.replace(hour=12, minute=40, second=0, microsecond=0)
        
        if ist_now < target_time:
            print(f"🛑 Time Guardrail Active: Abhi {ist_now.strftime('%H:%M')} ho raha hai. Quota reset (12:40) ka intezaar hai. Exiting!")
            sys.exit(0)

# Initialization
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
client = genai.Client(api_key=GEMINI_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==============================================================================
# 2. MASTER LIST (Wahi saari 60+ companies)
# ==============================================================================
TARGET_COMPANIES = [
    {"name": "Amazon Pay India", "domain": "amazon.in", "text": "Level 1: Support via https://www.amazon.in/contact-us. Level 2 Grievance Officer Mr. Amber Dwivedi email amazonpay-grievance-officer@amazonpay.in. Level 3 Nodal Officer Mahavir Jindal email amazonpay-nodal-officer@amazonpay.in."},
    # ... (Yahan apni wahi poori 60+ list wapas paste kar do) ...
]

# ==============================================================================
# 3. CORE PROCESSING LOGIC
# ==============================================================================
def process_single_company(company):
    print(f"DEBUG: Starting function for {company['name']}")
    raw_text = company['text']
    
    # Delta Filter
    current_hash = hashlib.md5(raw_text.encode('utf-8')).hexdigest()
    try:
        db = supabase.table("corporate_helplines").select("text_hash").eq("domain", company['domain']).execute()
        if db.data and db.data[0].get("text_hash") == current_hash:
            print("✅ Data matches. Skipping.")
            return True
    except Exception as e: print(f"DEBUG: DB lookup failed: {e}")

    # AI Mapping
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Extract structured data from: {raw_text}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text.strip())
        
        payload = data
        payload.update({
            "company_name": company['name'], 
            "domain": company['domain'], 
            "text_hash": current_hash,
            "last_verified_at": datetime.now().isoformat()
        })
        supabase.table("corporate_helplines").upsert(payload, on_conflict="domain").execute()
        return True
    except Exception as e:
        print(f"❌ Error in {company['name']}: {e}")
        if "429" in str(e): sys.exit(0)
        return False

# ==============================================================================
# 4. RUNNER
# ==============================================================================
if __name__ == "__main__":
    check_time_guardrail() # 👈 Sabse pehle ye check hoga!
    
    queue = TARGET_COMPANIES[:LIMIT] if LIMIT else TARGET_COMPANIES
    
    for company in queue:
        success = process_single_company(company)
        
        if not success:
            print(f"🔄 Retrying {company['name']} in 60s...")
            time.sleep(60)
            process_single_company(company)
            
        print(f"⏳ Waiting {SLEEP_TIME}s...")
        time.sleep(SLEEP_TIME)

    print("🏁 Batch complete.")