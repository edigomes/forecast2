#!/usr/bin/env python3
"""
Validação final da correção de lead time zero
Testa múltiplos cenários para garantir que a correção é robusta
"""

import requests
import json

def test_scenario(name, data, expected_batches_min=1):
    """Testar um cenário específico"""
    print(f"\n🧪 Testando: {name}")
    print("-" * 40)
    
    try:
        response = requests.post(
            'http://localhost:5000/mrp_advanced',
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            batches = result.get('batches', [])
            analytics = result.get('analytics', {})
            summary = analytics.get('summary', {})
            
            print(f"📦 Lotes: {len(batches)}")
            print(f"📈 Atendimento: {summary.get('demand_fulfillment_rate', 0):.1f}%")
            print(f"🏭 Produção: {summary.get('total_produced', 0)}")
            print(f"📊 Stockouts: {'Não' if not summary.get('stockout_occurred', True) else 'Sim'}")
            
            # Verificar estratégia
            strategies = [b.get('analytics', {}).get('advanced_mrp_strategy') for b in batches]
            jit_count = strategies.count('just_in_time')
            print(f"⚡ Just-in-time: {jit_count}/{len(batches)} lotes")
            
            # Verificar timing
            timing_ok = all(
                batch.get('order_date') == batch.get('arrival_date') 
                for batch in batches
            )
            print(f"⏰ Timing correto: {'Sim' if timing_ok else 'Não'}")
            
            # Critérios de sucesso
            success = (
                len(batches) >= expected_batches_min and
                jit_count > 0 and
                timing_ok and
                not summary.get('stockout_occurred', True)
            )
            
            print(f"✅ Resultado: {'PASSOU' if success else 'FALHOU'}")
            return success
            
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    print("🔧 VALIDAÇÃO FINAL: Lead Time Zero")
    print("=" * 50)
    
    scenarios = []
    
    # Cenário 1: Original do usuário
    scenarios.append((
        "Caso original do usuário",
        {
            "sporadic_demand": {
                "2025-07-07": 4000,
                "2025-08-27": 4000,
                "2025-10-17": 4000
            },
            "initial_stock": 4422,
            "leadtime_days": 0,
            "period_start_date": "2025-01-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-01-01",
            "end_cutoff_date": "2025-12-31"
        },
        2  # Espera pelo menos 2 lotes
    ))
    
    # Cenário 2: Estoque zero
    scenarios.append((
        "Estoque inicial zero",
        {
            "sporadic_demand": {
                "2025-08-01": 1000,
                "2025-09-01": 1000
            },
            "initial_stock": 0,
            "leadtime_days": 0,
            "period_start_date": "2025-07-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-07-01",
            "end_cutoff_date": "2025-12-31"
        },
        2  # Deve criar 2 lotes
    ))
    
    # Cenário 3: Uma única demanda grande
    scenarios.append((
        "Demanda única grande",
        {
            "sporadic_demand": {"2025-08-15": 5000},
            "initial_stock": 1000,
            "leadtime_days": 0,
            "period_start_date": "2025-08-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-08-01",
            "end_cutoff_date": "2025-12-31"
        },
        1  # Deve criar 1 lote
    ))
    
    # Cenário 4: Múltiplas demandas pequenas
    scenarios.append((
        "Múltiplas demandas pequenas",
        {
            "sporadic_demand": {
                "2025-08-01": 500,
                "2025-08-05": 500,
                "2025-08-10": 500,
                "2025-08-15": 500
            },
            "initial_stock": 200,
            "leadtime_days": 0,
            "period_start_date": "2025-07-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-07-01",
            "end_cutoff_date": "2025-12-31"
        },
        2  # Espera pelo menos 2 lotes
    ))
    
    # Cenário 5: Com margem de segurança
    scenarios.append((
        "Com margem de segurança 10%",
        {
            "sporadic_demand": {"2025-08-20": 2000},
            "initial_stock": 500,
            "leadtime_days": 0,
            "safety_margin_percent": 10,
            "period_start_date": "2025-08-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-08-01",
            "end_cutoff_date": "2025-12-31"
        },
        1  # Deve criar 1 lote com 10% extra
    ))
    
    # Executar todos os cenários
    results = []
    for name, data, expected in scenarios:
        success = test_scenario(name, data, expected)
        results.append((name, success))
    
    # Resumo final
    print("\n" + "=" * 50)
    print("📋 RESUMO FINAL")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status:12} | {name}")
    
    print("-" * 50)
    print(f"🎯 Taxa de sucesso: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 VALIDAÇÃO COMPLETA BEM-SUCEDIDA!")
        print("✅ A correção de lead time zero está funcionando perfeitamente")
        print("✅ Todos os cenários foram atendidos corretamente")
        print("✅ Estratégia just-in-time implementada com sucesso")
    else:
        print(f"\n⚠️ Alguns cenários falharam ({total-passed} de {total})")
        print("Pode ser necessário ajustes adicionais")

if __name__ == "__main__":
    main() 