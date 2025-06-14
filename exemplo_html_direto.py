#!/usr/bin/env python3
"""
Exemplo de uso do endpoint /generate_html com retorno HTML direto

Este script demonstra como usar o endpoint para retornar HTML puro (text/html)
em vez de JSON, permitindo exibição direta no navegador.

Casos de uso:
1. Abrir HTML em nova aba/janela
2. Incorporar em iframe
3. Salvar como arquivo HTML
4. Exibir direto em WebView
"""

import requests
import json
import webbrowser
import tempfile
import os
from datetime import datetime

# Configuração
SERVER_URL = "http://localhost:5000"

def exemplo_html_direto_com_html_data():
    """
    Exemplo usando html_data (dados do banco) para retornar HTML direto
    """
    print("="*80)
    print("EXEMPLO: HTML DIRETO COM html_data")
    print("="*80)
    
    # Dados que viriam do banco (campo _html_data da previsão)
    html_data_do_banco = {
        "date_iso": "2025-07-01T00:00:00",
        "explanation_data": {
            "confidence_score": "Média",
            "data_completeness": 100,
            "data_points": 29,
            "mape": 23.163763007474643,
            "outlier_count": 0,
            "r2": 0.40467070728000276,
            "seasonal_pattern": {
                "1": 0.6837204206836109,
                "2": 0.7272129710780018,
                "3": 0.9127957931638914,
                "4": 0.7973269062226118,
                "5": 0.6944566170026292,
                "6": 0.804666958808063,
                "7": 0.8886941279579317,
                "8": 0.9524539877300613,
                "9": 1.1855828220858895,
                "10": 1.513584574934268,
                "11": 1.5547765118317265,
                "12": 1.124780893952673
            },
            "seasonal_strength": 1.7400172193688208,
            "std": 528.049079205012,
            "training_period": {
                "end": "2025-05-31",
                "months": 29,
                "start": "2023-01-31"
            },
            "trend_slope": 18.630295566502483,
            "trend_strength": 0.4651627993773888
        },
        "is_quarterly": False,
        "item_id": 1687,
        "prediction": {
            "ds": "2025-07-01 00:00:00",
            "trend": 1380.92,
            "yearly": -153.7,
            "yhat": 1227.22,
            "yhat_lower": 502.75,
            "yhat_upper": 1951.69
        },
        "timestamp": 1751328000
    }
    
    # Payload para o endpoint
    payload = {
        "html_data": html_data_do_banco,
        "layout": "full",
        "return_html_direct": True  # Parâmetro para solicitar HTML direto
    }
    
    print("Enviando requisição para gerar HTML direto...")
    
    try:
        # Método 1: Usando parâmetro return_html_direct
        response = requests.post(
            f"{SERVER_URL}/generate_html",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ HTML recebido com sucesso!")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Tamanho: {len(response.text)} caracteres")
            
            # Salvar HTML em arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(response.text)
                html_file = f.name
            
            print(f"HTML salvo em: {html_file}")
            
            # Abrir no navegador
            print("Abrindo no navegador...")
            webbrowser.open(f"file://{html_file}")
            
            return html_file
            
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

def exemplo_html_direto_com_header():
    """
    Exemplo usando header Accept: text/html para retornar HTML direto
    """
    print("\n" + "="*80)
    print("EXEMPLO: HTML DIRETO COM HEADER Accept: text/html")
    print("="*80)
    
    # Dados que viriam do banco
    html_data_do_banco = {
        "date_iso": "2025-08-01T00:00:00",
        "explanation_data": {
            "confidence_score": "Alta",
            "data_completeness": 95.5,
            "data_points": 24,
            "mape": 12.4,
            "outlier_count": 2,
            "r2": 0.82,
            "seasonal_pattern": {
                "1": 0.85, "2": 0.90, "3": 1.15, "4": 1.05,
                "5": 0.95, "6": 1.10, "7": 1.25, "8": 1.35,
                "9": 1.20, "10": 1.45, "11": 1.55, "12": 1.30
            },
            "seasonal_strength": 0.8,
            "std": 120.5,
            "training_period": {
                "end": "2025-06-30",
                "months": 24,
                "start": "2023-07-01"
            },
            "trend_slope": 5.2,
            "trend_strength": 0.3
        },
        "is_quarterly": False,
        "item_id": 2500,
        "prediction": {
            "ds": "2025-08-01 00:00:00",
            "trend": 850.0,
            "yearly": 42.5,
            "yhat": 892.5,
            "yhat_lower": 720.0,
            "yhat_upper": 1065.0
        },
        "timestamp": 1754006400
    }
    
    # Payload para o endpoint
    payload = {
        "html_data": html_data_do_banco,
        "layout": "compact"  # Layout compacto para popup
    }
    
    print("Enviando requisição com header Accept: text/html...")
    
    try:
        # Método 2: Usando header Accept
        response = requests.post(
            f"{SERVER_URL}/generate_html",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/html"  # Header que solicita HTML direto
            }
        )
        
        if response.status_code == 200:
            print(f"✅ HTML recebido com sucesso!")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Tamanho: {len(response.text)} caracteres")
            
            # Salvar HTML em arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='_compact.html', delete=False, encoding='utf-8') as f:
                f.write(response.text)
                html_file = f.name
            
            print(f"HTML compacto salvo em: {html_file}")
            
            # Abrir no navegador
            print("Abrindo no navegador...")
            webbrowser.open(f"file://{html_file}")
            
            return html_file
            
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

def exemplo_html_trimestral_direto():
    """
    Exemplo de HTML direto para previsão trimestral
    """
    print("\n" + "="*80)
    print("EXEMPLO: HTML DIRETO PARA PREVISÃO TRIMESTRAL")
    print("="*80)
    
    # Dados de previsão trimestral
    html_data_trimestral = {
        "date_iso": "2025-07-01T00:00:00",
        "explanation_data": {
            "confidence_score": "Média",
            "data_completeness": 100,
            "data_points": 36,
            "mape": 18.7,
            "outlier_count": 1,
            "r2": 0.65,
            "seasonal_pattern": {
                "1": 0.75, "2": 0.80, "3": 0.95, "4": 0.85,
                "5": 0.90, "6": 1.05, "7": 1.15, "8": 1.25,
                "9": 1.35, "10": 1.50, "11": 1.45, "12": 1.20
            },
            "seasonal_strength": 1.2,
            "std": 450.0,
            "training_period": {
                "end": "2025-06-30",
                "months": 36,
                "start": "2022-07-01"
            },
            "trend_slope": 12.5,
            "trend_strength": 0.4
        },
        "is_quarterly": True,
        "item_id": 3000,
        "prediction": {
            "ds": "2025-07-01 00:00:00",
            "trend": 4200.0,
            "yearly": 350.0,
            "yhat": 4550.0,
            "yhat_lower": 3800.0,
            "yhat_upper": 5300.0
        },
        "quarterly_info": {
            "quarter_name": "Q3/2025",
            "start_date": "2025-07-01",
            "end_date": "2025-09-30",
            "monthly_details": [
                {
                    "month": "2025-07",
                    "yhat": 1450.0,
                    "yhat_lower": 1200.0,
                    "yhat_upper": 1700.0
                },
                {
                    "month": "2025-08",
                    "yhat": 1550.0,
                    "yhat_lower": 1300.0,
                    "yhat_upper": 1800.0
                },
                {
                    "month": "2025-09",
                    "yhat": 1550.0,
                    "yhat_lower": 1300.0,
                    "yhat_upper": 1800.0
                }
            ]
        },
        "timestamp": 1751328000
    }
    
    # Payload para o endpoint
    payload = {
        "html_data": html_data_trimestral,
        "layout": "full",
        "return_html_direct": True
    }
    
    print("Enviando requisição para HTML trimestral...")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/generate_html",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ HTML trimestral recebido com sucesso!")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Tamanho: {len(response.text)} caracteres")
            
            # Salvar HTML em arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='_trimestral.html', delete=False, encoding='utf-8') as f:
                f.write(response.text)
                html_file = f.name
            
            print(f"HTML trimestral salvo em: {html_file}")
            
            # Abrir no navegador
            print("Abrindo no navegador...")
            webbrowser.open(f"file://{html_file}")
            
            return html_file
            
        else:
            print(f"❌ Erro {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return None

def comparar_json_vs_html():
    """
    Comparação entre retorno JSON e HTML direto
    """
    print("\n" + "="*80)
    print("COMPARAÇÃO: JSON vs HTML DIRETO")
    print("="*80)
    
    html_data = {
        "date_iso": "2025-09-01T00:00:00",
        "explanation_data": {
            "confidence_score": "Alta",
            "data_completeness": 100,
            "data_points": 18,
            "mape": 8.5,
            "outlier_count": 0,
            "r2": 0.91,
            "seasonal_pattern": {
                "1": 0.80, "2": 0.85, "3": 1.00, "4": 0.95,
                "5": 1.05, "6": 1.20, "7": 1.35, "8": 1.40,
                "9": 1.30, "10": 1.15, "11": 1.10, "12": 0.95
            },
            "seasonal_strength": 0.9,
            "std": 85.2,
            "training_period": {
                "end": "2025-08-31",
                "months": 18,
                "start": "2024-03-01"
            },
            "trend_slope": 8.7,
            "trend_strength": 0.25
        },
        "is_quarterly": False,
        "item_id": 4000,
        "prediction": {
            "ds": "2025-09-01 00:00:00",
            "trend": 1200.0,
            "yearly": 156.0,
            "yhat": 1356.0,
            "yhat_lower": 1180.0,
            "yhat_upper": 1532.0
        },
        "timestamp": 1756684800
    }
    
    # 1. Requisição JSON (padrão)
    print("1️⃣  Requisição JSON (padrão):")
    try:
        response_json = requests.post(
            f"{SERVER_URL}/generate_html",
            json={"html_data": html_data, "layout": "compact"},
            headers={"Content-Type": "application/json"}
        )
        
        if response_json.status_code == 200:
            print(f"   ✅ Sucesso - Content-Type: {response_json.headers.get('content-type')}")
            print(f"   📊 Tamanho da resposta: {len(response_json.text)} caracteres")
            
            # Parse JSON para ver estrutura
            json_data = response_json.json()
            print(f"   🔧 Estrutura JSON: {list(json_data.keys())}")
            print(f"   📝 Tamanho do HTML interno: {len(json_data.get('html', ''))} caracteres")
        else:
            print(f"   ❌ Erro: {response_json.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Requisição HTML direto
    print("\n2️⃣  Requisição HTML direto:")
    try:
        response_html = requests.post(
            f"{SERVER_URL}/generate_html",
            json={"html_data": html_data, "layout": "compact", "return_html_direct": True},
            headers={"Content-Type": "application/json"}
        )
        
        if response_html.status_code == 200:
            print(f"   ✅ Sucesso - Content-Type: {response_html.headers.get('content-type')}")
            print(f"   📊 Tamanho da resposta: {len(response_html.text)} caracteres")
            print(f"   🌐 Conteúdo: HTML puro pronto para exibição")
            
            # Salvar para comparação
            with tempfile.NamedTemporaryFile(mode='w', suffix='_comparacao.html', delete=False, encoding='utf-8') as f:
                f.write(response_html.text)
                html_file = f.name
            
            print(f"   💾 Salvo em: {html_file}")
            
        else:
            print(f"   ❌ Erro: {response_html.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    print(f"\n📋 RESUMO:")
    print(f"   • JSON: Estruturado, precisa parsing, para APIs")
    print(f"   • HTML direto: Pronto para exibição, para navegadores")
    print(f"   • Ambos têm o mesmo conteúdo HTML interno")

def demonstrar_casos_de_uso():
    """
    Demonstra os principais casos de uso do HTML direto
    """
    print("\n" + "="*80)
    print("CASOS DE USO DO HTML DIRETO")
    print("="*80)
    
    casos_de_uso = [
        {
            "nome": "🔗 Link direto para relatório",
            "descricao": "Gerar URL que abre relatório diretamente no navegador",
            "exemplo": "https://meuapp.com/generate_html + POST com html_data"
        },
        {
            "nome": "🖼️  Iframe incorporado",
            "descricao": "Incorporar explicação em popup ou modal",
            "exemplo": "<iframe src='/generate_html_endpoint'></iframe>"
        },
        {
            "nome": "💾 Arquivo HTML para download",
            "descricao": "Salvar explicação como arquivo HTML",
            "exemplo": "response.text -> arquivo.html"
        },
        {
            "nome": "📱 WebView em apps mobile",
            "descricao": "Exibir explicação em WebView de app nativo",
            "exemplo": "webView.loadData(htmlContent, 'text/html', 'utf-8')"
        },
        {
            "nome": "📧 Email HTML",
            "descricao": "Enviar explicação por email em formato HTML",
            "exemplo": "email.body = htmlContent (com layout compact)"
        },
        {
            "nome": "🖨️  Impressão/PDF",
            "descricao": "Gerar PDF a partir do HTML ou imprimir",
            "exemplo": "wkhtmltopdf ou print do navegador"
        }
    ]
    
    for i, caso in enumerate(casos_de_uso, 1):
        print(f"\n{i}. {caso['nome']}")
        print(f"   📝 {caso['descricao']}")
        print(f"   💡 {caso['exemplo']}")
    
    print(f"\n🎯 VANTAGENS DO HTML DIRETO:")
    print(f"   • Menos processamento no frontend")
    print(f"   • Compatível com qualquer navegador")
    print(f"   • Pode ser usado em contextos onde JSON não é ideal")
    print(f"   • Reduz complexidade de integração")

def main():
    """
    Executa todos os exemplos
    """
    print("🚀 EXEMPLOS DE HTML DIRETO - ENDPOINT /generate_html")
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    
    arquivos_gerados = []
    
    # Executar exemplos
    arquivo1 = exemplo_html_direto_com_html_data()
    if arquivo1:
        arquivos_gerados.append(arquivo1)
    
    arquivo2 = exemplo_html_direto_com_header()
    if arquivo2:
        arquivos_gerados.append(arquivo2)
    
    arquivo3 = exemplo_html_trimestral_direto()
    if arquivo3:
        arquivos_gerados.append(arquivo3)
    
    comparar_json_vs_html()
    demonstrar_casos_de_uso()
    
    # Resumo final
    print(f"\n" + "="*80)
    print("📋 RESUMO DOS EXEMPLOS")
    print("="*80)
    
    if arquivos_gerados:
        print(f"✅ {len(arquivos_gerados)} arquivos HTML gerados com sucesso:")
        for arquivo in arquivos_gerados:
            print(f"   📄 {arquivo}")
        
        print(f"\n🌐 Todos os arquivos foram abertos no navegador padrão")
        print(f"🗑️  Para limpar arquivos temporários:")
        for arquivo in arquivos_gerados:
            print(f"   rm '{arquivo}'" if os.name != 'nt' else f"   del '{arquivo}'")
    else:
        print("❌ Nenhum arquivo foi gerado. Verifique se o servidor está rodando.")
    
    print(f"\n🔧 COMO USAR EM PRODUÇÃO:")
    print(f"   1. Armazenar campo '_html_data' no banco junto com previsões")
    print(f"   2. Para exibir: POST /generate_html com html_data + return_html_direct=true")
    print(f"   3. Ou usar header Accept: text/html para HTML direto")
    print(f"   4. Layout 'compact' para popups, 'full' para páginas completas")

if __name__ == "__main__":
    main() 