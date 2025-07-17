#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso da funcionalidade force_informative_batches
"""

import json
from mrp import MRPOptimizer

# Dados de exemplo (cenário onde não há necessidade de produção)
dados_exemplo = {
    "daily_demands": {
        "2025-08": 1.6212903225806452
    },
    "initial_stock": 174,
    "leadtime_days": 20,
    "period_start_date": "2025-08-01",
    "period_end_date": "2025-08-31",
    "start_cutoff_date": "2025-08-01",
    "end_cutoff_date": "2025-08-31",
    "include_extended_analytics": True,
    "ignore_safety_stock": True,
    "force_informative_batches": True  # 🎯 NOVA FLAG
}

# Criar otimizador
optimizer = MRPOptimizer()

# Executar com lotes informativos
resultado = optimizer.calculate_batches_with_start_end_cutoff(**dados_exemplo)

print("=== RESULTADO COM force_informative_batches=True ===")
print(f"Batches gerados: {len(resultado['batches'])}")
print(f"Batches reais (analytics): {resultado['analytics']['summary']['total_batches']}")
print(f"Produção real: {resultado['analytics']['summary']['total_produced']}")
print(f"Estoque final: {resultado['analytics']['summary']['final_stock']}")
print()

# Mostrar detalhes do lote informativo
if resultado['batches']:
    batch = resultado['batches'][0]
    print("=== DETALHES DO LOTE INFORMATIVO ===")
    print(f"📅 Data pedido: {batch['order_date']}")
    print(f"🚚 Data chegada: {batch['arrival_date']}")
    print(f"📦 Quantidade: {batch['quantity']}")
    print(f"💡 Explicação: {batch['analytics']['explanation']}")
    print(f"🔧 Estratégia: {batch['analytics']['strategy_explanation']}")
    print(f"📊 Ratio demanda: {batch['quantity']/(1.62*31):.1f}x (agora sempre 1.0x - quantidade = demanda total)")
    print()

# Exemplo de JSON de saída
output_json = json.dumps(resultado, indent=2, ensure_ascii=False)
print("JSON de saída (primeiros 1000 caracteres):")
print(output_json[:1000] + "..." if len(output_json) > 1000 else output_json) 