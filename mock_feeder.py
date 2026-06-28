# -*- coding: utf-8 -*-
import sys
import time
from supabase import create_client, Client

SUPABASE_URL = "https://irqzochxonpasmxsvewa.supabase.co"
SUPABASE_KEY = "sb_publishable_iompK6J4ZsaK7qOCYuw10w_hP4xSb2z"

print("=========================================================")
print("  🚀 HELPLINEHUB - MOCK DATABASE FEEDER RUNNING...")
print("=========================================================")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✔ Supabase Client connection established!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

MOCK_DATA = [
    {
        "company_name": "State Bank of India (SBI)",
        "domain": "sbi.co.in",
        "level_1_phone": "18001234",
        "level_1_email": "customercare@sbi.co.in",
        "level_2_name": "Shri Rajesh Kumar (Nodal Officer)",
        "level_2_phone": "02222741212",
        "level_2_email": "nodal.officer@sbi.co.in",
        "level_3_email": "appellate.authority@sbi.co.in",
        "escalation_details": "Agar Nodal Officer 10 dino mein samadhan na de, toh direct Chairman Office ko escalate karein.",
        "address": "State Bank Bhavan, Madame Cama Road, Nariman Point, Mumbai, Maharashtra 400021"
    },
    {
        "company_name": "Paytm",
        "domain": "paytm.com",
        "level_1_phone": "1800120130",
        "level_1_email": "care@paytm.com",
        "level_2_name": "Mr. Amit Misra (Grievance Head)",
        "level_2_phone": "0120488088",
        "level_2_email": "nodal.officer@paytm.com",
        "level_3_email": "appellate@paytm.com",
        "escalation_details": "Delayed refund ya stuck payments ke case mein 48 hours baad escalate karein.",
        "address": "One 97 Communications Ltd., Tech Zone, Sector 137, Noida, UP 201305"
    }
]

for record in MOCK_DATA:
    try:
        supabase.table("corporate_helplines").upsert({
            "company_name": record["company_name"],
            "domain": record["domain"],
            "level_1_phone": record["level_1_phone"],
            "level_1_email": record["level_1_email"],
            "level_2_name": record["level_2_name"],
            "level_2_phone": record["level_2_phone"],
            "level_2_email": record["level_2_email"],
            "level_3_email": record["level_3_email"],
            "escalation_details": record["escalation_details"],
            "address": record["address"],
            "report_status": "normal",
            "working_votes": 15,
            "broken_votes": 0,
            "last_voted_at": "2026-06-27T12:00:00Z"
        }).execute()
        print(f"  ➔ Sync complete for: {record['company_name']}")
    except Exception as e:
        print(f"  ❌ Error uploading {record['company_name']}: {e}")

print("=========================================================")