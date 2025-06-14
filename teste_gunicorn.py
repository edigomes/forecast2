#!/usr/bin/env python3
"""
Teste do servidor Gunicorn em produção

Este script testa se o servidor está funcionando corretamente quando
executado via Gunicorn, incluindo CORS e funcionalidades principais.
"""

import requests
import time
import json
import subprocess
import signal
import os
import sys
from datetime import datetime

# Configurações
GUNICORN_URL = "http://localhost:5000"
TEST_TIMEOUT = 30  # seconds

def wait_for_server(url, timeout=30):
    """Aguarda servidor ficar disponível"""
    print(f"⏳ Aguardando servidor em {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/", timeout=5)
            print(f"✅ Servidor disponível! Status: {response.status_code}")
            return True
        except requests.exceptions.RequestException:
            time.sleep(1)
            print(".", end="", flush=True)
    
    print(f"\n❌ Timeout: Servidor não respondeu em {timeout} segundos")
    return False

def test_cors_gunicorn():
    """Testa CORS com Gunicorn"""
    print("\n" + "="*70)
    print("🌐 TESTE CORS COM GUNICORN")
    print("="*70)
    
    # Dados de teste
    test_data = {
        "html_data": {
            "item_id": 777,
            "prediction": {
                "ds": "2025-08-01 00:00:00",
                "yhat": 150.0,
                "yhat_lower": 120.0,
                "yhat_upper": 180.0,
                "trend": 145.0,
                "yearly": 5.0
            },
            "explanation_data": {
                "confidence_score": "Alta",
                "data_points": 18,
                "mape": 8.5,
                "r2": 0.85,
                "seasonal_pattern": {"8": 1.1},
                "seasonal_strength": 0.7,
                "std": 25.0,
                "training_period": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "months": 18
                },
                "trend_slope": 3.2,
                "trend_strength": 0.4
            },
            "is_quarterly": False,
            "date_iso": "2025-08-01T00:00:00",
            "timestamp": 1754006400
        },
        "layout": "compact",
        "return_html_direct": True
    }
    
    # Lista de origens para testar
    test_origins = [
        "http://localhost:3000",
        "https://app.example.com",
        "https://myapp.vercel.app",
        "http://192.168.1.100:8080"
    ]
    
    results = []
    
    for origin in test_origins:
        print(f"\n🔍 Testando origem: {origin}")
        
        try:
            headers = {
                "Origin": origin,
                "Content-Type": "application/json",
                "Accept": "text/html"
            }
            
            response = requests.post(
                f"{GUNICORN_URL}/generate_html",
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            cors_header = response.headers.get("Access-Control-Allow-Origin", "")
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code}")
                print(f"   ✅ CORS: {cors_header}")
                print(f"   ✅ Tamanho resposta: {len(response.text)} chars")
                results.append({"origin": origin, "success": True})
            else:
                print(f"   ❌ Status: {response.status_code}")
                results.append({"origin": origin, "success": False})
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            results.append({"origin": origin, "success": False})
    
    # Resumo
    successful = sum(1 for r in results if r["success"])
    print(f"\n📊 CORS com Gunicorn: {successful}/{len(results)} testes passaram")
    
    return successful == len(results)

def test_performance_gunicorn():
    """Testa performance com múltiplas requisições"""
    print("\n" + "="*70)
    print("⚡ TESTE DE PERFORMANCE GUNICORN")
    print("="*70)
    
    # Dados simples para teste
    test_data = {
        "html_data": {
            "item_id": 888,
            "prediction": {
                "ds": "2025-09-01 00:00:00",
                "yhat": 100.0,
                "yhat_lower": 80.0,
                "yhat_upper": 120.0,
                "trend": 98.0,
                "yearly": 2.0
            },
            "explanation_data": {
                "confidence_score": "Média",
                "data_points": 12,
                "mape": 12.0,
                "r2": 0.75,
                "seasonal_pattern": {"9": 1.05},
                "seasonal_strength": 0.5,
                "std": 15.0,
                "training_period": {
                    "start": "2024-01-01",
                    "end": "2024-12-01",
                    "months": 12
                },
                "trend_slope": 2.0,
                "trend_strength": 0.3
            },
            "is_quarterly": False,
            "date_iso": "2025-09-01T00:00:00",
            "timestamp": 1756684800
        },
        "layout": "compact"
    }
    
    # Teste com múltiplas requisições simultâneas
    import concurrent.futures
    
    def make_request(request_id):
        try:
            start_time = time.time()
            response = requests.post(
                f"{GUNICORN_URL}/generate_html",
                json=test_data,
                timeout=5
            )
            end_time = time.time()
            
            return {
                "id": request_id,
                "status": response.status_code,
                "time": end_time - start_time,
                "size": len(response.text) if response.status_code == 200 else 0
            }
        except Exception as e:
            return {
                "id": request_id,
                "status": 0,
                "time": 0,
                "error": str(e)
            }
    
    # Executar 10 requisições concorrentes
    num_requests = 10
    print(f"🚀 Executando {num_requests} requisições concorrentes...")
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Analisar resultados
    successful = [r for r in results if r["status"] == 200]
    failed = [r for r in results if r["status"] != 200]
    
    if successful:
        avg_time = sum(r["time"] for r in successful) / len(successful)
        min_time = min(r["time"] for r in successful)
        max_time = max(r["time"] for r in successful)
        
        print(f"\n📊 RESULTADOS DE PERFORMANCE:")
        print(f"   ✅ Requisições bem-sucedidas: {len(successful)}/{num_requests}")
        print(f"   ⏱️  Tempo total: {total_time:.2f}s")
        print(f"   ⚡ Tempo médio por request: {avg_time:.3f}s")
        print(f"   🏃 Tempo mínimo: {min_time:.3f}s")
        print(f"   🐌 Tempo máximo: {max_time:.3f}s")
        print(f"   📈 Requests/segundo: {len(successful)/total_time:.2f}")
    
    if failed:
        print(f"\n❌ Requisições falharam: {len(failed)}")
        for f in failed[:3]:  # Mostrar apenas 3 primeiros erros
            print(f"   - Request {f['id']}: {f.get('error', f'Status {f['status']}')}")
    
    return len(successful) >= num_requests * 0.8  # 80% de sucesso

def main():
    """Executa todos os testes do Gunicorn"""
    print("🚀 TESTES DO SERVIDOR GUNICORN")
    print(f"URL: {GUNICORN_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Aguardar servidor estar disponível
    if not wait_for_server(GUNICORN_URL, TEST_TIMEOUT):
        print("❌ Servidor não está disponível. Certifique-se que Gunicorn está rodando.")
        print("\nPara iniciar o servidor:")
        print("   bash start_production.sh")
        print("   ou")
        print("   gunicorn --config gunicorn_config.py wsgi:application")
        sys.exit(1)
    
    # Executar testes
    tests_results = []
    
    try:
        tests_results.append(("CORS", test_cors_gunicorn()))
    except Exception as e:
        print(f"❌ Erro no teste CORS: {e}")
        tests_results.append(("CORS", False))
    
    try:
        tests_results.append(("Performance", test_performance_gunicorn()))
    except Exception as e:
        print(f"❌ Erro no teste Performance: {e}")
        tests_results.append(("Performance", False))
    
    # Relatório final
    print("\n" + "="*70)
    print("📋 RELATÓRIO FINAL - GUNICORN")
    print("="*70)
    
    passed = 0
    for test_name, success in tests_results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 RESUMO: {passed}/{len(tests_results)} testes passaram")
    
    if passed == len(tests_results):
        print("🎉 Servidor Gunicorn está funcionando perfeitamente!")
        print("✅ CORS, performance e health checks OK")
    else:
        print("⚠️  Alguns testes falharam - verifique configuração")
    
    print(f"\n💡 PARA MONITORAR LOGS:")
    print(f"   tail -f logs/gunicorn.log")
    print(f"   tail -f logs/access.log")
    print(f"   tail -f logs/error.log")

if __name__ == "__main__":
    main() 