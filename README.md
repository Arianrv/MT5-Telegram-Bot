# MT5-Telegram-Bot
A Telegram bot for price tracking and reporting built for Forex brokers (MT5/MT4)

A fully automated Telegram bot that reads real-time price data from Telegram channels and generates hourly and daily reports — built for integration with MetaTrader 5 (MT5) traders and brokers. (Requires server-side configuration to fetch data and generate charts in MetaTrader / MetaManager!)

---

## 🚀 Features

- 📥 Listens to Telegram messages from price sources
- 🧠 Detects and extracts prices (DOLLAR, EURO) intelligently
- 🕒 Sends **hourly reports** showing high/low prices
- 📊 Sends **daily final report** with:
  - Opening price
  - Closing price
  - Highest & lowest prices
  - Percentage change
- 🗃 Stores all price data in a lightweight JSON file
- 📆 Fully aligned with **Iran timezone** using `jdatetime` (can be modified to support other timezones)
- 🤖 Runs 24/7 with robust logging and crash resistance (Requires server-side configuration)

---

## 🛠 Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Arianrv/MT5-Telegram-Bot.git
   cd MT5-Telegram-Bot
