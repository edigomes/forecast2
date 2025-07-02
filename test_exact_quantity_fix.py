#!/usr/bin/env python3
"""
Teste para verificar se exact_quantity_match agora está funcionando corretamente
após a correção do bug que gerava lotes muito grandes.
"""

from mrp import MRPOptimizer, OptimizationParams

def test_exact_quantity_match():
    """Testa se exact_quantity_match produz exatamente a quantidade necessária"""
    
    print("="*80)
    print("TESTE: EXACT_QUANTITY_MATCH = True")
    print("="*80)
    
    # Configuração do teste
    initial_stock = 1000.0
    leadtime_days = 60  # Lead time longo para testar cenário crítico
    
    # Demanda total: 5000 unidades
    daily_demands = {
        "2024-01": 100.0,  # 31 dias = 3100
        "2024-02": 65.5,   # 29 dias = 1900  
        # Total: 5000 unidades
    }
    
    # Quantidade que DEVE ser produzida: 5000 - 1000 = 4000 unidades
    expected_production = 5000.0 - initial_stock
    
    print(f"📊 Configuração do teste:")
    print(f"   - Estoque inicial: {initial_stock}")
    print(f"   - Demanda total: 5000 unidades")
    print(f"   - Lead time: {leadtime_days} dias")
    print(f"   - Produção esperada (exact): {expected_production} unidades")
    print()
    
    # Criar otimizador
    params = OptimizationParams(
        min_batch_size=100.0,
        max_batch_size=2000.0,  # Limite para forçar múltiplos lotes
        safety_days=0,  # Sem segurança extra
        setup_cost=250.0
    )
    
    optimizer = MRPOptimizer(params)
    
    # Teste com exact_quantity_match=True
    print("🎯 Testando com exact_quantity_match=True:")
    
    result = optimizer.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=initial_stock,
        leadtime_days=leadtime_days,
        period_start_date="2024-01-01",
        period_end_date="2024-02-29",
        start_cutoff_date="2023-11-01",
        end_cutoff_date="2024-03-31",
        exact_quantity_match=True,  # 🎯 TESTE PRINCIPAL
        ignore_safety_stock=True   # Para ter controle total
    )
    
    # Analisar resultados
    batches = result['batches']
    total_produced = sum(batch['quantity'] for batch in batches)
    
    print(f"\n📋 Resultados:")
    print(f"   - Total de lotes: {len(batches)}")
    print(f"   - Total produzido: {total_produced}")
    print(f"   - Produção esperada: {expected_production}")
    print(f"   - Diferença: {total_produced - expected_production:.2f}")
    print(f"   - Precisão: {abs(total_produced - expected_production) < 0.01}")
    
    print(f"\n📦 Detalhes dos lotes:")
    for i, batch in enumerate(batches, 1):
        print(f"   Lote {i}: {batch['quantity']:.2f} unidades - {batch['order_date']} → {batch['arrival_date']}")
    
    # Verificar estoque final
    analytics = result['analytics']
    final_stock = analytics['summary']['final_stock']
    expected_final_stock = initial_stock + total_produced - 5000
    
    print(f"\n📈 Análise de estoque:")
    print(f"   - Estoque final: {final_stock}")
    print(f"   - Estoque final esperado: {expected_final_stock:.2f}")
    print(f"   - Diferença de estoque: {abs(final_stock - expected_final_stock):.2f}")
    
    # Validação final
    is_exact = abs(total_produced - expected_production) < 0.01
    
    print(f"\n{'✅ TESTE PASSOU' if is_exact else '❌ TESTE FALHOU'}")
    print(f"Exact quantity match está {'funcionando' if is_exact else 'QUEBRADO'}!")
    
    if not is_exact:
        print(f"\n🚨 PROBLEMA: Era esperado {expected_production} unidades, mas foi produzido {total_produced}")
        print(f"   Excesso de produção: {total_produced - expected_production:.2f} unidades")
        print(f"   Percentual de excesso: {((total_produced - expected_production) / expected_production * 100):.1f}%")
    
    return is_exact

def test_comparison_without_exact():
    """Testa comportamento normal (sem exact_quantity_match) para comparação"""
    
    print("\n" + "="*80)
    print("TESTE COMPARATIVO: EXACT_QUANTITY_MATCH = False")
    print("="*80)
    
    initial_stock = 1000.0
    leadtime_days = 60
    
    daily_demands = {
        "2024-01": 100.0,  
        "2024-02": 65.5,   
    }
    
    params = OptimizationParams(
        min_batch_size=100.0,
        max_batch_size=2000.0,
        safety_days=0,
        setup_cost=250.0
    )
    
    optimizer = MRPOptimizer(params)
    
    result = optimizer.calculate_batches_with_start_end_cutoff(
        daily_demands=daily_demands,
        initial_stock=initial_stock,
        leadtime_days=leadtime_days,
        period_start_date="2024-01-01",
        period_end_date="2024-02-29",
        start_cutoff_date="2023-11-01",
        end_cutoff_date="2024-03-31",
        exact_quantity_match=False,  # Comportamento normal
        ignore_safety_stock=True
    )
    
    batches = result['batches']
    total_produced = sum(batch['quantity'] for batch in batches)
    expected_production = 4000.0
    
    print(f"📊 Resultado sem exact_quantity_match:")
    print(f"   - Total produzido: {total_produced}")
    print(f"   - Diferença vs exact: {total_produced - expected_production:.2f}")
    print(f"   - Lotes criados: {len(batches)}")
    
    return total_produced

if __name__ == "__main__":
    # Executar testes
    exact_works = test_exact_quantity_match()
    normal_production = test_comparison_without_exact()
    
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    print(f"✅ Exact quantity match: {'FUNCIONANDO' if exact_works else 'QUEBRADO'}")
    print(f"📊 Produção normal: {normal_production:.2f} unidades")
    print(f"🎯 Produção exact: 4000.00 unidades")
    
    if exact_works:
        print("\n🎉 CORREÇÃO BEM-SUCEDIDA!")
        print("   O exact_quantity_match agora produz exatamente a quantidade necessária.")
    else:
        print("\n🚨 CORREÇÃO AINDA NECESSÁRIA!")
        print("   O exact_quantity_match ainda está gerando lotes muito grandes.") 