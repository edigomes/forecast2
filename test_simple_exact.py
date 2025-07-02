#!/usr/bin/env python3
"""
Teste simples para confirmar exact_quantity_match com números redondos
"""

from mrp import MRPOptimizer, OptimizationParams

def test_simple_exact():
    print("🎯 TESTE SIMPLES: exact_quantity_match=True")
    print("="*50)
    
    # Configuração simples
    initial_stock = 500.0
    total_demand = 2000.0  # Demanda redonda
    expected_production = total_demand - initial_stock  # = 1500.0
    
    # Demanda que resulta exatamente em 2000 unidades
    daily_demands = {
        "2024-01": 64.516129,  # 31 dias = 2000.0 exato
    }
    
    params = OptimizationParams(
        min_batch_size=100.0,
        max_batch_size=1000.0,
        safety_days=0
    )
    
    optimizer = MRPOptimizer(params)
    
    result = optimizer.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=initial_stock,
        leadtime_days=30,
        period_start_date="2024-01-01",
        period_end_date="2024-01-31",
        start_cutoff_date="2023-12-01",
        end_cutoff_date="2024-02-29",
        exact_quantity_match=True,
        ignore_safety_stock=True
    )
    
    batches = result['batches']
    total_produced = sum(batch['quantity'] for batch in batches)
    
    print(f"📊 Resultados:")
    print(f"   Estoque inicial: {initial_stock}")
    print(f"   Demanda total: {total_demand}")
    print(f"   Produção esperada: {expected_production}")
    print(f"   Produção real: {total_produced}")
    print(f"   Diferença: {abs(total_produced - expected_production):.6f}")
    print(f"   Lotes: {len(batches)}")
    
    for i, batch in enumerate(batches, 1):
        print(f"      Lote {i}: {batch['quantity']:.3f}")
    
    # Verificar precisão
    is_exact = abs(total_produced - expected_production) < 0.001
    print(f"\n{'✅ PERFEITO' if is_exact else '❌ ERRO'}")
    
    return is_exact

if __name__ == "__main__":
    test_simple_exact() 