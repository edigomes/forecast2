#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 EXEMPLO: Force Excess Production - Produção mesmo com estoque suficiente

Este exemplo demonstra como usar o parâmetro `force_excess_production` para
forçar a produção mesmo quando há estoque suficiente.
"""

from mrp import MRPOptimizer
import json

def exemplo_force_excess_production():
    """
    Demonstra produção forçada mesmo com estoque suficiente
    """
    print("🎯 EXEMPLO: Force Excess Production")
    print("=" * 50)
    
    optimizer = MRPOptimizer()
    
    # Cenário: Estoque alto, demanda baixa
    daily_demands = {
        '2024-01-15': 100,
        '2024-01-16': 150,
        '2024-01-17': 200,
        '2024-01-18': 120,
        '2024-01-19': 80
    }
    
    initial_stock = 5000  # Estoque muito alto
    leadtime_days = 5
    
    print(f"📦 Estoque inicial: {initial_stock}")
    print(f"📈 Demanda total: {sum(daily_demands.values())}")
    print(f"🕐 Lead time: {leadtime_days} dias")
    print()
    
    # Teste 1: Cenário normal (sem produção em excesso)
    print("🔍 TESTE 1: Cenário Normal")
    print("-" * 30)
    
    result_normal = optimizer.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=initial_stock,
        leadtime_days=leadtime_days,
        period_start_date='2024-01-10',
        period_end_date='2024-01-30',
        start_cutoff_date='2024-01-10',
        end_cutoff_date='2024-01-30'
    )
    
    print(f"Batches gerados: {len(result_normal['batches'])}")
    print(f"Produção em excesso: {result_normal.get('has_excess_production', False)}")
    print("✅ Resultado: Nenhum lote produzido (estoque suficiente)")
    print()
    
    # Teste 2: Forçar produção em excesso
    print("🔍 TESTE 2: Forçar Produção em Excesso")
    print("-" * 30)
    
    result_excess = optimizer.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=initial_stock,
        leadtime_days=leadtime_days,
        period_start_date='2024-01-10',
        period_end_date='2024-01-30',
        start_cutoff_date='2024-01-10',
        end_cutoff_date='2024-01-30',
        force_excess_production=True
    )
    
    print(f"Batches gerados: {len(result_excess['batches'])}")
    print(f"Produção em excesso: {result_excess.get('has_excess_production', False)}")
    
    if result_excess['batches']:
        batch = result_excess['batches'][0]
        print(f"📦 Lote 1:")
        print(f"  - Quantidade: {batch['quantity']}")
        print(f"  - Data pedido: {batch['order_date']}")
        print(f"  - Data chegada: {batch['arrival_date']}")
        print(f"  - Produção em excesso: {batch['analytics']['excess_production']}")
        print(f"  - Urgência: {batch['analytics']['urgency_level']}")
        print(f"  - Estoque antes: {batch['analytics']['stock_before_arrival']}")
        print(f"  - Estoque depois: {batch['analytics']['stock_after_arrival']}")
        print(f"  - Dias de cobertura: {batch['analytics']['coverage_days']}")
    
    print()
    print("🎯 IMPORTANTE:")
    print("- Analytics são idênticos aos lotes normais")
    print("- Único campo diferente: 'excess_production': True")
    print("- Campo no resultado: 'has_excess_production': True")
    print("- Urgência permanece 'normal'")
    
    return result_excess

if __name__ == "__main__":
    exemplo_force_excess_production() 