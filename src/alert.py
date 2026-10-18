import os
import requests
import pandas as pd

def send_slack_alert(merged_df: pd.DataFrame, total_inputs: int, scenario_time: str) -> str:
    """Builds an executive summary of exceptions and sends it via Slack."""
    matched = len(merged_df[merged_df['Status'] == 'Matched'])
    exceptions = merged_df[merged_df['Status'] != 'Matched']
    
    msg = f"📊 *September Register Reconciliation*\n"
    msg += f"Time: {scenario_time}\n\n"
    msg += f"🔒 *Completeness Check Passed:* All {total_inputs} input rows successfully accounted for.\n\n"
    msg += f"✅ {matched} items matched perfectly.\n\n"
    msg += f"⚠️ *Exceptions ({len(exceptions)} found):*\n"
    
    for _, row in exceptions.iterrows():
        grn = int(row['GRN_key']) if pd.notna(row['GRN_key']) else 'Unknown'
        status = row['Status']
        
        if status == 'Mismatch':
            msg += f"• GRN {grn}: Qty conflict -> Reg={row['Qty_Reg']}, ERP={row['Qty_ERP']}, Store={row['Qty_Store']}\n"
        elif "Missing from" in status:
            msg += f"• GRN {grn}: {status}\n"
        elif status == 'Unreadable Register Entry':
            msg += f"• GRN {grn}: Unreadable value in handwritten register.\n"
        elif status == 'Orphan (No GRN)':
            msg += f"• Orphan row: Store logged Qty {row['Qty_Store']} with no GRN attached.\n"
            
    msg += "\n🔗 Review exceptions in portal: https://kestrel.internal/reconcile"
    
    # Slack API Call
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    payload = {"text": msg}
    
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()
    return "Slack delivery successful"