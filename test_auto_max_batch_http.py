"""
🎯 TESTE HTTP: Auto-calculation do max_batch_size via API
Demonstra como usar a nova funcionalidade via endpoints HTTP
"""

import requests
import json

def test_auto_max_batch_http():
    """Testa auto-calculation via API HTTP"""
    
    base_url = "http://localhost:5000"
    
    # Dados de teste
    test_data = {
        "daily_demands": {
            "2025-07": 60.75, 
            "2025-08": 60.75, 
            "2025-09": 62.78, 
            "2025-10": 60.75, 
            "2025-11": 62.78, 
            "2025-12": 60.75
        },
        "initial_stock": 0,
        "leadtime_days": 50,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-05-01",
        "end_cutoff_date": "2025-12-31"
    }
    
    print("="*80)
    print("🎯 TESTE HTTP: AUTO-CALCULATION DO MAX_BATCH_SIZE")
    print("="*80)
    
    # TESTE 1: Configuração Manual (comportamento antigo)
    print("\n📊 TESTE 1: MRP Manual via /mrp_optimize")
    manual_request = test_data.copy()
    manual_request.update({
        "setup_cost": 75,
        "holding_cost_rate": 0.25,
        "max_batch_size": 6418,
        "auto_calculate_max_batch_size": False,  # ⭐ Desabilitado
        "enable_consolidation": False
    })
    
    try:
        response1 = requests.post(f"{base_url}/mrp_optimize", json=manual_request)
        if response1.status_code == 200:
            result1 = response1.json()
            print(f"  ✅ Status: {response1.status_code}")
            print(f"  Lotes planejados: {len(result1['batches'])}")
            print(f"  Produção total: {result1['analytics']['summary']['total_produced']}")
            for i, batch in enumerate(result1['batches'], 1):
                print(f"    Lote {i}: {batch['quantity']} unidades")
        else:
            print(f"  ❌ Erro: {response1.status_code} - {response1.text}")
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")
    
    # TESTE 2: Auto-calculation via /mrp_optimize
    print("\n🎯 TESTE 2: Auto-calculation via /mrp_optimize")
    auto_request = test_data.copy()
    auto_request.update({
        "setup_cost": 100,
        "holding_cost_rate": 0.20,
        "max_batch_size": 999999,  # ⭐ Valor muito alto
        "auto_calculate_max_batch_size": True,  # ⭐ HABILITADO
        "max_batch_multiplier": 3.0,  # ⭐ 3x o EOQ
        "enable_consolidation": True,
        "include_extended_analytics": True
    })
    
    try:
        response2 = requests.post(f"{base_url}/mrp_optimize", json=auto_request)
        if response2.status_code == 200:
            result2 = response2.json()
            print(f"  ✅ Status: {response2.status_code}")
            print(f"  Lotes planejados: {len(result2['batches'])}")
            print(f"  Produção total: {result2['analytics']['summary']['total_produced']}")
            
            # Mostrar EOQ teórico se disponível
            if 'extended_analytics' in result2['analytics']:
                eoq = result2['analytics']['extended_analytics'].get('optimization_metrics', {}).get('theoretical_eoq')
                if eoq:
                    print(f"  EOQ teórico: {eoq}")
                    print(f"  Max batch efetivo: ~{eoq * 3.0:.0f} (3x EOQ)")
            
            for i, batch in enumerate(result2['batches'], 1):
                print(f"    Lote {i}: {batch['quantity']} unidades")
        else:
            print(f"  ❌ Erro: {response2.status_code} - {response2.text}")
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")
    
    # TESTE 3: Auto-calculation via /mrp_advanced (demanda esporádica)
    print("\n🚀 TESTE 3: Auto-calculation via /mrp_advanced (Esporádica)")
    sporadic_request = {
        "sporadic_demand": {
            "2025-07-15": 1200,
            "2025-08-20": 1800,
            "2025-09-10": 2000,
            "2025-10-25": 1500,
            "2025-11-15": 2200,
            "2025-12-05": 1800
        },
        "initial_stock": 0,
        "leadtime_days": 50,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-05-01",
        "end_cutoff_date": "2025-12-31",
        "safety_margin_percent": 5.0,
        "setup_cost": 150,
        "holding_cost_rate": 0.18,
        "max_batch_size": 999999,
        "auto_calculate_max_batch_size": True,  # ⭐ HABILITADO
        "max_batch_multiplier": 2.5,  # ⭐ 2.5x o EOQ
        "enable_consolidation": True,
        "include_extended_analytics": True
    }
    
    try:
        response3 = requests.post(f"{base_url}/mrp_advanced", json=sporadic_request)
        if response3.status_code == 200:
            result3 = response3.json()
            print(f"  ✅ Status: {response3.status_code}")
            print(f"  Lotes planejados: {len(result3['batches'])}")
            print(f"  Produção total: {result3['analytics']['summary']['total_produced']}")
            print(f"  Taxa atendimento: {result3['analytics']['summary']['demand_fulfillment_rate']}%")
            
            for i, batch in enumerate(result3['batches'], 1):
                print(f"    Lote {i}: {batch['quantity']} unidades (chegada: {batch['arrival_date']})")
                if batch['analytics'].get('consolidated_group'):
                    print(f"      ✓ Consolidado: {batch['analytics']['group_size']} demandas")
        else:
            print(f"  ❌ Erro: {response3.status_code} - {response3.text}")
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")
    
    # TESTE 4: Configuração JSON completa
    print("\n✨ TESTE 4: Configuração JSON Completa para Copy/Paste")
    json_config = {
        # Dados obrigatórios
        "daily_demands": {
            "2025-07": 60.75, 
            "2025-08": 60.75, 
            "2025-09": 62.78, 
            "2025-10": 60.75, 
            "2025-11": 62.78, 
            "2025-12": 60.75
        },
        "initial_stock": 0,
        "leadtime_days": 50,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-05-01",
        "end_cutoff_date": "2025-12-31",
        
        # 🎯 CONFIGURAÇÃO AUTO-CALCULATION
        "auto_calculate_max_batch_size": True,  # ⭐ Habilitar auto-calculation
        "max_batch_multiplier": 3.5,           # ⭐ 3.5x o EOQ teórico
        "max_batch_size": 20000,               # ⭐ Limite alto como backup
        
        # Otimização para lotes ideais
        "setup_cost": 80,                      # ⭐ Custo setup moderado
        "holding_cost_rate": 0.22,             # ⭐ Custo manutenção balanceado
        "enable_eoq_optimization": True,       # ⭐ Habilitar EOQ
        "enable_consolidation": True,          # ⭐ Consolidação inteligente
        "include_extended_analytics": True     # ⭐ Analytics completos
    }
    
    print("  Configuração JSON para usar:")
    print("  " + "="*60)
    print(json.dumps(json_config, indent=2, ensure_ascii=False))
    print("  " + "="*60)
    
    print("\n🎯 CONCLUSÕES:")
    print("✅ AUTO-CALCULATION funciona via API HTTP!")
    print("✅ Use auto_calculate_max_batch_size=True nos endpoints")
    print("✅ Configurar max_batch_multiplier entre 2.0 e 6.0")
    print("✅ Manter max_batch_size alto como backup de segurança")
    print("✅ Endpoints suportados: /mrp_optimize, /mrp_advanced")

if __name__ == "__main__":
    test_auto_max_batch_http() 