#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do endpoint /generate_html
"""

import requests
import json

# Configuração do servidor
SERVER_URL = "http://localhost:5000"

def exemplo_generate_html_mensal():
    """Exemplo de geração de HTML para previsão mensal"""
    print("\n📊 EXEMPLO: GERAÇÃO DE HTML MENSAL")
    print("-" * 50)
    
    # Dados da previsão (normalmente você obteria isso de /predict)
    dados_html = {
        "item_id": 1,
        "prediction": {
            "yhat": 150.5,
            "yhat_lower": 130.2,
            "yhat_upper": 170.8,
            "trend": 145.0,
            "yearly": 5.5,
            "ds": "2024-01-01"
        },
        "explanation_data": {
            "data_points": 12,
            "confidence_score": "Alta",
            "mape": 8.5,
            "r2": 0.85,
            "outlier_count": 1,
            "trend_slope": 2.5,
            "seasonal_pattern": {1: 1.1, 2: 0.9, 3: 1.0},
            "training_period": {
                "start": "2023-01-01",
                "end": "2023-12-01"
            }
        },
        "layout": "compact"  # ou "full"
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/generate_html", json=dados_html)
        
        if response.status_code == 200:
            resultado = response.json()
            html_content = resultado['html']
            info = resultado['info']
            
            print(f"✅ HTML gerado com sucesso!")
            print(f"📏 Tamanho: {info['size_chars']} caracteres")
            print(f"🎨 Layout: {info['layout']}")
            print(f"📅 Período: {info['period']}")
            
            # Salvar HTML
            filename = f"html_mensal_{info['layout']}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 Salvo em: {filename}")
            
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def exemplo_generate_html_trimestral():
    """Exemplo de geração de HTML para previsão trimestral"""
    print("\n📅 EXEMPLO: GERAÇÃO DE HTML TRIMESTRAL")
    print("-" * 50)
    
    dados_html = {
        "item_id": 2,
        "prediction": {
            "yhat": 450.0,
            "yhat_lower": 400.0,
            "yhat_upper": 500.0,
            "trend": 440.0,
            "yearly": 10.0,
            "ds": "2024-01-01"
        },
        "explanation_data": {
            "data_points": 18,
            "confidence_score": "Média",
            "mape": 12.3,
            "r2": 0.72,
            "outlier_count": 0,
            "trend_slope": 3.0,
            "training_period": {
                "start": "2022-07-01",
                "end": "2023-12-01"
            }
        },
        "layout": "full",
        "is_quarterly": True,
        "quarterly_info": {
            "quarter_name": "Q1/2024",
            "start_date": "2024-01-01",
            "end_date": "2024-03-01",
            "monthly_details": [
                {"month": "2024-01", "yhat": 150, "yhat_lower": 130, "yhat_upper": 170},
                {"month": "2024-02", "yhat": 145, "yhat_lower": 125, "yhat_upper": 165},
                {"month": "2024-03", "yhat": 155, "yhat_lower": 135, "yhat_upper": 175}
            ]
        }
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/generate_html", json=dados_html)
        
        if response.status_code == 200:
            resultado = response.json()
            html_content = resultado['html']
            info = resultado['info']
            
            print(f"✅ HTML trimestral gerado!")
            print(f"📏 Tamanho: {info['size_chars']} caracteres")
            print(f"🎨 Layout: {info['layout']}")
            print(f"📅 Trimestre: {info['period']}")
            
            # Salvar HTML
            filename = f"html_trimestral_{info['layout']}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 Salvo em: {filename}")
            
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def exemplo_comparacao_layouts():
    """Compara layouts full vs compact usando o endpoint"""
    print("\n⚖️  EXEMPLO: COMPARAÇÃO DE LAYOUTS")
    print("-" * 50)
    
    # Dados base
    dados_base = {
        "item_id": 3,
        "prediction": {
            "yhat": 200.0,
            "yhat_lower": 180.0,
            "yhat_upper": 220.0,
            "trend": 195.0,
            "yearly": 5.0,
            "ds": "2024-06-01"
        },
        "explanation_data": {
            "data_points": 15,
            "confidence_score": "Alta",
            "mape": 7.2,
            "r2": 0.88,
            "outlier_count": 2,
            "trend_slope": 1.8
        }
    }
    
    try:
        # Layout full
        dados_full = dados_base.copy()
        dados_full["layout"] = "full"
        response_full = requests.post(f"{SERVER_URL}/generate_html", json=dados_full)
        
        # Layout compact
        dados_compact = dados_base.copy()
        dados_compact["layout"] = "compact"
        response_compact = requests.post(f"{SERVER_URL}/generate_html", json=dados_compact)
        
        if response_full.status_code == 200 and response_compact.status_code == 200:
            info_full = response_full.json()['info']
            info_compact = response_compact.json()['info']
            
            print(f"📋 Layout FULL:")
            print(f"   • Tamanho: {info_full['size_chars']} caracteres")
            print(f"   • Período: {info_full['period']}")
            
            print(f"\n🎯 Layout COMPACT:")
            print(f"   • Tamanho: {info_compact['size_chars']} caracteres")
            print(f"   • Período: {info_compact['period']}")
            
            reducao = ((info_full['size_chars'] - info_compact['size_chars']) / info_full['size_chars']) * 100
            print(f"\n📊 Redução de tamanho: {reducao:.1f}%")
            
        else:
            print("❌ Erro nas requisições")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def exemplo_uso_pratico():
    """Exemplo de uso prático - simulando fluxo real"""
    print("\n🔄 EXEMPLO: USO PRÁTICO")
    print("-" * 50)
    print("Simulando cenário real onde você:")
    print("1. Faz previsão com explicação desabilitada")
    print("2. Extrai dados da previsão")
    print("3. Gera HTML separadamente")
    
    # Simulando dados que você obteria de /predict (sem html_summary)
    previsao_obtida = {
        "item_id": 10,
        "ds": "2024-08-01 00:00:00",
        "yhat": 175.3,
        "yhat_lower": 155.8,
        "yhat_upper": 194.8,
        "trend": 170.0,
        "yearly": 5.3,
        "weekly": 0.0,
        "holidays": 0.0
    }
    
    # Dados de explicação que você tem (de alguma fonte)
    dados_explicacao = {
        "data_points": 24,
        "confidence_score": "Alta",
        "mape": 6.8,
        "r2": 0.91,
        "outlier_count": 0,
        "trend_slope": 2.2,
        "seasonal_strength": 0.4,
        "trend_strength": 0.3
    }
    
    # Preparar dados para geração de HTML
    dados_para_html = {
        "item_id": previsao_obtida["item_id"],
        "prediction": {
            "yhat": previsao_obtida["yhat"],
            "yhat_lower": previsao_obtida["yhat_lower"],
            "yhat_upper": previsao_obtida["yhat_upper"],
            "trend": previsao_obtida["trend"],
            "yearly": previsao_obtida["yearly"],
            "ds": previsao_obtida["ds"]
        },
        "explanation_data": dados_explicacao,
        "layout": "compact"  # Para usar em popup
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/generate_html", json=dados_para_html)
        
        if response.status_code == 200:
            html_gerado = response.json()['html']
            info = response.json()['info']
            
            print(f"✅ HTML gerado para uso prático!")
            print(f"📊 Item: {info['item_id']}")
            print(f"📅 Período: {info['period']}")
            print(f"🎨 Layout: {info['layout']} ({info['size_chars']} chars)")
            
            # Salvar para uso
            with open("html_para_popup.html", "w", encoding="utf-8") as f:
                f.write(html_gerado)
            print(f"📄 HTML pronto para uso: html_para_popup.html")
            
        else:
            print(f"❌ Erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🎨 DEMONSTRAÇÃO DO ENDPOINT /generate_html")
    print("=" * 60)
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    
    try:
        exemplo_generate_html_mensal()
        exemplo_generate_html_trimestral()
        exemplo_comparacao_layouts()
        exemplo_uso_pratico()
        
        print("\n✅ DEMONSTRAÇÃO CONCLUÍDA!")
        print("=" * 60)
        print("\n📋 Endpoint criado: POST /generate_html")
        print("\n📝 Parâmetros obrigatórios:")
        print("  • item_id: ID do item")
        print("  • prediction: {yhat, yhat_lower, yhat_upper, trend, yearly, ds}")
        print("\n📝 Parâmetros opcionais:")
        print("  • explanation_data: Dados de explicação")
        print("  • layout: 'full' ou 'compact'")
        print("  • is_quarterly: true/false")
        print("  • quarterly_info: Dados do trimestre")
        print("\n🎯 Retorna:")
        print("  • html: String HTML gerada")
        print("  • info: Metadados (tamanho, layout, etc.)")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("Certifique-se de que o servidor está rodando!") 