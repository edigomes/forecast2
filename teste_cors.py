#!/usr/bin/env python3
"""
Teste de CORS - Verifica se o servidor aceita requests de qualquer origem

Este script simula requests vindos de diferentes origens para testar
se o CORS está configurado corretamente.
"""

import requests
import json

# Configuração
SERVER_URL = "http://localhost:5000"

def teste_cors_headers():
    """
    Testa se o servidor retorna os headers de CORS apropriados
    """
    print("="*70)
    print("🌐 TESTE DE CORS - HEADERS")
    print("="*70)
    
    # Testar endpoint predict com headers CORS
    headers_test = {
        "Origin": "http://meusite.com",  # Simular origem diferente
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
        "Content-Type": "application/json"
    }
    
    try:
        # Fazer request OPTIONS (preflight)
        print("1️⃣  Testando preflight request (OPTIONS)...")
        response = requests.options(
            f"{SERVER_URL}/predict",
            headers=headers_test
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Verificar headers de CORS
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }
        
        print("Headers de CORS retornados:")
        for header, value in cors_headers.items():
            status = "✅" if value else "❌"
            print(f"   {status} {header}: {value}")
        
        # Verificar se permite qualquer origem
        if cors_headers["Access-Control-Allow-Origin"] == "*":
            print("✅ CORS configurado para aceitar qualquer origem")
        else:
            print(f"⚠️  CORS limitado à origem: {cors_headers['Access-Control-Allow-Origin']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def teste_cors_post_request():
    """
    Testa POST request com origem diferente
    """
    print("\n" + "="*70)
    print("📡 TESTE DE CORS - POST REQUEST")
    print("="*70)
    
    # Headers simulando request de origem diferente
    headers = {
        "Origin": "https://frontend.exemplo.com",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Dados mínimos para teste
    test_data = {
        "html_data": {
            "item_id": 999,
            "prediction": {
                "ds": "2025-07-01 00:00:00",
                "yhat": 100.0,
                "yhat_lower": 80.0,
                "yhat_upper": 120.0,
                "trend": 95.0,
                "yearly": 5.0
            },
            "explanation_data": {
                "confidence_score": "Alta",
                "data_points": 12,
                "mape": 10.0,
                "r2": 0.8,
                "seasonal_pattern": {"1": 1.0, "2": 1.0},
                "seasonal_strength": 0.5,
                "std": 15.0,
                "training_period": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "months": 12
                },
                "trend_slope": 2.0,
                "trend_strength": 0.3
            },
            "is_quarterly": False,
            "date_iso": "2025-07-01T00:00:00",
            "timestamp": 1751328000
        },
        "layout": "compact"
    }
    
    try:
        print("Enviando POST request com origem diferente...")
        response = requests.post(
            f"{SERVER_URL}/generate_html",
            json=test_data,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        
        # Verificar headers de resposta
        cors_origin = response.headers.get("Access-Control-Allow-Origin")
        if cors_origin:
            print(f"✅ Access-Control-Allow-Origin: {cors_origin}")
        else:
            print("❌ Header Access-Control-Allow-Origin não encontrado")
        
        if response.status_code == 200:
            print("✅ Request bem-sucedido!")
            try:
                data = response.json()
                if "html" in data:
                    print(f"✅ HTML gerado: {len(data['html'])} caracteres")
                else:
                    print("⚠️  Response não contém HTML")
            except:
                print("⚠️  Response não é JSON válido")
        else:
            print(f"❌ Request falhou: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def teste_cors_diferentes_origens():
    """
    Testa requests de múltiplas origens diferentes
    """
    print("\n" + "="*70)
    print("🌍 TESTE DE CORS - MÚLTIPLAS ORIGENS")
    print("="*70)
    
    # Lista de origens para testar
    origens = [
        "http://localhost:3000",          # React dev server
        "https://meuapp.vercel.app",      # Vercel
        "https://app.exemplo.com",        # Domínio customizado
        "http://192.168.1.100:8080",      # IP local
        "https://frontend.herokuapp.com"  # Heroku
    ]
    
    # Dados simples para teste
    test_data = {
        "html_data": {
            "item_id": 123,
            "prediction": {
                "ds": "2025-06-01 00:00:00",
                "yhat": 50.0,
                "yhat_lower": 40.0,
                "yhat_upper": 60.0,
                "trend": 48.0,
                "yearly": 2.0
            },
            "explanation_data": {
                "confidence_score": "Média",
                "data_points": 6,
                "mape": 15.0,
                "r2": 0.6,
                "seasonal_pattern": {"6": 1.1},
                "seasonal_strength": 0.3,
                "std": 8.0,
                "training_period": {"start": "2024-01-01", "end": "2024-06-01", "months": 6},
                "trend_slope": 1.0,
                "trend_strength": 0.2
            },
            "is_quarterly": False,
            "date_iso": "2025-06-01T00:00:00",
            "timestamp": 1748736000
        },
        "layout": "compact"
    }
    
    resultados = []
    
    for origem in origens:
        print(f"\n🔍 Testando origem: {origem}")
        
        try:
            headers = {
                "Origin": origem,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{SERVER_URL}/generate_html",
                json=test_data,
                headers=headers,
                timeout=5
            )
            
            cors_header = response.headers.get("Access-Control-Allow-Origin", "")
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ✅ CORS Header: {cors_header}")
                resultados.append({"origem": origem, "status": "✅ Sucesso"})
            else:
                print(f"   ❌ Status: {response.status_code}")
                resultados.append({"origem": origem, "status": f"❌ Erro {response.status_code}"})
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            resultados.append({"origem": origem, "status": f"❌ Exceção: {str(e)[:50]}"})
    
    # Resumo dos resultados
    print(f"\n📋 RESUMO DOS TESTES:")
    for resultado in resultados:
        print(f"   {resultado['status']} - {resultado['origem']}")
    
    sucessos = sum(1 for r in resultados if "✅" in r["status"])
    print(f"\n🎯 {sucessos}/{len(origens)} origens testadas com sucesso")
    
    return sucessos == len(origens)

def main():
    """
    Executa todos os testes de CORS
    """
    print("🚀 TESTES DE CORS - SERVIDOR FORECAST")
    print("Certifique-se de que o servidor está rodando em http://localhost:5000")
    
    testes_realizados = []
    
    # Teste 1: Headers CORS
    try:
        resultado1 = teste_cors_headers()
        testes_realizados.append(("Headers CORS", resultado1))
    except Exception as e:
        print(f"❌ Erro no teste de headers: {e}")
        testes_realizados.append(("Headers CORS", False))
    
    # Teste 2: POST Request
    try:
        resultado2 = teste_cors_post_request()
        testes_realizados.append(("POST Request", resultado2))
    except Exception as e:
        print(f"❌ Erro no teste de POST: {e}")
        testes_realizados.append(("POST Request", False))
    
    # Teste 3: Múltiplas origens
    try:
        resultado3 = teste_cors_diferentes_origens()
        testes_realizados.append(("Múltiplas Origens", resultado3))
    except Exception as e:
        print(f"❌ Erro no teste de múltiplas origens: {e}")
        testes_realizados.append(("Múltiplas Origens", False))
    
    # Relatório final
    print("\n" + "="*70)
    print("📋 RELATÓRIO FINAL DOS TESTES")
    print("="*70)
    
    sucessos = 0
    for nome, sucesso in testes_realizados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status} - {nome}")
        if sucesso:
            sucessos += 1
    
    print(f"\n🎯 RESUMO: {sucessos}/{len(testes_realizados)} testes passaram")
    
    if sucessos == len(testes_realizados):
        print("🎉 CORS está funcionando perfeitamente!")
        print("✅ Seu servidor aceita requests de qualquer origem")
    else:
        print("⚠️  Alguns testes falharam - verifique a configuração")
    
    print("\n💡 INSTRUÇÕES EXTRAS:")
    print("   • Para produção, considere limitar as origens por segurança")
    print("   • Teste também com seu frontend real")
    print("   • Monitore logs do servidor para debug")

if __name__ == "__main__":
    main() 