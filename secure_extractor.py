import os
import re
import json
import time
import sys
import hashlib
from datetime import datetime
from google import genai
from google.genai import types
from supabase import create_client

# --- SETUP & CONFIG ---
IS_GITHUB = os.environ.get('GITHUB_ACTIONS') == 'true'
SLEEP_TIME = 90 if IS_GITHUB else 2
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

client = genai.Client(api_key=GEMINI_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- MASTER LIST OF 60+ COMPANIES ---
TARGET_COMPANIES = [
    {"name": "Amazon Pay India", "domain": "amazon.in", "text": "Level 1: Support via https://www.amazon.in/contact-us. Level 2 Grievance Officer Mr. Amber Dwivedi email amazonpay-grievance-officer@amazonpay.in. Level 3 Nodal Officer Mahavir Jindal email amazonpay-nodal-officer@amazonpay.in."},
    {"name": "Airtel India", "domain": "airtel.in", "text": "Level 1 Desk customer.care@airtel.in or call 1800112211. Level 2 Nodal Officer Mr. Rajesh Kumar email nodal.officer@airtel.in. Level 3 Appellate Desk appellate.officer@airtel.in direct desk 011-23456789."},
    {"name": "Flipkart India", "domain": "flipkart.com", "text": "Level 1 Support support@flipkart.com. Level 2 Grievance Officer Mr. Shreeram Sharma email grievance.officer@flipkart.com. Level 3 Nodal Officer Mrs. Priya Verma email nodal.officer@flipkart.com."},
    {"name": "Reliance Jio", "domain": "jio.com", "text": "Level 1 Desk customercare@jio.com. Level 2 Nodal Officer nodal.officer@jio.com. Level 3 Appellate Desk appellate.desk@jio.com."},
    {"name": "Paytm", "domain": "paytm.com", "text": "Level 1 Support customer.care@paytm.com. Level 2 Grievance Officer Mr. Sarthak Mishra email grievance.officer@paytm.com. Level 3 Nodal Officer nodal@paytm.com."},
    {"name": "Zomato", "domain": "zomato.com", "text": "Level 1 Support support@zomato.com. Level 2 Grievance Officer Ms. Anjali Hegde email grievance@zomato.com. Level 3 Nodal Officer nodal.officer@zomato.com."},
    {"name": "Swiggy", "domain": "swiggy.in", "text": "Level 1 Support support@swiggy.in. Level 2 Grievance Officer Mr. Arun Verma email grievances@swiggy.in. Level 3 Nodal Officer nodalofficer@swiggy.in."},
    {"name": "PhonePe", "domain": "phonepe.com", "text": "Level 1 Support customercare@phonepe.com. Level 2 Grievance Officer Mr. Rohit Ambasta email grievance.officer@phonepe.com. Level 3 Nodal Officer nodal.officer@phonepe.com."},
    {"name": "Meesho", "domain": "meesho.com", "text": "Level 1 Support help@meesho.com. Level 2 Grievance Officer Mr. Alok Kumar email grievance-officer@meesho.com. Level 3 Nodal Officer nodal-officer@meesho.com."},
    {"name": "Uber India", "domain": "uber.com", "text": "Level 1 Help help.uber.com. Level 2 Grievance Officer Mr. Nitin Nair email grievance-officer-india@uber.com. Level 3 Nodal Officer nodal-officer-india@uber.com."},
    {"name": "Vodafone Idea", "domain": "vodafoneidea.com", "text": "Level 1 Support customercare@vodafoneidea.com. Level 2 Nodal Officer nodal.officer@vodafoneidea.com. Level 3 Appellate Desk appellate.authority@vodafoneidea.com."},
    {"name": "Google Pay India", "domain": "pay.google.com", "text": "Level 1 Support support-in@google.com. Level 2 Grievance Officer Mr. Vikas Agrawal email gpay-grievance@google.com. Level 3 Nodal Officer nodal-eng-india@google.com."},
    {"name": "CRED", "domain": "cred.club", "text": "Level 1 Support membersupport@cred.club. Level 2 Grievance Officer grievance.officer@cred.club. Level 3 Nodal Officer compliance.head@cred.club."},
    {"name": "MobiKwik", "domain": "mobikwik.com", "text": "Level 1 Support support@mobikwik.com. Level 2 Grievance Officer grievance@mobikwik.com. Level 3 Nodal Officer nodal@mobikwik.com."},
    {"name": "BharatPe", "domain": "bharatpe.com", "text": "Level 1 Support nodalofficer@bharatpe.com. Level 2 Grievance Officer grievance@bharatpe.com. Level 3 Nodal Officer legal@bharatpe.com."},
    {"name": "Myntra", "domain": "myntra.com", "text": "Level 1 Support support@myntra.com. Level 2 Grievance Officer grievanceofficer@myntra.com. Level 3 Nodal Officer nodal@myntra.com."},
    {"name": "Ajio", "domain": "ajio.com", "text": "Level 1 Support cs.orders@ajio.com. Level 2 Grievance Officer grievance.officer@ajio.com. Level 3 Nodal Officer nodal.head@ajio.com."},
    {"name": "Nykaa", "domain": "nykaa.com", "text": "Level 1 Support support@nykaa.com. Level 2 Grievance Officer grievance.officer@nykaa.com. Level 3 Nodal Officer nodal.officer@nykaa.com."},
    {"name": "Tata CLiQ", "domain": "tatacliq.com", "text": "Level 1 Support support@tatacliq.com. Level 2 Grievance Officer executive.grievance@tatacliq.com. Level 3 Nodal Officer nodal.officer@tatacliq.com."},
    {"name": "Blinkit", "domain": "blinkit.com", "text": "Level 1 Support help@blinkit.com. Level 2 Grievance Officer grievance.officer@blinkit.com. Level 3 Nodal Officer nodal@blinkit.com."},
    {"name": "Zepto", "domain": "zepto.co", "text": "Level 1 Support support@zepto.co. Level 2 Grievance Officer grievance.officer@zepto.co. Level 3 Nodal Officer nodal@zepto.co."},
    {"name": "BigBasket", "domain": "bigbasket.com", "text": "Level 1 Support customerservice@bigbasket.com. Level 2 Grievance Officer grievance@bigbasket.com. Level 3 Nodal Officer nodal.officer@bigbasket.com."},
    {"name": "JioMart", "domain": "jiomart.com", "text": "Level 1 Support cs@jiomart.com. Level 2 Grievance Officer grievance.officer@jiomart.com. Level 3 Nodal Officer nodal@jiomart.com."},
    {"name": "Zerodha", "domain": "zerodha.com", "text": "Level 1 Support compliance@zerodha.com. Level 2 Grievance Officer grievance@zerodha.com. Level 3 Nodal Officer nodal@zerodha.com."},
    {"name": "Groww", "domain": "groww.in", "text": "Level 1 Support support@groww.in. Level 2 Grievance Officer grievance@groww.in. Level 3 Nodal Officer nodal.officer@groww.in."},
    {"name": "Angel One", "domain": "angelone.in", "text": "Level 1 Support support@angelone.in. Level 2 Grievance Officer compliance@angelone.in. Level 3 Nodal Officer regulatory.nodal@angelone.in."},
    {"name": "Upstox", "domain": "upstox.com", "text": "Level 1 Support complaints@upstox.com. Level 2 Grievance Officer grievance.officer@upstox.com. Level 3 Nodal Officer nodal@upstox.com."},
    {"name": "INDmoney", "domain": "indmoney.com", "text": "Level 1 Support help@indmoney.com. Level 2 Grievance Officer head.grievance@indmoney.com. Level 3 Nodal Officer nodal@indmoney.com."},
    {"name": "CoinSwitch Kuber", "domain": "coinswitch.co", "text": "Level 1 Support support@coinswitch.co. Level 2 Grievance Officer compliance.officer@coinswitch.co. Level 3 Nodal Officer legal@coinswitch.co."},
    {"name": "JioCinema", "domain": "jiocinema.com", "text": "Level 1 Support support@jiocinema.com. Level 2 Grievance Officer grievance.officer@jiocinema.com. Level 3 Nodal Officer compliance@jiocinema.com."},
    {"name": "Disney+ Hotstar", "domain": "hotstar.com", "text": "Level 1 Support support@hotstar.com. Level 2 Grievance Officer grievance.officer@hotstar.com. Level 3 Nodal Officer nodal@hotstar.com."},
    {"name": "Netflix India", "domain": "netflix.com", "text": "Level 1 Support help@netflix.com. Level 2 Grievance Officer grievance-india@netflix.com. Level 3 Nodal Officer legal-india@netflix.com."},
    {"name": "Amazon Prime Video", "domain": "primevideo.com", "text": "Level 1 Support help@primevideo.com. Level 2 Grievance Officer video-grievance-officer@amazon.in. Level 3 Nodal Officer nodal-india@amazon.in."},
    {"name": "Zee5", "domain": "zee5.com", "text": "Level 1 Support support.in@zee5.com. Level 2 Grievance Officer grievanceofficer@zee5.com. Level 3 Nodal Officer nodal@zee5.com."},
    {"name": "SonyLIV", "domain": "sonyliv.com", "text": "Level 1 Support customersupport@setindia.com. Level 2 Grievance Officer liv.grievance@setindia.com. Level 3 Nodal Officer nodal@setindia.com."},
    {"name": "BookMyShow", "domain": "bookmyshow.com", "text": "Level 1 Support helpdesk@bookmyshow.com. Level 2 Grievance Officer grievance@bookmyshow.com. Level 3 Nodal Officer nodal@bookmyshow.com."},
    {"name": "MakeMyTrip", "domain": "makemytrip.com", "text": "Level 1 Support help@makemytrip.com. Level 2 Grievance Officer senior.officer@makemytrip.com. Level 3 Nodal Officer nodal.officer@makemytrip.com."},
    {"name": "Goibibo", "domain": "goibibo.com", "text": "Level 1 Support travelcare@goibibo.com. Level 2 Grievance Officer grievance@goibibo.com. Level 3 Nodal Officer nodal@goibibo.com."},
    {"name": "EaseMyTrip", "domain": "easemytrip.com", "text": "Level 1 Support support@easemytrip.com. Level 2 Grievance Officer grievance@easemytrip.com. Level 3 Nodal Officer nodal.officer@easemytrip.com."},
    {"name": "Yatra", "domain": "yatra.com", "text": "Level 1 Support support@yatra.com. Level 2 Grievance Officer escalation@yatra.com. Level 3 Nodal Officer nodal@yatra.com."},
    {"name": "Cleartrip", "domain": "cleartrip.com", "text": "Level 1 Support customersupport@cleartrip.com. Level 2 Grievance Officer grievance.officer@cleartrip.com. Level 3 Nodal Officer nodal@cleartrip.com."},
    {"name": "redBus", "domain": "redbus.in", "text": "Level 1 Support grievances@redbus.in. Level 2 Grievance Officer grievance.officer@redbus.in. Level 3 Nodal Officer nodal@redbus.in."},
    {"name": "AbhiBus", "domain": "abhibus.com", "text": "Level 1 Support support@abhibus.com. Level 2 Grievance Officer grievance@abhibus.com. Level 3 Nodal Officer nodal@abhibus.com."},
    {"name": "Ixigo", "domain": "ixigo.com", "text": "Level 1 Support feedback@ixigo.com. Level 2 Grievance Officer grievance.officer@ixigo.com. Level 3 Nodal Officer nodal@ixigo.com."},
    {"name": "Ola Cabs", "domain": "olacabs.com", "text": "Level 1 Support support@olacabs.com. Level 2 Grievance Officer grievance.officer@olacabs.com. Level 3 Nodal Officer nodal@olacabs.com."},
    {"name": "Rapido", "domain": "rapido.bike", "text": "Level 1 Support info@rapido.bike. Level 2 Grievance Officer grievance@rapido.bike. Level 3 Nodal Officer nodal.officer@rapido.bike."},
    {"name": "Tata Play", "domain": "tataplay.com", "text": "Level 1 Support help@tataplay.com. Level 2 Grievance Officer grievance.officer@tataplay.com. Level 3 Nodal Officer nodal.officer@tataplay.com."},
    {"name": "Dish TV", "domain": "dishtv.in", "text": "Level 1 Support customercare@dishtv.in. Level 2 Grievance Officer grievance@dishtv.in. Level 3 Nodal Officer nodal.officer@dishtv.in."},
    {"name": "ACT Fibernet", "domain": "actcorp.in", "text": "Level 1 Support helpdesk@actcorp.in. Level 2 Grievance Officer nodal.officer@actcorp.in. Level 3 Nodal Officer appellate@actcorp.in."},
    {"name": "Hathway Broadband", "domain": "hathway.com", "text": "Level 1 Support info@hathway.com. Level 2 Grievance Officer grievance@hathway.com. Level 3 Nodal Officer nodal@hathway.com."},
    {"name": "Samsung India", "domain": "samsung.com", "text": "Level 1 Support support.india@samsung.com. Level 2 Grievance Officer grievance.officer@samsung.com. Level 3 Nodal Officer nodal.officer@samsung.com."},
    {"name": "Xiaomi India", "domain": "mi.com", "text": "Level 1 Support service.in@xiaomi.com. Level 2 Grievance Officer grievance.officer@xiaomi.com. Level 3 Nodal Officer nodal@xiaomi.com."},
    {"name": "OnePlus India", "domain": "oneplus.in", "text": "Level 1 Support onepluscare@oneplus.com. Level 2 Grievance Officer grievance.officer@oneplus.com. Level 3 Nodal Officer nodal@oneplus.com."},
    {"name": "Realme India", "domain": "realme.com", "text": "Level 1 Support service.in@realme.com. Level 2 Grievance Officer grievance.officer@realme.com. Level 3 Nodal Officer nodal@realme.com."},
    {"name": "Apple India Support", "domain": "apple.com", "text": "Level 1 Support apple.com/in/support. Level 2 Grievance Officer bangalore_admin@apple.com. Level 3 Nodal Officer legal@apple.com."},
    {"name": "Croma Retail", "domain": "croma.com", "text": "Level 1 Support customersupport@croma.com. Level 2 Grievance Officer grievance.officer@croma.com. Level 3 Nodal Officer nodal@croma.com."},
    {"name": "Reliance Digital", "domain": "reliancedigital.in", "text": "Level 1 Support reliancedigital@ril.com. Level 2 Grievance Officer grievance.officer@ril.com. Level 3 Nodal Officer nodal@ril.com."},
    {"name": "Policybazaar", "domain": "policybazaar.com", "text": "Level 1 Support support@policybazaar.com. Level 2 Grievance Officer grievance@policybazaar.com. Level 3 Nodal Officer nodal@policybazaar.com."},
    {"name": "ACKO General Insurance", "domain": "acko.com", "text": "Level 1 Support grievance@acko.com. Level 2 Grievance Officer grievance.officer@acko.com. Level 3 Nodal Officer nodalofficer@acko.com."},
    {"name": "Digit Insurance", "domain": "godigit.com", "text": "Level 1 Support cs@godigit.com. Level 2 Grievance Officer grievance@godigit.com. Level 3 Nodal Officer nodal.officer@godigit.com."},
    {"name": "Ditto Insurance", "domain": "joinditto.in", "text": "Level 1 Support support@joinditto.in. Level 2 Grievance Officer grievance@joinditto.in. Level 3 Nodal Officer nodal@joinditto.in."},
    {"name": "PhysicsWallah", "domain": "pw.live", "text": "Level 1 Support support@pw.live. Level 2 Grievance Officer grievance.officer@pw.live. Level 3 Nodal Officer nodal@pw.live."},
    {"name": "Unacademy", "domain": "unacademy.com", "text": "Level 1 Support help@unacademy.com. Level 2 Grievance Officer grievance.officer@unacademy.com. Level 3 Nodal Officer nodal@unacademy.com."},
    {"name": "upGrad", "domain": "upgrad.com", "text": "Level 1 Support customercare@upgrad.com. Level 2 Grievance Officer grievance@upgrad.com. Level 3 Nodal Officer nodal@upgrad.com."},
    {"name": "NoBroker", "domain": "nobroker.in", "text": "Level 1 Support marketing@nobroker.in. Level 2 Grievance Officer grievance@nobroker.in. Level 3 Nodal Officer nodal@nobroker.in."},
    {"name": "MagicBricks", "domain": "magicbricks.com", "text": "Level 1 Support support@magicbricks.com. Level 2 Grievance Officer grievance@magicbricks.com. Level 3 Nodal Officer nodal@magicbricks.com."},
    {"name": "99acres", "domain": "99acres.com", "text": "Level 1 Support support@99acres.com. Level 2 Grievance Officer grievance@99acres.com. Level 3 Nodal Officer nodal@99acres.com."},
    {"name": "Housing.com", "domain": "housing.com", "text": "Level 1 Support rent@housing.com. Level 2 Grievance Officer grievance@housing.com. Level 3 Nodal Officer nodal@housing.com."},
    {"name": "Dream11", "domain": "dream11.com", "text": "Level 1 Support support@dream11.com. Level 2 Grievance Officer grievance@dream11.com. Level 3 Nodal Officer nodal@dream11.com."},
    {"name": "MPL", "domain": "mpl.live", "text": "Level 1 Support community@mpl.live. Level 2 Grievance Officer grievance@mpl.live. Level 3 Nodal Officer nodal@mpl.live."},
    {"name": "WinZO", "domain": "winzogames.com", "text": "Level 1 Support support@winzogames.com. Level 2 Grievance Officer grievance.officer@winzogames.com. Level 3 Nodal Officer nodal@winzogames.com."},
    {"name": "Ola Electric", "domain": "olaelectric.in", "text": "Level 1 Support support@olaelectric.in. Level 2 Grievance Officer grievance.officer@olaelectric.in. Level 3 Nodal Officer nodal@olaelectric.in."},
    {"name": "Ather Energy", "domain": "atherenergy.com", "text": "Level 1 Support support@atherenergy.com. Level 2 Grievance Officer grievance@atherenergy.com. Level 3 Nodal Officer nodal@atherenergy.com."},
    {"name": "Tata Motors", "domain": "tatamotors.com", "text": "Level 1 Support customercare@tatamotors.com. Level 2 Grievance Officer quality.grievance@tatamotors.com. Level 3 Nodal Officer nodal@tatamotors.com."},
    {"name": "Maruti Suzuki", "domain": "marutisuzuki.com", "text": "Level 1 Support contact@maruti.co.in. Level 2 Grievance Officer quality.grievance@maruti.co.in. Level 3 Nodal Officer nodal@maruti.co.in."},
    {"name": "Delhivery", "domain": "delhivery.com", "text": "Level 1 Support customer.support@delhivery.com. Level 2 Grievance Officer grievance@delhivery.com. Level 3 Nodal Officer nodal.officer@delhivery.com."},
    {"name": "Blue Dart", "domain": "bluedart.com", "text": "Level 1 Support customerservice@bluedart.com. Level 2 Grievance Officer regional.head@bluedart.com. Level 3 Nodal Officer nodal.officer@bluedart.com."},
    {"name": "Naukri.com", "domain": "naukri.com", "text": "Level 1 Support support@naukri.com. Level 2 Grievance Officer grievance@naukri.com. Level 3 Nodal Officer nodal@naukri.com."},
    {"name": "LinkedIn", "domain": "linkedin.com", "text": "Level 1 Support help.linkedin.com. Level 2 Grievance Officer legal-india@linkedin.com. Level 3 Nodal Officer nodalofficer-india@linkedin.com."},
    {"name": "Mamaearth", "domain": "mamaearth.in", "text": "Level 1 Support care@mamaearth.in. Level 2 Grievance Officer grievance@mamaearth.in. Level 3 Nodal Officer nodal@mamaearth.in."},
    {"name": "Sugar Cosmetics", "domain": "sugarcosmetics.com", "text": "Level 1 Support hello@sugarcosmetics.com. Level 2 Grievance Officer grievance@sugarcosmetics.com. Level 3 Nodal Officer nodal@sugarcosmetics.com."},
    {"name": "Lenskart", "domain": "lenskart.com", "text": "Level 1 Support support@lenskart.com. Level 2 Grievance Officer grievance@lenskart.com. Level 3 Nodal Officer nodal@lenskart.com."},
    {"name": "Boat Lifestyle", "domain": "boat-lifestyle.com", "text": "Level 1 Support info@imaginemarketingindia.com. Level 2 Grievance Officer grievance.officer@imaginemarketingindia.com. Level 3 Nodal Officer compliance@imaginemarketingindia.com."}
]

# --- FUNCTIONS ---
def process_single_company(company):
    print(f"\n🚀 Processing: {company['name']}")
    raw_text = company['text']
    
    # Delta Filter
    current_hash = hashlib.md5(raw_text.encode('utf-8')).hexdigest()
    try:
        db = supabase.table("corporate_helplines").select("text_hash").eq("domain", company['domain']).execute()
        if db.data and db.data[0].get("text_hash") == current_hash:
            return True
    except: pass

    # AI Mapping
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"Extract structured data from: {raw_text}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text.strip())
        payload = data
        payload.update({"company_name": company['name'], "domain": company['domain'], "text_hash": current_hash, "last_verified_at": datetime.now().isoformat()})
        supabase.table("corporate_helplines").upsert(payload, on_conflict="domain").execute()
        return True
    except Exception as e:
        if "429" in str(e): sys.exit(0)
        return False

if __name__ == "__main__":
    # Runtime limit logic
    queue = TARGET_COMPANIES[:3] if not IS_GITHUB else TARGET_COMPANIES
    
    for company in queue:
        success = process_single_company(company)
        if not success:
            time.sleep(60)
            process_single_company(company)
        time.sleep(SLEEP_TIME)