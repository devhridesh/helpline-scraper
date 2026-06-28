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
    """Bina kisi API key ke DuckDuckGo se live search extraction execute karta hai."""
    try:
        print(f"\n[WEB SEARCH] Executing Search Query: '{query}'...")
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # DuckDuckGo HTML engine par POST request bhej rahe hain
        response = requests.post(url, data={"q": query}, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[WEB SEARCH] Error: Unable to fetch results (Status Code: {response.status_code})")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("div", class_="result")
        
        extracted_data = []
        # Top 5 search results ko loop chalakar extract karenge
        for item in results[:5]:
            title_tag = item.find("a", class_="result__url")
            snippet_tag = item.find("a", class_="result__snippet")
            
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href")
                
                # Link cleaner (agar relative URL ho toh protocol fix karein)
                if link and link.startswith("//"):
                    link = "https:" + link
                    
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No description available."
                
                print(f" -> Found: {title} | Link: {link}")
                extracted_data.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })
                
        if not extracted_data:
            print("[WEB SEARCH] Warning: No results extracted. HTML layout might have changed.")
            
        return extracted_data

    except Exception as e:
        print(f"\n❌ [WEB SEARCH] Unexpected System Error: {str(e)}")
        return []


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
    
    sample_query = "Airtel customer care helpline number India"
    results = run_web_search(sample_query)
    
    if results:
        sync_with_supabase(results)
        
    print("\n--- PROCESS COMPLETED SUCCESSFULLY ---")