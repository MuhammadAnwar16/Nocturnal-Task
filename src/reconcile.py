import pandas as pd

def run_reconciliation(erp_path: str, store_path: str, vision_data: list) -> tuple:
    """Merges the three data sources and tags exceptions dynamically."""
    erp_df = pd.read_csv(erp_path)
    store_df = pd.read_excel(store_path)
    reg_df = pd.DataFrame(vision_data)
    
    total_inputs = len(erp_df) + len(store_df) + len(reg_df)
    
    # 1. Normalize
    erp_df['GRN_key'] = erp_df['grn_no'].astype(str).str.extract(r'(\d+)').astype(float)
    erp_clean = erp_df[['GRN_key', 'qty']].rename(columns={'qty': 'Qty_ERP'})
    
    store_df['GRN_key'] = store_df['GRN'].astype(float)
    store_clean = store_df.groupby('GRN_key', dropna=False)['Qty Received'].sum().reset_index()
    store_clean = store_clean.rename(columns={'Qty Received': 'Qty_Store'})
    
    reg_df['GRN_key'] = reg_df['GRN'].astype(float)
    reg_clean = reg_df[['GRN_key', 'Qty']].rename(columns={'Qty': 'Qty_Reg'})
    
    # 2. Three-Way Merge
    merged = pd.merge(reg_clean, erp_clean, on='GRN_key', how='outer')
    merged = pd.merge(merged, store_clean, on='GRN_key', how='outer')
    
    # 3. Proof of Completeness Check
    erp_c = erp_df.groupby('GRN_key', dropna=False).size()
    store_c = store_df.groupby('GRN_key', dropna=False).size()
    reg_c = reg_df.groupby('GRN_key', dropna=False).size()
    lineage = pd.concat([erp_c, store_c, reg_c], axis=1).fillna(0)
    
    total_accounted = lineage.sum().sum()
    if total_accounted != total_inputs:
        raise ValueError(f"Completeness Failure: Ingested {total_inputs} rows, but output maps {total_accounted}")
        
    # 4. Dynamic Categorization
    register_grns = reg_clean['GRN_key'].dropna().unique()

    def categorize(row):
        if pd.isna(row['GRN_key']): 
            return "Orphan (No GRN)"
        
        in_register = row['GRN_key'] in register_grns
        if in_register and pd.isna(row['Qty_Reg']): 
            return "Unreadable Register Entry"
            
        missing_from = []
        if not in_register: missing_from.append("Register")
        if pd.isna(row['Qty_ERP']): missing_from.append("ERP")
        if pd.isna(row['Qty_Store']): missing_from.append("Store")
        
        if missing_from:
            return f"Missing from: {', '.join(missing_from)}"
            
        if row['Qty_Reg'] == row['Qty_ERP'] == row['Qty_Store']: 
            return "Matched"
            
        return "Mismatch"
        
    merged['Status'] = merged.apply(categorize, axis=1)
    return merged, total_inputs