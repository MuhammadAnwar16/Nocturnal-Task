import os
import argparse
import logging
from dotenv import load_dotenv
from src.vision import extract_register_data
from src.reconcile import run_reconciliation
from src.alert import send_slack_alert

# 1. Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-10-15 08:30", help="Scenario Clock PKT")
    args = parser.parse_args()

    logger.info(f"Starting reconciliation for {args.date}...")
    
    try:
        # 2. State Management (Idempotency) - Only process NEW pages
        processed_log = "data/processed_log.txt"
        if not os.path.exists(processed_log):
            open(processed_log, 'w').close()
            
        with open(processed_log, 'r') as f:
            processed_files = f.read().splitlines()

        image_paths = ["data/t4_register_page1.jpg", "data/t4_register_page2.jpg"]
        new_images = [img for img in image_paths if img not in processed_files]

        if not new_images:
            logger.info("No new register pages found. Exiting to prevent duplicate alerts.")
            return
            
        logger.info(f"Found {len(new_images)} new register page(s). Extracting via Gemini...")
        vision_data = extract_register_data(new_images)
        
        logger.info("Running 3-way Pandas reconciliation...")
        merged_df, total_inputs = run_reconciliation(
            erp_path="data/t4_erp_grn.csv",
            store_path="data/t4_store_sheet.xlsx",
            vision_data=vision_data
        )
        
        logger.info("Sending exception alert to Finance Controller via Slack...")
        result = send_slack_alert(merged_df, total_inputs, args.date)
        
        # 3. Save state only on complete success
        with open(processed_log, 'a') as f:
            for img in new_images:
                f.write(img + '\n')
                
        logger.info(f"✅ Success! Workflow complete. Result: {result}")
        
    except Exception as e:
        logger.error(f"CRITICAL FAILURE: {e}", exc_info=False)

if __name__ == "__main__":
    main()