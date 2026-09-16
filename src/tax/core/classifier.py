from enum import Enum

# Staking assets confirmed by Bitpanda platform (real staking, not promotional)
STAKING_ASSETS = {'ADA', 'AVAX', 'AXS', 'APE', 'VSN', 'DOT', 'ETH', 'SOL', 'MATIC', 'ATOM'}

class FiscalCategory(Enum):
    CAPITAL_GAIN_LOSS = "ganancia_perdida_patrimonial"
    MOBILE_CAPITAL_INCOME = "rendimiento_capital_mobiliario"
    NON_TRANSMISSION_GAIN = "ganancia_no_derivada"
    TAX_NEUTRAL = "neutral"
    SWAP = "swap"
    IGNORED = "ignored"

def classify_transaction(row):
    """
    Classifies a Bitpanda transaction row into a Spanish tax category.

    Classification logic designed to match Blockpit's approach:
    - sell / swap-sell → Capital Gain/Loss (savings base, casillas 1800-1814)
    - reward (any) → Non-Transmission Gain (general base, casilla 0304)
      NOTE: Blockpit classifies ALL Bitpanda rewards (including staking) as
      Airdrops/Non-Transmission Gains. While Spanish AEAT guidance is ambiguous,
      we mirror Blockpit for comparability. A tax advisor may argue for 0033.
    - buy → Tax Neutral (creates FIFO lot)
    - transfers / deposits / withdrawals → Tax Neutral (portfolio movement)
    """
    tx_type = row.get('Transaction Type')
    swap_id = row.get('Swap_ID')

    if swap_id is not None:
        return FiscalCategory.SWAP

    if tx_type == 'sell':
        return FiscalCategory.CAPITAL_GAIN_LOSS

    elif tx_type == 'buy':
        return FiscalCategory.TAX_NEUTRAL

    elif tx_type == 'reward':
        if row.get('Asset','') in STAKING_ASSETS:
            return FiscalCategory.MOBILE_CAPITAL_INCOME
        return FiscalCategory.NON_TRANSMISSION_GAIN

    elif tx_type in ['transfer', 'transfer(stake)', 'transfer(unstake)', 'deposit', 'withdrawal']:
        return FiscalCategory.TAX_NEUTRAL

    else:
        return FiscalCategory.TAX_NEUTRAL
