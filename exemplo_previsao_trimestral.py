import requests
import json
from datetime import datetime, timedelta

# Configuração do servidor
SERVER_URL = "http://localhost:5000"

# Dados de exemplo para teste
exemplo_dados = {
    "sales_data": [
        {"item_id": 1, "timestamp": "2023-01-15", "demand": 100},
        {"item_id": 1, "timestamp": "2023-02-15", "demand": 120},
        {"item_id": 1, "timestamp": "2023-03-15", "demand": 110},
        {"item_id": 1, "timestamp": "2023-04-15", "demand": 130},
        {"item_id": 1, "timestamp": "2023-05-15", "demand": 140},
        {"item_id": 1, "timestamp": "2023-06-15", "demand": 135},
        {"item_id": 1, "timestamp": "2023-07-15", "demand": 150},
        {"item_id": 1, "timestamp": "2023-08-15", "demand": 160},
        {"item_id": 1, "timestamp": "2023-09-15", "demand": 155},
        {"item_id": 1, "timestamp": "2023-10-15", "demand": 170},
        {"item_id": 1, "timestamp": "2023-11-15", "demand": 180},
        {"item_id": 1, "timestamp": "2023-12-15", "demand": 175},
        
        {"item_id": 2, "timestamp": "2023-01-15", "demand": 200},
        {"item_id": 2, "timestamp": "2023-02-15", "demand": 210},
        {"item_id": 2, "timestamp": "2023-03-15", "demand": 220},
        {"item_id": 2, "timestamp": "2023-04-15", "demand": 230},
        {"item_id": 2, "timestamp": "2023-05-15", "demand": 240},
        {"item_id": 2, "timestamp": "2023-06-15", "demand": 235},
        {"item_id": 2, "timestamp": "2023-07-15", "demand": 250},
        {"item_id": 2, "timestamp": "2023-08-15", "demand": 260},
        {"item_id": 2, "timestamp": "2023-09-15", "demand": 255},
        {"item_id": 2, "timestamp": "2023-10-15", "demand": 270},
        {"item_id": 2, "timestamp": "2023-11-15", "demand": 280},
        {"item_id": 2, "timestamp": "2023-12-15", "demand": 275},
    ],
    "data_inicio": "2024-01-01",
    "trimestres": 4,  # Prever 4 trimestres (1 ano)
    "seasonality_mode": "multiplicative",
    "confidence_level": 0.95
}

def testar_previsao_trimestral_metodo1():
    """
    Método 1: Usando o endpoint principal com parâmetro agrupamento_trimestral=True
    """
    print("\n" + "="*80)
    print("MÉTODO 1: Endpoint principal com agrupamento_trimestral=True")
    print("="*80)
    
    dados_request = exemplo_dados.copy()
    dados_request["agrupamento_trimestral"] = True
    dados_request["periodos"] = dados_request.pop("trimestres")  # Renomear para o endpoint principal
    
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=dados_request)
        
        if response.status_code == 200:
            resultado = response.json()
            
            print(f"✅ Previsão trimestral realizada com sucesso!")
            print(f"📊 Total de previsões: {len(resultado['forecast'])}")
            print(f"🗓️  Agrupamento trimestral: {resultado.get('agrupamento_trimestral', False)}")
            
            # Mostrar detalhes de cada previsão
            for previsao in resultado['forecast']:
                quarter_info = previsao.get('_quarter_info', {})
                quarter_name = quarter_info.get('quarter_name', 'N/A')
                
                print(f"\n📈 Item {previsao['item_id']} - Trimestre {quarter_name}")
                print(f"   📅 Data: {previsao['ds']}")
                print(f"   💰 Previsão: {previsao['yhat']}")
                print(f"   📊 Intervalo: [{previsao['yhat_lower']}, {previsao['yhat_upper']}]")
                
                # Mostrar detalhes mensais se disponível
                monthly_details = quarter_info.get('monthly_details', [])
                if monthly_details:
                    print(f"   📝 Detalhes mensais:")
                    for detalhe in monthly_details:
                        print(f"      {detalhe['month']}: {detalhe['yhat']}")
                    
        else:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na comunicação: {e}")

def testar_previsao_trimestral_metodo2():
    """
    Método 2: Usando o endpoint dedicado /predict_quarterly
    """
    print("\n" + "="*80)
    print("MÉTODO 2: Endpoint dedicado /predict_quarterly")
    print("="*80)
    
    try:
        response = requests.post(f"{SERVER_URL}/predict_quarterly", json=exemplo_dados)
        
        if response.status_code == 200:
            resultado = response.json()
            
            print(f"✅ Previsão trimestral realizada com sucesso!")
            print(f"📊 Total de previsões: {len(resultado['forecast'])}")
            print(f"🗓️  Agrupamento trimestral: {resultado.get('agrupamento_trimestral', False)}")
            
            # Mostrar resumo por item
            itens_resumo = {}
            for previsao in resultado['forecast']:
                item_id = previsao['item_id']
                if item_id not in itens_resumo:
                    itens_resumo[item_id] = []
                itens_resumo[item_id].append(previsao)
            
            for item_id, previsoes in itens_resumo.items():
                print(f"\n🎯 RESUMO ITEM {item_id}:")
                total_previsto = sum(p['yhat'] for p in previsoes)
                print(f"   📈 Total previsto para 4 trimestres: {total_previsto:.2f}")
                print(f"   📊 Média por trimestre: {total_previsto/len(previsoes):.2f}")
                
                for previsao in previsoes:
                    quarter_info = previsao.get('_quarter_info', {})
                    quarter_name = quarter_info.get('quarter_name', 'N/A')
                    print(f"   📅 {quarter_name}: {previsao['yhat']}")
                    
        else:
            print(f"❌ Erro na requisição: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na comunicação: {e}")

def comparar_previsao_mensal_vs_trimestral():
    """
    Comparação entre previsão mensal normal e previsão trimestral
    """
    print("\n" + "="*80)
    print("COMPARAÇÃO: Previsão Mensal vs Trimestral")
    print("="*80)
    
    # Previsão mensal normal (12 meses)
    dados_mensal = exemplo_dados.copy()
    dados_mensal["periodos"] = 12
    dados_mensal.pop("trimestres")
    
    try:
        print("🔄 Gerando previsão mensal...")
        response_mensal = requests.post(f"{SERVER_URL}/predict", json=dados_mensal)
        
        print("🔄 Gerando previsão trimestral...")
        response_trimestral = requests.post(f"{SERVER_URL}/predict_quarterly", json=exemplo_dados)
        
        if response_mensal.status_code == 200 and response_trimestral.status_code == 200:
            mensal = response_mensal.json()
            trimestral = response_trimestral.json()
            
            print("\n📊 COMPARAÇÃO DOS RESULTADOS:")
            print("-" * 50)
            
            # Agrupar previsões mensais por item
            mensal_por_item = {}
            for prev in mensal['forecast']:
                item_id = prev['item_id']
                if item_id not in mensal_por_item:
                    mensal_por_item[item_id] = []
                mensal_por_item[item_id].append(prev)
            
            # Comparar com previsões trimestrais
            for item_id in mensal_por_item.keys():
                print(f"\n🎯 ITEM {item_id}:")
                
                # Total mensal
                total_mensal = sum(p['yhat'] for p in mensal_por_item[item_id])
                print(f"   📈 Total previsão mensal (12 meses): {total_mensal:.2f}")
                
                # Total trimestral
                previsoes_item = [p for p in trimestral['forecast'] if p['item_id'] == item_id]
                total_trimestral = sum(p['yhat'] for p in previsoes_item)
                print(f"   📈 Total previsão trimestral (4 trimestres): {total_trimestral:.2f}")
                
                # Diferença
                diferenca = abs(total_mensal - total_trimestral)
                percentual = (diferenca / total_mensal) * 100 if total_mensal > 0 else 0
                print(f"   📊 Diferença: {diferenca:.2f} ({percentual:.2f}%)")
                
        else:
            print("❌ Erro em uma das requisições")
            
    except Exception as e:
        print(f"❌ Erro na comparação: {e}")

if __name__ == "__main__":
    print("🚀 DEMONSTRAÇÃO DE PREVISÕES TRIMESTRAIS")
    print("=" * 80)
    print("Este script demonstra como usar as novas funcionalidades de previsão trimestral.")
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    print("\nPressione Enter para continuar ou Ctrl+C para sair...")
    
    try:
        input()
        
        # Testar os diferentes métodos
        testar_previsao_trimestral_metodo1()
        testar_previsao_trimestral_metodo2()
        comparar_previsao_mensal_vs_trimestral()
        
        print("\n" + "="*80)
        print("✅ DEMONSTRAÇÃO CONCLUÍDA!")
        print("="*80)
        print("\nFormatos de requisição suportados:")
        print("\n1️⃣  Endpoint principal com agrupamento:")
        print("   POST /predict")
        print("   {")
        print('     "agrupamento_trimestral": true,')
        print('     "periodos": 4,  // número de trimestres')
        print('     "sales_data": [...],')
        print('     "data_inicio": "2024-01-01"')
        print("   }")
        
        print("\n2️⃣  Endpoint dedicado:")
        print("   POST /predict_quarterly")
        print("   {")
        print('     "trimestres": 4,  // número de trimestres')
        print('     "sales_data": [...],')
        print('     "data_inicio": "2024-01-01"')
        print("   }")
        
    except KeyboardInterrupt:
        print("\n👋 Demonstração cancelada pelo usuário.") 