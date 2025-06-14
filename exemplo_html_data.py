#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do campo _html_data para armazenamento no banco
"""

import requests
import json

# Configuração do servidor
SERVER_URL = "http://localhost:5000"

def simular_fluxo_completo():
    """Simula o fluxo completo: previsão -> banco -> HTML"""
    print("🔄 SIMULANDO FLUXO COMPLETO")
    print("=" * 60)
    
    # 1. Fazer previsão (retorna _html_data)
    print("\n1. 📊 FAZENDO PREVISÃO...")
    dados_previsao = {
        "sales_data": [
            {"item_id": 1, "data": "2023-01-01", "quantidade": 100},
            {"item_id": 1, "data": "2023-02-01", "quantidade": 120},
            {"item_id": 1, "data": "2023-03-01", "quantidade": 95},
            {"item_id": 1, "data": "2023-04-01", "quantidade": 130},
            {"item_id": 1, "data": "2023-05-01", "quantidade": 110},
            {"item_id": 1, "data": "2023-06-01", "quantidade": 140}
        ],
        "data_inicio": "2023-07-01",
        "periodos": 1,
        "include_explanation": False  # Não precisamos do HTML agora
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=dados_previsao)
        
        if response.status_code == 200:
            resultado = response.json()
            previsao = resultado['forecast'][0]
            
            print(f"✅ Previsão realizada!")
            print(f"   Item: {previsao['item_id']}")
            print(f"   Previsão: {previsao['yhat']} unidades")
            print(f"   Data: {previsao['ds']}")
            
            # Verificar se _html_data está presente
            if '_html_data' in previsao:
                html_data = previsao['_html_data']
                print(f"✅ _html_data presente! ({len(json.dumps(html_data))} chars)")
                
                # 2. Simular armazenamento no banco
                print(f"\n2. 💾 SIMULANDO ARMAZENAMENTO NO BANCO...")
                dados_banco = {
                    "previsao_id": 12345,
                    "item_id": previsao['item_id'],
                    "yhat": previsao['yhat'],
                    "data_previsao": previsao['ds'],
                    "html_data": html_data  # Campo para armazenar no banco
                }
                
                # Simular salvamento (aqui você salvaria no seu banco)
                with open("dados_banco_simulado.json", "w", encoding="utf-8") as f:
                    json.dump(dados_banco, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Dados salvos no 'banco' (arquivo simulado)")
                print(f"   Campo html_data: {len(json.dumps(html_data))} caracteres")
                
                # 3. Gerar HTML usando dados do banco
                print(f"\n3. 🎨 GERANDO HTML A PARTIR DOS DADOS DO BANCO...")
                
                # Simular recuperação do banco
                html_data_do_banco = dados_banco['html_data']
                
                # Gerar HTML compacto
                dados_html_compact = {
                    "html_data": html_data_do_banco,
                    "layout": "compact"
                }
                
                response_compact = requests.post(f"{SERVER_URL}/generate_html", json=dados_html_compact)
                
                if response_compact.status_code == 200:
                    html_compact = response_compact.json()['html']
                    info_compact = response_compact.json()['info']
                    
                    print(f"✅ HTML compacto gerado!")
                    print(f"   Tamanho: {info_compact['size_chars']} caracteres")
                    print(f"   Layout: {info_compact['layout']}")
                    
                    # Salvar HTML compacto
                    with open("popup_do_banco.html", "w", encoding="utf-8") as f:
                        f.write(html_compact)
                    print(f"📄 Popup salvo: popup_do_banco.html")
                
                # Gerar HTML completo
                dados_html_full = {
                    "html_data": html_data_do_banco,
                    "layout": "full"
                }
                
                response_full = requests.post(f"{SERVER_URL}/generate_html", json=dados_html_full)
                
                if response_full.status_code == 200:
                    html_full = response_full.json()['html']
                    info_full = response_full.json()['info']
                    
                    print(f"✅ HTML completo gerado!")
                    print(f"   Tamanho: {info_full['size_chars']} caracteres")
                    print(f"   Layout: {info_full['layout']}")
                    
                    # Salvar HTML completo
                    with open("relatorio_do_banco.html", "w", encoding="utf-8") as f:
                        f.write(html_full)
                    print(f"📄 Relatório salvo: relatorio_do_banco.html")
                
                return True
                
            else:
                print("❌ _html_data não encontrado na resposta")
                return False
                
        else:
            print(f"❌ Erro na previsão: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def exemplo_previsao_trimestral():
    """Exemplo com previsão trimestral"""
    print("\n📅 EXEMPLO: PREVISÃO TRIMESTRAL")
    print("-" * 50)
    
    dados_trimestral = {
        "sales_data": [
            {"item_id": 2, "data": "2023-01-01", "quantidade": 200},
            {"item_id": 2, "data": "2023-02-01", "quantidade": 220},
            {"item_id": 2, "data": "2023-03-01", "quantidade": 195},
            {"item_id": 2, "data": "2023-04-01", "quantidade": 230},
            {"item_id": 2, "data": "2023-05-01", "quantidade": 210},
            {"item_id": 2, "data": "2023-06-01", "quantidade": 240}
        ],
        "data_inicio": "2023-07-01",
        "agrupamento_trimestral": True,
        "periodos": 1,  # 1 trimestre
        "include_explanation": False
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=dados_trimestral)
        
        if response.status_code == 200:
            resultado = response.json()
            previsao_trim = resultado['forecast'][0]
            
            print(f"✅ Previsão trimestral realizada!")
            print(f"   Trimestre: {previsao_trim.get('_quarter_info', {}).get('quarter_name', 'N/A')}")
            print(f"   Total: {previsao_trim['yhat']} unidades")
            
            if '_html_data' in previsao_trim:
                html_data_trim = previsao_trim['_html_data']
                
                # Gerar HTML trimestral compacto
                dados_html = {
                    "html_data": html_data_trim,
                    "layout": "compact"
                }
                
                response_html = requests.post(f"{SERVER_URL}/generate_html", json=dados_html)
                
                if response_html.status_code == 200:
                    html_trimestral = response_html.json()['html']
                    
                    with open("trimestre_do_banco.html", "w", encoding="utf-8") as f:
                        f.write(html_trimestral)
                    
                    print(f"✅ HTML trimestral gerado: trimestre_do_banco.html")
                    print(f"   Inclui detalhamento mensal: {'Detalhamento Mensal' in html_trimestral}")
                
        else:
            print(f"❌ Erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def analisar_html_data():
    """Analisa a estrutura do _html_data"""
    print("\n🔍 ANALISANDO ESTRUTURA DO _html_data")
    print("-" * 50)
    
    # Ler dados do banco simulado
    try:
        with open("dados_banco_simulado.json", "r", encoding="utf-8") as f:
            dados_banco = json.load(f)
        
        html_data = dados_banco['html_data']
        
        print(f"📋 Estrutura do _html_data:")
        print(f"   • item_id: {html_data.get('item_id')}")
        print(f"   • is_quarterly: {html_data.get('is_quarterly')}")
        print(f"   • date_iso: {html_data.get('date_iso')}")
        print(f"   • timestamp: {html_data.get('timestamp')}")
        
        print(f"\n📊 prediction:")
        prediction = html_data.get('prediction', {})
        for key, value in prediction.items():
            print(f"   • {key}: {value}")
        
        print(f"\n📈 explanation_data:")
        explanation = html_data.get('explanation_data', {})
        for key, value in explanation.items():
            if isinstance(value, dict):
                print(f"   • {key}: {json.dumps(value)[:50]}...")
            else:
                print(f"   • {key}: {value}")
        
        print(f"\n💾 Tamanho total: {len(json.dumps(html_data))} caracteres")
        print(f"💡 Ideal para armazenar em campo TEXT/JSON no banco")
        
    except FileNotFoundError:
        print("❌ Execute o fluxo completo primeiro para gerar os dados")

if __name__ == "__main__":
    print("🎯 DEMONSTRAÇÃO DO CAMPO _html_data")
    print("=" * 60)
    print("Este exemplo mostra como:")
    print("1. Obter _html_data da previsão")
    print("2. Armazenar no banco de dados")
    print("3. Gerar HTML a partir dos dados armazenados")
    print("\nCertifique-se de que o servidor está rodando em http://localhost:5000")
    
    try:
        # Fluxo principal
        sucesso = simular_fluxo_completo()
        
        if sucesso:
            exemplo_previsao_trimestral()
            analisar_html_data()
            
            print("\n✅ DEMONSTRAÇÃO CONCLUÍDA!")
            print("=" * 60)
            print("\n💡 VANTAGENS DO _html_data:")
            print("  ✅ Armazena apenas dados estruturados (não HTML)")
            print("  ✅ Tamanho menor que HTML completo")
            print("  ✅ Flexibilidade para gerar diferentes layouts")
            print("  ✅ Fácil de armazenar em campo JSON do banco")
            print("  ✅ Permite regenerar HTML quando necessário")
            
            print("\n📄 Arquivos gerados:")
            print("  • dados_banco_simulado.json - Simulação do banco")
            print("  • popup_do_banco.html - HTML compacto")
            print("  • relatorio_do_banco.html - HTML completo")
            print("  • trimestre_do_banco.html - HTML trimestral")
            
            print("\n🔄 Fluxo recomendado:")
            print("  1. POST /predict (sem include_explanation)")
            print("  2. Salvar _html_data no banco")
            print("  3. POST /generate_html quando precisar do HTML")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        print("Certifique-se de que o servidor está rodando!") 