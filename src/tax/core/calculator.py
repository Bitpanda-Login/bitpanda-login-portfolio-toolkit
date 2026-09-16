import pandas as pd
from collections import defaultdict
from .parser import parse_bitpanda_csv
from .fifo import FIFOEngine
from .classifier import classify_transaction, FiscalCategory
from .reconciliation import reconcile_balances

def calculate_taxes(filepath, year, fifo_prev_path=None, end_date=None, fifo_start_date=None):
    metadata, df_all = parse_bitpanda_csv(filepath)
    
    # Pre-scan: detect Bitpanda promotional/listing-reward tokens.
    # A token is "promotional" if it NEVER appears in a standalone 'buy' transaction
    # (only received via transfer/deposit/airdrop, possibly also via swap).
    # These tokens are taxable as Non-Transmission Gains (casilla 0304) when received.
    #
    # Method: assets whose FIRST appearance in the CSV is a 'transfer'/'deposit' incoming,
    # AND that have no standalone 'buy' (outside of swaps) anywhere in the history.
    standalone_buys = set(
        df_all[
            (df_all['Transaction Type'] == 'buy') &
            (df_all['Swap_ID'].isna())
        ]['Asset'].unique()
    )
    # Also find assets whose first incoming event is a transfer (not a buy)
    # Exclude fiat currencies and non-crypto assets (they will never have a buy)
    FIAT_CURRENCIES = {'EUR', 'USD', 'GBP', 'CHF', 'USDT', 'USDC', 'BUSD', 'DAI'}
    crypto_only = df_all[~df_all['Asset'].isin(FIAT_CURRENCIES)]
    # Use "Asset type" column if present to filter only Cryptocurrency
    if 'Asset type' in df_all.columns:
        crypto_only = df_all[df_all['Asset type'] == 'Cryptocurrency']
    
    first_incoming = (
        crypto_only[crypto_only['In/Out'] == 'incoming']
        .sort_values('Timestamp')
        .groupby('Asset')
        .first()
        .reset_index()
    )
    transfer_first_assets = set(
        first_incoming[
            first_incoming['Transaction Type'].isin(['transfer', 'deposit'])
        ]['Asset']
    )
    # Promo = never independently bought AND first seen via transfer/deposit
    promo_assets = transfer_first_assets - standalone_buys

    
    df_process = df_all.copy()
    fifo = FIFOEngine()
    if fifo_prev_path:
        fifo.load_state(fifo_prev_path)
        df_process = df_process[df_process['Timestamp'].dt.year >= int(year)].copy()
    else:
        df_process = df_process[df_process['Timestamp'].dt.year <= int(year)].copy()
        
    if end_date:
        df_process = df_process[df_process['Timestamp'] <= pd.to_datetime(end_date, utc=True)].copy()

    # Blockpit compatibility mode: ignore all acquisition lots before this date.
    # Use this to match Blockpit's FIFO state when they only imported data from a specific date.
    # Example: --fifo-start-date 2022-01-01 excludes all 2021 buy lots (expensive AVAX, MIOTA etc)
    # making results consistent with a Blockpit account connected in early 2022.
    fifo_start_ts = pd.to_datetime(fifo_start_date, utc=True) if fifo_start_date else None

        
    results = {
        'capital_gains': 0.0,
        'capital_losses': 0.0,
        'mobile_capital_income': 0.0,
        'non_transmission_gains': 0.0,
        'fees_not_deducted': 0.0,
        'asset_summary': {},
        'transactions': [],
        'warnings': []
    }
    
    zero_cost_consumptions = defaultdict(float)
    
    # Pre-process swaps to link them
    swaps_dict = {}
    for idx, row in df_process.iterrows():
        swap_id = row.get('Swap_ID')
        if swap_id:
            if swap_id not in swaps_dict:
                swaps_dict[swap_id] = {'buy': None, 'sell': None}
            tx_type = row['Transaction Type']
            if tx_type in ['buy', 'sell']:
                swaps_dict[swap_id][tx_type] = row

    processed_swaps = set()
    
    for idx, row in df_process.iterrows():
        tx_year = row['Timestamp'].year
        tx_type = row['Transaction Type']
        category = classify_transaction(row)
        
        asset = row['Asset']
        amount_asset = row['Amount Asset']
        amount_fiat = row['Amount Fiat']
        fee_eur = row['Fee'] if row.get('Fee asset') == 'EUR' else 0.0
        
        is_target_year = (tx_year == int(year))
        
        if category == FiscalCategory.IGNORED:
            continue
            
        elif category == FiscalCategory.SWAP:
            swap_id = row['Swap_ID']
            if swap_id in processed_swaps:
                continue # Already processed this pair
                
            processed_swaps.add(swap_id)
            swap_data = swaps_dict[swap_id]
            sell_row = swap_data['sell']
            buy_row = swap_data['buy']
            
            if not sell_row is None and not buy_row is None:
                # The sell side generates a capital gain
                sell_asset = sell_row['Asset']
                sell_qty = sell_row['Amount Asset']
                sell_fiat = sell_row['Amount Fiat']
                sell_fee = sell_row['Fee'] if sell_row.get('Fee asset') == 'EUR' else 0.0
                
                # Consume FIFO for the asset being sold
                current_fifo_qty = sum(lot.qty for lot in fifo.inventory[sell_asset])
                if current_fifo_qty < sell_qty:
                    zero_cost_consumptions[sell_asset] += (sell_qty - current_fifo_qty)
                    
                cost_basis = fifo.consume_lots(sell_asset, sell_qty)
                proceeds = sell_fiat - sell_fee
                gain_loss = proceeds - cost_basis
                
                if tx_year == int(year):
                    if gain_loss > 0:
                        results['capital_gains'] += gain_loss
                    else:
                        results['capital_losses'] += gain_loss
                        
                    if sell_asset not in results['asset_summary']:
                        results['asset_summary'][sell_asset] = {'gains': 0.0, 'losses': 0.0, 'net': 0.0}
                    if gain_loss > 0:
                        results['asset_summary'][sell_asset]['gains'] += gain_loss
                    else:
                        results['asset_summary'][sell_asset]['losses'] += gain_loss
                    results['asset_summary'][sell_asset]['net'] += gain_loss
                    
                    results['transactions'].append({
                        'Date': sell_row['Timestamp'],
                        'Type': 'Swap (Sell)',
                        'Asset': sell_asset,
                        'Quantity': sell_qty,
                        'Value EUR': sell_fiat,
                        'Cost Basis': cost_basis,
                        'Gain/Loss': gain_loss
                    })
                    
                # The buy side creates a new FIFO lot
                buy_asset = buy_row['Asset']
                buy_qty = buy_row['Amount Asset']
                buy_fiat = buy_row['Amount Fiat']
                buy_fee = buy_row['Fee'] if buy_row.get('Fee asset') == 'EUR' else 0.0
                
                # The cost basis of the new asset is the proceeds of the sell (or the fiat value of the buy)
                # Technically they are the same in a swap, we'll use buy_fiat + buy_fee
                fifo.add_lot(buy_asset, buy_row['Timestamp'], buy_qty, buy_fiat + buy_fee, origin_type='Swap')
                
                if tx_year == int(year):
                    results['transactions'].append({
                        'Date': buy_row['Timestamp'],
                        'Type': 'Swap (Buy)',
                        'Asset': buy_asset,
                        'Quantity': buy_qty,
                        'Value EUR': buy_fiat,
                        'Cost Basis': buy_fiat + buy_fee,
                        'Gain/Loss': 0.0
                    })
        
        elif category == FiscalCategory.CAPITAL_GAIN_LOSS: # Sell
            current_fifo_qty = sum(lot.qty for lot in fifo.inventory[asset])
            if current_fifo_qty < amount_asset:
                zero_cost_consumptions[asset] += (amount_asset - current_fifo_qty)
                
            cost_basis = fifo.consume_lots(asset, amount_asset)
            proceeds = amount_fiat - fee_eur
            gain_loss = proceeds - cost_basis
            
            if is_target_year:
                if gain_loss > 0:
                    results['capital_gains'] += gain_loss
                else:
                    results['capital_losses'] += gain_loss
                    
                if asset not in results['asset_summary']:
                    results['asset_summary'][asset] = {'gains': 0.0, 'losses': 0.0, 'net': 0.0}
                if gain_loss > 0:
                    results['asset_summary'][asset]['gains'] += gain_loss
                else:
                    results['asset_summary'][asset]['losses'] += gain_loss
                results['asset_summary'][asset]['net'] += gain_loss
                
                results['transactions'].append({
                    'Date': row['Timestamp'],
                    'Type': 'Sell',
                    'Asset': asset,
                    'Quantity': amount_asset,
                    'Value EUR': amount_fiat,
                    'Cost Basis': cost_basis,
                    'Gain/Loss': gain_loss
                })
                
        elif category == FiscalCategory.TAX_NEUTRAL:
            if tx_type == 'buy':
                cost_eur = amount_fiat
                # In Blockpit compatibility mode, skip lots acquired before the FIFO start date.
                # This replicates what Blockpit does when it connects mid-history and lacks older buys.
                if fifo_start_ts is None or row['Timestamp'] >= fifo_start_ts:
                    fifo.add_lot(asset, row['Timestamp'], amount_asset, cost_eur + fee_eur, origin_type='Buy')

                
                if is_target_year:
                    results['transactions'].append({
                        'Date': row['Timestamp'],
                        'Type': 'Buy',
                        'Asset': asset,
                        'Quantity': amount_asset,
                        'Value EUR': amount_fiat,
                        'Cost Basis': cost_eur + fee_eur,
                        'Gain/Loss': 0.0
                    })
            elif tx_type in ['deposit', 'withdrawal', 'transfer', 'transfer(stake)', 'transfer(unstake)']:
                # All transfers are treated as neutral portfolio events UNLESS the asset
                # is a promotional token (never purchased via buy). In that case, the
                # first incoming transfer is treated as an Airdrop at the received market price.
                if fee_eur > 0 and is_target_year:
                    results['fees_not_deducted'] += fee_eur
                    
                in_out = row.get('In/Out')
                if in_out == 'incoming' and asset in promo_assets and amount_fiat > 0:
                    # Promotional/listing-reward token: treat as airdrop
                    market_price = row.get('Asset market price', 0)
                    cost_basis = amount_asset * market_price if market_price > 0 else amount_fiat
                    # Register as non-transmission gain (casilla 0304)
                    if is_target_year:
                        results['non_transmission_gains'] += amount_fiat
                        results['transactions'].append({
                            'Date': row['Timestamp'],
                            'Type': 'Airdrop/Promo',
                            'Asset': asset,
                            'Quantity': amount_asset,
                            'Value EUR': amount_fiat,
                            'Cost Basis': 0.0,
                            'Gain/Loss': 0.0
                        })
                    # Add to FIFO with received value as cost (avoids zero-cost sell later)
                    fifo.add_lot(asset, row['Timestamp'], amount_asset, amount_fiat, origin_type='Airdrop')

                    
        elif category == FiscalCategory.MOBILE_CAPITAL_INCOME: # Reward (Staking)
            if is_target_year:
                results['mobile_capital_income'] += amount_fiat
                results['transactions'].append({
                    'Date': row['Timestamp'],
                    'Type': 'Staking Reward',
                    'Asset': asset,
                    'Quantity': amount_asset,
                    'Value EUR': amount_fiat,
                    'Cost Basis': 0.0,
                    'Gain/Loss': 0.0
                })
            fifo.add_lot(asset, row['Timestamp'], amount_asset, amount_fiat, origin_type='Staking')
            
        elif category == FiscalCategory.NON_TRANSMISSION_GAIN: # Airdrop/Promo
            if is_target_year:
                results['non_transmission_gains'] += amount_fiat
                results['transactions'].append({
                    'Date': row['Timestamp'],
                    'Type': 'Airdrop/Promo',
                    'Asset': asset,
                    'Quantity': amount_asset,
                    'Value EUR': amount_fiat,
                    'Cost Basis': 0.0,
                    'Gain/Loss': 0.0
                })
            fifo.add_lot(asset, row['Timestamp'], amount_asset, amount_fiat, origin_type='Airdrop')
            
        # Stop processing if we've passed the target year
        if tx_year > int(year):
            break
            
    # Run reconciliation
    results['warnings'] = reconcile_balances(fifo, zero_cost_consumptions)
    
    return metadata, results, fifo
