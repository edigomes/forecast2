#!/usr/bin/env python3
"""
Teste do novo endpoint /mrp_sporadic
Verifica se o endpoint está funcionando corretamente com diferentes cenários.
"""

import requests
import json
import time
from datetime import datetime

# Configuração do servidor
BASE_URL = "http://127.0.0.1:5000"
ENDPOINT_URL = f"{BASE_URL}/mrp_sporadic"

def test_mrp_sporadic_basico():
    """
    Teste básico do endpoint com dados simples
    """
    print("=== TESTE BÁSICO DO ENDPOINT /mrp_sporadic ===")
    
    # Dados de teste básicos
    test_data = {
        "sporadic_demand": {
            "2024-01-15": 500.0,
            "2024-01-22": 300.0,
            "2024-02-05": 800.0,
            "2024-02-18": 400.0,
            "2024-03-10": 600.0
        },
        "initial_stock": 200.0,
        "leadtime_days": 7,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-04-15",
        "safety_margin_percent": 10.0,
        "safety_days": 2,
        "minimum_stock_percent": 5.0,
        "max_gap_days": 30
    }
    
    print("Enviando dados:")
    print(json.dumps(test_data, indent=2))
    
    try:
        # Fazer requisição
        start_time = time.time()
        response = requests.post(ENDPOINT_URL, json=test_data, timeout=30)
        end_time = time.time()
        
        # Verificar resposta
        print(f"\nTempo de resposta: {end_time - start_time:.2f}s")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCESSO! Endpoint funcionando corretamente.")
            print(f"Lotes planejados: {len(result['batches'])}")
            print(f"Estoque inicial: {result['analytics']['summary']['initial_stock']}")
            print(f"Estoque final: {result['analytics']['summary']['final_stock']}")
            print(f"Total produzido: {result['analytics']['summary']['total_produced']}")
            print(f"Taxa de atendimento: {result['analytics']['summary']['demand_fulfillment_rate']}%")
            
            # Mostrar alguns lotes
            print("\nPrimeiros lotes:")
            for i, batch in enumerate(result['batches'][:3], 1):
                print(f"  Lote {i}: {batch['order_date']} → {batch['arrival_date']} ({batch['quantity']})")
            
            return True
            
        else:
            print(f"❌ ERRO: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERRO de conexão: {e}")
        return False
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def test_mrp_sporadic_avancado():
    """
    Teste avançado com parâmetros de otimização
    """
    print("\n=== TESTE AVANÇADO COM OTIMIZAÇÃO ===")
    
    # Dados com parâmetros avançados
    test_data = {
        "sporadic_demand": {
            "2024-01-08": 1200.0,
            "2024-01-15": 300.0,
            "2024-01-16": 250.0,  # Demanda consecutiva
            "2024-01-28": 800.0,
            "2024-02-12": 1500.0, # Pico de demanda
            "2024-02-20": 400.0,
            "2024-03-05": 600.0,
            "2024-03-25": 900.0
        },
        "initial_stock": 500.0,
        "leadtime_days": 10,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2023-12-15",  # Pode começar antes
        "end_cutoff_date": "2024-04-30",
        "safety_margin_percent": 15.0,
        "safety_days": 3,
        "minimum_stock_percent": 10.0,
        "max_gap_days": 20,
        # Parâmetros avançados de otimização
        "setup_cost": 500.0,
        "holding_cost_rate": 0.18,
        "service_level": 0.98,
        "min_batch_size": 200.0,
        "max_batch_size": 3000.0,
        "enable_consolidation": True,
        "enable_eoq_optimization": True
    }
    
    print("Enviando dados avançados...")
    
    try:
        start_time = time.time()
        response = requests.post(ENDPOINT_URL, json=test_data, timeout=30)
        end_time = time.time()
        
        print(f"Tempo de resposta: {end_time - start_time:.2f}s")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCESSO! Teste avançado funcionando.")
            
            # Métricas de demanda esporádica
            sporadic_metrics = result['analytics']['sporadic_demand_metrics']
            print(f"Concentração de demanda: {sporadic_metrics['demand_concentration']['concentration_level']}")
            print(f"Previsibilidade: {sporadic_metrics['demand_predictability']}")
            print(f"Intervalo médio: {sporadic_metrics['interval_statistics']['average_interval_days']} dias")
            print(f"Picos detectados: {sporadic_metrics['peak_demand_analysis']['peak_count']}")
            
            # Eficiência de produção
            prod_efficiency = result['analytics']['production_efficiency']
            print(f"Entregas críticas: {prod_efficiency['critical_deliveries']}")
            print(f"Margem segurança média: {prod_efficiency['average_safety_margin']} dias")
            
            return True
            
        else:
            print(f"❌ ERRO: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def test_mrp_sporadic_validacoes():
    """
    Testa validações do endpoint
    """
    print("\n=== TESTE DE VALIDAÇÕES ===")
    
    # Teste 1: Dados vazios
    print("Teste 1: Dados vazios")
    response = requests.post(ENDPOINT_URL, json={})
    print(f"Status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")
    
    # Teste 2: Demanda inválida
    print("Teste 2: Demanda com formato inválido")
    test_data = {
        "sporadic_demand": {"data-inválida": 100},
        "initial_stock": 200,
        "leadtime_days": 7,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-04-15"
    }
    response = requests.post(ENDPOINT_URL, json=test_data)
    print(f"Status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")
    
    # Teste 3: Estoque negativo
    print("Teste 3: Estoque inicial negativo")
    test_data = {
        "sporadic_demand": {"2024-01-15": 100},
        "initial_stock": -50,  # Negativo
        "leadtime_days": 7,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-04-15"
    }
    response = requests.post(ENDPOINT_URL, json=test_data)
    print(f"Status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")
    
    # Teste 4: Datas inválidas
    print("Teste 4: Data final antes da inicial")
    test_data = {
        "sporadic_demand": {"2024-01-15": 100},
        "initial_stock": 200,
        "leadtime_days": 7,
        "period_start_date": "2024-03-31",  # Depois da final
        "period_end_date": "2024-01-01",    # Antes da inicial
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-04-15"
    }
    response = requests.post(ENDPOINT_URL, json=test_data)
    print(f"Status: {response.status_code} ({'✅' if response.status_code == 400 else '❌'})")
    
    print("Testes de validação concluídos!")

def test_mrp_sporadic_cenarios():
    """
    Testa diferentes cenários de uso
    """
    print("\n=== TESTE DE CENÁRIOS DIVERSOS ===")
    
    cenarios = [
        {
            "nome": "Demanda Única",
            "data": {
                "sporadic_demand": {"2024-02-14": 1000.0},  # Só uma demanda
                "initial_stock": 100.0,
                "leadtime_days": 5,
                "period_start_date": "2024-01-01",
                "period_end_date": "2024-03-31",
                "start_cutoff_date": "2024-01-01",
                "end_cutoff_date": "2024-04-15"
            }
        },
        {
            "nome": "Lead Time Zero",
            "data": {
                "sporadic_demand": {"2024-01-15": 500.0, "2024-02-15": 600.0},
                "initial_stock": 200.0,
                "leadtime_days": 0,  # Lead time zero
                "period_start_date": "2024-01-01",
                "period_end_date": "2024-03-31",
                "start_cutoff_date": "2024-01-01",
                "end_cutoff_date": "2024-04-15"
            }
        },
        {
            "nome": "Demandas Consecutivas",
            "data": {
                "sporadic_demand": {
                    "2024-01-15": 300.0,
                    "2024-01-16": 400.0,  # Consecutivas
                    "2024-01-17": 200.0,  # Consecutivas
                    "2024-02-15": 500.0
                },
                "initial_stock": 100.0,
                "leadtime_days": 3,
                "period_start_date": "2024-01-01",
                "period_end_date": "2024-03-31",
                "start_cutoff_date": "2024-01-01",
                "end_cutoff_date": "2024-04-15",
                "max_gap_days": 5  # Força consolidação
            }
        }
    ]
    
    sucessos = 0
    for cenario in cenarios:
        print(f"\nTestando cenário: {cenario['nome']}")
        
        try:
            response = requests.post(ENDPOINT_URL, json=cenario['data'], timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {cenario['nome']}: {len(result['batches'])} lotes planejados")
                sucessos += 1
            else:
                print(f"❌ {cenario['nome']}: Status {response.status_code}")
                print(f"   Erro: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ {cenario['nome']}: Exceção {e}")
    
    print(f"\nResultado: {sucessos}/{len(cenarios)} cenários testados com sucesso")
    return sucessos == len(cenarios)

def verificar_servidor():
    """
    Verifica se o servidor está rodando
    """
    print("Verificando se o servidor está rodando...")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        print("✅ Servidor está rodando!")
        return True
    except:
        print("❌ Servidor não está rodando!")
        print("   Por favor, execute: python server.py")
        return False

def salvar_exemplo_request():
    """
    Salva um exemplo de request para referência
    """
    exemplo = {
        "sporadic_demand": {
            "2024-01-15": 500.0,
            "2024-02-05": 800.0,
            "2024-03-10": 600.0
        },
        "initial_stock": 200.0,
        "leadtime_days": 7,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-04-15",
        "safety_margin_percent": 10.0,
        "safety_days": 2,
        "minimum_stock_percent": 5.0,
        "max_gap_days": 30,
        "setup_cost": 300.0,
        "service_level": 0.95,
        "enable_consolidation": True
    }
    
    with open('exemplo_request_mrp_sporadic.json', 'w', encoding='utf-8') as f:
        json.dump(exemplo, f, indent=2, ensure_ascii=False)
    
    print("Exemplo de request salvo em: exemplo_request_mrp_sporadic.json")

if __name__ == "__main__":
    test_mrp_sporadic_basico() 