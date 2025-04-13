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

# -------------------- UTILITIES --------------------
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("💾 daily_prices.json updated.")

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
        logger.info(f"💾 Saved new currency structure for {currency} with first price {price}")
        return

    c_data = data[today][currency]

    # Daily summary
    if "first_price" not in c_data:
        c_data["first_price"] = price
    c_data["highest_price"] = max(price, c_data["highest_price"])
    c_data["lowest_price"] = min(price, c_data["lowest_price"])
    c_data["last_price_until_now"] = price

    # Hourly summary
    if hour not in c_data["hours"]:
        c_data["hours"][hour] = {"first": price, "high": price, "low": price, "last": price}
    else:
        h = c_data["hours"][hour]
        h["high"] = max(price, h["high"])
        h["low"] = min(price, h["low"])
        h["last"] = price

    save_data(data)
    logger.info(f"💾 Saved updated price for {currency}: {price}")

# -------------------- TELEGRAM HANDLER --------------------
@client.on(events.NewMessage(chats=TARGET_CHANNEL))
async def handle_price(event):
    logger.info(f"📥 New message received: {event.raw_text}")
    try:
        msg = event.raw_text
        data = load_data()

        if "دلار" in msg:
            number = extract_number(msg)
            if number:
                update_price(data, "دلار", number)
                logger.info(f"✅ New price recorded for دلار: {number}")

        elif "یورو" in msg:
            number = extract_number(msg)
            if number:
                update_price(data, "یورو", number)
                logger.info(f"✅ New price recorded for یورو: {number}")

    except Exception as e:
        logger.error(f"❌ Error handling message: {e}")

# -------------------- REPORT FUNCTIONS --------------------
async def send_hourly_report():
    data = load_data()
    today = get_today_key()
    hour = get_current_hour()
    date_fa = get_persian_date()

    if today not in data:
        return

    message = f"\n🕒 گزارش ساعتی ({hour}‌:00) — {date_fa}\n"
    for currency in ["دلار", "یورو"]:
        c = data[today].get(currency)
        if not c or hour not in c["hours"]:
            continue
        if hour in c["hours"]:
            h = c["hours"][hour]
        else:
            logger.warning(f"No data for hour {hour} in {currency}")
            continue
        fluctuation = h["last"] - h["first"]
        sign = "-" if fluctuation < 0 else "+"
        fluctuation_abs = abs(fluctuation)
        message += (
            f"\n💱 {currency}\n"
            f"📈️️ اولین: {h['first']:,}\n"
            f"🔺️️ بالاترین: {h['high']:,}\n"
            f"🔻️ پایین‌ترین: {h['low']:,}\n"
            f"📉️️ آخرین: {h['last']:,}\n"
            f"📊️ نوسان: {fluctuation_abs:,}{sign} تومان\n"
        )

    await client.send_message(TARGET_CHANNEL, message.strip())

async def send_final_report():
    data = load_data()
    today = get_today_key()
    date_fa = get_persian_date()

    if today not in data:
        return

    message = f"📊 گزارش نهایی روز — {date_fa}\n"
    for currency in ["دلار", "یورو"]:
        c = data[today].get(currency)
        if not c:
            continue
        fluctuation = c["last_price_until_now"] - c["first_price"]
        sign = "-" if fluctuation < 0 else "+"
        fluctuation_abs = abs(fluctuation)

        message += (
            f"\n💱 {currency}\n"
            f"▫📈️ اولین قیمت: {c['first_price']:,}\n"
            f"📉️️ آخرین قیمت: {c['last_price_until_now']:,}\n"
            f"🔺️️ بالاترین: {c['highest_price']:,}\n"
            f"🔻️ پایین‌ترین: {c['lowest_price']:,}\n"
            f"📊️ نوسان کل: {fluctuation_abs:,}{sign} تومان\n"
        )

    await client.send_message(TARGET_CHANNEL, message.strip())

async def clear_daily_data():
    data = load_data()
    today = get_today_key()
    if today in data:
        del data[today]
        save_data(data)
        logger.info("✅ Cleared daily price data at midnight")

@client.on(events.NewMessage(chats=control_channel, pattern="^report$"))
async def handle_report_command(event):
    data = load_data()
    today = get_today_key()
    date_fa = get_persian_date()

    if today not in data:
        await event.reply("📭 داده‌ای برای امروز یافت نشد.")
        return

    message = f"🕒 گزارش تا به این لحظه — {date_fa}\n"
    for currency in ["دلار", "یورو"]:
        c = data[today].get(currency)
        if not c:
            continue
        fluctuation = c["last_price_until_now"] - c["first_price"]
        sign = "-" if fluctuation < 0 else "+"
        fluctuation_abs = abs(fluctuation)

        message += (
            f"\n💰 {currency}\n"
            f"📈️ اولین قیمت: {c['first_price']:,}\n"
            f"📉️ آخرین قیمت: {c['last_price_until_now']:,}\n"
            f"🔺️ بالاترین: {c['highest_price']:,}\n"
            f"🔻️ پایین‌ترین: {c['lowest_price']:,}\n"
            f"📊️ نوسان کل: {fluctuation_abs:,}{sign} تومان\n"
        )

    await event.reply(message.strip())
# -------------------- SCHEDULER --------------------
scheduler.add_job(send_hourly_report, "cron", hour="9-22", minute=0)
scheduler.add_job(send_final_report, "cron", hour=23, minute=0)
scheduler.add_job(clear_daily_data, "cron", hour=23, minute=59)

# -------------------- MAIN --------------------
async def main():
    await client.start(bot_token=report_bot)
    scheduler.start()
    logger.info("📈 Price Tracker Bot is running...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
