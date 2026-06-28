import sys
import requests
from bs4 import BeautifulSoup

print("--- SCRAMBLER BOOT INITIALIZED ---")

# --- Environment Credentials Config ---
# Google Keys ki ab koi zaroorat nahi hai! Sirf Supabase config bacha hai.
SUPABASE_URL = "https://irqzochxonpasmxsvewa.supabase.co"
SUPABASE_KEY = "sb_publishable_iompK6J4ZsaK7qOCYuw10w_hP4xSb2z"

print("--- CREDENTIALS LOADED SUCCESSFULLY ---")
def run_web_search(query):
    """DuckDuckGo se top 5 search results ke target URLs ki clean list extract karta hai."""
    try:
        print(f"\n[1. WEB SEARCH] Executing Search Query: '{query}'...")
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.post(url, data={"q": query}, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[1. WEB SEARCH] Error: Unable to fetch results (Status Code: {response.status_code})")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("div", class_="result")
        
        extracted_links = []
        for item in results[:5]:
            title_tag = item.find("a", class_="result__url")
            if title_tag:
                link = title_tag.get("href")
                if link:
                    if link.startswith("//"):
                        link = "https:" + link
                    print(f" -> Found Potential Link: {link}")
                    extracted_links.append(link)
                    
        if not extracted_links:
            print("[1. WEB SEARCH] Warning: No links extracted. HTML layout might have changed.")
            
        return extracted_links

    except Exception as e:
        print(f"\n❌ [1. WEB SEARCH] Unexpected System Error: {str(e)}")
        return []


# =====================================================================
# 🆕 NAYE FUNCTIONS: YAHAN SE COPY-PASTE SHURU KAREIN
# =====================================================================

def verify_official_url_with_ai(company_name, links_list):
    """Gemini se poochta hai ki list mein se asli official corporate domain ya strong authority kaun si hai."""
    if not links_list:
        return None
    try:
        print("[2. AI VERIFIER] Asking Gemini to identify the official domain...")
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        system_instruction = (
            f"Analyze this list of URLs found for '{company_name}'. "
            f"Identify the single official corporate website or a strong trusted authority (like Wikipedia or Govt portal). "
            f"Return ONLY the plain URL string. Do not include markdown, backticks, or explanations. "
            f"If no official or highly trusted site is found, return an empty string."
        )
        
        payload = {
            "contents": [{"parts": [{"text": f"{system_instruction}\n\nLinks List:\n{links_list}"}]}]
        }
        
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        if response.status_code == 200:
            verified_url = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if verified_url.startswith("```"):
                verified_url = verified_url.replace("```", "").strip()
            print(f" -> AI Verified Official URL: {verified_url}")
            return verified_url if verified_url else None
    except Exception as e:
        print(f" ❌ AI Verification Error: {str(e)}")
    return None


def find_support_page(official_url):
    """Official Homepage ke saare links khangal kar Contact/Support page ka deep link nikaalta hai."""
    if not official_url:
        return None
    try:
        print(f"[3. DEEP CRAWLER] Scanning homepage for support/contact links: {official_url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(official_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return official_url
            
        soup = BeautifulSoup(response.text, "html.parser")
        keywords = ["contact", "support", "helpline", "customer-care", "escalation", "grievance"]
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].lower()
            text = a_tag.get_text().lower()
            
            if any(k in href or k in text for k in keywords):
                target_href = a_tag["href"]
                if target_href.startswith("/"):
                    target_href = official_url.rstrip("/") + target_href
                elif not target_href.startswith("http"):
                    target_href = official_url.rstrip("/") + "/" + target_href
                print(f" -> Deep Support Link Located: {target_href}")
                return target_href
    except Exception as e:
        print(f" ⚠️ Crawler Warning: Could not parse deep links ({str(e)})")
        
    return official_url


# =====================================================================
# ⬇️ PURANA FUNCTION: ISKE NEECHE YEH PEHLE SE MAUJOOD HAI
# =====================================================================

def extract_page_text(url):
    """Target URL par jaakar uska raw content/text download karta hai."""
    try:
        print(f"[4. WEB SCRAPER] Fetching raw content from website...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return text[:6000]
    except Exception as e:
        print(f" ⚠️ Scraping Warning: Page load failed ({str(e)})")
    return None


def sync_with_supabase(data):
    """Extracted records ko Supabase corporate_helplines table mein push karta hai."""
    if not data:
        print("[SUPABASE SYNC] No data available to sync.")
        return
        
    print("\n[SUPABASE SYNC] Initializing database sync batch...")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    endpoint = f"{SUPABASE_URL}/rest/v1/corporate_helplines" 
    
    for record in data:
        payload = {
            "name": record["title"],
            "source_url": record["link"],
            "description": record["snippet"]
        }
        try:
            response = requests.post(endpoint, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                print(f" ✅ Success: Synced '{record['title']}' to database!")
            else:
                print(f" ⚠️ Database Warning: Status {response.status_code}")
                print(f"   Response Body: {response.text}")
        except Exception as e:
            print(f" ❌ Failed syncing entry to Supabase: {str(e)}")


if __name__ == "__main__":
    print("\n--- STARTING LIVE DATA SCRAPING PROCESS ---")
    
    target_company = "State Bank of India (SBI)"
    search_query = f"{target_company} corporate official website contact info"
    
    # 1. Top 5 links nikaalein
    all_links = run_web_search(search_query)
    
    # 2. AI se official domain verify karayein (Fake/Scammer sites filter karne ke liye)
    official_url = verify_official_url_with_ai(target_company, all_links)
    
    if official_url:
        # 3. Official site ke andar Contact/Support page dhoondhein
        support_url = find_support_page(official_url)
        
        # 4. Us deep support page ka raw content uthayein
        page_content = extract_page_text(support_url)
        
        if page_content:
            # 5. Gemini se strict JSON matrix parse karayein
            structured_json = parse_data_with_gemini(page_content)
            
            if structured_json:
                # 6. Supabase database mein sync karein
                sync_with_supabase(target_company, structured_json, support_url)
    else:
        print("❌ SECURITY BLOCK: No official website or trusted authority verified by AI. Skipping sync.")
        
    print("\n--- PROCESS COMPLETED SUCCESSFULLY ---")