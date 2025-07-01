#!/usr/bin/env python3
"""
Test script para verificar correção do bug de lead time 5 dias
"""

import requests
import json
from datetime import datetime

def test_leadtime_5_fix():
    """Testar correção para lead time 5 dias"""
    
    print("🧪 Testando correção para lead time 5 dias...")
    
    # Dados EXATOS do problema reportado pelo usuário
    test_data = {
        "sporadic_demand": {
            "2025-07-07": 4000,
            "2025-08-27": 4000,
            "2025-10-17": 4000
        },
        "initial_stock": 4422,
        "leadtime_days": 5,  # 5 dias de lead time
        "period_start_date": "2025-01-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-01-01",
        "end_cutoff_date": "2025-12-31",
        "safety_margin_percent": 0,
        "safety_days": 0,
        "minimum_stock_percent": 0,
        "enable_consolidation": True,
        "id": 2911
    }
    
    try:
        print("📤 Enviando requisição com lead time 5...")
        response = requests.post(
            'http://localhost:5000/mrp_advanced',
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ RESPOSTA RECEBIDA")
            print("=" * 50)
            
            # Verificar dados básicos
            batches = result.get('batches', [])
            analytics = result.get('analytics', {})
            summary = analytics.get('summary', {})
            
            print(f"📦 Total de lotes: {len(batches)}")
            print(f"📈 Taxa de atendimento: {summary.get('demand_fulfillment_rate', 0):.1f}%")
            print(f"🏭 Produção total: {summary.get('total_produced', 0)}")
            print(f"📊 Stockouts: {'Sim' if summary.get('stockout_occurred', False) else 'Não'}")
            
            # Análise detalhada dos lotes
            print("\n📋 ANÁLISE DE LOTES:")
            print("-" * 30)
            
            for i, batch in enumerate(batches, 1):
                order_date = batch.get('order_date')
                arrival_date = batch.get('arrival_date')
                quantity = batch.get('quantity')
                strategy = batch.get('analytics', {}).get('advanced_mrp_strategy', 'unknown')
                
                print(f"Lote {i}:")
                print(f"  • Pedido: {order_date}")
                print(f"  • Chegada: {arrival_date}")
                print(f"  • Quantidade: {quantity}")
                print(f"  • Estratégia: {strategy}")
                
                # Verificar timing do lead time
                if order_date and arrival_date:
                    from datetime import datetime
                    order_dt = datetime.strptime(order_date, '%Y-%m-%d')
                    arrival_dt = datetime.strptime(arrival_date, '%Y-%m-%d')
                    actual_leadtime = (arrival_dt - order_dt).days
                    print(f"  • Lead time real: {actual_leadtime} dias")
                print()
            
            # Verificações específicas para lead time 5 dias
            print("🔍 VERIFICAÇÕES CRÍTICAS:")
            print("-" * 30)
            
            # Verificação 1: Deve ter pelo menos 2 lotes
            if len(batches) >= 2:
                print("✅ Múltiplos lotes criados: OK")
            else:
                print(f"❌ Poucos lotes: {len(batches)} (esperado >= 2)")
            
            # Verificação 2: Taxa de atendimento deve ser melhor
            fulfillment_rate = summary.get('demand_fulfillment_rate', 0)
            if fulfillment_rate >= 50:  # Pelo menos 50%
                print("✅ Taxa de atendimento melhorada: OK")
            else:
                print(f"❌ Taxa de atendimento ainda baixa: {fulfillment_rate}%")
            
            # Verificação 3: Estratégia deve ser short_leadtime_sporadic
            strategies_used = [batch.get('analytics', {}).get('advanced_mrp_strategy') for batch in batches]
            if 'short_leadtime_sporadic' in strategies_used:
                print("✅ Estratégia short_leadtime_sporadic: OK")
            else:
                print(f"❌ Estratégia incorreta: {strategies_used}")
            
            # Verificação 4: Lead time correto (5 dias)
            leadtimes_correct = True
            for batch in batches:
                order_date = batch.get('order_date')
                arrival_date = batch.get('arrival_date')
                if order_date and arrival_date:
                    order_dt = datetime.strptime(order_date, '%Y-%m-%d')
                    arrival_dt = datetime.strptime(arrival_date, '%Y-%m-%d')
                    actual_leadtime = (arrival_dt - order_dt).days
                    if actual_leadtime != 5:
                        leadtimes_correct = False
                        break
            
            if leadtimes_correct:
                print("✅ Lead time de 5 dias respeitado: OK")
            else:
                print("❌ Lead time incorreto")
            
            # Verificação 5: Timing melhorado (chegada antes ou na data da demanda)
            timing_improved = False
            demand_dates = ['2025-07-07', '2025-08-27', '2025-10-17']
            for batch in batches:
                arrival_date = batch.get('arrival_date')
                for demand_date in demand_dates:
                    if arrival_date <= demand_date:
                        timing_improved = True
                        break
                if timing_improved:
                    break
            
            if timing_improved:
                print("✅ Timing melhorado: OK")
            else:
                print("❌ Timing ainda inadequado")
            
            # Análise de melhorias
            print(f"\n📊 COMPARAÇÃO COM PROBLEMA ORIGINAL:")
            print("-" * 40)
            print(f"ANTES: 1 lote, 0% atendimento, chegada tardia")
            print(f"AGORA: {len(batches)} lotes, {fulfillment_rate}% atendimento")
            
            # Critério de sucesso
            success = (
                len(batches) >= 2 and
                fulfillment_rate > 0 and
                'short_leadtime_sporadic' in strategies_used and
                leadtimes_correct
            )
            
            if success:
                print("🎉 CORREÇÃO BEM-SUCEDIDA!")
                return True
            else:
                print("⚠️ Ainda há problemas a resolver")
                return False
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return False

def test_multiple_leadtimes():
    """Testar múltiplos lead times curtos"""
    
    print("\n🧪 Testando múltiplos lead times curtos...")
    
    leadtimes_to_test = [1, 3, 5, 7, 10, 14]
    results = []
    
    for lt in leadtimes_to_test:
        print(f"\n⏱️ Testando lead time: {lt} dias")
        
        test_data = {
            "sporadic_demand": {
                "2025-08-01": 2000,
                "2025-09-01": 2000
            },
            "initial_stock": 1000,
            "leadtime_days": lt,
            "period_start_date": "2025-07-01",
            "period_end_date": "2025-12-31",
            "start_cutoff_date": "2025-07-01",
            "end_cutoff_date": "2025-12-31"
        }
        
        try:
            response = requests.post(
                'http://localhost:5000/mrp_advanced',
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                batches = result.get('batches', [])
                strategy = batches[0].get('analytics', {}).get('advanced_mrp_strategy') if batches else 'none'
                
                print(f"  📦 Lotes: {len(batches)}")
                print(f"  🎯 Estratégia: {strategy}")
                
                results.append((lt, len(batches), strategy))
            else:
                results.append((lt, 0, 'error'))
                
        except Exception as e:
            results.append((lt, 0, 'exception'))
    
    print(f"\n📊 RESUMO DOS LEAD TIMES:")
    print("-" * 40)
    for lt, batches, strategy in results:
        print(f"Lead time {lt:2d}d: {batches} lotes, {strategy}")
    
    return results

if __name__ == "__main__":
    print("🔧 TESTE DE CORREÇÃO: Lead Time 5 Dias")
    print("=" * 50)
    
    # Teste principal
    success1 = test_leadtime_5_fix()
    
    # Teste múltiplos lead times
    results = test_multiple_leadtimes()
    
    print("\n📋 RESUMO FINAL:")
    print("-" * 20)
    print(f"Teste lead time 5d: {'✅ PASSOU' if success1 else '❌ FALHOU'}")
    
    # Verificar se estratégia está sendo aplicada corretamente
    short_lt_count = sum(1 for _, _, strategy in results if strategy == 'short_leadtime_sporadic')
    print(f"Estratégia aplicada em {short_lt_count}/{len(results)} casos")
    
    if success1 and short_lt_count > 0:
        print("\n🎉 CORREÇÃO LEAD TIME CURTO CONFIRMADA!")
        print("✅ Nova estratégia short_leadtime_sporadic funcionando")
    else:
        print("\n⚠️ Ainda há problemas a investigar.") 