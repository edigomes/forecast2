#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from pprint import pprint

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
    "periodos": 6,
    "seasonality_mode": "multiplicative",
    "confidence_level": 0.95
}

def testar_sem_explicacao():
    """Teste padrão sem explicações (comportamento anterior)"""
    print("\n" + "="*80)
    print("TESTE 1: SEM EXPLICAÇÕES (Comportamento Padrão)")
    print("="*80)
    
    dados = exemplo_dados.copy()
    
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=dados)
        
        if response.status_code == 200:
            resultado = response.json()
            
            print(f"✅ Previsão realizada sem explicações")
            print(f"📊 Total de previsões: {len(resultado['forecast'])}")
            
            # Mostrar estrutura básica
            previsao_exemplo = resultado['forecast'][0]
            print(f"\n📋 Estrutura da resposta (primeira previsão):")
            print(f"   item_id: {previsao_exemplo['item_id']}")
            print(f"   ds: {previsao_exemplo['ds']}")
            print(f"   yhat: {previsao_exemplo['yhat']}")
            print(f"   trend: {previsao_exemplo['trend']}")
            print(f"   yearly: {previsao_exemplo['yearly']}")
            print(f"   _explanation: {'✅ Presente' if '_explanation' in previsao_exemplo else '❌ Ausente (conforme esperado)'}")
            
        else:
            print(f"❌ Erro na requisição: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def testar_explicacao_basica():
    """Teste com explicações no nível básico"""
    print("\n🔍 TESTE: EXPLICAÇÃO BÁSICA")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "basic"
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        print(f"✅ Previsão: {previsao['yhat']} unidades")
        
        if '_explanation' in previsao:
            exp = previsao['_explanation']
            print(f"📝 {exp.get('summary', 'N/A')}")
            print(f"🎯 Confiança: {exp.get('confidence', 'N/A')}")
            
            # NOVO: Mostrar disponibilidade do HTML
            if 'html_summary' in exp:
                print(f"📋 Resumo HTML: Disponível ({len(exp['html_summary'])} caracteres)")
                print(f"   Para visualizar o HTML completo, acesse exp['html_summary']")
        
    print()

def testar_explicacao_detalhada():
    """Teste com explicações detalhadas"""
    print("\n📊 TESTE: EXPLICAÇÃO DETALHADA")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "detailed"
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        print(f"✅ Item {previsao['item_id']}: {previsao['yhat']} unidades")
        
        if '_explanation' in previsao:
            exp = previsao['_explanation']
            print(f"\n📝 {exp.get('summary', 'N/A')}")
            
            components = exp.get('components', {})
            if components:
                print(f"\n🔍 Tendência: {components.get('trend_explanation', 'N/A')}")
                print(f"🔄 Sazonalidade: {components.get('seasonal_explanation', 'N/A')}")
    
    print()

def testar_explicacao_avancada():
    print("\n🔬 TESTE: EXPLICAÇÃO AVANÇADA")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "advanced"
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        print(f"✅ Item {previsao['item_id']}: {previsao['yhat']} unidades")
        
        if '_explanation' in previsao:
            exp = previsao['_explanation']
            print(f"\n📝 {exp.get('summary', 'N/A')}")
            
            # Métricas técnicas
            technical = exp.get('technical_metrics', {})
            if technical:
                print(f"\n🔬 Métricas:")
                print(f"   MAE: {technical.get('mae', 'N/A')}")
                print(f"   MAPE: {technical.get('mape', 'N/A')}")
                print(f"   R²: {technical.get('r2', 'N/A')}")
    
    print()

def testar_explicacao_trimestral():
    print("\n📅 TESTE: EXPLICAÇÃO TRIMESTRAL")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "agrupamento_trimestral": True,
        "periodos": 1,  # 1 trimestre
        "include_explanation": True,
        "explanation_level": "detailed"
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        quarter_info = previsao.get('_quarter_info', {})
        print(f"✅ {quarter_info.get('quarter_name', 'N/A')}: {previsao['yhat']} unidades")
        
        if '_explanation' in previsao:
            exp = previsao['_explanation']
            print(f"\n📝 {exp.get('summary', 'N/A')}")
            
            breakdown = exp.get('quarterly_breakdown', {})
            if breakdown:
                print(f"📊 Média mensal: {breakdown.get('monthly_average', 'N/A')}")
    
    print()

def testar_html_summary():
    """Teste específico para demonstrar o resumo HTML"""
    print("\n🌐 TESTE: RESUMO HTML FORMATADO")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "detailed",
        "periodos": 1  # Apenas 1 período para exemplo mais limpo
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        if '_explanation' in previsao and 'html_summary' in previsao['_explanation']:
            html_content = previsao['_explanation']['html_summary']
            
            print(f"✅ Resumo HTML gerado com sucesso!")
            print(f"📏 Tamanho: {len(html_content)} caracteres")
            print(f"📅 Período: {previsao['ds'][:10]}")
            print(f"🎯 Previsão: {previsao['yhat']} unidades")
            
            # Salvar HTML em arquivo para visualização
            try:
                with open("previsao_exemplo.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"📄 HTML salvo em: previsao_exemplo.html")
                print("   Abra este arquivo em um navegador para visualizar")
            except Exception as e:
                print(f"❌ Erro ao salvar HTML: {e}")
        else:
            print("❌ Resumo HTML não encontrado")
    else:
        print(f"❌ Erro na requisição: {response.status_code}")
    
    print()

if __name__ == "__main__":
    print("🚀 DEMONSTRAÇÃO DE EXPLICABILIDADE")
    print("=" * 50)
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    
    try:
        testar_explicacao_basica()
        testar_explicacao_detalhada()
        testar_explicacao_avancada()
        testar_explicacao_trimestral()
        
        print("\n✅ DEMONSTRAÇÃO CONCLUÍDA!")
        print("=" * 50)
        print("\n📖 Parâmetros de explicabilidade:")
        print("  • include_explanation: true/false")
        print("  • explanation_level: 'basic'/'detailed'/'advanced'")
        print("  • explanation_language: 'pt'/'en'")
        print("\n🎯 Benefícios:")
        print("  • Entenda como o modelo chegou nas previsões")
        print("  • Identifique fatores que influenciam as previsões")
        print("  • Avalie a confiança e qualidade das previsões")
        print("  • Obtenha recomendações para melhorar a precisão")
        print("\n📋 NOVO: Campo html_summary")
        print("  • Resumo HTML formatado comum para todos os níveis")
        print("  • Ideal para exibição em interfaces web")
        print("  • Inclui todos os componentes e análises")
        print("  • Meses em português (corrigido)")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("Certifique-se de que o servidor está rodando!")

# Função auxiliar para demonstrar HTML completo
if __name__ == "__main__" and len(__import__('sys').argv) > 1 and __import__('sys').argv[1] == "--html":
    testar_html_summary() 