# Trading Execution Engine (Oanda API)

A Python-based trading execution engine that integrates with the Oanda API to trade Forex pairs.  
It supports limit and market entries, customizable stop-loss pips, and streamlined session logging.  
Built with **asyncio** for responsive execution and live pricing streams.

---

## Features
- Connects to Oanda’s REST & streaming APIs.
- Handles **market** and **limit** entries with stop-loss management.
- Live **price streaming** with configurable instruments.
- Supports **primary** and **secondary** accounts.
- Structured **session logging**.
- Extendable configuration via `config.json`.

---

## Requirements
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for environment & dependency management
- An [Oanda](https://www.oanda.com/) account with API key access

---

## Setup

1. **Clone the repo**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>```

2. **Install dependencies using uv**

   ```bash
   uv run pip install -r requirements.txt
   ```

3. **Create a `.env` file in the project root** with your credentials:

   ```env
   PRIMARY_ACCOUNT_ID = '101-001-35340676-601'
   SECONDARY_ACCOUNT_ID = '101-001-46274824-002'
   OANDA_API_KEY = 'your_api_key_here'
   ```

   * `PRIMARY_ACCOUNT_ID` → your main Oanda account ID
   * `SECONDARY_ACCOUNT_ID` → optional secondary account ID(s)
   * `OANDA_API_KEY` → your Oanda API key

4. **Configure instruments in `config.json`**
   Add/modify pairs as needed:

   ```json
   {
       "INSTRUMENTS": {
           "GU": {
               "symbol": "GBP_USD",
               "pip_value": 0.0001,
               "precision": 5
           },
           "UJ": {
               "symbol": "USD_JPY",
               "pip_value": 0.01,
               "precision": 3
           },
           "EU": {
               "symbol": "EUR_USD",
               "pip_value": 0.0001,
               "precision": 5
           },
           "GJ": {
               "symbol": "GBP_JPY",
               "pip_value": 0.01,
               "precision": 3
           }
       }
   }
   ```

---

## Running the Program

Start the execution engine with:

```bash
uv run main.py
```

You’ll be prompted to:

* Enter **risk per session**
* Choose **primary or secondary account**
* Select **instrument & position**

From there, the program will begin streaming live prices and allow:

* `1` → Place limit entry (with cancel option)
* `2` → Place market entry
* `3` → Change stop-loss pips

---

## Project Structure

```
src/
 ├── pricing_stream.py       # Handles Oanda price streaming
 ├── oanda_service.py        # Client wrapper for Oanda API
 ├── order_manager.py        # Order placement & management
 ├── trade_logger.py         # Session logging utility
 └── utils.py                # User input helpers
config.json                  # Supported forex pairs
.env                         # API credentials (need to create this when cloning)
main.py                      # Entry point
```

---

## Notes

* Ensure `.env` is **not committed** to git (`.gitignore` should include `.env`).
* Requires a funded Oanda practice/live account to execute trades.
* Test carefully in a **practice environment** before deploying live.

---

## License

MIT License — use at your own risk.

