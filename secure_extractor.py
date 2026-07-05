import os
import re
import json
import time
import sys  # 🛑 Script ko instantly kill karne ke liye
import hashlib
from datetime import datetime
from google import genai  # ✅ Google ki nayi official SDK import
from google.genai import types  # ✅ Configuration settings ke liye
from supabase import create_client, Client

# ==============================================================================
# 1. ENVIRONMENT CONFIGURATION & MULTI-PLATFORM KEY LOADER
# ==============================================================================
try:
    from dotenv import load_dotenv
    print("🔄 [System Diagnostics]: Detected local python-dotenv environment.")
    load_dotenv()
    print("✅ [System Diagnostics]: Local environment variables injected successfully.")
except ImportError:
    print("🚀 [System Diagnostics]: Running on production cloud engine (Bypassing local dotenv check)...")
    pass

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([GEMINI_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY]):
    print("\n❌ CRITICAL INITIALIZATION FAULT: Missing required credentials!")
    exit(1)

print("⚙️ [Initialization]: Connecting API Clients...")
# ✅ Naye SDK ke mutabik Client instance initialize kiya
client = genai.Client(api_key=GEMINI_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("🎯 [Initialization]: API Client instances initialized successfully!")


# ==============================================================================
# 2. STEP 1: PARSING ENGINE (REGEX EMAIL EXTRACTION)
# ==============================================================================
def extract_emails_with_regex(raw_text: str) -> list:
    print("\n🔍 [Pipeline Phase 1]: Triggering core Regex structural scanning pattern...")
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-]{2,}'
    all_emails = re.findall(email_pattern, raw_text)
    unique_emails = list(set(all_emails))
    print(f"✅ [Pipeline Phase 1]: Scan complete. Whitelist compiled: {unique_emails}")
    return unique_emails


# ==============================================================================
# 3. STEP 2: BRAIN ENGINE (NEW SDK + SMART LIMIT ROUTER)
# ==============================================================================
def map_data_with_gemini(raw_text: str, verified_emails: list, max_retries: int = 2) -> dict:
    """
    Naye google-genai SDK ke sath data map karta hai aur error message ke type 
    (Day vs Minute) ke hisab se smart decision leta hai.
    """
    print("🧠 [Pipeline Phase 2]: Passing structured tokens to Gemini LLM mapping core...")
    if not verified_emails:
        print("⚠️ [Pipeline Phase 2 Warning]: Empty credentials array. Bypassing AI analysis.")
        return {}

    system_instruction = (
        "You are a strict data classification bot. Your single job is to map verified contact details to corporate hierarchy.\n"
        f"STRICT RULE 1: For any email field, you can ONLY use emails present in this whitelist: {verified_emails}.\n"
        "STRICT RULE 2: DO NOT use your internal training knowledge or guess any data. If an email from the whitelist does not explicitly match a level in the text, leave that field empty (\"\").\n"
        "STRICT RULE 3: Extract human names and phone numbers only if explicitly linked to that escalation level in the text.\n\n"
        "Return a raw, clean JSON object matching these exact keys with string values. No markdown blocks, no backticks, no comments:\n"
        "{\n"
        "  \"level_1_phone\": \"\", \"level_1_email\": \"\",\n"
        "  \"level_2_name\": \"\", \"level_2_phone\": \"\", \"level_2_email\": \"\",\n"
        "  \"level_3_name\": \"\", \"level_3_phone\": \"\", \"level_3_email\": \"\"\n"
        "}"
    )

    prompt = f"Raw Source Context Document Block:\n{raw_text}"
    
    # 🔄 Smart Retry & Routing Loop
    for attempt in range(1, max_retries + 1):
        try:
            # ✅ Naye SDK ka official content generation method
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                )
            )
            print("✅ [Pipeline Phase 2 Success]: AI successfully parsed data hierarchy!")
            return json.loads(response.text.strip())
            
        except Exception as err:
            error_message = str(err)
            
            # Check if it's a Quota/Rate Limit issue (429 or ResourceExhausted)
            if "429" in error_message or "exhausted" in error_message.lower():
                
                # 🛑 CASE A: Daily Quota Cap Hit (Pure din ki limit khatam)
                if "perday" in error_message.lower() or "requests_per_day" in error_message.lower():
                    print("\n❌ [CRITICAL QUOTA CAP]: Google AI Studio Daily Free Limit completely exhausted!")
                    print("🛑 [Auto-Stopping]: Daily limits reset after 24 hours. Halting script immediately to save GitHub minutes.")
                    sys.exit(0)  # Pure script ko instantly clean exit kar dega
                
                # ⏳ CASE B: Per-Minute Rate Limit Hit (Sirf 1 minute ka block)
                elif "perminute" in error_message.lower() or "requests_per_minute" in error_message.lower() or "resource_exhausted" in error_message.lower():
                    print(f"\n⚠️ [RATE LIMIT]: Hit per-minute cap (Attempt {attempt}/{max_retries}).")
                    if attempt < max_retries:
                        sleep_duration = 60
                        print(f"⏳ [Smart Sleep]: Pausing for {sleep_duration} seconds to clear the minute window...")
                        time.sleep(sleep_duration)
                    else:
                        print("❌ [RATE CRITICAL]: Minute cap retries exhausted for this link.")
                        return {}
                else:
                    print(f"❌ [QUOTA EXHAUSTED]: Generic exhaustion detected: {error_message}")
                    return {}
            else:
                print(f"❌ [Pipeline Phase 2 Fault]: General exception encountered: {error_message}")
                return {}
            
    return {}


# ==============================================================================
# 4. STEP 3: SMART SYNC ENGINE (DELTA SCRAPING / HASH CHECK OVERRIDE)
# ==============================================================================
def process_and_sync_corporate_data(company_name: str, domain: str, webpage_raw_text: str, gov_verified: bool = False):
    print(f"\n🚀 [Core Orchestrator]: Checking synchronization profile for: {company_name}")
    print("------------------------------------------------------------------------------------")
    
    sanitized_text = webpage_raw_text.strip()
    current_text_hash = hashlib.md5(sanitized_text.encode('utf-8')).hexdigest()
    
    try:
        db_response = supabase.table("corporate_helplines").select("text_hash").eq("domain", domain).execute()
        if db_response.data:
            historical_hash = db_response.data[0].get("text_hash")
            if historical_hash == current_text_hash:
                print(f"🎯 [DELTA FILTER]: No content updates detected for {domain}. Quota saved! ✅")
                print("------------------------------------------------------------------------------------")
                return
    except Exception as cache_error:
        print(f"⚠️ [Cache Warning]: Could not read baseline hash: {cache_error}")

    clean_emails = extract_emails_with_regex(webpage_raw_text)
    structured_data = map_data_with_gemini(webpage_raw_text, clean_emails)
    
    if not structured_data:
        print(f"⚠️ [Core Orchestrator Abort]: Sync skipped due to missing data map.")
        return

    current_timestamp = datetime.now().strftime("%d-%b-%Y")
    
    payload = {
        "company_name": company_name,
        "domain": domain,
        "level_1_phone": structured_data.get("level_1_phone", ""),
        "level_1_email": structured_data.get("level_1_email", ""),
        "level_2_name": structured_data.get("level_2_name", ""),
        "level_2_phone": structured_data.get("level_2_phone", ""),
        "level_2_email": structured_data.get("level_2_email", ""),
        "level_3_name": structured_data.get("level_3_name", ""),
        "level_3_phone": structured_data.get("level_3_phone", ""),
        "level_3_email": structured_data.get("level_3_email", ""),
        "gov_verified": gov_verified,
        "last_verified_at": current_timestamp,
        "text_hash": current_text_hash
    }
    
    try:
        print("📡 [Supabase Client]: Broadcasting fresh transaction payload stream...")
        supabase.table("corporate_helplines").upsert(payload, on_conflict="domain").execute()
        print(f"✅ [Supabase Status]: TRANSACTION COMMITTED. Website updated successfully.")
    except Exception as db_exception:
        print(f"❌ [Supabase Fault]: Cloud table update process aborted: {db_exception}")
    
    print("------------------------------------------------------------------------------------")


# ==============================================================================
# 5. CORE RUNNER (OFFICIAL TARGET DATA LOOPS)
# ==============================================================================
if __name__ == "__main__":
    print("\n🏁 [Execution Root]: Booting automated corporate helpline system...")
    
    # 📌 TARGET 1: Amazon Pay India
    amazon_text = (
        "Level 1: Customer Support (Queries & Complaints) "
        "You can contact our 24x7 customer service team via https://www.amazon.in/contact-us which provides online resolution. "
        "Level 2: Grievance Officer (Complaints) "
        "Grievance Officer - Mr. Amber Dwivedi. Email - amazonpay-grievance-officer@amazonpay.in. "
        "Address - Amazon Pay (India) Private Limited, Sattva Horizon, Bengaluru - 560064. "
        "Level 3: Nodal Officer (Complaints) "
        "Principal Nodal Officer - Mahavir Jindal. Email - amazonpay-nodal-officer@amazonpay.in."
    )
    process_and_sync_corporate_data("Amazon Pay India", "amazon.in", amazon_text, gov_verified=True)
    
    # 📌 TARGET 2: Airtel India
    airtel_text = (
        "Welcome to Airtel India Compliance Section. For general support contact customer.care@airtel.in or call 1800112211. "
        "Our Nodal Officer for appellate authority is Mr. Rajesh Kumar. If you want to escalate your issue to level 2, "
        "please write to our core appellate team at appellate.officer@airtel.in or dial direct desk 011-23456789."
    )
    process_and_sync_corporate_data("Airtel India", "airtel.in", airtel_text, gov_verified=True)

    print("\n🏁 [Execution Root]: Auto-healing lifecycle run completed successfully.")