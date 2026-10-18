# Kestrel Industries - Register Reconciliation (Task 4)

## What it does, and how to run it
This system automatically cross-checks three different inventory records: a handwritten register, an ERP system export, and a storekeeper's Excel sheet. Instead of a human spending three days hunting for mismatches at month-end, this script does the math instantly. It ignores the items that match perfectly and sends the Finance Controller a short Slack message highlighting only the exceptions (what's missing, mismatched, or unreadable).

**To run:**
1. Install the required tools: `pip install -r requirements.txt`
2. Create a `.env` file containing your `GEMINI_API_KEY` and `SLACK_WEBHOOK_URL`.
3. Run the script: `python main.py --date "2026-10-15 08:30"`

## The assumptions I made
* **The "GRN" is the single source of truth:** I used the Goods Received Note (GRN) number to link records across all three systems.
* **Directors only care about the problems:** I assumed the Finance Controller doesn't want to see 86 rows of perfect data. The system only alerts them to the handful of items that actually need their attention.
* **Bad data shouldn't be ignored:** The store sheet had a messy row with a -5000 quantity and no GRN. Instead of dropping it, I assumed it must be explicitly flagged as an "Orphan row" so it isn't lost.

## How it fails, and how someone would know
* **The Math Check (Completeness Failure):** Before sending any alerts, the system counts the total number of items it ingested and compares it to the final output. If even one row was accidentally dropped, the system intentionally crashes and logs an error. This guarantees we never send a mathematically flawed report to the executive team.
* **AI Server Hiccups:** If the Google Gemini AI is temporarily overloaded, the script doesn't just crash. It intelligently waits 5 seconds and tries again (up to 3 times) before safely halting.

## How I handled the data
* **Security & Privacy:** The data is processed entirely in the computer's temporary memory. API keys and passwords are kept in a separate, hidden `.env` file that is never uploaded to the code repository.
* **No Duplicate Alerts:** I added a simple memory file (`processed_log.txt`). If the controller accidentally runs the script twice on the same day, it remembers which handwritten pages it already read and skips them, preventing spam.
* **Messaging Pivot:** Due to Twilio sandbox regional restrictions in Pakistan and ISP-level blocks on the Telegram API, I utilized a free Slack webhook to strictly adhere to the "don't pay for anything" rule. To move this to WhatsApp in production, I would simply swap the API URL in my code to point to Meta's official Cloud API using Kestrel's verified Business ID.

## What I'd do with another week
1. **One-Click Fixes:** Instead of just sending a Slack message, I would include interactive buttons. If the AI flags a number as "Unreadable," the Controller could click a button in Slack, see the cropped picture of the handwriting, type the correct number, and instantly update the ERP.
2. **Database Upgrade:** I would move the script's memory from a simple text file to a real cloud database (like PostgreSQL) so it can scale to handle hundreds of register pages a month.

## AI Tools Used
* **Gemini 3.8 Flash:** Used as the visual engine to accurately read the messy, handwritten register photos and turn them into structured data.
* **Gemini (Chat):** Used as a thought partner to help structure the 3-way matching logic and speed up the boilerplate setup for Slack webhooks.

## Rough Time Log
**Total Time Spent: 1.5 hours**
* Data exploration & Vision AI prompt tuning: 30 minutes
* Core matching logic (handling edge cases and completeness): 40 minutes
* Alerting setup, Slack webhook pivot, and documentation: 20 minutes# Nocturnal-Task
