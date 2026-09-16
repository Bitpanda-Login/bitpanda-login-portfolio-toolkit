import pandas as pd
import numpy as np

def parse_bitpanda_csv(filepath):
    """
    Parses a Bitpanda trades CSV file and applies Bitpanda-specific heuristics:
    1. Filter out micro-transfers of BEST (cashback/rebates)
    2. Detect and link Crypto-to-Crypto swaps
    """
    metadata = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        metadata['disclaimer'] = f.readline().strip().replace('"', '')
        metadata['user'] = f.readline().strip().replace('"', '')
        metadata['email'] = f.readline().strip().replace('"', '')
        metadata['account_opened'] = f.readline().strip().replace('"', '').replace('Account opened at: ', '')
        metadata['venue'] = f.readline().strip().replace('"', '').replace('Venue: ', '')
        
    df = pd.read_csv(filepath, skiprows=5)
    
    numeric_cols = ['Amount Fiat', 'Amount Asset', 'Asset market price', 'Fee', 'Fee percent', 'Spread', 'Tax Fiat']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace('-', '0'), errors='coerce').fillna(0)
    
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='ISO8601', utc=True)
    df = df.sort_values(by='Timestamp', ascending=True).reset_index(drop=True)
    
    # Heuristic 1: Filter BEST micro-transfers (cashback/rebates)
    # We ignore BEST transfers/deposits/withdrawals with Fiat Value < 0.10 EUR
    is_best_micro = (df['Asset'] == 'BEST') & (df['Amount Fiat'] < 0.10) & (df['Transaction Type'].isin(['transfer', 'withdrawal', 'deposit']))
    df = df[~is_best_micro].copy().reset_index(drop=True)
    
    # Heuristic 2: Detect Crypto-to-Crypto Swaps
    # A swap is a 'sell' and a 'buy' occurring at the exact same timestamp with similar 'Amount Fiat'
    df['Swap_ID'] = None
    
    swap_id_counter = 1
    # Group by Timestamp to find simultaneous buy/sell
    for ts, group in df.groupby('Timestamp'):
        if len(group) == 2:
            tx_types = set(group['Transaction Type'])
            if tx_types == {'buy', 'sell'}:
                # Verify that the fiat values are very close (usually they are identical, but we allow 1% margin)
                buy_row = group[group['Transaction Type'] == 'buy'].iloc[0]
                sell_row = group[group['Transaction Type'] == 'sell'].iloc[0]
                
                # Check if fiat values are within 1% of each other
                fiat_diff = abs(buy_row['Amount Fiat'] - sell_row['Amount Fiat'])
                max_fiat = max(buy_row['Amount Fiat'], sell_row['Amount Fiat'], 0.01)
                
                if (fiat_diff / max_fiat) < 0.05: # 5% tolerance just in case of spread differences
                    df.loc[group.index, 'Swap_ID'] = f"SWAP_{swap_id_counter}"
                    swap_id_counter += 1
                
    return metadata, df

def get_available_years(df):
    if df.empty or 'Timestamp' not in df.columns:
        return []
    years = df['Timestamp'].dt.year.unique()
    return sorted(list(years))
