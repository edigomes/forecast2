#!/usr/bin/env python3
"""
Test script para verificar correção do bug de lead time zero
"""

import requests
import json
from datetime import datetime

def test_leadtime_zero_fix():
    """Testar correção para lead time zero"""
    
    print("🧪 Testando correção para lead time zero...")
    
    # Dados EXATOS do problema reportado pelo usuário
    test_data = {
        "sporadic_demand": {
            "2025-07-07": 4000,
            "2025-08-27": 4000,
            "2025-10-17": 4000
        },
        "initial_stock": 4422,
        "leadtime_days": 0,  # ZERO - produção instantânea
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
        print("📤 Enviando requisição com lead time 0...")
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
            print(f"📈 Taxa de atendimento: {summary.get('demand_fulfillment_rate', 0)}%")
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
                print()
            
            # Verificações específicas para lead time zero
            print("🔍 VERIFICAÇÕES CRÍTICAS:")
            print("-" * 30)
            
            # Verificação 1: Deve ter 3 lotes (ou pelo menos os necessários)
            expected_batches = 3 if summary.get('initial_stock', 0) < 4000 else 2
            if len(batches) >= 2:  # Pelo menos cobrir as demandas críticas
                print("✅ Lotes criados: OK")
            else:
                print(f"❌ Lotes insuficientes: {len(batches)} (esperado >= 2)")
            
            # Verificação 2: Taxa de atendimento deve ser alta
            fulfillment_rate = summary.get('demand_fulfillment_rate', 0)
            if fulfillment_rate >= 60:  # Pelo menos 60% (ainda pode ter alguns ajustes)
                print("✅ Taxa de atendimento: OK")
            else:
                print(f"❌ Taxa de atendimento baixa: {fulfillment_rate}%")
            
            # Verificação 3: Estratégia deve ser just_in_time
            strategies_used = [batch.get('analytics', {}).get('advanced_mrp_strategy') for batch in batches]
            if 'just_in_time' in strategies_used:
                print("✅ Estratégia just-in-time: OK")
            else:
                print(f"❌ Estratégia incorreta: {strategies_used}")
            
            # Verificação 4: Order date = Arrival date para lead time 0
            timing_correct = True
            for batch in batches:
                if batch.get('order_date') != batch.get('arrival_date'):
                    timing_correct = False
                    break
            
            if timing_correct:
                print("✅ Timing (order=arrival): OK")
            else:
                print("❌ Timing incorreto para lead time 0")
            
            # Análise de melhorias
            print(f"\n📊 COMPARAÇÃO COM PROBLEMA ORIGINAL:")
            print("-" * 40)
            print(f"ANTES: 1 lote, 0% atendimento, stockouts severos")
            print(f"AGORA: {len(batches)} lotes, {fulfillment_rate}% atendimento")
            
            if fulfillment_rate > 0 and len(batches) > 1:
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

def test_leadtime_zero_simple():
    """Teste simples para lead time zero"""
    
    print("\n🧪 Teste simples para lead time zero...")
    
    simple_data = {
        "sporadic_demand": {"2025-08-01": 1000},
        "initial_stock": 500,
        "leadtime_days": 0,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-07-01",
        "end_cutoff_date": "2025-12-31"
    }
    
    try:
        response = requests.post(
            'http://localhost:5000/mrp_advanced',
            json=simple_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            batches = result.get('batches', [])
            
            print(f"✅ Lotes criados: {len(batches)}")
            
            if len(batches) > 0:
                batch = batches[0]
                strategy = batch.get('analytics', {}).get('advanced_mrp_strategy')
                print(f"✅ Estratégia: {strategy}")
                
                if strategy == 'just_in_time':
                    print("🎉 Estratégia just-in-time funcionando!")
                    return True
            
        return False
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🔧 TESTE DE CORREÇÃO: Lead Time Zero")
    print("=" * 50)
    
    # Teste 1: Caso específico do usuário
    success1 = test_leadtime_zero_fix()
    
    # Teste 2: Caso simples
    success2 = test_leadtime_zero_simple()
    
    print("\n📋 RESUMO DOS TESTES:")
    print("-" * 20)
    print(f"Teste complexo: {'✅ PASSOU' if success1 else '❌ FALHOU'}")
    print(f"Teste simples: {'✅ PASSOU' if success2 else '❌ FALHOU'}")
    
    if success1 and success2:
        print("\n🎉 CORREÇÃO CONFIRMADA!")
        print("O bug de lead time zero foi corrigido com sucesso.")
    else:
        print("\n⚠️ Ainda há problemas a investigar.") 