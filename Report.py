import os
import json
import logging
import jdatetime
import re
from pytz import timezone
from telethon import TelegramClient, events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from Functions import api_id, api_hash, report_bot, Target_channel, control_channel

# -------------------- CONFIGURATION --------------------
SESSION_NAME = "report_bot"
TARGET_CHANNEL = Target_channel
TIMEZONE = timezone("Asia/Tehran")
JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_prices.json")

# -------------------- LOGGING --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("report_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"📂 Using data file: {JSON_FILE}")

# -------------------- TELEGRAM CLIENT --------------------
client = TelegramClient(SESSION_NAME, api_id, api_hash)
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# -------------------- STATE --------------------
minute_report_enabled = True

# -------------------- UTILITIES --------------------
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("🗂 daily_prices.json updated.")

def get_today_key():
    return jdatetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_persian_date():
    date = jdatetime.datetime.now(TIMEZONE)
    return f"{date.day} {date.j_months_fa[date.month - 1]} {date.year}"

def get_current_hour():
    return jdatetime.datetime.now(TIMEZONE).strftime("%H")

def extract_number(text):
    match = re.search(r"(\d{4,6})", text.replace(",", ""))
    return int(match.group(1)) if match else None

def update_price(data, currency, price):
    today = get_today_key()
    hour = get_current_hour()

    if today not in data:
        data[today] = {}
    if currency not in data[today]:
        data[today][currency] = {
            "first_price": price,
            "highest_price": price,
            "lowest_price": price,
            "last_price_until_now": price,
            "hours": {hour: {"first": price, "high": price, "low": price, "last": price}}
        }
        save_data(data)
        logger.info(f"🗂 Saved new currency structure for {currency} with first price {price}")
        return

    c_data = data[today][currency]
    c_data["highest_price"] = max(price, c_data["highest_price"])
    c_data["lowest_price"] = min(price, c_data["lowest_price"])
    c_data["last_price_until_now"] = price

    if hour not in c_data["hours"]:
        c_data["hours"][hour] = {"first": price, "high": price, "low": price, "last": price}
    else:
        h = c_data["hours"][hour]
        h["high"] = max(price, h["high"])
        h["low"] = min(price, h["low"])
        h["last"] = price

    save_data(data)
    logger.info(f"🗂 Saved updated price for {currency}: {price}")

# -------------------- TELEGRAM HANDLER --------------------
@client.on(events.NewMessage(chats=TARGET_CHANNEL))
async def handle_price(event):
    logger.info(f"📥 New message received: {event.raw_text}")
    try:
        msg = event.raw_text.replace("‌", "")
        if "مع" not in msg:
            logger.info("⛔ Skipped: no 'مع'")
            return

        if "نقدی" in msg:
            mode = "نقدی"
        elif "پسفردا" in msg or "پس‌فردا" in msg:
            mode = "پس‌فردایی"
        else:
            mode = "فردایی"

        if "دلار" in msg:
            currency = f"دلار {mode} مع"
        elif "یورو" in msg:
            currency = f"یورو {mode} مع"
        else:
            logger.info("⛔ Skipped: unrecognized currency")
            return

        number = extract_number(msg)
        if number:
            data = load_data()
            update_price(data, currency, number)
            logger.info(f"✅ New price recorded for {currency}: {number}")

    except Exception as e:
        logger.error(f"❌ Error handling message: {e}")

# -------------------- REPORT HELPERS --------------------
def generate_report(data, today, hour=None, label=""):
    message = f"\n{label} — {get_persian_date()}\n"
    currency_keys = [
        "دلار فردایی مع", "دلار نقدی مع", "دلار پس‌فردایی مع",
        "یورو فردایی مع", "یورو نقدی مع", "یورو پس‌فردایی مع"
    ]
    added = False
    for currency in currency_keys:
        c = data[today].get(currency)
        if not c:
            continue
        if hour:
            if hour not in c["hours"]:
                continue
            h = c["hours"][hour]
            high = h["high"]
            low = h["low"]
            last = c["last_price_until_now"]
            fluctuation = high - low
            percentage = (fluctuation / low) * 100 if low else 0
            trend_emoji = "⚖️" if fluctuation == 0 else ("🔺" if fluctuation > 0 else "🔻")
            currency_icon = "💲" if "دلار" in currency else "💶"
            message += (
                f"\n{currency_icon} {currency}\n"
                f"⏫ بالاترین: {high:,}\n"
                f"⏬ پایین‌ترین: {low:,}\n"
                f" ."
            )
        else:
            first = c["first_price"]
            last = c["last_price_until_now"]
            fluctuation = last - first
            percentage = (fluctuation / first) * 100 if first else 0
            sign = "+" if fluctuation >= 0 else "-"
            trend_emoji = "⚖️" if fluctuation == 0 else ("🔺" if fluctuation > 0 else "🔻")
            currency_icon = "💲" if "دلار" in currency else "💶"
            message += (
                f"\n{currency_icon} {currency}\n"
                f"📈 اولین قیمت: {first:,}\n"
                f"📉 آخرین قیمت: {last:,}\n"
                f"⏫ بالاترین: {c['highest_price']:,}\n"
                f"⏬ پایین‌ترین: {c['lowest_price']:,}\n"
                f"{trend_emoji} نوسان کل: {sign}{abs(fluctuation):,} تومان\n"
                f"{trend_emoji} درصد تغییر: {sign}{abs(percentage):.1f}%\n"
            )
        added = True

    return message.strip() if added else None

# -------------------- MINUTE REPORT --------------------
async def send_minute_report():
    global minute_report_enabled
    if not minute_report_enabled:
        return
    data = load_data()
    today = get_today_key()
    hour = get_current_hour()
    if today not in data:
        return
    label = f"⏱️ گزارش دقیقه‌ای ({hour}:{jdatetime.datetime.now(TIMEZONE).minute:02})"
    message = generate_report(data, today, hour, label=label)
    if message:
        await client.send_message(TARGET_CHANNEL, message)

# -------------------- HOURLY REPORT --------------------
async def send_hourly_report():
    data = load_data()
    today = get_today_key()
    current_jdt = jdatetime.datetime.now(TIMEZONE)
    previous_hour = (current_jdt.hour - 1) % 24
    hour_str = f"{previous_hour:02}"
    if today not in data:
        return
    label = f"🕒 گزارش ساعتی ({hour_str}:00 - {current_jdt.hour:02}:00)"
    message = generate_report(data, today, hour_str, label=label)
    if message:
        await client.send_message(TARGET_CHANNEL, message)

# -------------------- FINAL REPORT --------------------
async def send_final_report():
    data = load_data()
    today = get_today_key()
    if today not in data:
        return
    message = generate_report(data, today, label="📊 گزارش نهایی روز")
    if message:
        await client.send_message(TARGET_CHANNEL, message)

# -------------------- DAILY CLEAR --------------------
async def clear_daily_data():
    data = load_data()
    today = get_today_key()
    if today in data:
        del data[today]
        save_data(data)
        logger.info("✅ Cleared daily price data at midnight")

# -------------------- MANUAL REPORT + TOGGLES --------------------
@client.on(events.NewMessage(chats=control_channel))
async def handle_control_commands(event):
    global minute_report_enabled
    text = event.raw_text.strip().lower()

    if text == "report":
        data = load_data()
        today = get_today_key()
        if today not in data:
            await event.reply("📭 داده‌ای برای امروز یافت نشد.")
            return
        message = generate_report(data, today, label="🕒 گزارش تا به این لحظه")
        if message:
            await event.reply(message)
"""
    elif text == "minrep on":
        minute_report_enabled = True
        await event.reply("✅ گزارش دقیقه‌ای فعال شد")

    elif text == "minrep off":
        minute_report_enabled = False
        await event.reply("❌ گزارش دقیقه‌ای غیرفعال شد")
"""
# -------------------- SCHEDULER --------------------
# scheduler.add_job(send_minute_report, "cron", second=0)
scheduler.add_job(send_hourly_report, "cron", hour="9-21", minute=0)
scheduler.add_job(send_final_report, "cron", hour=23, minute=0)
scheduler.add_job(clear_daily_data, "cron", hour=23, minute=58)

# -------------------- MAIN --------------------
async def main():
    await client.start(bot_token=report_bot)
    scheduler.start()
    logger.info("📈 Reporter Bot is running...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
