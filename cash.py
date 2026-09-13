import requests
import json
import time
import random
import uuid
import urllib3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings()

# ════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APP_BEARER = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzY29wZSI6Im9mZmVycyxzZWFyY2gscHJvZHVjdHMsaGVscGVyIiwiaXNzIjoiaHR0cHM6Ly9jYXNoa2Fyby5jb20vdjEvZjQ4MGE2MGUtNGFjMS00YzYzLWI2ZDItMDkxNDg3MTlkYTExIiwiaWF0IjoxNzg5MjE5NzI3LCJleHAiOjE3ODkyMjE1Mjd9.hdyryq88lR2iGidHLjmCdnTLctfWdCQoNrn9psxLUs4"

PROXY = {
    "http":  "http://305f4eaa9e64c006bde3:c57b6b35b9c05e03@gw.dataimpulse.com:823",
    "https": "http://305f4eaa9e64c006bde3:c57b6b35b9c05e03@gw.dataimpulse.com:823"
}

BASE   = "https://api.cashkaro.com"
CK_API = "https://ckapi.bankkaro.com"
TUT    = "https://tutorial.cashkaro.com"

DEVICE = {
    "deviceID":      "02e8bb5e79084f52",
    "advertisingID": "acae0938-41e9-4225-864c-1fb28466f78c",
    "appVersion":    "4.8",
    "appBuild":      "40063",
    "osVersion":     "9",
    "sdkVersion":    28,
    "countryCode":   "US",
    "networkType":   "wifi",
    "device_brand":  "Redmi",
    "device_model":  "23113RKC6C"
}

FIRST_NAMES = ["Rahul","Amit","Priya","Neha","Rohit","Pooja","Vijay","Ankita",
               "Suresh","Divya","Ravi","Sneha","Ajay","Meena","Karan","Deepak",
               "Sunita","Arun","Kavya","Nitin","Sonia","Manoj","Rekha","Vishal"]
LAST_NAMES  = ["Kumar","Sharma","Singh","Gupta","Verma","Yadav","Mishra",
               "Patel","Shah","Joshi","Tiwari","Pandey","Dubey","Chauhan"]
DOMAINS     = ["gmail.com","yahoo.com","outlook.com","hotmail.com"]

# States
PHONE, OTP = range(2)

# ════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════
def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def random_email(name):
    clean = name.lower().replace(" ", "")
    return f"{clean}{random.randint(100,9999)}@{random.choice(DOMAINS)}"

def random_app_instance():
    return uuid.uuid4().hex + uuid.uuid4().hex[:8]

def new_session():
    s = requests.Session()
    s.proxies.update(PROXY)
    s.verify = False
    return s

def plain_session():
    s = requests.Session()
    s.verify = False
    return s

def api_h():
    return {
        "accept":               "application/vnd.api+json",
        "Accept-Encoding":      "gzip",
        "authorization":        f"Bearer {APP_BEARER}",
        "Connection":           "Keep-Alive",
        "Content-Type":         "application/vnd.api+json",
        "Host":                 "api.cashkaro.com",
        "User-Agent":           "okhttp/4.12.0",
        "x-api-key":            "",
        "x-chkr-app":           json.dumps(DEVICE, separators=(',',':')),
        "x-chkr-app-platform":  "Android",
        "x-chkr-app-version":   "4.8",
        "x-pps-appcheck":       "",
        "x-user-agent":         "Mozilla/5.0 (Linux; Android 9; 23113RKC6C Build/PQ3B.190801.07131748; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Safari/537.36"
    }

def tut_h():
    return {
        "Accept":             "*/*",
        "Accept-Encoding":    "gzip, deflate, br, zstd",
        "Accept-Language":    "en-US,en;q=0.9",
        "Connection":         "keep-alive",
        "Content-Type":       "application/json",
        "Host":               "ckapi.bankkaro.com",
        "Origin":             TUT,
        "Referer":            f"{TUT}/",
        "sec-ch-ua":          '"Chromium";v="124", "Android WebView";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile":   "?0",
        "sec-ch-ua-platform": '"Android"',
        "Sec-Fetch-Dest":     "empty",
        "Sec-Fetch-Mode":     "cors",
        "Sec-Fetch-Site":     "cross-site",
        "User-Agent":         "Mozilla/5.0 (Linux; Android 9; 23113RKC6C Build/PQ3B.190801.07131748; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Safari/537.36",
        "X-Requested-With":   "com.cashkaro"
    }

# ════════════════════════════════════════════════════
#  ACCOUNT CREATION
# ════════════════════════════════════════════════════
def is_registered(s, phone):
    try:
        r = s.post(f"{BASE}/v1/loginotp?device=App",
            headers=api_h(),
            json={"data": {"type": "user_otp",
                           "attributes": {"mobile_number": int(phone)}}},
            timeout=15)
        if r.status_code == 422:
            detail = (r.json().get("errors") or [{}])[0].get("detail","")
            return "not registered" not in detail.lower()
        return r.status_code in (200, 201)
    except:
        return False

def send_otp(s, phone):
    r = s.post(f"{BASE}/v1/signupotp",
        headers=api_h(),
        json={"data": {"type": "user_otp",
                       "attributes": {"mobile_number": int(phone)}}},
        timeout=15)
    if r.status_code != 201:
        raise Exception(f"OTP send fail {r.status_code}: {r.text}")
    otp_guid = r.json()["data"]["id"]
    return otp_guid

def verify_otp(s, phone, otp, otp_guid):
    r = s.post(f"{BASE}/v1/verifysignupotp?device=App",
        headers=api_h(),
        json={"data": {"type": "user_otp",
                       "attributes": {
                           "mobile_number": int(phone),
                           "otp_guid":      otp_guid,
                           "otp":           str(otp)
                       }}},
        timeout=15)
    if r.status_code != 200:
        raise Exception(f"OTP verify fail {r.status_code}: {r.text}")

def signup(s, phone, name, email, otp_guid):
    r = s.post(f"{BASE}/v1/signupV1?device=App",
        headers=api_h(),
        json={"data": {"type": "auth",
                       "attributes": {
                           "fullname":      name,
                           "email":         email,
                           "mobile_number": int(phone),
                           "otp_guid":      otp_guid,
                           "ip_address":    "172.16.1.15",
                           "device_info": {
                               "fcm_id":            "c8qgdvG8S-qbdVl3fiM-Zg:APA91bHCXlGlIUgUpQ93Lev6bWLNoWekft4OCq1RqNy6PZUZTzRQ_EZpfgbRaT1hjwrQh0F2Mwot7Bwjx8MLm6TkLs_dJaGLvYpZrEPNcQdlh-Dnvvk8H70",
                               "device_unique_id":  "02e8bb5e79084f52",
                               "imei_number":       "none",
                               "advertising_id":    "acae0938-41e9-4225-864c-1fb28466f78c",
                               "device_brand":      "Redmi",
                               "device_model":      "23113RKC6C",
                               "device_client":     "Android",
                               "app_version":       "4.8",
                               "app_version_code":  "40063-",
                               "os_name":           "Android",
                               "os_version":        "9",
                               "device_country":    "US",
                               "latitude":          "0.00000000",
                               "longitude":         "0.00000000",
                               "language":          "en-US",
                               "network_type":      "wifi",
                               "screen_resolution": "hdpi",
                               "screen_density":    "240dpi",
                               "screen_height":     "1600px",
                               "screen_width":      "900px",
                               "app_instance_id":   random_app_instance()
                           }
                       }}},
        timeout=15)
    if r.status_code not in (200, 201):
        raise Exception(f"Signup fail {r.status_code}: {r.text}")
    resp    = r.json()
    user_id = str(resp["data"]["id"])
    u_token = resp["data"]["attributes"].get("access_token","")
    return user_id, u_token

# ════════════════════════════════════════════════════
#  TUTORIAL
# ════════════════════════════════════════════════════
def get_exit(cs, user_id):
    r = cs.get(f"{CK_API}/ckmock/api/users/get-exit/{user_id}",
        headers=tut_h(), timeout=20)
    resp = r.json()
    exit_id  = resp["exit_id"]
    click_id = resp["click_id"]
    return exit_id, click_id

def tut_register(cs, user_id, exit_id, click_id):
    cs.post(f"{CK_API}/ckmock/api/users/register",
        json={
            "user_id":  str(user_id),
            "exit_id":  exit_id,
            "click_id": click_id
        },
        headers=tut_h(), timeout=20)

    cs.post(f"{CK_API}/ckmock/api/register",
        json={
            "ck_id": str(user_id),
            "os":    "Android"
        },
        headers=tut_h(), timeout=20)

def add_event(cs, user_id, exit_id, click_id, event_name, completed=False):
    body = {
        "click_id": click_id,
        "events": [{
            "event_name": event_name,
            "path_name":  "tutorial.cashkaro.com/k",
            "user_id":    str(user_id)
        }],
        "exit_id":  exit_id,
        "user_id":  str(user_id)
    }
    if completed:
        body["completed"] = True
    r = cs.post(f"{CK_API}/ckmock/api/users/addEvent",
        json=body, headers=tut_h(), timeout=20)
    resp = r.json()
    return resp.get("postback", False)

def complete_tutorial(cs, user_id, exit_id, click_id):
    add_event(cs, user_id, exit_id, click_id, "ck_tutorial_start")
    time.sleep(random.uniform(1.5, 2.5))

    add_event(cs, user_id, exit_id, click_id, "flipkart_store_click_forward_button")
    time.sleep(random.uniform(1.5, 2.5))

    add_event(cs, user_id, exit_id, click_id, "flipkart_store_cta_forward_button")
    time.sleep(random.uniform(1.5, 2.5))

    add_event(cs, user_id, exit_id, click_id, "my_earnings_cta_forward_button")
    time.sleep(random.uniform(1.5, 2.5))

    add_event(cs, user_id, exit_id, click_id, "req_payment_page_forward_button")
    time.sleep(random.uniform(1.5, 2.5))

    pb = add_event(cs, user_id, exit_id, click_id, "ck_tutorial_complete", completed=True)
    return pb

# ════════════════════════════════════════════════════
#  MAIN RUNNER
# ════════════════════════════════════════════════════
def run(phone):
    s  = new_session()
    cs = plain_session()

    name  = random_name()
    email = random_email(name)

    status_msg = f"\n{'═'*50}\n  📱 {phone}\n  👤 {name}  |  📧 {email}\n{'═'*50}\n"

    if is_registered(s, phone):
        return {
            "phone": phone,
            "status": "⛔ already registered",
            "message": status_msg + "⛔ Already registered — skip"
        }

    otp_guid = send_otp(s, phone)
    
    return {
        "phone": phone,
        "name": name,
        "email": email,
        "otp_guid": otp_guid,
        "s": s,
        "cs": cs,
        "status": "pending_otp",
        "message": status_msg + "✅ OTP sent! Enter OTP below:"
    }

def verify_and_complete(phone, otp, otp_guid, s, cs, name, email):
    try:
        verify_otp(s, phone, otp, otp_guid)
        
        user_id, u_token = signup(s, phone, name, email, otp_guid)
        
        time.sleep(2)
        
        exit_id, click_id = get_exit(cs, user_id)
        tut_register(cs, user_id, exit_id, click_id)
        
        time.sleep(1)
        
        postback = complete_tutorial(cs, user_id, exit_id, click_id)
        
        if postback:
            return {
                "phone": phone,
                "user_id": user_id,
                "status": "✅ 15rs",
                "message": "💰 15rs CREDITED! ✅"
            }
        else:
            return {
                "phone": phone,
                "user_id": user_id,
                "status": "⚠️ check karo",
                "message": "⚠️ postback false — manually check karo"
            }
    except Exception as e:
        return {
            "phone": phone,
            "status": f"❌ {e}",
            "message": f"❌ Error: {e}"
        }

# ════════════════════════════════════════════════════
#  TELEGRAM HANDLERS
# ════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    reply_keyboard = [["🚀 Start Process"]]
    await update.message.reply_text(
        "╔══════════════════════════════════════════════╗\n"
        "║        CashKaro 15rs Bot  🖤                 ║\n"
        "║      Click button to proceed                 ║\n"
        "╚══════════════════════════════════════════════╝\n\n"
        "This bot will create CashKaro accounts and credit 15rs automatically.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for phone number"""
    if update.message.text == "🚀 Start Process":
        await update.message.reply_text(
            "📱 Enter phone number (10 digits):",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHONE
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input"""
    phone = update.message.text.strip()
    
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid phone number. Please enter 10 digits.")
        return PHONE
    
    await update.message.reply_text("⏳ Processing... sending OTP...")
    
    try:
        result = run(phone)
        context.user_data['result'] = result
        
        if result['status'] == "pending_otp":
            await update.message.reply_text(result['message'])
            return OTP
        else:
            await update.message.reply_text(result['message'])
            reply_keyboard = [["✅ Continue"], ["❌ Exit"]]
            await update.message.reply_text(
                "Do you want to process another number?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )
            return PHONE
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return PHONE

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP input"""
    otp = update.message.text.strip()
    result = context.user_data.get('result', {})
    
    if not otp.isdigit():
        await update.message.reply_text("❌ Invalid OTP. Please enter digits only.")
        return OTP
    
    await update.message.reply_text("⏳ Verifying OTP and completing tutorial...")
    
    try:
        final_result = verify_and_complete(
            result['phone'],
            otp,
            result['otp_guid'],
            result['s'],
            result['cs'],
            result['name'],
            result['email']
        )
        
        await update.message.reply_text(final_result['message'])
        
        reply_keyboard = [["✅ Continue"], ["❌ Exit"]]
        await update.message.reply_text(
            "📊 RESULT:\n"
            f"  Status: {final_result['status']}\n"
            f"  Phone: {final_result['phone']}\n"
            f"  UID: {final_result.get('user_id', '—')}\n\n"
            "Do you want to process another number?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return PHONE
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return PHONE

async def handle_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle continue or exit"""
    if update.message.text == "✅ Continue":
        await update.message.reply_text(
            "📱 Enter phone number (10 digits):",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHONE
    else:
        reply_keyboard = [["🚀 Start Process"]]
        await update.message.reply_text(
            "Bye! Click the button to start again.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return PHONE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("Cancelled!")
    return ConversationHandler.END

# ════════════════════════════════════════════════════
#  MAIN BOT
# ════════════════════════════════════════════════════
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone),
                MessageHandler(filters.Regex("^(✅ Continue|❌ Exit)$"), handle_continue),
                MessageHandler(filters.Regex("^🚀 Start Process$"), ask_phone),
            ],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
