#!/usr/bin/env python3
"""
Exemplo de uso da função calculate_batches_for_sporadic_demand
para planejamento de lotes de insumos com demandas esporádicas.

Esta função é uma versão otimizada em Python da função PHP original,
mantendo total compatibilidade e adicionando algoritmos de supply chain.
"""

from mrp import MRPOptimizer, OptimizationParams
import json
from datetime import datetime, timedelta

def exemplo_demanda_esporadica_basico():
    """
    Exemplo básico de planejamento para demandas esporádicas.
    Demonstra uso com dados simples.
    """
    print("=== EXEMPLO BÁSICO - DEMANDA ESPORÁDICA ===")
    
    # Configurar otimizador com parâmetros personalizados
    params = OptimizationParams(
        setup_cost=300.0,           # Custo de setup
        holding_cost_rate=0.15,     # 15% ao ano
        service_level=0.95,         # 95% de nível de serviço
        min_batch_size=100.0,       # Lote mínimo
        max_batch_size=5000.0,      # Lote máximo
        safety_days=3               # 3 dias de segurança
    )
    
    optimizer = MRPOptimizer(params)
    
    # Demandas esporádicas específicas por data
    sporadic_demand = {
        "2024-01-15": 500.0,    # Demanda específica em 15/01
        "2024-01-22": 300.0,    # Demanda específica em 22/01  
        "2024-02-05": 800.0,    # Demanda específica em 05/02
        "2024-02-18": 400.0,    # Demanda específica em 18/02
        "2024-03-10": 600.0     # Demanda específica em 10/03
    }
    
    # Parâmetros do planejamento
    initial_stock = 200.0           # Estoque inicial
    leadtime_days = 7               # Lead time de 7 dias
    period_start_date = "2024-01-01"    # Início do período
    period_end_date = "2024-03-31"      # Fim do período
    start_cutoff_date = "2024-01-01"    # Pode começar a produzir a partir de 01/01
    end_cutoff_date = "2024-04-15"      # Última chegada possível em 15/04
    
    # Executar planejamento otimizado
    resultado = optimizer.calculate_batches_for_sporadic_demand(
        sporadic_demand=sporadic_demand,
        initial_stock=initial_stock,
        leadtime_days=leadtime_days,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        start_cutoff_date=start_cutoff_date,
        end_cutoff_date=end_cutoff_date,
        safety_margin_percent=10.0,     # 10% de margem de segurança
        safety_days=2,                  # 2 dias de segurança
        minimum_stock_percent=5.0,      # 5% da maior demanda como estoque mínimo
        max_gap_days=30                 # Máximo 30 dias entre lotes
    )
    
    # Exibir resultados
    print(f"Lotes planejados: {len(resultado['batches'])}")
    print(f"Estoque inicial: {resultado['analytics']['summary']['initial_stock']}")
    print(f"Estoque final: {resultado['analytics']['summary']['final_stock']}")
    print(f"Estoque mínimo: {resultado['analytics']['summary']['minimum_stock']} em {resultado['analytics']['summary']['minimum_stock_date']}")
    print(f"Total produzido: {resultado['analytics']['summary']['total_produced']}")
    print(f"Taxa de atendimento: {resultado['analytics']['summary']['demand_fulfillment_rate']}%")
    print(f"Rupturas de estoque: {'Sim' if resultado['analytics']['summary']['stockout_occurred'] else 'Não'}")
    
    print("\n--- LOTES PLANEJADOS ---")
    for i, lote in enumerate(resultado['batches'], 1):
        print(f"Lote {i}:")
        print(f"  Pedido: {lote['order_date']}")
        print(f"  Chegada: {lote['arrival_date']}")
        print(f"  Quantidade: {lote['quantity']}")
        print(f"  Demanda alvo: {lote['analytics']['target_demand_date']} ({lote['analytics']['target_demand_quantity']})")
        print(f"  Crítico: {'Sim' if lote['analytics']['is_critical'] else 'Não'}")
        print(f"  Urgência: {lote['analytics']['urgency_level']}")
        print()
    
    print("--- MÉTRICAS ESPORÁDICAS ---")
    sporadic_metrics = resultado['analytics']['sporadic_demand_metrics']
    print(f"Concentração de demanda: {sporadic_metrics['demand_concentration']['concentration_level']}")
    print(f"Previsibilidade: {sporadic_metrics['demand_predictability']}")
    print(f"Intervalo médio entre demandas: {sporadic_metrics['interval_statistics']['average_interval_days']} dias")
    print(f"Picos de demanda detectados: {sporadic_metrics['peak_demand_analysis']['peak_count']}")
    
    return resultado

def exemplo_demanda_esporadica_avancado():
    """
    Exemplo avançado com cenário mais complexo e múltiplas configurações.
    """
    print("\n=== EXEMPLO AVANÇADO - CENÁRIO COMPLEXO ===")
    
    # Parâmetros otimizados para cenário complexo
    params = OptimizationParams(
        setup_cost=500.0,
        holding_cost_rate=0.18,
        service_level=0.98,
        min_batch_size=200.0,
        max_batch_size=3000.0,
        consolidation_window_days=5,
        enable_consolidation=True,
        enable_eoq_optimization=True
    )
    
    optimizer = MRPOptimizer(params)
    
    # Cenário com demandas irregulares e variadas
    sporadic_demand = {
        "2024-01-08": 1200.0,   # Grande demanda no início
        "2024-01-15": 300.0,    # Demanda pequena
        "2024-01-16": 250.0,    # Demanda consecutiva (possível consolidação)
        "2024-01-28": 800.0,    # Demanda média
        "2024-02-12": 1500.0,   # Pico de demanda
        "2024-02-20": 400.0,    # Demanda normal
        "2024-03-05": 600.0,    # Demanda normal
        "2024-03-06": 350.0,    # Demanda consecutiva
        "2024-03-25": 900.0,    # Demanda no final
        "2024-04-02": 200.0     # Demanda após período (para teste)
    }
    
    resultado = optimizer.calculate_batches_for_sporadic_demand(
        sporadic_demand=sporadic_demand,
        initial_stock=500.0,
        leadtime_days=10,
        period_start_date="2024-01-01",
        period_end_date="2024-03-31",
        start_cutoff_date="2023-12-15",  # Pode começar antes do período
        end_cutoff_date="2024-04-30",
        safety_margin_percent=15.0,      # Margem maior para demandas irregulares
        safety_days=3,
        minimum_stock_percent=10.0,      # Estoque mínimo maior
        max_gap_days=20                  # Gaps menores para maior controle
    )
    
    # Análise detalhada
    analytics = resultado['analytics']
    
    print("--- ANÁLISE DE DEMANDA ---")
    demand_analysis = analytics['demand_analysis']
    print(f"Total de eventos de demanda: {demand_analysis['demand_events']}")
    print(f"Demanda média por evento: {demand_analysis['average_demand_per_event']}")
    print(f"Período: {demand_analysis['first_demand_date']} a {demand_analysis['last_demand_date']}")
    print(f"Demanda por mês: {demand_analysis['demand_by_month']}")
    
    print("\n--- EFICIÊNCIA DE PRODUÇÃO ---")
    prod_efficiency = analytics['production_efficiency']
    print(f"Tamanho médio de lote: {prod_efficiency['average_batch_size']}")
    print(f"Entregas críticas: {prod_efficiency['critical_deliveries']}")
    print(f"Margem de segurança média: {prod_efficiency['average_safety_margin']} dias")
    print(f"Eficiência de lotes: {prod_efficiency['batch_efficiency']}%")
    
    # Mostrar gaps de produção
    if prod_efficiency['production_gaps']:
        print(f"\nGaps de produção:")
        for gap in prod_efficiency['production_gaps']:
            print(f"  Lote {gap['from_batch']} → {gap['to_batch']}: {gap['gap_days']} dias ({gap['gap_type']})")
    
    print(f"\n--- PONTOS CRÍTICOS IDENTIFICADOS ---")
    if analytics['critical_points']:
        for ponto in analytics['critical_points']:
            print(f"Data: {ponto['date']}, Estoque: {ponto['stock']}, Severidade: {ponto['severity']}")
    else:
        print("Nenhum ponto crítico identificado! ✓")
    
    return resultado

def exemplo_comparacao_cenarios():
    """
    Exemplo que compara diferentes cenários e configurações.
    """
    print("\n=== COMPARAÇÃO DE CENÁRIOS ===")
    
    # Demanda base para comparação
    base_demand = {
        "2024-01-10": 400.0,
        "2024-01-25": 600.0,
        "2024-02-08": 500.0,
        "2024-02-22": 700.0,
        "2024-03-15": 550.0
    }
    
    cenarios = [
        {
            "nome": "Conservador",
            "params": {
                "safety_margin_percent": 20.0,
                "safety_days": 5,
                "minimum_stock_percent": 15.0
            }
        },
        {
            "nome": "Equilibrado", 
            "params": {
                "safety_margin_percent": 10.0,
                "safety_days": 3,
                "minimum_stock_percent": 8.0
            }
        },
        {
            "nome": "Agressivo",
            "params": {
                "safety_margin_percent": 5.0,
                "safety_days": 1,
                "minimum_stock_percent": 3.0
            }
        }
    ]
    
    optimizer = MRPOptimizer()
    
    print("Cenário\t\tLotes\tProdução\tEstoque Min\tAtendimento")
    print("-" * 60)
    
    for cenario in cenarios:
        resultado = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=base_demand,
            initial_stock=300.0,
            leadtime_days=7,
            period_start_date="2024-01-01",
            period_end_date="2024-03-31", 
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-04-15",
            **cenario["params"]
        )
        
        summary = resultado['analytics']['summary']
        print(f"{cenario['nome']:<15}\t{summary['total_batches']}\t{summary['total_produced']:.0f}\t\t{summary['minimum_stock']:.0f}\t\t{summary['demand_fulfillment_rate']}%")

def salvar_resultado_detalhado():
    """
    Salva um resultado detalhado em arquivo JSON para análise posterior.
    """
    print("\n=== SALVANDO RESULTADO DETALHADO ===")
    
    optimizer = MRPOptimizer()
    
    # Cenário detalhado para análise
    resultado = optimizer.calculate_batches_for_sporadic_demand(
        sporadic_demand={
            "2024-01-12": 350.0,
            "2024-01-20": 500.0,
            "2024-02-03": 280.0,
            "2024-02-15": 720.0,
            "2024-02-28": 440.0,
            "2024-03-10": 600.0,
            "2024-03-22": 380.0
        },
        initial_stock=250.0,
        leadtime_days=8,
        period_start_date="2024-01-01",
        period_end_date="2024-03-31",
        start_cutoff_date="2023-12-20",
        end_cutoff_date="2024-04-20",
        safety_margin_percent=12.0,
        safety_days=2,
        minimum_stock_percent=7.0,
        max_gap_days=25
    )
    
    # Salvar em arquivo
    nome_arquivo = f"resultado_esporadico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    
    print(f"Resultado salvo em: {nome_arquivo}")
    print(f"Tamanho do arquivo: {len(json.dumps(resultado)) / 1024:.1f} KB")
    
    return nome_arquivo

if __name__ == "__main__":
    try:
        # Executar exemplos
        exemplo_demanda_esporadica_basico()
        exemplo_demanda_esporadica_avancado() 
        exemplo_comparacao_cenarios()
        arquivo_salvo = salvar_resultado_detalhado()
        
        print("\n" + "="*60)
        print("TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO! ✓")
        print("="*60)
        print("\nPróximos passos:")
        print("1. Analise os resultados detalhados")
        print("2. Ajuste os parâmetros conforme necessário")
        print("3. Integre com seu sistema PHP")
        print(f"4. Revise o arquivo salvo: {arquivo_salvo}")
        
    except Exception as e:
        print(f"ERRO na execução: {e}")
        import traceback
        traceback.print_exc() 