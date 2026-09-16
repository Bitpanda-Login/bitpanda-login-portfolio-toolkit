import json
from collections import defaultdict, deque
import os
import pandas as pd

class Lot:
    def __init__(self, date, qty, total_cost_eur, origin_type='Buy'):
        self.date = date
        self.qty = qty
        self.total_cost_eur = total_cost_eur
        self.unit_cost = total_cost_eur / qty if qty > 0 else 0.0
        self.origin_type = origin_type

    def to_dict(self):
        d_str = self.date.isoformat() if pd.notnull(self.date) else None
        return {
            'date': d_str,
            'qty': self.qty,
            'total_cost_eur': self.total_cost_eur,
            'unit_cost': self.unit_cost,
            'origin_type': self.origin_type
        }

    @classmethod
    def from_dict(cls, data):
        d = pd.to_datetime(data['date']) if data.get('date') else None
        return cls(d, data['qty'], data.get('total_cost_eur', data['qty']*data['unit_cost']), data.get('origin_type', 'Buy'))

class FIFOEngine:
    def __init__(self):
        self.inventory = defaultdict(deque) # { asset: deque([Lot, ...]) }
    
    def add_lot(self, asset, date, qty, total_cost_eur, origin_type='Buy'):
        if qty <= 0:
            return
        self.inventory[asset].append(Lot(date, qty, total_cost_eur, origin_type))
        
    def consume_lots(self, asset, qty_to_sell):
        """
        Consume 'qty_to_sell' of 'asset' using FIFO.
        Returns total cost basis of the consumed lots.
        """
        remaining_to_sell = qty_to_sell
        total_cost_basis = 0.0
        
        if asset not in self.inventory or not self.inventory[asset]:
            return 0.0

        while remaining_to_sell > 0 and self.inventory[asset]:
            oldest_lot = self.inventory[asset][0]
            
            if oldest_lot.qty <= remaining_to_sell:
                total_cost_basis += oldest_lot.qty * oldest_lot.unit_cost
                remaining_to_sell -= oldest_lot.qty
                self.inventory[asset].popleft()
            else:
                total_cost_basis += remaining_to_sell * oldest_lot.unit_cost
                oldest_lot.qty -= remaining_to_sell
                oldest_lot.total_cost_eur = oldest_lot.qty * oldest_lot.unit_cost
                remaining_to_sell = 0
                
        return total_cost_basis

    def save_state(self, filepath):
        state = {}
        for asset, dq in self.inventory.items():
            state[asset] = [lot.to_dict() for lot in dq]
                
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)

    def load_state(self, filepath):
        if not os.path.exists(filepath):
            return False
            
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
        self.inventory = defaultdict(deque)
        for asset, lots_data in state.items():
            for lot_data in lots_data:
                self.inventory[asset].append(Lot.from_dict(lot_data))
        return True
