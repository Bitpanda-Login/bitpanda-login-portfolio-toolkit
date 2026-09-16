def reconcile_balances(fifo, zero_cost_consumptions):
    """
    Generates warnings about the final state of the portfolio.
    """
    warnings = []
    
    for asset, lots in fifo.inventory.items():
        fifo_balance = sum(lot.qty for lot in lots)
        if fifo_balance < -1e-8:
            warnings.append(f"WARNING: Balance negativo en FIFO para {asset}: {fifo_balance:.8f}")
            
    for asset, qty in zero_cost_consumptions.items():
        if qty > 1e-8:
            warnings.append(f"INFO: Se vendieron {qty:.8f} de {asset} sin coste histórico (se asumió coste 0 EUR).")
            
    return warnings
