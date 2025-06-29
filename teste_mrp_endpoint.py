import requests
import json
from datetime import datetime, timedelta

def test_mrp_endpoint():
    """
    Teste do endpoint MRP com dados de exemplo
    """
    # URL do servidor local
    url = "http://127.0.0.1:5000/mrp_optimize"
    
    # Dados de exemplo para teste
    test_data = {
        "daily_demands": {
            "2024-01": 56.18,
            "2024-02": 62.50,
            "2024-03": 58.75,
            "2024-04": 71.20,
            "2024-05": 65.10,
            "2024-06": 70.00
        },
        "initial_stock": 329.0,
        "leadtime_days": 5,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-06-30",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-06-30",
        
        # Parâmetros opcionais de otimização
        "setup_cost": 300.0,
        "service_level": 0.98,
        "enable_consolidation": True,
        "consolidation_window_days": 7,
        "min_batch_size": 100.0,
        "safety_days": 5
    }
    
    print("="*80)
    print("TESTE DO ENDPOINT MRP")
    print("="*80)
    print(f"URL: {url}")
    print(f"Dados de entrada:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("-"*80)
    
    try:
        # Fazer requisição POST
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("SUCESSO! Resultados da otimização MRP:")
            print("-"*80)
            
            # Exibir resumo
            if 'analytics' in result and 'summary' in result['analytics']:
                summary = result['analytics']['summary']
                print("RESUMO:")
                print(f"  • Estoque inicial: {summary.get('initial_stock', 'N/A')}")
                print(f"  • Estoque final: {summary.get('final_stock', 'N/A')}")
                print(f"  • Estoque mínimo: {summary.get('minimum_stock', 'N/A')}")
                print(f"  • Estoque médio: {summary.get('average_stock', 'N/A')}")
                print(f"  • Total de lotes: {summary.get('total_batches', 'N/A')}")
                print(f"  • Produção total: {summary.get('total_produced', 'N/A')}")
                print(f"  • Demanda total: {summary.get('total_demand', 'N/A')}")
                print(f"  • Taxa de cobertura: {summary.get('production_coverage_rate', 'N/A')}%")
                
                if summary.get('stockout_occurred'):
                    print("  ⚠️ ATENÇÃO: Estoque negativo detectado!")
                else:
                    print("  ✅ Nenhum estoque negativo")
            
            # Exibir métricas de performance
            if 'analytics' in result and 'performance_metrics' in result['analytics']:
                metrics = result['analytics']['performance_metrics']
                print("\nMÉTRICAS DE PERFORMANCE:")
                print(f"  • Nível de serviço: {metrics.get('realized_service_level', 'N/A')}%")
                print(f"  • Giro de estoque: {metrics.get('inventory_turnover', 'N/A')}")
                print(f"  • Dias médios de estoque: {metrics.get('average_days_of_inventory', 'N/A')}")
                print(f"  • Frequência de setup: {metrics.get('setup_frequency', 'N/A')}")
                print(f"  • Tamanho médio do lote: {metrics.get('average_batch_size', 'N/A')}")
            
            # Exibir análise de custos
            if 'analytics' in result and 'cost_analysis' in result['analytics']:
                costs = result['analytics']['cost_analysis']
                print("\nANÁLISE DE CUSTOS:")
                print(f"  • Custo total: ${costs.get('total_cost', 'N/A')}")
                print(f"  • Custo de setup: ${costs.get('setup_cost', 'N/A')}")
                print(f"  • Custo de manutenção: ${costs.get('holding_cost', 'N/A')}")
                print(f"  • Custo de falta: ${costs.get('stockout_cost', 'N/A')}")
            
            # Exibir lotes planejados
            if 'batches' in result:
                batches = result['batches']
                print(f"\nLOTES PLANEJADOS ({len(batches)} total):")
                
                for i, batch in enumerate(batches[:10]):  # Mostrar até 10 primeiros
                    print(f"  Lote {i+1}:")
                    print(f"    📅 Data pedido: {batch.get('order_date', 'N/A')}")
                    print(f"    📦 Data chegada: {batch.get('arrival_date', 'N/A')}")
                    print(f"    📊 Quantidade: {batch.get('quantity', 'N/A')}")
                    
                    if 'analytics' in batch:
                        analytics = batch['analytics']
                        print(f"    📈 Estoque antes: {analytics.get('stock_before_arrival', 'N/A')}")
                        print(f"    📈 Estoque depois: {analytics.get('stock_after_arrival', 'N/A')}")
                        print(f"    ⏱️ Cobertura: {analytics.get('coverage_days', 'N/A')} dias")
                        print(f"    🔴 Urgência: {analytics.get('urgency_level', 'N/A')}")
                    print()
                
                if len(batches) > 10:
                    print(f"    ... e mais {len(batches) - 10} lotes")
            
            # Salvar resultado completo
            with open('teste_mrp_resultado.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Resultado completo salvo em 'teste_mrp_resultado.json'")
            
        else:
            print(f"ERRO: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Detalhes do erro: {error_data}")
            except:
                print(f"Resposta do servidor: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("ERRO: Não foi possível conectar ao servidor!")
        print("Certifique-se de que o servidor está rodando em http://127.0.0.1:5000")
    except requests.exceptions.Timeout:
        print("ERRO: Timeout na requisição!")
    except Exception as e:
        print(f"ERRO inesperado: {str(e)}")
    
    print("="*80)

def test_mrp_endpoint_simple():
    """
    Teste simplificado apenas com parâmetros obrigatórios
    """
    url = "http://127.0.0.1:5000/mrp_optimize"
    
    # Dados mínimos necessários
    simple_data = {
        "daily_demands": {
            "2024-01": 50.0,
            "2024-02": 55.0,
            "2024-03": 60.0
        },
        "initial_stock": 200.0,
        "leadtime_days": 3,
        "period_start_date": "2024-01-01",
        "period_end_date": "2024-03-31",
        "start_cutoff_date": "2024-01-01",
        "end_cutoff_date": "2024-03-31"
    }
    
    print("\n" + "="*80)
    print("TESTE SIMPLIFICADO (APENAS PARÂMETROS OBRIGATÓRIOS)")
    print("="*80)
    
    try:
        response = requests.post(url, json=simple_data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCESSO! Teste simplificado passou.")
            print(f"   Lotes planejados: {len(result.get('batches', []))}")
            
            if result.get('batches'):
                first_batch = result['batches'][0]
                print(f"   Primeiro lote: {first_batch.get('quantity')} unidades em {first_batch.get('order_date')}")
        else:
            print(f"❌ FALHA: {response.status_code}")
            print(f"   Erro: {response.json()}")
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")

if __name__ == "__main__":
    # Executar ambos os testes
    test_mrp_endpoint()
    test_mrp_endpoint_simple() 