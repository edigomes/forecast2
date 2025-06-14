#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do layout compacto para popups
"""

import requests
import json

# Configuração do servidor
SERVER_URL = "http://localhost:5000"

# Dados de exemplo
exemplo_dados = {
    "sales_data": [
        {"item_id": 1, "data": "2023-01-01", "quantidade": 100},
        {"item_id": 1, "data": "2023-02-01", "quantidade": 120},
        {"item_id": 1, "data": "2023-03-01", "quantidade": 95},
        {"item_id": 1, "data": "2023-04-01", "quantidade": 130},
        {"item_id": 1, "data": "2023-05-01", "quantidade": 110},
        {"item_id": 1, "data": "2023-06-01", "quantidade": 140}
    ],
    "data_inicio": "2023-07-01",
    "periodos": 3
}

def testar_layout_full():
    """Testa layout completo (padrão)"""
    print("\n📋 TESTE: LAYOUT COMPLETO (PADRÃO)")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "detailed",
        "html_layout": "full"  # Layout completo
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        if '_explanation' in previsao and 'html_summary' in previsao['_explanation']:
            html_content = previsao['_explanation']['html_summary']
            
            print(f"✅ Layout completo gerado!")
            print(f"📏 Tamanho: {len(html_content)} caracteres")
            print(f"🎯 Previsão: {previsao['yhat']} unidades")
            
            # Salvar HTML completo
            with open("layout_completo.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 HTML completo salvo em: layout_completo.html")
        else:
            print("❌ HTML summary não encontrado")
    else:
        print(f"❌ Erro na requisição: {response.status_code}")

def testar_layout_compacto():
    """Testa layout compacto para popups"""
    print("\n🎯 TESTE: LAYOUT COMPACTO (POPUP)")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "include_explanation": True,
        "explanation_level": "detailed",
        "html_layout": "compact"  # Layout compacto para popup
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        if '_explanation' in previsao and 'html_summary' in previsao['_explanation']:
            html_content = previsao['_explanation']['html_summary']
            
            print(f"✅ Layout compacto gerado!")
            print(f"📏 Tamanho: {len(html_content)} caracteres")
            print(f"🎯 Previsão: {previsao['yhat']} unidades")
            print(f"📐 Largura máxima: 400px (ideal para popup)")
            
            # Salvar HTML compacto
            with open("layout_compacto.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 HTML compacto salvo em: layout_compacto.html")
        else:
            print("❌ HTML summary não encontrado")
    else:
        print(f"❌ Erro na requisição: {response.status_code}")

def testar_trimestre_compacto():
    """Testa layout compacto para previsões trimestrais"""
    print("\n📅 TESTE: TRIMESTRE COMPACTO")
    print("-" * 50)
    
    dados = exemplo_dados.copy()
    dados.update({
        "agrupamento_trimestral": True,
        "periodos": 2,  # 2 trimestres
        "include_explanation": True,
        "explanation_level": "basic",
        "html_layout": "compact"
    })
    
    response = requests.post(f"{SERVER_URL}/predict", json=dados)
    if response.status_code == 200:
        resultado = response.json()
        previsao = resultado['forecast'][0]
        
        if '_explanation' in previsao and 'html_summary' in previsao['_explanation']:
            html_content = previsao['_explanation']['html_summary']
            
            print(f"✅ Trimestre compacto gerado!")
            print(f"📏 Tamanho: {len(html_content)} caracteres")
            print(f"🎯 Previsão trimestral: {previsao['yhat']} unidades")
            print(f"📅 Período: {previsao.get('_quarter_info', {}).get('quarter_name', 'N/A')}")
            
            # Salvar HTML trimestral compacto
            with open("trimestre_compacto.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"📄 HTML trimestral compacto salvo em: trimestre_compacto.html")
        else:
            print("❌ HTML summary não encontrado")
    else:
        print(f"❌ Erro na requisição: {response.status_code}")

def comparar_layouts():
    """Compara os dois layouts lado a lado"""
    print("\n⚖️  COMPARAÇÃO DOS LAYOUTS")
    print("-" * 50)
    
    # Layout completo
    dados_full = exemplo_dados.copy()
    dados_full.update({
        "include_explanation": True,
        "explanation_level": "detailed",
        "html_layout": "full",
        "periodos": 1
    })
    
    # Layout compacto
    dados_compact = exemplo_dados.copy()
    dados_compact.update({
        "include_explanation": True,
        "explanation_level": "detailed",
        "html_layout": "compact",
        "periodos": 1
    })
    
    try:
        # Requisições
        response_full = requests.post(f"{SERVER_URL}/predict", json=dados_full)
        response_compact = requests.post(f"{SERVER_URL}/predict", json=dados_compact)
        
        if response_full.status_code == 200 and response_compact.status_code == 200:
            full_html = response_full.json()['forecast'][0]['_explanation']['html_summary']
            compact_html = response_compact.json()['forecast'][0]['_explanation']['html_summary']
            
            print(f"📋 Layout COMPLETO:")
            print(f"   • Tamanho: {len(full_html)} caracteres")
            print(f"   • Largura máxima: 800px")
            print(f"   • Ideal para: Páginas completas, relatórios")
            
            print(f"\n🎯 Layout COMPACTO:")
            print(f"   • Tamanho: {len(compact_html)} caracteres")
            print(f"   • Largura máxima: 400px")
            print(f"   • Ideal para: Popups, tooltips, modais")
            
            print(f"\n📊 Redução de tamanho: {((len(full_html) - len(compact_html)) / len(full_html)) * 100:.1f}%")
            
            # Criar página de comparação
            comparison_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Comparação de Layouts</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ display: flex; gap: 20px; }}
                    .layout {{ flex: 1; }}
                    h2 {{ text-align: center; color: #333; }}
                    .full {{ border: 2px solid #2196f3; }}
                    .compact {{ border: 2px solid #ff9800; }}
                </style>
            </head>
            <body>
                <h1 style="text-align: center;">📊 Comparação de Layouts HTML</h1>
                <div class="container">
                    <div class="layout full">
                        <h2>📋 Layout Completo (800px)</h2>
                        {full_html}
                    </div>
                    <div class="layout compact">
                        <h2>🎯 Layout Compacto (400px)</h2>
                        {compact_html}
                    </div>
                </div>
            </body>
            </html>
            """
            
            with open("comparacao_layouts.html", "w", encoding="utf-8") as f:
                f.write(comparison_html)
            print(f"📄 Comparação salva em: comparacao_layouts.html")
            
        else:
            print("❌ Erro nas requisições")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🎨 DEMONSTRAÇÃO DE LAYOUTS HTML")
    print("=" * 50)
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    
    try:
        testar_layout_full()
        testar_layout_compacto()
        testar_trimestre_compacto()
        comparar_layouts()
        
        print("\n✅ DEMONSTRAÇÃO CONCLUÍDA!")
        print("=" * 50)
        print("\n🎨 Layouts disponíveis:")
        print("  • html_layout: 'full' (padrão) - Layout completo para páginas")
        print("  • html_layout: 'compact' - Layout compacto para popups")
        print("\n📐 Características:")
        print("  • Full: 800px largura, todas as seções, ideal para relatórios")
        print("  • Compact: 400px largura, informações essenciais, ideal para popups")
        print("\n📄 Arquivos gerados:")
        print("  • layout_completo.html - Exemplo do layout full")
        print("  • layout_compacto.html - Exemplo do layout compact")
        print("  • trimestre_compacto.html - Trimestre em layout compact")
        print("  • comparacao_layouts.html - Comparação lado a lado")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("Certifique-se de que o servidor está rodando!") 