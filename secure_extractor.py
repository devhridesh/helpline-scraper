import os
import re
import json
from datetime import datetime
import google.generativeai as genai
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURATION & ENVIRONMENT SETUP
# ==========================================
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Environment keys validations (GitHub Secrets Check)
if not all([GEMINI_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY]):
    print("❌ Critical Error: Missing environment credentials!")
    print("Please check GEMINI_API_KEY, SUPABASE_URL, and SUPABASE_SERVICE_ROLE_KEY.")
    exit(1)

# Clients Initializations
genai.configure(api_key=GEMINI_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ==========================================
# 2. STEP 1: REGEX EMAIL EXTRACTION
# ==========================================
def extract_emails_with_regex(raw_text: str) -> list:
    """
    Webpage ke raw text se strictly saare valid emails nikaalta hai 
    taaki fake AI hallucination ka risk 0% ho sake.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    all_emails = re.findall(email_pattern, raw_text)
    
    # Duplicates filter karne ke liye set database use kiya
    unique_emails = list(set(all_emails))
    print(f"🔍 [Regex Whitelist Found]: {unique_emails}")
    return unique_emails


# ==========================================
# 3. STEP 2: STRICT GEMINI HIERARCHY MAPPER
# ==========================================
def map_data_with_gemini(raw_text: str, verified_emails: list) -> dict:
    """
    Regex se nikle genuine emails ko text context ke hisab se 
    Level 1, 2, aur 3 corporate hierarchy me structured format me set karta hai.
    """
    # Safe guard check: Agar page par koi email mila hi nahi toh operation bachaayein
    if not verified_emails:
        return {
            "level_1_phone": "", "level_1_email": "",
            "level_2_name": "", "level_2_phone": "", "level_2_email": "",
            "level_3_name": "", "level_3_phone": "", "level_3_email": ""
        }

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Absolute Strict Grounding Instructions
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

    prompt = f"Raw Webpage Text To Analyze:\n{raw_text}"
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            system_instruction=system_instruction
        )
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"❌ Gemini Parsing / Mapping Error: {e}")
        return {}


# ==========================================
# 4. STEP 3: AUTOMATED SUPABASE SYNC (UPSERT)
# ==========================================
def process_and_sync_corporate_data(company_name: str, domain: str, webpage_raw_text: str, gov_verified: bool = False):
    """
    Pure automation engine ko handle karta hai aur data direct Supabase me upsert (overwrite) karta hai.
    """
    print(f"\n🚀 Processing Engine Started for: {company_name} ({domain})...")
    
    # 1. Extract Valid Whitelisted Emails
    clean_emails = extract_emails_with_regex(webpage_raw_text)
    
    # 2. Context Structuring using Gemini
    structured_data = map_data_with_gemini(webpage_raw_text, clean_emails)
    
    if not structured_data:
        print(f"⚠️ Warning: No schema structure mapping parsed for {company_name}. Sync skipped.")
        return

    # 3. Dynamic Autopilot Live Timestamp Setup
    current_timestamp = datetime.now().strftime("%d-%b-%Y") # Output Format: 29-Jun-2026
    
    # 4. Payload Mapping For Supabase
    payload = {
        "company_name": company_name,
        "domain": domain, # Unique key base tracker for UPSERT
        "level_1_phone": structured_data.get("level_1_phone", ""),
        "level_1_email": structured_data.get("level_1_email", ""),
        "level_2_name": structured_data.get("level_2_name", ""),
        "level_2_phone": structured_data.get("level_2_phone", ""),
        "level_2_email": structured_data.get("level_2_email", ""),
        "level_3_name": structured_data.get("level_3_name", ""),
        "level_3_phone": structured_data.get("level_3_phone", ""),
        "level_3_email": structured_data.get("level_3_email", ""),
        "gov_verified": gov_verified,
        "last_verified_at": current_timestamp
    }
    
    # 5. DB Query Execution (Auto-Overwrite Engine)
    try:
        # on_conflict='domain' updates matching record without creating duplicate entries
        supabase.table("corporate_helplines").upsert(payload, on_conflict="domain").execute()
        print(f"✅ Live Sync Complete! {company_name} database row updated on autopilot.")
    except Exception as e:
        print(f"❌ Supabase Integration Upsert Fault: {e}")


# ==========================================
# 5. CORE LOOP RUNNER (TEST INTEGRATION)
# ==========================================
if __name__ == "__main__":
    # Mock data execution trace check (Airtel India Sample Layout)
    sample_scraped_text = (
        "Welcome to Airtel India Compliance Section. For general support contact customer.care@airtel.in or call 1800112211. "
        "Our Nodal Officer for appellate authority is Mr. Rajesh Kumar. If you want to escalate your issue to level 2, "
        "please write to our core appellate team at appellate.officer@airtel.in or dial direct desk 011-23456789."
    )
    
    # Core function execution
    process_and_sync_corporate_data(
        company_name="Airtel India",
        domain="airtel.in",
        webpage_raw_text=sample_scraped_text,
        gov_verified=False
    )