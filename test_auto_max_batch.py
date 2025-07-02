"""
🎯 TESTE: Auto-calculation do max_batch_size
Demonstra como o sistema pode otimizar automaticamente sem limitações artificiais
"""

import json
from mrp import MRPOptimizer, OptimizationParams

def test_auto_max_batch_size():
    """Testa otimização automática do max_batch_size"""
    
    # Dados de teste
    daily_demands = {
        "2025-07": 60.75, 
        "2025-08": 60.75, 
        "2025-09": 62.78, 
        "2025-10": 60.75, 
        "2025-11": 62.78, 
        "2025-12": 60.75
    }
    
    print("="*80)
    print("🎯 TESTE: AUTO-CALCULATION DO MAX_BATCH_SIZE")
    print("="*80)
    
    # TESTE 1: Configuração Manual (comportamento antigo)
    print("\n📊 TESTE 1: Max Batch Size MANUAL (6.418)")
    manual_params = OptimizationParams(
        setup_cost=75,
        holding_cost_rate=0.25,
        max_batch_size=6418,  # ⭐ Limitação manual
        auto_calculate_max_batch_size=False,  # ⭐ Desabilitado
        enable_consolidation=False,
        max_batches_long_leadtime=2
    )
    
    optimizer1 = MRPOptimizer(manual_params)
    result1 = optimizer1.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=0,
        leadtime_days=50,
        period_start_date="2025-07-01",
        period_end_date="2025-12-31",
        start_cutoff_date="2025-05-01",
        end_cutoff_date="2025-12-31"
    )
    
    print(f"  Lotes planejados: {len(result1['batches'])}")
    print(f"  Produção total: {result1['analytics']['summary']['total_produced']}")
    print(f"  EOQ teórico: {result1['analytics'].get('extended_analytics', {}).get('optimization_metrics', {}).get('theoretical_eoq', 'N/A')}")
    for i, batch in enumerate(result1['batches'], 1):
        print(f"    Lote {i}: {batch['quantity']} unidades")
    
    
    # TESTE 2: Auto-calculation Conservadora (4x EOQ)
    print("\n🎯 TESTE 2: Auto-calculation CONSERVADORA (4x EOQ)")
    auto_conservative_params = OptimizationParams(
        setup_cost=75,
        holding_cost_rate=0.25,
        max_batch_size=999999,  # ⭐ Valor alto = sem limitação prática
        auto_calculate_max_batch_size=True,  # ⭐ HABILITADO
        max_batch_multiplier=4.0,  # ⭐ 4x o EOQ
        enable_consolidation=False,
        max_batches_long_leadtime=5
    )
    
    optimizer2 = MRPOptimizer(auto_conservative_params)
    result2 = optimizer2.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=0,
        leadtime_days=50,
        period_start_date="2025-07-01",
        period_end_date="2025-12-31",
        start_cutoff_date="2025-05-01",
        end_cutoff_date="2025-12-31"
    )
    
    print(f"  Lotes planejados: {len(result2['batches'])}")
    print(f"  Produção total: {result2['analytics']['summary']['total_produced']}")
    print(f"  EOQ teórico: {result2['analytics'].get('extended_analytics', {}).get('optimization_metrics', {}).get('theoretical_eoq', 'N/A')}")
    for i, batch in enumerate(result2['batches'], 1):
        print(f"    Lote {i}: {batch['quantity']} unidades")
    
    # Calcular max_batch_size efetivo usado
    annual_demand = sum(daily_demands.values()) * 365 / 6  # Aproximação anual
    effective_max = optimizer2._get_effective_max_batch_size(annual_demand)
    print(f"  Max batch size efetivo calculado: {effective_max:.0f}")
    
    
    # TESTE 3: Auto-calculation Agressiva (6x EOQ)
    print("\n🚀 TESTE 3: Auto-calculation AGRESSIVA (6x EOQ)")
    auto_aggressive_params = OptimizationParams(
        setup_cost=50,  # ⭐ Setup mais barato
        holding_cost_rate=0.15,  # ⭐ Custo manutenção menor
        max_batch_size=999999,
        auto_calculate_max_batch_size=True,  # ⭐ HABILITADO
        max_batch_multiplier=6.0,  # ⭐ 6x o EOQ = lotes maiores
        enable_consolidation=False,
        max_batches_long_leadtime=3
    )
    
    optimizer3 = MRPOptimizer(auto_aggressive_params)
    result3 = optimizer3.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=0,
        leadtime_days=50,
        period_start_date="2025-07-01",
        period_end_date="2025-12-31",
        start_cutoff_date="2025-05-01",
        end_cutoff_date="2025-12-31"
    )
    
    print(f"  Lotes planejados: {len(result3['batches'])}")
    print(f"  Produção total: {result3['analytics']['summary']['total_produced']}")
    print(f"  EOQ teórico: {result3['analytics'].get('extended_analytics', {}).get('optimization_metrics', {}).get('theoretical_eoq', 'N/A')}")
    for i, batch in enumerate(result3['batches'], 1):
        print(f"    Lote {i}: {batch['quantity']} unidades")
    
    # Calcular max_batch_size efetivo usado
    effective_max3 = optimizer3._get_effective_max_batch_size(annual_demand)
    print(f"  Max batch size efetivo calculado: {effective_max3:.0f}")
    
    
    # TESTE 4: Auto-calculation com Valor Alto Manual (melhor dos mundos)
    print("\n✨ TESTE 4: Auto-calculation INTELIGENTE (2.5x EOQ + valor alto)")
    auto_smart_params = OptimizationParams(
        setup_cost=100,
        holding_cost_rate=0.20,
        max_batch_size=15000,  # ⭐ Limite alto mas sensato
        auto_calculate_max_batch_size=True,  # ⭐ HABILITADO
        max_batch_multiplier=2.5,  # ⭐ 2.5x EOQ (mais conservador)
        enable_consolidation=True,  # ⭐ Consolidação habilitada
        max_batches_long_leadtime=4
    )
    
    optimizer4 = MRPOptimizer(auto_smart_params)
    result4 = optimizer4.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=0,
        leadtime_days=50,
        period_start_date="2025-07-01",
        period_end_date="2025-12-31",
        start_cutoff_date="2025-05-01",
        end_cutoff_date="2025-12-31"
    )
    
    print(f"  Lotes planejados: {len(result4['batches'])}")
    print(f"  Produção total: {result4['analytics']['summary']['total_produced']}")
    print(f"  EOQ teórico: {result4['analytics'].get('extended_analytics', {}).get('optimization_metrics', {}).get('theoretical_eoq', 'N/A')}")
    for i, batch in enumerate(result4['batches'], 1):
        print(f"    Lote {i}: {batch['quantity']} unidades")
    
    effective_max4 = optimizer4._get_effective_max_batch_size(annual_demand)
    print(f"  Max batch size efetivo calculado: {effective_max4:.0f}")
    
    
    # COMPARAÇÃO FINAL
    print("\n" + "="*80)
    print("📊 COMPARAÇÃO DOS RESULTADOS")
    print("="*80)
    print(f"1. Manual (6.418):       {len(result1['batches'])} lotes, {result1['analytics']['summary']['total_produced']:.0f} produzido")
    print(f"2. Auto 4x EOQ:          {len(result2['batches'])} lotes, {result2['analytics']['summary']['total_produced']:.0f} produzido")
    print(f"3. Auto 6x EOQ:          {len(result3['batches'])} lotes, {result3['analytics']['summary']['total_produced']:.0f} produzido")
    print(f"4. Auto 2.5x + Consol:   {len(result4['batches'])} lotes, {result4['analytics']['summary']['total_produced']:.0f} produzido")
    
    print("\n🎯 CONCLUSÃO:")
    print("✅ O sistema PODE otimizar automaticamente sem max_batch_size fixo")
    print("✅ Use auto_calculate_max_batch_size=True + max_batch_multiplier")
    print("✅ Configuração recomendada: multiplier 2.5-4.0 + consolidation=True")
    print("✅ Para lotes ideais: setup_cost baixo + holding_cost médio")

if __name__ == "__main__":
    test_auto_max_batch_size() 