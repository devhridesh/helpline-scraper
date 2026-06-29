import re
import os
from datetime import datetime
import google.generativeai as genai
from supabase import create_client, Client

# 1. API Keys aur Clients ka Setup
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Unique operations ke liye service role best hai

genai.configure(api_key=GOOGLE_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. STEP 1: Pure Regex Email Extractor
def extract_emails_with_regex(raw_text: str) -> list:
    """Webpage ke raw text se strictly saare valid emails nikaalta hai bina kisi AI hallucination ke."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    all_emails = re.findall(email_pattern, raw_text)
    # Duplicate hatane ke liye set banakar vapas list mein convert kiya
    unique_emails = list(set(all_emails))
    print(f"🔍 [Regex Found Emails]: {unique_emails}")
    return unique_emails


# 3. STEP 2: Strict Gemini Mapper
def map_data_with_gemini(raw_text: str, verified_emails: list) -> dict:
    """Regex se nikle huye emails ko hierarchy ke hisab se structure karta hai."""
    
    # Agar text mein kuch nahi mila toh faltu API call bachaane ke liye khali schema return karo
    if not verified_emails:
        return {
            "level_1_phone": "", "level_1_email": "",
            "level_2_name": "", "level_2_phone": "", "level_2_email": "",
            "level_3_name": "", "level_3_phone": "", "level_3_email": ""
        }

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Absolute Strict Grounding Prompt Instruction
    system_instruction = (
        "You are a strict data classification bot. Your single job is to map verified contact details to corporate hierarchy.\n"
        f"STRICT RULE 1: For any email field, you can ONLY use emails present in this whitelist: {verified_emails}.\n"
        "STRICT RULE 2: DO NOT use your internal training knowledge or guess any data. If an email from the whitelist does not explicitly match a level in the text, leave that field empty (\"\").\n"
        "STRICT RULE 3: Extract human names and phone numbers only if explicitly linked to that escalation level in the text.\n\n"
        "Return a raw, clean JSON object matching these exact keys with string values. No markdown blocks, no backticks:\n"
        "{\n"
        "  \"level_1_phone\": \"\", \"level_1_email\": \"\",\n"
        "  \"level_2_name\": \"\", \"level_2_phone\": \"\", \"level_2_email\": \"\",\n"
        "  \"level_3_name\": \"\", \"level_3_phone\": \"\", \"level_3_email\": \"\"\n"
        "}"
    )

    prompt = f"Raw Text:\n{raw_text}"
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            system_instruction=system_instruction
        )
        # JSON response ko parse karke python dict mein badla
        import json
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"❌ Gemini Parsing Error: {e}")
        return {}


# 4. STEP 3: Automated Pipeline Trigger with Supabase UPSERT
def process_and_sync_corporate_data(company_name: str, domain: str, webpage_raw_text: str, gov_verified: bool = False):
    """Poore system ko automate karke database mein data sync (UPSERT) karta hai."""
    print(f"🚀 Processing Data for: {company_name} ({domain})...")
    
    # 1. Regex Se Clean Emails Nikalo
    clean_emails = extract_emails_with_regex(webpage_raw_text)
    
    # 2. Gemini Se Hierarchy Setup Karvao
    structured_data = map_data_with_gemini(webpage_raw_text, clean_emails)
    
    if not structured_data:
        print("⚠️ Mapping fail ho gayi. Operation aborted.")
        return

    # 3. Live Autopilot Timestamp Generate Karo
    current_timestamp = datetime.now().strftime("%d-%b-%Y") # Format: 29-Jun-2026
    
    # 4. Database Payload Taiyar Karo
    payload = {
        "company_name": company_name,
        "domain": domain, # Yeh unique key hai, isi par upsert kaam karega
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
    
    # 5. Supabase UPSERT Query execution
    try:
        # on_conflict='domain' ka matlab hai agar domain pehle se hai toh auto-overwrite (Update) kar do!
        result = supabase.table("corporate_helplines").upsert(payload, on_conflict="domain").execute()
        print(f"✅ Successfully synced {company_name} to database! [Status: Overwritten/Inserted]")
    except Exception as e:
        print(f"❌ Supabase Upsert Operation Failed: {e}")

# Example Integration Test Check:
if __name__ == "__main__":
    # Dummy mock text testing ke liye (Airtel/Paytm ka sample dummy layout)
    sample_scraped_text = (
        "Welcome to Airtel India Compliance Section. For general support contact customer.care@airtel.in or call 1800112211. "
        "Our Nodal Officer for appellate authority is Mr. Rajesh Kumar. If you want to escalate your issue to level 2, "
        "please write to our core appellate team at appellate.officer@airtel.in or dial direct desk 011-23456789."
    )
    
    # Triggering the workflow
    process_and_sync_corporate_data(
        company_name="Airtel India",
        domain="airtel.in",
        webpage_raw_text=sample_scraped_text,
        gov_verified=False # Jab tak Gov data match na ho, tab tak false rakhein
    )