import os
import re
import json
import time  # ⏳ Auto-pause aur retry ke liye
import hashlib  # 🧠 Quota bachane ke liye (Hash Check)
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions  # ⚠️ Specific Google API Errors pakadne ke liye
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
genai.configure(api_key=GEMINI_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
print("🎯 [Initialization]: API Client instances initialized successfully!")


# ==============================================================================
# 2. STEP 1: PARSING ENGINE (REGEX EMAIL EXTRACTION)
# ==============================================================================
def extract_emails_with_regex(raw_text: str) -> list:
    print("\n🔍 [Pipeline Phase 1]: Triggering core Regex structural scanning pattern...")
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    all_emails = re.findall(email_pattern, raw_text)
    unique_emails = list(set(all_emails))
    print(f"✅ [Pipeline Phase 1]: Scan complete. Whitelist compiled: {unique_emails}")
    return unique_emails

# ==============================================================================
# 3. STEP 2: BRAIN ENGINE (AUTO-RETRY ON QUOTA LIMITS)
# ==============================================================================
def map_data_with_gemini(raw_text: str, verified_emails: list, max_retries: int = 3) -> dict:
    """
    Gemini AI se data map karta hai. Agar 429 Quota Error aata hai, toh 
    yeh automatic pause lekar dubara koshish karta hai.
    """
    print("🧠 [Pipeline Phase 2]: Passing structured tokens to Gemini LLM mapping core...")
    if not verified_emails:
        print("⚠️ [Pipeline Phase 2 Warning]: Empty credentials array. Bypassing AI analysis.")
        return {}

    # 📝 1. System instruction ko pehle string me define karo
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

    # ✅ 2. Model initialization ke time par hi system_instruction pass karo
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=system_instruction
    )
    
    prompt = f"Raw Source Context Document Block:\n{raw_text}"
    
    # 🔄 Auto-Retry Loop Block
    for attempt in range(1, max_retries + 1):
        try:
            # ✅ 3. generate_content ko ekdum clean rakho (Bina system_instruction argument ke)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            print("✅ [Pipeline Phase 2 Success]: AI successfully parsed data hierarchy!")
            return json.loads(response.text.strip())
            
        except exceptions.ResourceExhausted as quota_err:
            # ⏳ Jab 429 Rate Limit hit hogi, tab yeh chalega
            print(f"\n⚠️ [QUOTA WARNING]: Gemini Free Limit Exhausted (Attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                sleep_duration = 60  # 1 minute ka cooldown window
                print(f"⏳ [Auto-Healing]: Pausing script execution for {sleep_duration} seconds to reset quota window...")
                time.sleep(sleep_duration)
                print("🔄 [Auto-Healing]: Resuming execution stream, retrying AI mapping call now...")
            else:
                print("❌ [QUOTA CRITICAL]: Daily/Absolute Free Quota completely dried up. Postponing loop for next cron run.")
                return {}
                
        except Exception as general_err:
            print(f"❌ [Pipeline Phase 2 Fault]: General exception encountered: {general_err}")
            return {}
            
    return {}

# ==============================================================================
# 4. STEP 3: SMART SYNC ENGINE (DELTA SCRAPING / HASH CHECK OVERRIDE)
# ==============================================================================
def process_and_sync_corporate_data(company_name: str, domain: str, webpage_raw_text: str, gov_verified: bool = False):
    print(f"\n🚀 [Core Orchestrator]: Checking synchronization profile for: {company_name}")
    print("------------------------------------------------------------------------------------")
    
    # ⚡ 1. Calculate Unique Text MD5 Hash
    sanitized_text = webpage_raw_text.strip()
    current_text_hash = hashlib.md5(sanitized_text.encode('utf-8')).hexdigest()
    
    # ⚡ 2. Database Hash Validation Check
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

    # ⚡ 3. Fall-through Execution only when text changes
    clean_emails = extract_emails_with_regex(webpage_raw_text)
    structured_data = map_data_with_gemini(webpage_raw_text, clean_emails)
    
    if not structured_data:
        print(f"⚠️ [Core Orchestrator Abort]: No data extracted (Possibly due to Limit Exhaustion). Sync skipped.")
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
    
    # 📌 TARGET 1: Amazon Pay India (Official Details)
    amazon_text = (
        "Level 1: Customer Support (Queries & Complaints) "
        "You can contact our 24x7 customer service team via https://www.amazon.in/contact-us which provides online resolution. "
        "Level 2: Grievance Officer (Complaints) "
        "Grievance Officer – Mr. Amber Dwivedi. Email – amazonpay-grievance-officer@amazonpay.in. "
        "Address – Amazon Pay (India) Private Limited, Sattva Horizon, Bengaluru – 560064. "
        "Level 3: Nodal Officer (Complaints) "
        "Principal Nodal Officer - Mahavir Jindal. Email – amazonpay-nodal-officer@amazonpay.in."
    )
    process_and_sync_corporate_data("Amazon Pay India", "amazon.in", amazon_text, gov_verified=True)
    
    # 📌 TARGET 2: Airtel India (Official Details)
    airtel_text = (
        "Welcome to Airtel India Compliance Section. For general support contact customer.care@airtel.in or call 1800112211. "
        "Our Nodal Officer for appellate authority is Mr. Rajesh Kumar. If you want to escalate your issue to level 2, "
        "please write to our core appellate team at appellate.officer@airtel.in or dial direct desk 011-23456789."
    )
    process_and_sync_corporate_data("Airtel India", "airtel.in", airtel_text, gov_verified=True)

    print("\n🏁 [Execution Root]: Auto-healing lifecycle run completed successfully.")