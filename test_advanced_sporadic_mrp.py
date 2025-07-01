#!/usr/bin/env python3
"""
Teste completo da classe AdvancedSporadicMRPPlanner
Verifica funcionalidade, compatibilidade e qualidade dos resultados.
"""

import sys
import os
import unittest
import json
from datetime import datetime, timedelta
from typing import Dict, List

# Adicionar o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from advanced_sporadic_mrp import (
        AdvancedSporadicMRPPlanner, 
        AdvancedMRPCalculations,
        create_advanced_mrp_optimizer,
        integrate_advanced_mrp_with_existing
    )
    from mrp import MRPOptimizer, OptimizationParams, BatchResult, clean_for_json
    IMPORTS_OK = True
except ImportError as e:
    print(f"Erro de importação: {e}")
    IMPORTS_OK = False


class TestAdvancedSporadicMRPPlanner(unittest.TestCase):
    """Testes para o planejador avançado de MRP esporádico"""
    
    def setUp(self):
        """Configuração inicial para cada teste"""
        if not IMPORTS_OK:
            self.skipTest("Importações falharam")
            
        self.params = OptimizationParams(
            setup_cost=300.0,
            holding_cost_rate=0.20,
            service_level=0.95,
            min_batch_size=100.0,
            max_batch_size=5000.0,
            safety_days=3
        )
        self.planner = AdvancedSporadicMRPPlanner(self.params)
        
        # Demandas de teste
        self.test_demands = {
            "2024-01-15": 500.0,
            "2024-01-22": 300.0,
            "2024-02-05": 800.0,
            "2024-02-18": 400.0,
            "2024-03-10": 600.0
        }
        
        # Parâmetros de teste
        self.initial_stock = 200.0
        self.leadtime_days = 14
        self.start_period = datetime(2024, 1, 1)
        self.end_period = datetime(2024, 3, 31)
        self.start_cutoff = datetime(2024, 1, 1)
        self.end_cutoff = datetime(2024, 4, 15)
        self.safety_days = 3
        self.safety_margin_percent = 10.0
        self.absolute_minimum_stock = 50.0
        self.max_gap_days = 30
    
    def test_demand_analysis_basic(self):
        """Testa análise básica de padrões de demanda"""
        analysis = self.planner._analyze_demand_patterns_advanced(
            self.test_demands, self.leadtime_days
        )
        
        # Verificar campos obrigatórios
        required_fields = [
            'total_demand', 'mean_demand', 'std_demand', 'cv',
            'abc_class', 'xyz_class', 'variability_level',
            'intervals', 'seasonality', 'trend', 'regularity_score'
        ]
        
        for field in required_fields:
            self.assertIn(field, analysis, f"Campo '{field}' não encontrado na análise")
        
        # Verificar valores sensatos
        self.assertGreater(analysis['total_demand'], 0, "Demanda total deve ser positiva")
        self.assertGreater(analysis['mean_demand'], 0, "Demanda média deve ser positiva")
        self.assertIn(analysis['abc_class'], ['A', 'B', 'C'], "Classificação ABC inválida")
        self.assertIn(analysis['xyz_class'], ['X', 'Y', 'Z'], "Classificação XYZ inválida")
        
        print(f"✓ Análise de demanda: {analysis['abc_class']}{analysis['xyz_class']} - {analysis['variability_level']} variabilidade")
    
    def test_mrp_calculations_advanced(self):
        """Testa cálculos avançados de MRP"""
        demand_analysis = self.planner._analyze_demand_patterns_advanced(
            self.test_demands, self.leadtime_days
        )
        
        mrp_calcs = self.planner._calculate_advanced_mrp_parameters(
            demand_analysis, self.leadtime_days, 100.0
        )
        
        # Verificar tipos e valores
        self.assertIsInstance(mrp_calcs, AdvancedMRPCalculations)
        self.assertGreater(mrp_calcs.eoq, 0, "EOQ deve ser positivo")
        self.assertGreater(mrp_calcs.safety_stock, 0, "Safety stock deve ser positivo")
        self.assertGreater(mrp_calcs.reorder_point, 0, "Reorder point deve ser positivo")
        
        # Verificar limites
        self.assertGreaterEqual(mrp_calcs.eoq, self.params.min_batch_size, "EOQ abaixo do mínimo")
        self.assertLessEqual(mrp_calcs.eoq, self.params.max_batch_size, "EOQ acima do máximo")
        
        print(f"✓ Cálculos MRP: EOQ={mrp_calcs.eoq:.1f}, Safety={mrp_calcs.safety_stock:.1f}, ROP={mrp_calcs.reorder_point:.1f}")
    
    def test_eoq_strategy(self):
        """Testa estratégia baseada em EOQ"""
        batches = self.planner.plan_sporadic_batches_advanced(
            self.test_demands, self.initial_stock, self.leadtime_days,
            self.start_period, self.end_period, self.start_cutoff, self.end_cutoff,
            self.safety_days, self.safety_margin_percent, self.absolute_minimum_stock,
            self.max_gap_days
        )
        
        # Verificar que lotes foram criados
        self.assertGreater(len(batches), 0, "Nenhum lote foi criado")
        
        # Verificar estrutura dos lotes
        for batch in batches:
            self.assertIsInstance(batch, BatchResult)
            self.assertIsInstance(batch.analytics, dict)
            
            # Verificar campos obrigatórios
            required_analytics = [
                'stock_before_arrival', 'stock_after_arrival', 'target_demand_date',
                'advanced_mrp_strategy', 'eoq_used', 'safety_stock_calculated'
            ]
            
            for field in required_analytics:
                self.assertIn(field, batch.analytics, f"Campo '{field}' ausente nos analytics")
        
        print(f"✓ Estratégia EOQ gerou {len(batches)} lotes")
        
        # Verificar compatibilidade JSON
        result_dict = {'batches': [self._batch_to_dict(b) for b in batches]}
        json_result = json.dumps(clean_for_json(result_dict))
        self.assertIsInstance(json_result, str)
        print("✓ Compatibilidade JSON verificada")
    
    def test_high_variability_strategy(self):
        """Testa estratégia para alta variabilidade"""
        # Criar demandas com alta variabilidade
        high_var_demands = {
            "2024-01-15": 100.0,
            "2024-01-22": 2000.0,  # Pico alto
            "2024-02-05": 150.0,
            "2024-02-18": 1800.0,  # Outro pico
            "2024-03-10": 200.0
        }
        
        batches = self.planner.plan_sporadic_batches_advanced(
            high_var_demands, self.initial_stock, self.leadtime_days,
            self.start_period, self.end_period, self.start_cutoff, self.end_cutoff,
            self.safety_days, self.safety_margin_percent, self.absolute_minimum_stock,
            self.max_gap_days
        )
        
        self.assertGreater(len(batches), 0, "Nenhum lote criado para alta variabilidade")
        
        # Verificar se estratégia de buffer dinâmico foi usada
        for batch in batches:
            if batch.analytics.get('advanced_mrp_strategy') == 'dynamic_buffer':
                self.assertIn('strategy_dynamic_buffer', batch.analytics)
                print("✓ Estratégia de buffer dinâmico aplicada")
                break
        
        print(f"✓ Alta variabilidade: {len(batches)} lotes gerados")
    
    def test_long_leadtime_strategy(self):
        """Testa estratégia para lead time longo"""
        long_leadtime = 60  # 60 dias
        
        batches = self.planner.plan_sporadic_batches_advanced(
            self.test_demands, self.initial_stock, long_leadtime,
            self.start_period, self.end_period, self.start_cutoff, self.end_cutoff,
            self.safety_days, self.safety_margin_percent, self.absolute_minimum_stock,
            self.max_gap_days
        )
        
        self.assertGreater(len(batches), 0, "Nenhum lote criado para lead time longo")
        
        # Verificar estratégia de previsão
        forecasting_used = any(
            batch.analytics.get('advanced_mrp_strategy') == 'long_leadtime_forecasting'
            for batch in batches
        )
        
        if forecasting_used:
            print("✓ Estratégia de previsão para lead time longo aplicada")
        
        print(f"✓ Lead time longo: {len(batches)} lotes gerados")
    
    def test_integration_with_existing_mrp(self):
        """Testa integração com MRPOptimizer existente"""
        # Criar otimizador padrão
        standard_optimizer = MRPOptimizer(self.params)
        
        # Integrar capacidades avançadas
        advanced_optimizer = integrate_advanced_mrp_with_existing(standard_optimizer)
        
        # Testar função calculate_batches_for_sporadic_demand
        result = advanced_optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=self.test_demands,
            initial_stock=self.initial_stock,
            leadtime_days=self.leadtime_days,
            period_start_date="2024-01-01",
            period_end_date="2024-03-31",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-04-15",
            safety_margin_percent=10.0,
            safety_days=3
        )
        
        # Verificar estrutura do resultado
        self.assertIn('batches', result)
        self.assertIn('analytics', result)
        self.assertIsInstance(result['batches'], list)
        
        # Verificar analytics avançados nos lotes
        if result['batches']:
            first_batch = result['batches'][0]
            advanced_fields = [
                'advanced_mrp_strategy', 'eoq_used', 'abc_classification', 
                'xyz_classification', 'optimization_quality'
            ]
            
            for field in advanced_fields:
                if field in first_batch['analytics']:
                    print(f"✓ Campo avançado '{field}' presente")
        
        print("✓ Integração com MRPOptimizer existente funcionando")
    
    def test_convenience_function(self):
        """Testa função de conveniência"""
        # Criar otimizador avançado diretamente
        advanced_optimizer = create_advanced_mrp_optimizer(self.params)
        
        # Verificar que é uma instância válida
        self.assertIsInstance(advanced_optimizer, MRPOptimizer)
        
        # Testar funcionalidade
        result = advanced_optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand={"2024-01-15": 500.0, "2024-02-15": 600.0},
            initial_stock=100.0,
            leadtime_days=7,
            period_start_date="2024-01-01",
            period_end_date="2024-02-28",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-03-15"
        )
        
        self.assertIn('batches', result)
        print("✓ Função de conveniência funcionando")
    
    def test_compatibility_with_existing_analytics(self):
        """Testa compatibilidade total com analytics existentes"""
        # Usar otimizador avançado
        advanced_optimizer = create_advanced_mrp_optimizer(self.params)
        
        result = advanced_optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=self.test_demands,
            initial_stock=self.initial_stock,
            leadtime_days=self.leadtime_days,
            period_start_date="2024-01-01",
            period_end_date="2024-03-31",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-04-15"
        )
        
        # Verificar campos obrigatórios existentes
        required_batch_fields = [
            'order_date', 'arrival_date', 'quantity', 'analytics'
        ]
        
        required_analytics_fields = [
            'stock_before_arrival', 'stock_after_arrival', 'target_demand_date',
            'target_demand_quantity', 'urgency_level', 'efficiency_ratio',
            'is_critical', 'safety_margin_days'
        ]
        
        if result['batches']:
            batch = result['batches'][0]
            
            # Verificar campos do lote
            for field in required_batch_fields:
                self.assertIn(field, batch, f"Campo obrigatório '{field}' ausente")
            
            # Verificar campos dos analytics
            for field in required_analytics_fields:
                self.assertIn(field, batch['analytics'], f"Analytics obrigatório '{field}' ausente")
            
            print("✓ Compatibilidade total com campos existentes verificada")
        
        # Verificar analytics do resultado
        required_result_analytics = [
            'summary', 'stock_evolution', 'demand_analysis', 'sporadic_demand_metrics'
        ]
        
        for field in required_result_analytics:
            self.assertIn(field, result['analytics'], f"Analytics resultado '{field}' ausente")
        
        print("✓ Compatibilidade com estrutura de analytics do resultado verificada")
    
    def test_performance_comparison(self):
        """Testa comparação de performance entre métodos"""
        import time
        
        # Criar demandas maiores para teste de performance
        large_demands = {}
        base_date = datetime(2024, 1, 1)
        for i in range(50):  # 50 demandas
            date_str = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d')
            large_demands[date_str] = 200 + (i % 10) * 100
        
        # Testar método original
        standard_optimizer = MRPOptimizer(self.params)
        
        start_time = time.time()
        result_standard = standard_optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=large_demands,
            initial_stock=500.0,
            leadtime_days=14,
            period_start_date="2024-01-01",
            period_end_date="2024-06-30",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-07-15"
        )
        time_standard = time.time() - start_time
        
        # Testar método avançado
        advanced_optimizer = create_advanced_mrp_optimizer(self.params)
        
        start_time = time.time()
        result_advanced = advanced_optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=large_demands,
            initial_stock=500.0,
            leadtime_days=14,
            period_start_date="2024-01-01",
            period_end_date="2024-06-30",
            start_cutoff_date="2024-01-01",
            end_cutoff_date="2024-07-15"
        )
        time_advanced = time.time() - start_time
        
        print(f"✓ Performance - Padrão: {time_standard:.3f}s, Avançado: {time_advanced:.3f}s")
        print(f"✓ Lotes - Padrão: {len(result_standard['batches'])}, Avançado: {len(result_advanced['batches'])}")
        
        # Verificar que ambos geram resultados válidos
        self.assertGreater(len(result_standard['batches']), 0)
        self.assertGreater(len(result_advanced['batches']), 0)
    
    def _batch_to_dict(self, batch: BatchResult) -> Dict:
        """Converte BatchResult para dicionário"""
        return {
            'order_date': batch.order_date,
            'arrival_date': batch.arrival_date,
            'quantity': batch.quantity,
            'analytics': batch.analytics
        }


class TestSupplyChainPyIntegration(unittest.TestCase):
    """Testes específicos para integração com supplychainpy"""
    
    def test_supplychainpy_availability(self):
        """Testa se supplychainpy está disponível ou funciona sem ela"""
        from advanced_sporadic_mrp import SUPPLYCHAINPY_AVAILABLE
        
        if SUPPLYCHAINPY_AVAILABLE:
            print("✓ supplychainpy disponível - usando cálculos da biblioteca")
        else:
            print("✓ supplychainpy não disponível - usando cálculos manuais")
        
        # Testar EOQ independente da disponibilidade
        planner = AdvancedSporadicMRPPlanner()
        
        eoq_manual = planner._calculate_eoq_manual(1000, 100, 20)
        eoq_lib = planner._calculate_eoq_supplychainpy(1000, 100, 20)
        
        # Ambos devem dar resultados similares
        self.assertGreater(eoq_manual, 0)
        self.assertGreater(eoq_lib, 0)
        
        # Diferença deve ser pequena (menos de 10%)
        diff_percent = abs(eoq_manual - eoq_lib) / max(eoq_manual, eoq_lib)
        self.assertLess(diff_percent, 0.1, "EOQ manual e biblioteca muito diferentes")
        
        print(f"✓ EOQ - Manual: {eoq_manual:.1f}, Biblioteca: {eoq_lib:.1f}")


def run_comprehensive_test():
    """Executa teste abrangente com diferentes cenários"""
    print("=" * 60)
    print("TESTE ABRANGENTE - ADVANCED SPORADIC MRP PLANNER")
    print("=" * 60)
    
    # Cenários de teste
    scenarios = [
        {
            'name': 'Demanda Regular Baixa Variabilidade',
            'demands': {
                "2024-01-07": 300, "2024-01-14": 310, "2024-01-21": 295,
                "2024-01-28": 305, "2024-02-04": 290, "2024-02-11": 315
            },
            'leadtime': 7,
            'initial_stock': 150
        },
        {
            'name': 'Demanda Irregular Alta Variabilidade',
            'demands': {
                "2024-01-05": 100, "2024-01-25": 2000, "2024-02-15": 150,
                "2024-03-01": 1800, "2024-03-20": 200
            },
            'leadtime': 14,
            'initial_stock': 300
        },
        {
            'name': 'Lead Time Muito Longo',
            'demands': {
                "2024-02-01": 500, "2024-03-01": 600, "2024-04-01": 550,
                "2024-05-01": 580, "2024-06-01": 520
            },
            'leadtime': 60,
            'initial_stock': 100
        },
        {
            'name': 'Muitas Demandas Pequenas',
            'demands': {f"2024-01-{i:02d}": 50 + (i % 3) * 10 for i in range(1, 29, 2)},
            'leadtime': 10,
            'initial_stock': 200
        }
    ]
    
    optimizer = create_advanced_mrp_optimizer()
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        try:
            result = optimizer.calculate_batches_for_sporadic_demand(
                sporadic_demand=scenario['demands'],
                initial_stock=scenario['initial_stock'],
                leadtime_days=scenario['leadtime'],
                period_start_date="2024-01-01",
                period_end_date="2024-06-30",
                start_cutoff_date="2024-01-01",
                end_cutoff_date="2024-07-15"
            )
            
            batches = result['batches']
            analytics = result['analytics']
            
            print(f"✓ Lotes gerados: {len(batches)}")
            print(f"✓ Demanda total: {analytics['demand_analysis']['total_demand']:.0f}")
            print(f"✓ Produção total: {analytics['summary']['total_produced']:.0f}")
            print(f"✓ Taxa de atendimento: {analytics['summary']['demand_fulfillment_rate']:.1f}%")
            
            if batches:
                first_batch = batches[0]
                strategy = first_batch['analytics'].get('advanced_mrp_strategy', 'unknown')
                quality = first_batch['analytics'].get('optimization_quality', 'unknown')
                print(f"✓ Estratégia principal: {strategy}")
                print(f"✓ Qualidade otimização: {quality}")
                
                # Verificar campos avançados
                advanced_fields = [
                    'eoq_used', 'safety_stock_calculated', 'abc_classification', 
                    'xyz_classification', 'demand_variability_cv'
                ]
                present_fields = [f for f in advanced_fields if f in first_batch['analytics']]
                print(f"✓ Campos avançados: {len(present_fields)}/{len(advanced_fields)}")
            
        except Exception as e:
            print(f"✗ Erro no cenário: {e}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == '__main__':
    # Teste simples primeiro
    success = run_simple_test()
    
    if success and IMPORTS_OK:
        print("\n=== TESTES UNITÁRIOS ===")
        unittest.main(verbosity=2)
    else:
        print("Teste simplificado falhou - pulando testes unitários")
    
    print("\n" + "=" * 60)
    
    # Executar teste abrangente
    run_comprehensive_test() 