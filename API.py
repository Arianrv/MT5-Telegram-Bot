import logging
from telethon import TelegramClient, events
from Functions import api_id, api_hash, load_config, save_config
from Functions import Channel_VIP, Target_channel, modify_message, extract_number_from_text
import asyncio

# --------------------------------------  Setup Logging  -----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------  Setup Telegram Client (User Login, NOT Bot!)  ------------------------------
client = TelegramClient('api_session', api_id, api_hash)


# ------------------------  Fetching from VIP Channel with Telegram API Client  ------------------------
@client.on(events.NewMessage(chats=Channel_VIP))
async def message_handler(event):
    """Handles messages from the VIP channel."""

    # Load the latest configuration from config.json
    config = load_config()

    # Read VIP fetching state and tolerances
    fetching_messages = config.get("fetching_messages", False)

    # Tolerances and states for Dollar and Euro
    tolerance_d_farda = config.get("دلار", {}).get("tolerance", 50)  # General tolerance for Dollar
    tolerance_d_naghdi = config.get("دلار", {}).get("T_Naghdi", 50)  # Tolerance for نقدی
    tolerance_d_pasfarda = config.get("دلار", {}).get("T_pasfarda", 50)  # Tolerance for پس‌فردایی
    tolerance_e = config.get("یورو", {}).get("tolerance", 300)  # Tolerance for Euro

    # Bubble values for Dollar and Euro
    bubble_hd_farda = config.get("bubble_hd_farda", 0)
    bubble_hd_naghdi = config.get("bubble_hd_naghdi", 0)
    bubble_hd_pasfarda = config.get("bubble_hd_pasfarda", 0)
    bubble_he_farda = config.get("bubble_he_farda", 0)
    bubble_he_naghdi = config.get("bubble_he_naghdi", 0)
    bubble_he_pasfarda = config.get("bubble_he_pasfarda", 0)

    # Tolerance states for Dollar (based on the config)
    dx_tolerance_state = config.get("dx_tolerance_state", True)
    dp_tolerance_state = config.get("dp_tolerance_state", True)
    dn_tolerance_state = config.get("dn_tolerance_state", True)

    d_state = True if config["دلار"]["state"] == "on" else False
    e_state = True if config["یورو"]["state"] == "on" else False

    # Ensure the fetching feature is enabled
    if not fetching_messages:
        logger.info("VIP fetching is OFF. Ignoring message.")
        return

    # Extract the message
    message = event.raw_text.strip().lower()
    logger.info(f"📩 VIP message: {message}")

    try:
        modified_text = modify_message(message)
        if not modified_text:
            return

        # Iterate through each line
        for line in modified_text.split("\n"):
            number = extract_number_from_text(line)
            if number:
                adjusted_number = number  # Base price

                # ------------------------  Dollar Processing  ------------------------
                if "دلار" in line:
                    if not d_state:
                        logger.info("❌ Dollar processing is OFF. Skipping Dollar message.")
                        continue

                    # Check if the corresponding tolerance state is enabled
                    if "نقدی" in line and not dn_tolerance_state:
                        logger.info("❌ Dollar نقدی tolerance is OFF. Skipping this message.")
                        continue  # Skip processing for نقدی if tolerance is off
                    if "پس فردا" in line or "پسفردا" in line and not dp_tolerance_state:
                        logger.info("❌ Dollar پس‌فردایی tolerance is OFF. Skipping this message.")
                        continue  # Skip processing for پس‌فردایی if tolerance is off
                    if "فردا" in line and not dx_tolerance_state:
                        logger.info("❌ Dollar فردایی tolerance is OFF. Skipping this message.")
                        continue  # Skip processing for فردایی if tolerance is off

                    # Proceed with processing the Dollar price if the related tolerance state is on
                    if "نقدی" in line:
                        last_price_d = config["دلار"].get("price_naghdi", 100000)
                        tol = tolerance_d_naghdi  # Tolerance for نقدی
                        bubble = bubble_hd_naghdi  # Apply bubble for نقدی
                    elif "پس فردا" in line or "پسفردا" in line:
                        last_price_d = config["دلار"].get("price_pasfarda", 100000)
                        tol = tolerance_d_pasfarda  # Tolerance for پس‌فردایی
                        bubble = bubble_hd_pasfarda  # Apply bubble for پس‌فردایی
                    else:
                        last_price_d = config["دلار"].get("price_farda", 100000)
                        tol = tolerance_d_farda  # Tolerance for فردایی
                        bubble = bubble_hd_farda  # Apply bubble for فردایی

                    # Tolerance check for Dollar
                    if abs(number - last_price_d) <= tol:
                        adjusted_number += bubble  # Apply the bubble adjustment

                        if "نقدی" in line:
                            config["دلار"]["price_naghdi"] = adjusted_number
                            logger.info(f"✅ Updated دلار نقدی to {adjusted_number}")
                        elif "پس" in line:
                            config["دلار"]["price_pasfarda"] = adjusted_number
                            logger.info(f"✅ Updated دلار پس‌فردا to {adjusted_number}")
                        else:
                            config["دلار"]["price_farda"] = adjusted_number
                            logger.info(f"✅ Updated دلار فردا to {adjusted_number}")

                        save_config(config)

                        logger.info(f"✅ Updated Dollar Price: {number}, Adjusted: {adjusted_number}")
                    else:
                        logger.warning(f"❌ Price {number} outside tolerance {tol}. Ignoring.")
                        continue

                # ------------------------  Euro Processing  ------------------------
                elif "یورو" in line:
                    if not e_state:
                        logger.info("❌ Euro processing is OFF. Skipping Euro message.")
                        continue

                    # Determine which type of Euro price (Naghdi, Pasfarda, Farda)
                    if "نقدی" in line:
                        last_price_e = config["یورو"].get("price_naghdi", 100000)
                        tol = tolerance_e  # Tolerance for نقدی
                        bubble = bubble_he_naghdi  # Apply bubble for نقدی
                    elif "پس" in line:
                        last_price_e = config["یورو"].get("price_pasfarda", 100000)
                        tol = config["یورو"].get("T_pasfarda", 100)  # Tolerance for پس‌فردایی
                        bubble = bubble_he_pasfarda  # Apply bubble for پس‌فردایی
                    else:
                        last_price_e = config["یورو"].get("price_farda", 100000)
                        tol = config["یورو"].get("T_farda", 100)  # Tolerance for فردایی
                        bubble = bubble_he_farda  # Apply bubble for فردایی

                    # Tolerance check for Euro
                    if abs(number - last_price_e) <= tol:
                        adjusted_number += bubble

                        if "نقدی" in line:
                            config["یورو"]["price_naghdi"] = adjusted_number
                            logger.info(f"✅ Updated یورو نقدی to {adjusted_number}")
                        elif "پس" in line:
                            config["یورو"]["price_pasfarda"] = adjusted_number
                            logger.info(f"✅ Updated یورو پس‌فردا to {adjusted_number}")
                        else:
                            config["یورو"]["price_farda"] = adjusted_number
                            logger.info(f"✅ Updated یورو فردا to {adjusted_number}")

                        save_config(config)
                        logger.info(f"✅ Updated Euro Price: {number}, Adjusted: {adjusted_number}")
                    else:
                        logger.warning(f"❌ Price {number} outside tolerance {tol}. Ignoring.")
                        continue

                # ✅ Forward the modified message to the Target Channel
                adjusted_line = line.replace(str(number), str(adjusted_number))
                await client.send_message(Target_channel, adjusted_line)
                logger.info(f"📤 Forwarded modified message: {adjusted_line}")

    except Exception as e:
        logger.error(f"⚠️ Error processing VIP message: {e}")


# ------------------------  Run the Bot  ------------------------
async def main():
    await client.start()
    logger.info("✅ VIP fetching is now listening for messages.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    logger.info("🚀 Starting VIP Fetching Bot...")
    asyncio.run(main())
