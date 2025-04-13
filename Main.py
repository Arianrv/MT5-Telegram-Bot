"""
                Created by  Bersavosh
                Instagram:  @barsarnj
                Email:      arianrv@gmail.com
                                                           """

from Functions import convert_english_to_persian, convert_persian_to_english, calculate_ranges, show_table
from Functions import get_sender_name, help_text, api_id, api_hash, bot_token, in_Group, load_config
from Functions import Target_channel, control_channel, config
from Functions import save_config, in_Group_msg_map
from telethon import TelegramClient, events, Button
from telethon.events import CallbackQuery
import logging
import asyncio
import time
import sys
import os
import re


# ----------------------   Load save prices, tolerances and states  ----------------------------------------------------
try:
    config = load_config()
    config_states = config

    last_price_d_f = config.get("دلار", {}).get("price_farda", 90000)
    last_price_d_n = config.get("دلار", {}).get("price_naghdi", 90000)
    last_price_d_p = config.get("دلار", {}).get("price_pasfarda", 90000)

    last_price_e_f = config.get("یورو", {}).get("price_farda", 95000)
    last_price_e_n = config.get("یورو", {}).get("price_naghdi", 95000)
    last_price_e_p = config.get("یورو", {}).get("price_pasfarda", 95000)

    tolerance_d_f = config.get("دلار", {}).get("tolerance", 50)
    tolerance_d_n = config.get("دلار", {}).get("T_Naghdi", 50)
    tolerance_d_p = config.get("دلار", {}).get("T_pasfarda", 50)

    dx_tolerance_state = config_states.get("dx_tolerance_state", True)
    dn_tolerance_state = config_states.get("dn_tolerance_state", True)
    dp_tolerance_state = config_states.get("dp_tolerance_state", True)

    comma_format = config_states.get("comma_format", False)
    d_state = True if config_states["دلار"].get("state") == "on" else False
    e_state = True if config_states["یورو"].get("state") == "on" else False
    change_threshold = config_states.get("change_threshold")

    bubble_hd_farda     = config_states.get("bubble_hd_farda", 0)
    bubble_hd_naghdi    = config_states.get("bubble_hd_naghdi", 0)
    bubble_hd_pasfarda  = config_states.get("bubble_hd_pasfarda", 0)
    bubble_he_farda     = config_states.get("bubble_he_farda", 0)
    bubble_he_naghdi    = config_states.get("bubble_he_naghdi", 0)
    bubble_he_pasfarda  = config_states.get("bubble_he_pasfarda", 0)

except Exception as e:
    print(f"[DEBUG] ❌ Error loading states: {e}")
    d_state = True  # Default to enabled if error occurs
    e_state = True  # Default to enabled if error occurs

# ----------------------   Logging configuration  ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ----------------------   Connecting to the Bot  ----------------------------------------------------------------------
try:
    client = TelegramClient('main_session', int(api_id), api_hash).start(bot_token=bot_token)
    logger.info("Telegram client initialized successfully.")

except Exception as e:
    logger.error(f"Failed to initialize Telegram client: {e}")
    sys.exit(1)


# ----------------------  Send any messages to Target_channel  ---------------------------------------------------------
async def send_to_Target_channel(message):
    try:
        logger.info(f"Sending message to channel: {message}")
        await client.send_message(Target_channel, message)
    except Exception as e:
        logger.error(f"Failed to send message to channel: {e}")


# ----------------------  Parameters, Ranges and States ----------------------------------------------------------------
def calculate_ranges(config):
    try:
        last_price_d_f = config.get("دلار", {}).get("price_farda", 90000)
        last_price_d_n = config.get("دلار", {}).get("price_naghdi", 90000)
        last_price_d_p = config.get("دلار", {}).get("price_pasfarda", 90000)

        tolerance_d_f = config.get("دلار", {}).get("tolerance", 50)
        tolerance_d_n = config.get("دلار", {}).get("T_Naghdi", 50)
        tolerance_d_p = config.get("دلار", {}).get("T_pasfarda", 50)

        dollar_min_f = max(0, last_price_d_f - tolerance_d_f)
        dollar_max_f = last_price_d_f + tolerance_d_f

        dollar_min_n = max(0, last_price_d_n - tolerance_d_n)
        dollar_max_n = last_price_d_n + tolerance_d_n

        dollar_min_p = max(0, last_price_d_p - tolerance_d_p)
        dollar_max_p = last_price_d_p + tolerance_d_p

        range_dollar_f = f"{dollar_max_f} - {dollar_min_f}"
        range_dollar_n = f"{dollar_max_n} - {dollar_min_n}"
        range_dollar_p = f"{dollar_max_p} - {dollar_min_p}"

        return (range_dollar_f, range_dollar_n, range_dollar_p, dollar_min_f, dollar_max_f, dollar_min_n,
                dollar_max_n, dollar_min_p, dollar_max_p)
    except KeyError as e:
        logger.error(f"[calculate_ranges] Missing key in config: {e}")
        return "0 - 0", "0 - 0", "0 - 0", 0, 0, 0, 0, 0, 0

# ----------------------  Comma setup function  ------------------------------------------------------------------------
def format_price(price):
    return f"{price:,}" if comma_format else str(price)


# ----------------------  Bubble Function for V.I.P Channel  -----------------------------------------------------------
def bubble(currency, value):
    """Applies user-defined adjustments to fetched prices and saves them to prices.json."""
    global config_states, bubble_adjustments

    if currency in bubble_adjustments:
        bubble_adjustments[currency] += value  # Update adjustment
        config_states[f"bubble_{currency}"] = bubble_adjustments[currency]  # Save to config_states
        save_config(config_states)  # Save to prices.json

        logging.info(f"Bubble applied: {currency} {value}, New Adjustment: {bubble_adjustments[currency]}")


# ----------------------  Message interpretation for 2, 3, 4, and 5 digits entry  --------------------------------------
async def interpret_price(command, price, last_price, currency, mode):

    print(f"[DEBUG] Received command: {command}, price: {price}, last_price: {last_price}, currency: {currency}, mode: {mode}")

    if last_price is None:
        last_price = 100000
        print(f"[DEBUG] last_price was None, defaulting to 100000")

    interpreted = price

    # ----------------------- Handle two-digit entry (X0, X5, etc.) ----------------------------------------------------
    if 0 <= price <= 99:
        option1 = (last_price // 100) * 100 + price
        option2 = ((last_price // 100) - 1) * 100 + price
        option3 = ((last_price // 100) + 1) * 100 + price

        closest_options = sorted([option1, option2, option3], key=lambda x: abs(x - last_price))
        if abs(closest_options[0] - last_price) == abs(closest_options[1] - last_price):
            interpreted = max(closest_options[0], closest_options[1])
        else:
            interpreted = closest_options[0]

    # ----------------------- Handle three-digit entry (XX0, XX5, etc.) ------------------------------------------------
    elif len(str(price)) == 3:
        option1 = (last_price // 1000) * 1000 + price
        option2 = ((last_price // 1000) - 1) * 1000 + price
        option3 = ((last_price // 1000) + 1) * 1000 + price

        closest_options = sorted([option1, option2, option3], key=lambda x: abs(x - last_price))
        if abs(closest_options[0] - last_price) == abs(closest_options[1] - last_price):
            interpreted = max(closest_options[0], closest_options[1])
        else:
            interpreted = closest_options[0]

    # ------------------------- Handle four-digit entry (XXX0, XXX5, etc.) ---------------------------------------------
    elif len(str(price)) == 4:
        option1 = (last_price // 10000) * 10000 + price
        option2 = ((last_price // 10000) - 1) * 10000 + price
        option3 = ((last_price // 10000) + 1) * 10000 + price

        closest_options = sorted([option1, option2, option3], key=lambda x: abs(x - last_price))
        if abs(closest_options[0] - last_price) == abs(closest_options[1] - last_price):
            interpreted = max(closest_options[0], closest_options[1])
        else:
            interpreted = closest_options[0]

    # ------------------------- Handle five-digit entry (Full price) ---------------------------------------------------
    elif len(str(price)) == 5:
        interpreted = price

    # ----------------------- Tolerance Check based on currency and mode -----------------------------------------------
    config = load_config()

    if currency == "دلار":
        tol_key = {"farda": "tolerance", "naghdi": "T_Naghdi", "pasfarda": "T_pasfarda"}[mode]
        tol_state_key = {"farda": "dx_tolerance_state", "naghdi": "dn_tolerance_state", "pasfarda": "dp_tolerance_state"}[mode]
    elif currency == "یورو":
        tol_key = "tolerance"
        tol_state_key = "ex_tolerance_state"
    else:
        print(f"[DEBUG] Unknown currency: {currency}")
        return None

    tol_state = config.get(tol_state_key, False)
    tolerance = config[currency].get(tol_key, 50)

    if tol_state:
        difference = abs(interpreted - last_price)
        if difference > tolerance:
            k_range = f"{last_price - tolerance} تا {last_price + tolerance}"
            print(f"[DEBUG] ❌ Price {interpreted} outside tolerance ({k_range}), diff: {difference}")
            await client.send_message(
                in_Group,
                f"⚠️ قیمت وارد شده {interpreted} خارج از محدوده مجاز {k_range} است! ❌"
            )
            return None

    print(f"[DEBUG] ✅ Accepted closest price: {interpreted}")
    return interpreted


# Change Backup
# ----------------------  Handling Messages from Control_channel  ------------------------------------------------------
@client.on(events.NewMessage(chats=control_channel, incoming=True))
async def control_handler(event):
    global config_states, last_price_d_f, last_price_e_f, comma_format
    global tolerance_d, tolerance_e, d_state, e_state
    logging.info(
        f"[DEBUG] Handling control message (Event ID: {event.id}, Sender ID: {event.sender_id}): {event.raw_text}")

    config_states = load_config()
    try:

        message = event.raw_text
        sender = await event.get_sender()

        # -----------------------------  Safe Tolerance Updates (with digit check) -------------------------------------
        if message.lower().startswith("dx "):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                tolerance_d = int(parts[1])
                config["دلار"]["tolerance"] = tolerance_d
                save_config(config)
                await event.reply(f"تلرانس دلار به {tolerance_d} تغییر کرد.")
                config_text = show_table()
                await event.reply(config_text, parse_mode="html")
                logging.info("Set دلار tolerance to %d", tolerance_d)
                return

        if message.lower().startswith("dn "):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                tlrnc_n = int(parts[1])
                config["دلار"]["T_Naghdi"] = tlrnc_n
                save_config(config)
                await event.reply(f"تلرانس دلار نقدی به {tlrnc_n} تغییر کرد.")
                config_text = show_table()
                await event.reply(config_text, parse_mode="html")
                logging.info("Set دلار نقدی to %d", tlrnc_n)
                return

        if message.lower().startswith("dp "):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                tlrnc_p = int(parts[1])
                config["دلار"]["T_pasfarda"] = tlrnc_p
                save_config(config)
                await event.reply(f"تلرانس دلار پس فردایی به {tlrnc_p} تغییر کرد.")
                config_text = show_table()
                await event.reply(config_text, parse_mode="html")
                logging.info("Set دلار پسفردایی to %d", tlrnc_p)
                return

        # -----------------------------  State of Tolerances before fetching prices ------------------------------------
        if message.lower() == "dp on":
            # Enable tolerance for Dollar after the "dp on" command
            dp_tolerance_state = True
            config_states["dp_tolerance_state"] = dp_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("✅ دلار پس‌فردایی روشن شد.")  # Notify the group
            logging.info("Dollar پس‌فردایی tolerance (dp) set to True")

        elif message.lower() == "dp off":
            # Disable tolerance for Dollar after the "dp off" command
            dp_tolerance_state = False
            config_states["dp_tolerance_state"] = dp_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("❌ دلار پس‌فردایی خاموش شد.")  # Notify the group
            logging.info("Dollar پس‌فردایی tolerance (dp) set to False")

        elif message.lower() == "dx on":
            # Enable tolerance for Dollar فردایی after the "dx on" command
            dx_tolerance_state = True
            config_states["dx_tolerance_state"] = dx_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("✅ دلار فردایی روشن شد.")  # Notify the group
            logging.info("Dollar فردایی tolerance (dx) set to True")

        elif message.lower() == "dx off":
            # Disable tolerance for Dollar فردایی after the "dx off" command
            dx_tolerance_state = False
            config_states["dx_tolerance_state"] = dx_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("❌ دلار فردایی خاموش شد.")  # Notify the group
            logging.info("Dollar فردایی tolerance (dx) set to False")

        elif message.lower() == "dn on":
            # Enable tolerance for Dollar نقدی after the "dn on" command
            dn_tolerance_state = True
            config_states["dn_tolerance_state"] = dn_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("✅ دلار نقدی روشن شد.")  # Notify the group
            logging.info("Dollar نقدی tolerance (dn) set to True")

        elif message.lower() == "dn off":
            # Disable tolerance for Dollar نقدی after the "dn off" command
            dn_tolerance_state = False
            config_states["dn_tolerance_state"] = dn_tolerance_state
            save_config(config_states)  # Save the updated tolerance state
            await event.reply("❌ دلار نقدی خاموش شد.")  # Notify the group
            logging.info("Dollar نقدی tolerance (dn) set to False")

        # Handle threshold command
        if message.lower().startswith("xx "):
            try:
                new_threshold = int(message.split()[1])
                if 1 <= new_threshold <= 100:
                    global change_threshold
                    change_threshold = new_threshold
                    config["change_threshold"] = new_threshold
                    save_config(config)
                    logging.info(f"Change threshold set to {new_threshold}%")
                    await event.reply(f"✅ XX = {new_threshold}%")
                else:
                    await event.reply("لطفاً عددی بین ۱ تا ۱۰۰ وارد کنید.")
            except ValueError:
                await event.reply("فرمت دستور اشتباه است. مثال: xx 30")
            return

        # --------------------- Set Euro Tolerance --------------------------------------------------------------
        if message.lower() == "ex on":
            # Set Euro tolerance state to True
            config_states["ex_tolerance_state"] = True
            save_config(config_states)  # Save the updated state to config
            await event.reply("✅ تلورانس یورو روشن شد.")  # Notify the group
            logging.info("Euro tolerance (ex) set to True")

        elif message.lower() == "ex off":
            # Set Euro tolerance state to False
            config_states["ex_tolerance_state"] = False
            save_config(config_states)  # Save the updated state to config
            await event.reply("❌ تلورانس یورو خاموش شد.")  # Notify the group
            logging.info("Euro tolerance (ex) set to False")

        # Handle the case where ex tolerance is set
        if message.lower().startswith("ex "):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                tolerance_e = int(parts[1])
                config["یورو"]["tolerance"] = tolerance_e
                save_config(config)  # Save the updated tolerance value
                await event.reply(f"تلورانس یورو به {tolerance_e} تغییر کرد.")
                config_text = show_table()
                await event.reply(config_text, parse_mode="html")
                logging.info(f"Set یورو tolerance to {tolerance_e}")

        # -----------------------------  State of Fetching from VIP channel ------------------------------------
        if message.lower() == "vip on":
            fetching_messages = True
            config_states["fetching_messages"] = True
            save_config(config_states)
            await event.reply("✅ VIP prices fetching is now ON.")
            logger.info("VIP fetching turned ON.")

        elif message.lower() == "vip off":
            fetching_messages = False
            config_states["fetching_messages"] = False
            save_config(config_states)
            await event.reply("❌ VIP prices fetching is now OFF.")
            logger.info("VIP fetching turned OFF.")

        # -----------------------------  Handle Help command ---------------------------------------------------
        if message.lower() == "help":
            await event.reply(help_text, parse_mode="html")

        # -----------------------------  Handle Bubble command -------------------------------------------------
        if message.lower().startswith(("hd", "he")):
            try:
                parts = message.split()
                if len(parts) == 3:
                    base = parts[0].lower()  # hd or he
                    mode = parts[1].lower()  # f / n / p
                    value = int(parts[2])  # adjustment value

                    currency = "دلار" if base == "hd" else "یورو"
                    eng = "dollar" if base == "hd" else "euro"

                    mode_map = {
                        "f": "farda",
                        "n": "naghdi",
                        "p": "pasfarda"
                    }

                    if mode in mode_map:
                        key = f"bubble_{base}_{mode_map[mode]}"
                        config_states[key] = value
                        save_config(config_states)

                        # Format value for display
                        symbol = "-" if value < 0 else ""
                        reply_val = convert_english_to_persian(str(abs(value))) + symbol
                        mode_label = {
                            "f": "فردایی",
                            "n": "نقدی",
                            "p": "پس‌فردایی"
                        }

                        await event.reply(
                            f"✅ تنظیم حباب {currency} ({mode_label[mode]}) به \u200F{reply_val} انجام شد.")
                        logging.info(f"Bubble {eng} {mode_label[mode]} set to {value}")
                    else:
                        await event.reply("❌ دستور نادرست! از بین `f`, `n`, `p` انتخاب کنید.")
                else:
                    await event.reply("❌ فرمت نادرست! مثال: he f 10 یا hd n -5")
            except ValueError:
                await event.reply("❌ مقدار نادرست! لطفاً عددی وارد کنید.")

        # -----------------------------  Handle ping command ---------------------------------------------------
        if message.lower() == "ping":
            start_time = time.time()
            sent_message = await event.reply("🏓 Pong!")
            end_time = time.time()
            latency = round((end_time - start_time) * 1000)
            await sent_message.edit(f"🏓 Pong! Latency: {latency} ms")
            logging.info(f"Ping command executed. Latency: {latency} ms")
            return

        #  -------------------------------  Comma  -------------------------------------------------------------
        if message.lower() == "comma on":
            comma_format = True
            config["comma_format"] = True
            save_config(config)
            logging.info("Comma format enabled.")
            await event.reply("کاما فعال شد.")
            return

        if message.lower() == "comma off":
            comma_format = False
            config["comma_format"] = False
            save_config(config)
            logging.info("Comma format disabled.")
            await event.reply("کاما غیرفعال شد.")
            return

        # ------------------------------ RESTART ---------------------------------------------------------------
        if message.lower() == "restart":
            await event.reply("♻️ درحال ری استارت ..")
            logging.info("Restarting bot...")
            save_config(config)
            await asyncio.sleep(2)
            os.execv(sys.executable, ['python'] + sys.argv)

        # ---------------------------- SHOW --------------------------------------------------------------------
        if message.lower() == "show":
            config_text = show_table()
            await event.reply(config_text, parse_mode="html")
            logging.info("Displayed current config.")
            return

        # ---------------------------- Currency's State Commands -----------------------------------------------
        if message.lower() == "d on":
            d_state = True
            config["دلار"]["state"] = "on"
            save_config(config)
            logging.info("دلار enabled.")
            await event.reply("✅ دلار روشن شد.")
            return

        if message.lower() == "d off":
            d_state = False
            config["دلار"]["state"] = "off"
            save_config(config)
            logging.info("دلار disabled.")
            await event.reply("❌ دلار خاموش شد.")
            return

        if message.lower() == "e on":
            e_state = True
            config["یورو"]["state"] = "on"
            save_config(config)
            logging.info("یورو enabled.")
            await event.reply("✅ یورو روشن شد.")
            return

        if message.lower() == "e off":
            e_state = False
            config["یورو"]["state"] = "off"
            save_config(config)
            logging.info("یورو disabled.")
            await event.reply("❌ یورو خاموش شد.")
            return

        config_states = load_config()

    except Exception as ea:
        logger.error(f"Error in control_channel_handler: {ea}")


# ----------------------  Handling Messages from input_Group  ----------------------------------------------------------
@client.on(events.NewMessage(chats=in_Group))
async def input_handler(event):
    global config, config_states
    global last_price_d, last_price_e
    global last_price_d_f
    global d_state, e_state
    global tolerance_d, tolerance_e
    global tolerance_d_f, tolerance_d_n, tolerance_d_p
    global dx_tolerance_state, dn_tolerance_state, dp_tolerance_state
    global comma_format, change_threshold

    config = load_config()
    range_d_f, range_d_n, range_d_p, d_min_f, d_max_f, d_min_n, d_max_n, d_min_p, d_max_p = calculate_ranges(config)
    name = await get_sender_name(event)
    try:
        message = event.raw_text
        sender = await event.get_chat()
        logging.info(f"Received message from {name}: {message}")

        #  ---------------------------- SHOW -----------------------------------------------------------------------
        if message.lower() == "show":
            config_text = show_table()
            await event.reply(config_text, parse_mode="html")
            logging.info("Displayed current config.")
            return

        # ---------------------------- Handle direct Dollar command (d= or D=) ------------------------------------
        if message.lower().startswith("d="):
            direct_price_match = re.match(r"^[dD]\s*=\s*(\d+)$", message)
            if direct_price_match:
                new_price = int(direct_price_match.group(1))
                reference_price = config["دلار"].get("price_farda", 90000)

                change = abs(new_price - reference_price) / reference_price * 100
                if change > change_threshold:
                    await event.reply(
                        f"{name}\nتغییر قیمت بیش از {change_threshold} درصد؟!",
                        buttons=[
                            [Button.inline("✅ تایید", f"confirm_{new_price}".encode("utf-8")),
                             Button.inline("❌ لغو", b"cancel")]
                        ]
                    )
                    logging.warning(f"Price change exceeds {change_threshold}% for dollar: {new_price}")
                    return

                config["دلار"].update({
                    "price": new_price,
                    "price_farda": new_price,
                    "price_naghdi": new_price,
                    "price_pasfarda": new_price
                })
                save_config(config)

                await send_to_Target_channel(f"دلار مع فردا {format_price(new_price)}")
                logging.info(f"Direct dollar price set to {new_price} by {name}")
                return

        # ---------------------------- Handle direct Euro command (e= or E=) --------------------------------------
        if message.lower().startswith("e="):
            direct_price_match = re.match(r"^[eE]\s*=\s*(\d+)$", message)
            if direct_price_match:
                new_price = int(direct_price_match.group(1))
                reference_price = config["یورو"].get("price_farda", 95000)

                change = abs(new_price - reference_price) / reference_price * 100
                if change > change_threshold:
                    await event.reply(
                        f"{name}\nتغییر قیمت بیش از {change_threshold} درصد؟!",
                        buttons=[
                            [Button.inline("✅ تایید", f"confirm_euro_{new_price}".encode("utf-8")),
                             Button.inline("❌ لغو", b"cancel")]
                        ]
                    )
                    logging.warning(f"Price change exceeds {change_threshold}% for euro: {new_price}")
                    return

                config["یورو"].update({
                    "price": new_price,
                    "price_farda": new_price,
                    "price_naghdi": new_price,
                    "price_pasfarda": new_price
                })
                save_config(config)

                await send_to_Target_channel(f"یورو مع فردا {format_price(new_price)}")
                logging.info(f"Direct euro price set to {new_price} by {name}")
                return

        # ---------------------------- Interpret and process price messages -----------------------------
        message = re.sub(r"([^\d\s])([\d])", r"\1 \2", message)  # Ensure correct spacing for numbers
        match = re.match(r"^(?:(\D+)[\s‌]*([\d]+)|([\d]+)[\s‌]*(\D+))$", message)

        if match:
            config = load_config()
            command = match.group(1) or match.group(4)
            price = int(convert_persian_to_english(match.group(2) or match.group(3)))

            if command in in_Group_msg_map:
                mapped_value = in_Group_msg_map[command]
                print(f"[DEBUG] Found command in message_map: {command} -> {mapped_value}")

                if 'یورو' in mapped_value:
                    if command in ['خی', 'فی', 'ی']:
                        save_key = "price_farda"
                    # Add other euro modes if needed

                    tolerance_e = config["یورو"].get("tolerance", 50)
                    last_price_e = config["یورو"].get(save_key, 95000)
                    tol_state = config.get("ex_tolerance_state", False)

                    interpreted_price_e = await interpret_price(command, price, last_price_e, "یورو",
                                                                save_key.split("_")[1])

                    if interpreted_price_e is None:
                        logging.warning("interpreted_price was None after calling interpret_price")
                        return

                    if tol_state and not (
                            last_price_e - tolerance_e <= interpreted_price_e <= last_price_e + tolerance_e):
                        warning_message = (
                            f"⚠️ قیمت وارد شده {interpreted_price_e} خارج از محدوده مجاز "
                            f"{last_price_e - tolerance_e} تا {last_price_e + tolerance_e}! ❌"
                        )
                        await client.send_message(in_Group, warning_message)
                        logging.warning(
                            f"Euro interpreted price {interpreted_price_e} outside tolerance range "
                            f"({last_price_e - tolerance_e} to {last_price_e + tolerance_e})"
                        )
                        return

                    config["یورو"][save_key] = interpreted_price_e
                    config["یورو"]["price"] = interpreted_price_e
                    save_config(config)
                    await send_to_Target_channel(f"{mapped_value} {format_price(interpreted_price_e)}")
                    logging.info(f"✅ Sent یورو ({save_key}): {interpreted_price_e}")

                elif 'دلار' in mapped_value:
                    if command in ['نم', 'نف', 'نخ']:
                        tol = config["دلار"].get("T_Naghdi", 50)
                        tol_state = config.get("dn_tolerance_state", False)
                        save_key = "price_naghdi"
                    elif command in ['خپ', 'فپ', 'پس']:
                        tol = config["دلار"].get("T_pasfarda", 50)
                        tol_state = config.get("dp_tolerance_state", False)
                        save_key = "price_pasfarda"
                    else:
                        tol = config["دلار"].get("tolerance", 50)
                        tol_state = config.get("dx_tolerance_state", False)
                        save_key = "price_farda"

                    last_price_d = config["دلار"].get(save_key, 90000)

                    interpreted_price_d = await interpret_price(command, price, last_price_d, "دلار",
                                                                save_key.split("_")[1])

                    if interpreted_price_d:
                        if tol_state and abs(interpreted_price_d - last_price_d) > tol:
                            await event.reply(f"❌ قیمت دلار {mapped_value} خارج از محدوده تلرانس {tol} است.")
                            logging.warning(f"Dollar price {mapped_value} outside tolerance {tol}")
                            return

                        config["دلار"][save_key] = interpreted_price_d
                        config["دلار"]["price"] = interpreted_price_d
                        save_config(config)
                        await send_to_Target_channel(f"{mapped_value} {format_price(interpreted_price_d)}")
                        logging.info(f"✅ Sent دلار ({save_key}): {interpreted_price_d}")

            else:
                # This block only triggers if match exists, but command is unknown (optional to keep)
                pass

        # ✅ Fallback: numeric-only message like "۴۰۰" → دلار مع فردا
        else:
            numeric_input = convert_persian_to_english(message).strip()
            if numeric_input.isdigit() and 2 <= len(numeric_input) <= 6:
                config = load_config()
                price = int(numeric_input.lstrip("0") or "0")
                currency = "دلار"
                mode = "farda"
                save_key = "price_farda"
                last_price_d = config[currency].get(save_key, 90000)

                interpreted_price_d = await interpret_price("auto", price, last_price_d, currency, mode)

                if interpreted_price_d is None:
                    await event.reply("❌ خطا در تفسیر قیمت دلار. لطفاً مجدد تلاش کنید.")
                    logging.error(f"Dollar price interpretation failed for input: {price}")
                    return

                if config.get("dx_tolerance_state", False):
                    tol = config[currency].get("tolerance", 50)
                    if abs(interpreted_price_d - last_price_d) > tol:
                        await event.reply(f"❌ قیمت دلار فردایی خارج از محدوده تلرانس {tol} است.")
                        logging.warning(f"Fallback دلار فردایی price outside tolerance: {interpreted_price_d}")
                        return

                config[currency][save_key] = interpreted_price_d
                config[currency]["price"] = interpreted_price_d
                save_config(config)

                await send_to_Target_channel(f"دلار مع فردا {format_price(interpreted_price_d)}")
                logging.info(f"✅ Fallback sent دلار (price_farda): {interpreted_price_d}")
                return


    except Exception as eb:
        logger.error(f"Error in in_Group_handler: {eb}")


# -------------  Handle button clicks for price confirmation or cancellation  ------------------------------------------
@client.on(CallbackQuery)
async def callback_handler(event):
    try:
        name = await get_sender_name(event)
        data = event.data.decode('utf-8')
        sender = await event.get_chat()

        if data.startswith("confirm_"):
            parts = data.split("_")
            if len(parts) == 2:
                # Dollar confirmation
                new_price = int(parts[1])
                global last_price_d_f
                last_price_d_f = new_price
                config["دلار"].update({
                    "price": new_price,
                    "price_farda": new_price,
                    "price_naghdi": new_price,
                    "price_pasfarda": new_price
                })
                save_config(config)
                await send_to_Target_channel(f"دلار مع فردا {format_price(new_price)}")
                await event.edit(buttons=None)  # Remove buttons
                await event.answer("✅ قیمت دلار تایید و بروزرسانی شد.", alert=True)
                logging.info(f"Direct dollar price confirmed: {new_price} by {name}")

            elif len(parts) == 3 and parts[1] == "euro":
                # Euro confirmation
                new_price = int(parts[2])
                global last_price_e_f
                last_price_e_f = new_price
                config["یورو"].update({
                    "price": new_price,
                    "price_farda": new_price,
                    "price_naghdi": new_price,
                    "price_pasfarda": new_price
                })
                save_config(config)
                await send_to_Target_channel(f"یورو مع فردا {format_price(new_price)}")
                await event.edit(buttons=None)  # Remove buttons
                await event.answer("✅ قیمت یورو تایید و بروزرسانی شد.", alert=True)
                logging.info(f"Direct euro price confirmed: {new_price} by {name}")

        elif data == "cancel":
            await event.edit(buttons=None)  # Remove buttons
            await event.answer("❌ لغو شد.", alert=True)
            logging.info("User cancelled the action.")
            return
    except Exception as ec:
        logging.error(f"Error in inline keyboard: {ec}")


if __name__ == "__main__":
    try:
        print("Bot is running...")
        client.run_until_disconnected()  # ✅ Keeps the bot running
    except KeyboardInterrupt:
        print("Bot stopped.")