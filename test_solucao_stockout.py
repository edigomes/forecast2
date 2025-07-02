"""
🎯 TESTE: Soluções para Evitar Stockout com Lead Time Longo
Demonstra 3 configurações que resolvem o problema de estoque negativo
"""

import json
from mrp import MRPOptimizer, OptimizationParams

def test_solucao_stockout():
    """Testa 3 soluções para evitar stockout com lead time longo"""
    
    # Dados originais do usuário
    dados_usuario = {
        "daily_demands": {
            "2025-07": 72.8763440860215,
            "2025-08": 72.8763440860215, 
            "2025-09": 75.30555555555556,
            "2025-10": 72.8763440860215,
            "2025-11": 75.30555555555556,
            "2025-12": 72.8763440860215
        },
        "initial_stock": 3479,
        "leadtime_days": 50,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-05-01", 
        "end_cutoff_date": "2025-12-31",
        "include_extended_analytics": True
    }
    
    print("=" * 80)
    print("🎯 SOLUÇÕES PARA EVITAR STOCKOUT COM LEAD TIME LONGO")
    print("=" * 80)
    
    # SOLUÇÃO 1: Margem Mínima de Segurança (RECOMENDADA)
    print("\n📊 SOLUÇÃO 1: MARGEM MÍNIMA DE SEGURANÇA")
    print("-" * 50)
    
    params_solucao1 = OptimizationParams(
        safety_days=3,                    # ✅ Reduzido para mínimo
        service_level=0.92,               # ✅ Menos conservador que 0.955
        auto_calculate_max_batch_size=True,
        enable_consolidation=True,
        min_batch_size=1
    )
    
    optimizer1 = MRPOptimizer(params_solucao1)
    resultado1 = optimizer1.calculate_batches_with_start_end_cutoff(
        **dados_usuario,
        ignore_safety_stock=False        # ✅ Permitir margem mínima
    )
    
    print(f"✅ Lotes: {len(resultado1['batches'])}")
    print(f"✅ Estoque mínimo: {resultado1['analytics']['summary']['minimum_stock']:.2f}")
    print(f"✅ Stockout: {'SIM' if resultado1['analytics']['summary']['stockout_occurred'] else 'NÃO'}")
    
    # SOLUÇÃO 2: Antecipação Maior dos Pedidos  
    print("\n🚀 SOLUÇÃO 2: MAIOR ANTECIPAÇÃO DOS PEDIDOS")
    print("-" * 50)
    
    params_solucao2 = OptimizationParams(
        safety_days=10,                   # ✅ Mais dias de antecipação
        auto_calculate_max_batch_size=True,
        enable_consolidation=True,
        min_batch_size=1
    )
    
    optimizer2 = MRPOptimizer(params_solucao2)
    resultado2 = optimizer2.calculate_batches_with_start_end_cutoff(
        **dados_usuario,
        ignore_safety_stock=True         # ✅ Ignorar safety stock mas compensar com antecipação
    )
    
    print(f"✅ Lotes: {len(resultado2['batches'])}")
    print(f"✅ Estoque mínimo: {resultado2['analytics']['summary']['minimum_stock']:.2f}")
    print(f"✅ Stockout: {'SIM' if resultado2['analytics']['summary']['stockout_occurred'] else 'NÃO'}")
    
    # SOLUÇÃO 3: Lotes Mais Frequentes
    print("\n📦 SOLUÇÃO 3: LOTES MAIS FREQUENTES")
    print("-" * 50)
    
    params_solucao3 = OptimizationParams(
        safety_days=5,
        auto_calculate_max_batch_size=True,
        enable_consolidation=True,
        min_batch_size=1,
        max_batches_long_leadtime=4       # ✅ 4 lotes em vez de 3
    )
    
    optimizer3 = MRPOptimizer(params_solucao3)
    resultado3 = optimizer3.calculate_batches_with_start_end_cutoff(
        **dados_usuario,
        ignore_safety_stock=True
    )
    
    print(f"✅ Lotes: {len(resultado3['batches'])}")
    print(f"✅ Estoque mínimo: {resultado3['analytics']['summary']['minimum_stock']:.2f}")
    print(f"✅ Stockout: {'SIM' if resultado3['analytics']['summary']['stockout_occurred'] else 'NÃO'}")
    
    # COMPARAÇÃO FINAL
    print("\n" + "=" * 80)
    print("📈 COMPARAÇÃO DAS SOLUÇÕES")
    print("=" * 80)
    
    solucoes = [
        ("Solução 1 (Margem Mínima)", resultado1),
        ("Solução 2 (Mais Antecipação)", resultado2),
        ("Solução 3 (Mais Lotes)", resultado3)
    ]
    
    for nome, resultado in solucoes:
        analytics = resultado['analytics']['summary']
        print(f"\n🎯 {nome}:")
        print(f"   • Lotes: {analytics['total_batches']}")
        print(f"   • Produção Total: {analytics['total_produced']:,.0f}")
        print(f"   • Estoque Mínimo: {analytics['minimum_stock']:,.2f}")
        print(f"   • Stockout: {'❌ SIM' if analytics['stockout_occurred'] else '✅ NÃO'}")
        
        if 'extended_analytics' in resultado['analytics']:
            custo = resultado['analytics']['extended_analytics']['cost_analysis']['total_cost']
            print(f"   • Custo Total: R$ {custo:,.2f}")
    
    # RECOMENDAÇÃO
    print("\n" + "🎯" * 20)
    print("RECOMENDAÇÃO: Use Solução 1 (Margem Mínima)")
    print("• Balance entre segurança e custo")
    print("• Evita stockouts sem excesso de estoque")
    print("• Configuração mais robusta para lead times longos")

if __name__ == "__main__":
    test_solucao_stockout() 