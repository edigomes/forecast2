import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MonteCarloResult:
    var_95: float
    cvar_95: float
    stockout_probability: float
    expected_stockouts: float
    service_level_mean: float
    service_level_std: float
    min_stock_p5: float
    min_stock_p50: float
    max_stock_p95: float
    demand_scenarios_summary: Dict


def run_monte_carlo_simulation(
    avg_demand: float,
    demand_std: float,
    leadtime_days: int,
    leadtime_std: float,
    initial_stock: float,
    batches: List[Dict],
    simulation_days: int = 180,
    n_simulations: int = 1000,
    seed: Optional[int] = None
) -> Dict:
    """Simulação Monte Carlo para análise de risco do plano MRP.
    
    Simula N cenários variando demanda diária e lead time para calcular
    distribuições de estoque, probabilidade de stockout e métricas de risco.
    """
    if avg_demand <= 0 or n_simulations <= 0 or simulation_days <= 0:
        return _empty_result()
    
    rng = np.random.default_rng(seed)
    
    min_stocks = np.zeros(n_simulations)
    final_stocks = np.zeros(n_simulations)
    stockout_counts = np.zeros(n_simulations)
    service_levels = np.zeros(n_simulations)
    
    batch_arrivals = _parse_batch_arrivals(batches)
    
    for sim in range(n_simulations):
        demands = rng.normal(avg_demand, max(demand_std, 0.01), simulation_days)
        demands = np.maximum(demands, 0)
        
        lt_variations = {}
        if leadtime_std > 0:
            for day, qty in batch_arrivals.items():
                lt_shift = int(round(rng.normal(0, leadtime_std)))
                new_day = max(0, day + lt_shift)
                lt_variations[new_day] = lt_variations.get(new_day, 0) + qty
        else:
            lt_variations = batch_arrivals.copy()
        
        stock = initial_stock
        min_stock = initial_stock
        stockouts = 0
        days_with_stock = 0
        
        for day in range(simulation_days):
            if day in lt_variations:
                stock += lt_variations[day]
            
            stock -= demands[day]
            
            if stock < 0:
                stockouts += 1
            else:
                days_with_stock += 1
            
            min_stock = min(min_stock, stock)
        
        min_stocks[sim] = min_stock
        final_stocks[sim] = stock
        stockout_counts[sim] = stockouts
        service_levels[sim] = days_with_stock / simulation_days * 100
    
    var_95 = float(np.percentile(min_stocks, 5))
    stocks_below_var = min_stocks[min_stocks <= var_95]
    cvar_95 = float(np.mean(stocks_below_var)) if len(stocks_below_var) > 0 else var_95
    
    stockout_probability = float(np.mean(stockout_counts > 0) * 100)
    
    return {
        'var_95': round(var_95, 2),
        'cvar_95': round(cvar_95, 2),
        'stockout_probability': round(stockout_probability, 2),
        'expected_stockouts_per_period': round(float(np.mean(stockout_counts)), 2),
        'service_level': {
            'mean': round(float(np.mean(service_levels)), 2),
            'std': round(float(np.std(service_levels)), 2),
            'p5': round(float(np.percentile(service_levels, 5)), 2),
            'p95': round(float(np.percentile(service_levels, 95)), 2)
        },
        'min_stock_distribution': {
            'p5': round(float(np.percentile(min_stocks, 5)), 2),
            'p25': round(float(np.percentile(min_stocks, 25)), 2),
            'p50': round(float(np.percentile(min_stocks, 50)), 2),
            'p75': round(float(np.percentile(min_stocks, 75)), 2),
            'p95': round(float(np.percentile(min_stocks, 95)), 2)
        },
        'final_stock_distribution': {
            'p5': round(float(np.percentile(final_stocks, 5)), 2),
            'p50': round(float(np.percentile(final_stocks, 50)), 2),
            'p95': round(float(np.percentile(final_stocks, 95)), 2)
        },
        'n_simulations': n_simulations,
        'simulation_days': simulation_days
    }


def _parse_batch_arrivals(batches: List[Dict]) -> Dict[int, float]:
    """Converte lista de batches em mapa de dia -> quantidade de chegada.
    
    Usa a menor arrival_date como dia 0 de referência.
    """
    arrivals = {}
    if not batches:
        return arrivals
    
    first_arrival = None
    for b in batches:
        arrival = b.get('arrival_date', '')
        if arrival:
            dt = pd.to_datetime(arrival)
            if first_arrival is None or dt < first_arrival:
                first_arrival = dt
    
    if first_arrival is None:
        return arrivals
    
    for b in batches:
        arrival = b.get('arrival_date', '')
        if arrival:
            dt = pd.to_datetime(arrival)
            day = max(0, (dt - first_arrival).days)
            qty = float(b.get('quantity', 0))
            arrivals[day] = arrivals.get(day, 0) + qty
    
    return arrivals


def _empty_result() -> Dict:
    return {
        'var_95': 0, 'cvar_95': 0, 'stockout_probability': 0,
        'expected_stockouts_per_period': 0,
        'service_level': {'mean': 100, 'std': 0, 'p5': 100, 'p95': 100},
        'min_stock_distribution': {'p5': 0, 'p25': 0, 'p50': 0, 'p75': 0, 'p95': 0},
        'final_stock_distribution': {'p5': 0, 'p50': 0, 'p95': 0},
        'n_simulations': 0, 'simulation_days': 0
    }
