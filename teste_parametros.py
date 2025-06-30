#!/usr/bin/env python3

import requests
import json
import time

# Configuração do servidor
BASE_URL = "http://127.0.0.1:5000"
ENDPOINT_URL = f"{BASE_URL}/mrp_sporadic"

def criar_request_base():
    """
    Cenário do usuário: 5 demandas incluindo 2 de 4000 unidades cada
    """
    return {
        "sporadic_demand": {
            "2025-07-07": 1.0,      # Demanda pequena
            "2025-08-05": 4000.0,   # Demanda 1 - 4000 unidades
            "2025-08-27": 1.0,      # Demanda pequena  
            "2025-09-25": 4000.0,   # Demanda 2 - 4000 unidades
            "2025-10-17": 1.0       # Demanda pequena
        },
        "initial_stock": 464.0,
        "leadtime_days": 70,
        "period_start_date": "2025-03-22",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-03-22",
        "end_cutoff_date": "2025-12-31",
        "safety_margin_percent": 8.0,
        "safety_days": 2,
        "minimum_stock_percent": 0.0
    }

def testar_configuracao(nome, config_extra):
    """
    Testa uma configuração específica
    """
    print(f"\n=== {nome} ===")
    
    # Criar request
    request_data = criar_request_base()
    request_data.update(config_extra)
    
    # Mostrar parâmetros extras
    print("Parâmetros extras:")
    for key, value in config_extra.items():
        print(f"  {key}: {value}")
    
    try:
        start_time = time.time()
        response = requests.post(ENDPOINT_URL, json=request_data, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            summary = result['analytics']['summary']
            
            print(f"SUCESSO em {end_time - start_time:.2f}s")
            print(f"   Lotes: {len(result['batches'])}")
            print(f"   Produção total: {summary['total_produced']:.0f}")
            print(f"   Taxa atendimento: {summary['demand_fulfillment_rate']:.1f}%")
            print(f"   Estoque final: {summary['final_stock']:.0f}")
            print(f"   Stockout: {'Sim' if summary['stockout_occurred'] else 'Não'}")
            
            # Mostrar lotes
            for i, batch in enumerate(result['batches'], 1):
                print(f"   Lote {i}: {batch['order_date']} -> {batch['arrival_date']} ({batch['quantity']:.0f})")
            
            return {
                'nome': nome,
                'lotes': len(result['batches']),
                'total_produzido': summary['total_produced'],
                'taxa_atendimento': summary['demand_fulfillment_rate'],
                'stockout': summary['stockout_occurred']
            }
            
        else:
            print(f"ERRO: {response.status_code}")
            print(f"   {response.text}")
            return None
            
    except Exception as e:
        print(f"EXCEÇÃO: {e}")
        return None

def testar_personalizado():
    print("\n=== TESTE PERSONALIZADO DO USUÁRIO ===")
    request_data = {
        "sporadic_demand": {
            "2025-07-07": 4000,
            "2025-08-27": 4000,
            "2025-10-17": 4000,
            "2025-08-05": 4000,
            "2025-09-25": 4000
        },
        "initial_stock": 5102,
        "leadtime_days": 30,
        "period_start_date": "2025-03-22",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-03-22",
        "end_cutoff_date": "2025-12-31",
        "safety_margin_percent": 8,
        "safety_days": 2,
        "minimum_stock_percent": 0,
        "max_gap_days": 20,
        "enable_consolidation": True,
        "consolidation_window_days": 30,
        "setup_cost": 1500
    }
    print("Payload:")
    print(json.dumps(request_data, indent=2))
    try:
        response = requests.post(ENDPOINT_URL, json=request_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            summary = result['analytics']['summary']
            print(f"SUCESSO!")
            print(f"   Lotes: {len(result['batches'])}")
            print(f"   Produção total: {summary['total_produced']:.0f}")
            print(f"   Taxa atendimento: {summary['demand_fulfillment_rate']:.1f}%")
            print(f"   Estoque final: {summary['final_stock']:.0f}")
            print(f"   Stockout: {'Sim' if summary['stockout_occurred'] else 'Não'}")
            for i, batch in enumerate(result['batches'], 1):
                print(f"   Lote {i}: {batch['order_date']} -> {batch['arrival_date']} ({batch['quantity']:.0f})")
        else:
            print(f"ERRO: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"EXCEÇÃO: {e}")

def main():
    print("="*80)
    print("TESTE DE COMPARACAO DE PARAMETROS MRP ESPORADICO")
    print("Cenario: 5 demandas (2 de 4000 unidades cada)")
    print("="*80)
    
    # Verificar servidor
    try:
        requests.get(BASE_URL, timeout=5)
        print("Servidor está rodando")
    except:
        print("Servidor não está rodando! Execute: python server.py")
        return
    
    # Configurações para testar
    configuracoes = [
        {
            'nome': '1. PADRAO',
            'config': {
                'max_gap_days': 999
            }
        },
        {
            'nome': '2. CONSOLIDACAO BASICA',
            'config': {
                'max_gap_days': 45,
                'enable_consolidation': True
            }
        },
        {
            'nome': '3. SETUP COST ALTO',
            'config': {
                'max_gap_days': 45,
                'setup_cost': 800.0,
                'enable_consolidation': True
            }
        },
        {
            'nome': '4. LOTE MINIMO GRANDE',
            'config': {
                'max_gap_days': 45,
                'min_batch_size': 7000.0,
                'enable_consolidation': True
            }
        },
        {
            'nome': '5. OTIMIZACAO COMPLETA',
            'config': {
                'max_gap_days': 30,
                'setup_cost': 1000.0,
                'min_batch_size': 6000.0,
                'enable_consolidation': True,
                'consolidation_window_days': 15
            }
        },
        {
            'nome': '6. SUPER CONSOLIDACAO',
            'config': {
                'max_gap_days': 20,
                'setup_cost': 1500.0,
                'min_batch_size': 8000.0,
                'enable_consolidation': True,
                'consolidation_window_days': 30
            }
        },
        {
            'nome': '7. ULTRA CONSOLIDACAO',
            'config': {
                'max_gap_days': 15,
                'setup_cost': 2000.0,
                'min_batch_size': 10000.0,
                'enable_consolidation': True,
                'consolidation_window_days': 60
            }
        }
    ]
    
    # Executar testes
    resultados = []
    for config in configuracoes:
        result = testar_configuracao(config['nome'], config['config'])
        if result:
            resultados.append(result)
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS RESULTADOS")
    print("="*80)
    
    if resultados:
        print(f"{'Configuracao':<25} {'Lotes':<6} {'Producao':<10} {'Atend%':<8} {'Stockout'}")
        print("-" * 70)
        
        for r in resultados:
            stockout_str = "Sim" if r['stockout'] else "Nao"
            print(f"{r['nome']:<25} {r['lotes']:<6} {r['total_produzido']:<10.0f} {r['taxa_atendimento']:<8.1f} {stockout_str}")
        
        # Encontrar melhor
        menos_lotes = min(resultados, key=lambda x: x['lotes'])
        print(f"\nMELHOR RESULTADO:")
        print(f"   {menos_lotes['nome']}: {menos_lotes['lotes']} lote(s)")
        
        if menos_lotes['lotes'] == 1:
            print("PERFEITO! Conseguimos consolidar em 1 lote apenas!")
        elif menos_lotes['lotes'] == 2:
            print("BOM! Conseguimos reduzir para 2 lotes")
        else:
            print("Ainda precisa de mais consolidacao")
    
    print("\n" + "="*80)
    print("TESTE CONCLUIDO!")
    print("="*80)

if __name__ == "__main__":
    main()
    testar_personalizado() 