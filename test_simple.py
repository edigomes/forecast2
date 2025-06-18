#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples da correção
"""

import pandas as pd
from modelo import ModeloAjustado

# Dados reais
html_data = {
    "date_iso": "2025-07-01T00:00:00",
    "explanation_data": {
        "seasonality_mode": "multiplicative",
        "seasonal_pattern": {
            "1": 0.6837204206836109,
            "2": 0.7272129710780018,
            "3": 0.9127957931638914,
            "4": 0.7973269062226118,
            "5": 0.6944566170026292,
            "6": 0.804666958808063,
            "7": 0.8886941279579317,  # JULHO
            "8": 0.9524539877300613,
            "9": 1.1855828220858895,
            "10": 1.513584574934268,
            "11": 1.5547765118317265,
            "12": 1.124780893952673
        },
        "data_points": 29,
        "confidence_score": "Media",
        "mape": 23.163763007474643,
        "r2": 0.40467070728000276,
        "outlier_count": 0,
        "data_completeness": 100,
        "seasonal_strength": 1.7400172193688208,
        "trend_strength": 0.4651627993773888,
        "training_period": {
            "start": "2023-01-31",
            "end": "2025-05-31",
            "months": 29
        },
        "trend_slope": 18.630295566502483,
        "std": 528.049079205012
    },
    "prediction": {
        "ds": "2025-07-01 00:00:00",
        "trend": 1380.92,
        "yearly": -153.7,
        "yhat": 1227.22,
        "yhat_lower": 502.75,
        "yhat_upper": 1951.69
    },
    "item_id": 1687
}

# Teste
item_id = html_data['item_id']
prediction = html_data['prediction']
explanation_data = html_data['explanation_data']
date = pd.to_datetime(html_data['date_iso'])

print("Data:", date)
print("Mes:", date.month)
print("Seasonality Mode:", explanation_data['seasonality_mode'])

# Verificar seasonal_pattern
seasonal_pattern = explanation_data['seasonal_pattern']
print("\nSeasonal Pattern:")
for month, factor in seasonal_pattern.items():
    print(f"  Mes {month}: {factor}")

# Teste de acesso
july_factor_str = seasonal_pattern.get("7")
july_factor_int = seasonal_pattern.get(7)

print(f"\nJULHO (mes 7):")
print(f"  seasonal_pattern['7'] (string): {july_factor_str}")
print(f"  seasonal_pattern[7] (int): {july_factor_int}")
print(f"  date.month: {date.month} (tipo: {type(date.month)})")

# Teste da correção
factor = seasonal_pattern.get(date.month, seasonal_pattern.get(str(date.month), 1.0))
print(f"  CORRECAO: factor = {factor}")

if factor < 0.95:
    percentage = (1 - factor) * 100
    print(f"  RESULTADO: {percentage:.1f}% abaixo da media")
    
print(f"\nTESTE COMPLETO:")
print(f"factor = {factor}")
print(f"factor < 0.95? {factor < 0.95}")
print(f"percentage = (1 - {factor}) * 100 = {(1 - factor) * 100:.1f}%") 