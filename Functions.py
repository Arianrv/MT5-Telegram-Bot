import re, os
import json
import logging
from dotenv import load_dotenv


# -----------------------  Opening json files  -------------------------------------------------------------------------
def load_json_file(filename, default_config=None):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        print(f"[logging] Error loading {filename}: {e}")

        if default_config:
            save_config(default_config, filename)
            print(f"Created a new {filename} with default settings.")

        return default_config


# Default configuration for Groups_Channels.json
default_Groups_Channels = {
    "Channel_VIP": -1002492704221,
    "group_username_or_id": -1002360624534,
    "control_channel": -1002250962179,
    "in_Group": -1002275397314,
    "Target_channel": -1002400467674
}

# Load Groups_Channels.json
config_GC = load_json_file('Groups_Channels.json', default_Groups_Channels)

# Default configuration for prices.json
default_prices_config = {
    "دلار": {"price": 95000, "state": "on", "tolerance": 60},
    "یورو": {"price": 100000, "state": "on", "tolerance": 60},
    "comma_format": False,
    "change_threshold": 20,
    "fetching_messages": True
}

# Load prices.json
config_states = load_json_file('prices.json', default_prices_config)

# -----------------------  Load environment variables  -----------------------------------------------------------------
import json

CONFIG_FILE = "prices.json"

DEFAULT_CONFIG = {
    "دلار": {"price": 95000, "state": "on", "tolerance": 55},
    "یورو": {"price": 95000, "state": "on", "tolerance": 56},
    "comma_format": False,
    "change_threshold": 25,
    "fetching_messages": True,
    "bubble_hd_vip": 0,
    "bubble_he_vip": 0
}


def load_config():
    """Load configuration from JSON and ensure all keys exist."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        config = DEFAULT_CONFIG.copy()  # Use defaults if file is missing/corrupt
        save_config(config)  # Save default config

    # Ensure all keys exist in config
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = default_value

    return config


def save_config(config):
    try:
        with open("prices.json", "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
        print("[DEBUG] Successfully saved config!")
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")


# -----------------------  Load environment variables  -----------------------------------------------------------------
load_dotenv("api.env")

# -----------------------  Load Tokens, Channels' and Groups' id  ------------------------------------------------------
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')
bot_token = os.getenv('bot_token')
report_bot = os.getenv('report_bot')
in_Group = config_GC['in_Group']
Channel_VIP = config_GC['Channel_VIP']
Target_channel = config_GC['Target_channel']
control_channel = config_GC['control_channel']
change_threshold = config_states.get("change_threshold", 20)
fetching_messages = config_states.get("fetching_messages", True)
config = config_states
session_file = f"session_{int(api_id)}"

# ----------------------   Load save prices, tolerances and states  ----------------------------------------------------
try:
    last_price_d = config_states.get("دلار", {}).get("price", 90000)
    last_price_e = config_states.get("یورو", {}).get("price", 95000)
    tolerance_d = config_states.get("دلار", {}).get("tolerance", 50)
    tolerance_e = config_states.get("یورو", {}).get("tolerance", 50)

    comma_format = config_states.get("comma_format", False)
    d_state = True if config_states["دلار"]["state"] == "on" else False
    e_state = True if config_states["یورو"]["state"] == "on" else False
    bubble_adjustments = {
        "hd_vip": config_states.get("hd_vip", 0),
        "he_vip": config_states.get("he_vip", 0)
    }
except Exception as e:
    print(f"[Loading states] Failed to catch : {e}")

# ----------------------  Process Messages from input group  -----------------------------------------------------------
in_Group_msg_map = {
    'خپ': 'دلار خپ',
    'فپ': 'دلار فپ',
    'پس': 'دلار مع پسفردا',
    'خی': 'یورو خف',
    'فی': 'یورو فف',
    'ی': 'یورو مع فردا',
    'نف': 'دلار ف نقدی',
    'نخ': 'دلار خ نقدی',
    'نم': 'دلار مع نقدی',
    'خ': 'دلار خف',
    'ف': 'دلار فف',
    'مع': 'دلار مع فردا'
}


# ----------------------  Extract number from text in VIP Channel  -----------------------------------------------------
def extract_number_from_text(line):
    match = re.search(r'\d+', line)
    return int(match.group()) if match else None


# ----------------------  Process Messages from VIP Channel  -----------------------------------------------------------
def modify_message(text):
    modified_lines = []
    for line in text.split("\n"):
        number = extract_number_from_text(line)

        if number:
            if '💵' in line and 'دلار' in line:
                if 'نقدی' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" دلار مع نقدی {number}")
                    elif 'خریدار' in line:
                        modified_lines.append(f" دلار خ نقدی {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" دلار ف نقدی {number}")
                elif 'پسفردا' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" دلار مع پسفردا {number}")
                    elif 'خریدار' in line and '🔵' in line:
                        modified_lines.append(f" دلار خپ {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" دلار فپ {number}")
                elif 'فردا' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" دلار مع فردا {number}")
                    elif 'خریدار' in line and '🔵' in line:
                        modified_lines.append(f" دلار خف {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" دلار فف {number}")

            elif '💶' in line and 'یورو' in line:
                if 'نقدی' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" 💶یورو مع نقدی {number}")
                    elif 'خریدار' in line and '🔵' in line:
                        modified_lines.append(f" 💶یورو خ نقدی {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" 💶یورو ف نقدی {number}")
                elif 'پسفردا' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" 💶یورو مع پسفردا {number}")
                    elif 'خریدار' in line and '🔵' in line:
                        modified_lines.append(f" 💶یورو خپ {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" 💶یورو فپ {number}")
                elif 'فردا' in line:
                    if 'معامله' in line and '✅' in line:
                        modified_lines.append(f" 💶یورو مع فردا {number}")
                    elif 'خریدار' in line and '🔵' in line:
                        modified_lines.append(f" 💶یورو خف {number}")
                    elif 'فروشنده' in line and '🔴' in line:
                        modified_lines.append(f" 💶یورو فف {number}")

    return "\n".join(modified_lines) if modified_lines else None


# ----------------------  Show Command background ----------------------------------------------------------------------
# Modify the show_table function to properly reflect the Euro tolerance

def show_table():
    config = load_config()

    def to_persian(val):
        return convert_english_to_persian(str(val))

    def status_text(state):
        return "روشن ✅" if state else "خاموش ❌"

    def range_line(price, tol):
        return f"{to_persian(price + tol)} - {to_persian(price - tol)}"

    dollar = config.get("دلار", {})
    euro = config.get("یورو", {})

    # Dollar Prices
    d_f = dollar.get("price_farda", 90000)
    d_n = dollar.get("price_naghdi", 90000)
    d_p = dollar.get("price_pasfarda", 90000)

    # Euro Prices
    e_f = euro.get("price_farda", 95000)
    e_n = euro.get("price_naghdi", 95000)
    e_p = euro.get("price_pasfarda", 95000)

    # Tolerances
    t_d_f = dollar.get("tolerance", 50)
    t_d_n = dollar.get("T_Naghdi", 50)
    t_d_p = dollar.get("T_pasfarda", 50)
    t_e = euro.get("tolerance", 50)

    # States
    s_d = dollar.get("state", "off") == "on"
    s_e = euro.get("state", "off") == "on"
    dx = config.get("dx_tolerance_state", False)
    dn = config.get("dn_tolerance_state", False)
    dp = config.get("dp_tolerance_state", False)
    ex = config.get("ex_tolerance_state", False)

    # Bubbles
    def get_bubble(k):
        val = config.get(k, 0)
        return to_persian(str(abs(val))) + ("-" if val < 0 else "")

    # Toggles
    fetching = config.get("fetching_messages", False)
    comma = config.get("comma_format", False)
    threshold = to_persian(config.get("change_threshold", 25))

    return f"""
📌 وضعیت:
    💵 دلار:
       🔹 وضعیت: {status_text(s_d)}
       🔹 قیمت‌ها:
         فردایی:     {to_persian(d_f)} 
           ⤶ محدوده: {range_line(d_f, t_d_f)}
         نقدی:     {to_persian(d_n)}
           ⤶ محدوده: {range_line(d_n, t_d_n)}
         پس‌فردا:  {to_persian(d_p)}
           ⤶ محدوده: {range_line(d_p, t_d_p)}

       🔸 تلورانس فردا:  ⇦ ({to_persian(t_d_f)})
       🔸 تلورانس نقدی:   ⇦ ({to_persian(t_d_n)})
       🔸 تلورانس پس‌فردا:  ⇦ ({to_persian(t_d_p)})

    💶 یورو:
       🔹 وضعیت: {status_text(s_e)}
       🔹 قیمت‌ها:
         فردایی:     {to_persian(e_f)}
           ⤶ محدوده: {range_line(e_f, t_e)}
         نقدی:     {to_persian(e_n)}
           ⤶ محدوده: {range_line(e_n, t_e)}
         پس‌فردا:  {to_persian(e_p)}
           ⤶ محدوده: {range_line(e_p, t_e)}       
       🔸 تلورانس کلی:   ({to_persian(t_e)})

    🧼  وضعیت حباب ها:
       🔹 دلار فردا:     {get_bubble("bubble_hd_farda")}
       🔹 دلار نقدی:     {get_bubble("bubble_hd_naghdi")}
       🔹 دلار پس‌فردا:  {get_bubble("bubble_hd_pasfarda")}
       🔸 یورو فردا:     {get_bubble("bubble_he_farda")}
       🔸 یورو نقدی:     {get_bubble("bubble_he_naghdi")}
       🔸 یورو پس‌فردا:  {get_bubble("bubble_he_pasfarda")}

    ⚙️ تنظیمات:
       🔸 دریافت VIP: {status_text(fetching)}
       🔸 درصد تغییر XX: {threshold}
       🔸 کاما: {status_text(comma)}
       .
""".strip()


# ----------------------   Number En/Fa Conversations  -----------------------------------------------------------------
def convert_persian_to_english(text):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    translation_table = str.maketrans(persian_digits, english_digits)
    return text.translate(translation_table)


def convert_english_to_persian(text):
    english_digits = "0123456789"
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(english_digits, persian_digits)
    return text.translate(translation_table)


# ----------------------  Save Configuration  --------------------------------------------------------------------------
def save_config(config_states):
    with open("prices.json", "w", encoding="utf-8") as file:
        json.dump(config_states, file, ensure_ascii=False, indent=4)


# ----------------------  Get sender's name  ---------------------------------------------------------------------------
async def get_sender_name(event):
    sender = await event.get_sender()  # Get the sender's information
    if sender.username:
        return f"@{sender.username}"
    elif sender.first_name:
        return sender.first_name
    else:
        return "User"


# ----------------------  Help command  --------------------------------------------------------------------------------
help_text = """
<b>📌 راهنمای دستورات ربات</b>

<b>🛠 دستورات نمایش وضعیت:</b>
🔹 <code>show</code> ➖ نمایش وضعیت قیمت ها  
🔹 <code>ping</code> ➖ بررسی سرعت پاسخگویی ربات  
🔹 <code>restart</code> ➖ ری‌استارت کردن ربات  

<b>💵 دستورات قیمت گذاری:</b>
🔹 <code>d=XXXXX</code> ➖ تنظیم قیمت مستقیم دلار  
🔸 <code>e=XXXXX</code> ➖ تنظیم قیمت مستقیم یورو    

<b>📊 مدیریت تلرانس ها :</b>
🔹 <code>dn X</code> ➖ تلورانس دلار نقدی 
🔹 <code>dx X</code> ➖ تلورانس دلار فردایی 
🔹 <code>dp X</code> ➖ تلورانس دلار پس فردایی 
🔸 <code>ex X</code> ➖ تغییر تلورانس یورو 
🔸 <code>xx X</code> ➖ تنظیم حد تغییر قیمت مستقیم 

<b>🧼 دستورات حباب برای کانال VIP:</b>
🔹 <code>hd n X</code> ➖ تنظیم حباب برای دلار نقدی
🔹 <code>hd f X</code> ➖ تنظیم حباب برای دلار فردایی
🔹 <code>hd p X</code> ➖ تنظیم حباب برای دلار پس فردایی
🔸 <code>he vip X</code> ➖ تنظیم حباب برای یورو

<b>🔄 کنترل وضعیت ارز ها:</b>
🔹 <code>d on</code> ➖ فعال کردن دریافت دلار  
🔹 <code>d off</code> ➖ غیرفعال کردن دریافت دلار  
🔸 <code>e on</code> ➖ فعال کردن دریافت یورو  
🔸 <code>e off</code> ➖ غیرفعال کردن دریافت یورو  

<b>📡 مدیریت دریافت لفظ‌های کانال VIP:</b>
🔹 <code>vip on</code> ➖ روشن کردن دریافت لفظ‌ها از کانال VIP  
🔹 <code>vip off</code> ➖ خاموش کردن دریافت لفظ‌ها از کانال VIP  

<b>🔢 تنظیمات نمایش عددی:</b>
🔹 <code>comma on</code> ➖ فعال کردن نمایش اعداد با کاما (۹۴,۵۰۰)  
🔹 <code>comma off</code> ➖ غیرفعال کردن نمایش اعداد با کاما (۹۴۵۰۰)  


⚠️ <i>نکته:</i> در دستورات بالا منظور از X، <b>عدد</b> است.
"""


# ------------------------- calculate ranges -------------------------------------------------------------------
def calculate_ranges(config):
    try:
        # Ensure that the keys exist in the config
        if "دلار" not in config or "price" not in config["دلار"] or "tolerance" not in config["دلار"]:
            raise KeyError("Missing price or tolerance in دلار")
        if "یورو" not in config or "price" not in config["یورو"] or "tolerance" not in config["یورو"]:
            raise KeyError("Missing price or tolerance in یورو")

        last_price_d = config["دلار"]["price"]
        last_price_e = config["یورو"]["price"]
        tolerance_d = config["دلار"]["tolerance"]
        tolerance_e = config["یورو"]["tolerance"]

        dollar_min = max(0, last_price_d - tolerance_d)
        dollar_max = last_price_d + tolerance_d
        euro_min = max(0, last_price_e - tolerance_e)
        euro_max = last_price_e + tolerance_e

        range_dollar = f"{dollar_max} - {dollar_min}"
        range_euro = f"{euro_max} - {euro_min}"

        return range_dollar, range_euro, dollar_min, dollar_max, euro_min, euro_max
    except KeyError as e:
        print(f"[Error] Missing key in config: {e}")
        return "0 - 0", "0 - 0", 0, 0, 0, 0

