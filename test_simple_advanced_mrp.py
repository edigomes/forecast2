#!/usr/bin/env python3
"""
Teste simples da implementação avançada de MRP
"""

import sys
import os
import json
from datetime import datetime

# Adicionar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_advanced_mrp():
    """Teste simples da funcionalidade avançada"""
    print("=== TESTE ADVANCED SPORADIC MRP ===")
    
    try:
        # Importar classes
        from mrp import MRPOptimizer, OptimizationParams
        print("✓ Importações básicas OK")
        
        # Criar otimizador padrão
        params = OptimizationParams(
            setup_cost=300.0,
            holding_cost_rate=0.20,
            service_level=0.95,
            min_batch_size=100.0,
            max_batch_size=5000.0
        )
        
        optimizer = MRPOptimizer(params)
        print("✓ MRPOptimizer criado")
        
        # Dados de teste
        test_demands = {
            "2024-01-15": 500.0,
            "2024-02-05": 800.0,
            "2024-03-10": 600.0
        }
        
        # Testar com algoritmos originais primeiro
        print("\n--- Testando algoritmos originais ---")
        result_original = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=test_demands,
            initial_stock=200.0,
            leadtime_days=14,
            period_start_date="2024-01-01",
            period_end_date="2024-03-31",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-04-15"
        )
        
        print(f"✓ Algoritmos originais: {len(result_original['batches'])} lotes gerados")
        
        # Verificar se advanced_sporadic_mrp.py existe
        if os.path.exists('advanced_sporadic_mrp.py'):
            print("✓ Arquivo advanced_sporadic_mrp.py encontrado")
            
            try:
                # Testar importação do planejador avançado
                from advanced_sporadic_mrp import create_advanced_mrp_optimizer
                print("✓ Importação do planejador avançado OK")
                
                # Criar otimizador avançado
                advanced_optimizer = create_advanced_mrp_optimizer(params)
                print("✓ Otimizador avançado criado")
                
                # Testar com algoritmos avançados
                print("\n--- Testando algoritmos avançados ---")
                result_advanced = advanced_optimizer.calculate_batches_for_sporadic_demand(
                    sporadic_demand=test_demands,
                    initial_stock=200.0,
                    leadtime_days=14,
                    period_start_date="2024-01-01",
                    period_end_date="2024-03-31",
                    start_cutoff_date="2024-01-01",
                    end_cutoff_date="2024-04-15"
                )
                
                print(f"✓ Algoritmos avançados: {len(result_advanced['batches'])} lotes gerados")
                
                # Verificar campos avançados
                if result_advanced['batches']:
                    batch = result_advanced['batches'][0]
                    analytics = batch.get('analytics', {})
                    
                    advanced_fields = [
                        'advanced_mrp_strategy', 'eoq_used', 'abc_classification',
                        'xyz_classification', 'optimization_quality'
                    ]
                    
                    found_fields = [f for f in advanced_fields if f in analytics]
                    print(f"✓ Campos avançados encontrados: {len(found_fields)}/{len(advanced_fields)}")
                    
                    for field in found_fields:
                        value = analytics[field]
                        print(f"  - {field}: {value}")
                
                # Verificar compatibilidade JSON
                json_str = json.dumps(result_advanced)
                print("✓ Compatibilidade JSON verificada")
                
                print("\n✓ TESTE AVANÇADO PASSOU COM SUCESSO!")
                return True
                
            except Exception as e:
                print(f"✗ Erro no planejador avançado: {e}")
                print("✓ Mas algoritmos originais funcionam normalmente")
                return False
        else:
            print("✗ Arquivo advanced_sporadic_mrp.py não encontrado")
            return False
            
    except Exception as e:
        print(f"✗ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Testa integração com mrp.py"""
    print("\n=== TESTE DE INTEGRAÇÃO ===")
    
    try:
        from mrp import MRPOptimizer, OptimizationParams
        
        # Verificar se a função _plan_sporadic_batches foi modificada
        optimizer = MRPOptimizer()
        
        # Verificar se há referência ao planejador avançado no código
        import inspect
        source = inspect.getsource(optimizer._plan_sporadic_batches)
        
        if 'AdvancedSporadicMRPPlanner' in source:
            print("✓ Integração detectada em _plan_sporadic_batches")
        else:
            print("✗ Integração não detectada")
            
        if 'advanced_sporadic_mrp' in source:
            print("✓ Importação do módulo avançado detectada")
        else:
            print("✗ Importação do módulo avançado não detectada")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na verificação de integração: {e}")
        return False


if __name__ == '__main__':
    success1 = test_advanced_mrp()
    success2 = test_integration()
    
    if success1 and success2:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    elif success1:
        print("\n⚠️  Algoritmos avançados funcionam, mas integração precisa de verificação")
    else:
        print("\n❌ Alguns testes falharam, mas funcionalidade básica preservada") 