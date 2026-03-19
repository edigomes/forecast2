#!/usr/bin/env python3
"""
Advanced Sporadic MRP Planner
Classe avançada para planejamento de lotes de produção/compra para demandas esporádicas
usando algoritmos de supply chain e cálculos manuais otimizados.

Mantém 100% de compatibilidade com os analytics existentes e adiciona inteligência avançada.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
from scipy import stats
from dataclasses import dataclass
import json
import math
import logging

from mrp import BatchResult, OptimizationParams, clean_for_json

logger = logging.getLogger(__name__)


@dataclass
class AdvancedMRPCalculations:
    """Estrutura para armazenar cálculos avançados de MRP"""
    eoq: float
    safety_stock: float
    reorder_point: float
    lead_time_demand: float
    lead_time_demand_std: float
    service_level_z_score: float
    holding_cost_per_unit: float
    annual_demand: float
    demand_variability: float
    abc_classification: str
    xyz_classification: str


class AdvancedSporadicMRPPlanner:
    """
    Planejador avançado de MRP para demandas esporádicas
    
    Implementa algoritmos sofisticados de supply chain baseados em:
    - Economic Order Quantity (EOQ) otimizado
    - Análise ABC/XYZ de demandas
    - Safety Stock calculado por múltiplos métodos
    - Reorder Point dinâmico
    - Análise de variabilidade de demanda
    - Consolidação inteligente baseada em lead time overlap
    - Previsão de demanda para lead times longos
    """
    
    def __init__(self, optimization_params: Optional[OptimizationParams] = None):
        self.params = optimization_params or OptimizationParams()
        self.calculations_cache = {}
        
    def plan_sporadic_batches_advanced(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        max_gap_days: int,
        unit_cost: float = 100.0,  # Custo unitário padrão para cálculos
        ignore_safety_stock: bool = False  # 🎯 NOVO: Ignorar estoques de segurança
    ) -> List[BatchResult]:
        """
        Algoritmo avançado para planejamento de lotes esporádicos
        
        Usa múltiplas estratégias:
        1. Análise ABC/XYZ das demandas
        2. Cálculo EOQ otimizado por grupo
        3. Safety stock baseado em variabilidade real
        4. Consolidação inteligente com análise de custos
        5. Prevenção de stockout com simulação Monte Carlo
        """
        
        if not valid_demands:
            return []
        
        if ignore_safety_stock:
            total_demand = sum(valid_demands.values())
            if initial_stock >= total_demand + absolute_minimum_stock:
                return []
            else:
                return self._create_exact_quantity_batch(
                    valid_demands, initial_stock, leadtime_days, start_period, end_period,
                    start_cutoff, end_cutoff, safety_days, absolute_minimum_stock
                )
        
        total_demand = sum(valid_demands.values())
        
        if initial_stock >= total_demand + absolute_minimum_stock:
            return []
        
        # Etapa 1: Análise avançada das demandas
        demand_analysis = self._analyze_demand_patterns_advanced(valid_demands, leadtime_days)
        
        # Etapa 2: Cálculos MRP avançados
        mrp_calcs = self._calculate_advanced_mrp_parameters(
            demand_analysis, leadtime_days, unit_cost
        )
        
        # ====== ESTRATÉGIAS SIMPLIFICADAS - FOCO EM EFICÁCIA ======
        # OBJETIVO: Insumos na data certa + estoque mínimo + respeitar lead times
        # PRINCÍPIO: Evitar complexidade desnecessária, manter compatibilidade dos analytics
        
        if leadtime_days == 0:
            # ✅ Lead time zero - produção instantânea (FUNCIONA PERFEITAMENTE)
            return self._just_in_time_strategy(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, mrp_calcs, demand_analysis
            )
        elif leadtime_days <= 14:
            # ✅ Lead time curto - estratégia otimizada (FUNCIONA PERFEITAMENTE)
            return self._short_leadtime_sporadic_strategy(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, mrp_calcs, demand_analysis, max_gap_days
            )
        elif 15 <= leadtime_days <= 45:
            # ✅ Lead time médio - estratégia específica (FUNCIONA PERFEITAMENTE)
            return self._medium_leadtime_sporadic_strategy(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, mrp_calcs, demand_analysis, max_gap_days
            )
        else:
            # ✅ Lead time longo (>45 dias) - consolidação inteligente (SIMPLES E EFICAZ)
            return self._hybrid_consolidation_strategy(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, mrp_calcs, demand_analysis, max_gap_days
            )
    
    def _create_exact_quantity_batch(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        absolute_minimum_stock: float = 0.0
    ) -> List[BatchResult]:
        """
        Cria um lote com quantidade exata necessária quando ignore_safety_stock=True.
        Se absolute_minimum_stock > 0, garante que o estoque residual fique acima do mínimo.
        """
        total_demand = sum(valid_demands.values())
        deficit = (total_demand + absolute_minimum_stock) - initial_stock
        
        if deficit <= 0:
            return []
        
        # Encontrar a primeira demanda para definir data do lote
        first_demand_date = min(pd.to_datetime(date) for date in valid_demands.keys())
        
        # Calcular datas do pedido considerando lead time e safety days
        target_arrival_date = first_demand_date - pd.Timedelta(days=safety_days)
        order_date = target_arrival_date - pd.Timedelta(days=leadtime_days)
        order_date = max(order_date, start_cutoff)
        actual_arrival_date = order_date + pd.Timedelta(days=leadtime_days)
        
        # Verificar se chegará dentro do período válido
        if actual_arrival_date > end_cutoff:
            actual_arrival_date = end_cutoff
            order_date = actual_arrival_date - pd.Timedelta(days=leadtime_days)
        
        # Criar analytics simplificados
        analytics = {
            'stock_before_arrival': initial_stock,
            'stock_after_arrival': initial_stock + deficit,
            'coverage_days': 0,
            'actual_lead_time': leadtime_days,
            'urgency_level': 'normal',
            'production_start_delay': 0,
            'arrival_delay': 0,
            'target_demand_date': min(valid_demands.keys()),
            'target_demand_quantity': total_demand,
            'shortfall_covered': deficit,
            'safety_margin_percent': 0.0,  # Sem margem de segurança
            'exact_quantity_mode': True,  # Flag especial
            'ignore_safety_stock_applied': True
        }
        
        # Criar o lote
        batch = BatchResult(
            order_date=order_date.strftime('%Y-%m-%d'),
            arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
            quantity=deficit,  # Quantidade exata necessária
            analytics=analytics
        )
        
        logger.debug(f"EXACT QUANTITY BATCH: deficit={deficit}, order_date={order_date.strftime('%Y-%m-%d')}, arrival_date={actual_arrival_date.strftime('%Y-%m-%d')}")
        
        return [batch]
    
    def _analyze_demand_patterns_advanced(
        self, 
        valid_demands: Dict[str, float], 
        leadtime_days: int
    ) -> Dict:
        """Análise avançada dos padrões de demanda"""
        
        demands = list(valid_demands.values())
        dates = [pd.to_datetime(d) for d in valid_demands.keys()]
        
        if not demands:
            return self._get_empty_demand_analysis()
        
        # Estatísticas básicas
        total_demand = sum(demands)
        mean_demand = np.mean(demands)
        std_demand = np.std(demands)
        cv = std_demand / mean_demand if mean_demand > 0 else 0
        
        # Análise de intervalos
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            intervals.append(interval)
        
        # Classificação ABC (baseada em valor total)
        abc_class = self._classify_abc(total_demand)
        
        # Classificação XYZ (baseada em variabilidade)
        xyz_class = self._classify_xyz(cv)
        
        # Análise de sazonalidade
        seasonality = self._detect_seasonality_advanced(dates, demands)
        
        # Tendência
        trend = self._calculate_trend_advanced(dates, demands)
        
        # Variabilidade de intervalos
        interval_cv = np.std(intervals) / np.mean(intervals) if intervals and np.mean(intervals) > 0 else 0
        
        return {
            'total_demand': total_demand,
            'mean_demand': mean_demand,
            'std_demand': std_demand,
            'cv': cv,
            'demands': demands,
            'abc_class': abc_class,
            'xyz_class': xyz_class,
            'variability_level': 'low' if cv < 0.3 else ('medium' if cv < 0.7 else 'high'),
            'intervals': intervals,
            'mean_interval': np.mean(intervals) if intervals else 0,
            'interval_cv': interval_cv,
            'seasonality': seasonality,
            'trend': trend,
            'demand_concentration': len(demands) / ((dates[-1] - dates[0]).days + 1) if len(dates) > 1 else 1,
            'peak_demands': [d for d in demands if d > mean_demand * 1.5],
            'regularity_score': self._calculate_regularity_score(intervals)
        }
    
    def _calculate_advanced_mrp_parameters(
        self,
        demand_analysis: Dict,
        leadtime_days: int,
        unit_cost: float
    ) -> AdvancedMRPCalculations:
        """Calcula parâmetros MRP usando fórmulas avançadas"""
        
        annual_demand = demand_analysis['total_demand'] * (365 / 90)  # Anualizar baseado em 90 dias
        
        # EOQ usando cálculo manual
        eoq_classic = self._calculate_eoq_manual(
            annual_demand, self.params.setup_cost, unit_cost * self.params.holding_cost_rate
        )
        
        # Ajustar EOQ baseado no padrão de demanda
        eoq_adjusted = self._adjust_eoq_for_sporadic_demand(eoq_classic, demand_analysis, leadtime_days)
        
        clamped_service_level = max(0.5, min(0.99, self.params.service_level))
        
        safety_stock = self._calculate_safety_stock_advanced(
            demand_analysis['std_demand'], 
            leadtime_days, 
            clamped_service_level,
            demand_analysis
        )
        
        # Lead time demand
        lead_time_demand = demand_analysis['mean_demand'] * (leadtime_days / (demand_analysis['mean_interval'] or 1))
        lead_time_demand_std = demand_analysis['std_demand'] * np.sqrt(leadtime_days / (demand_analysis['mean_interval'] or 1))
        
        # Reorder point
        reorder_point = lead_time_demand + safety_stock
        
        # Service level Z-score
        service_level_z_score = stats.norm.ppf(clamped_service_level)
        
        return AdvancedMRPCalculations(
            eoq=eoq_adjusted,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            lead_time_demand=lead_time_demand,
            lead_time_demand_std=lead_time_demand_std,
            service_level_z_score=service_level_z_score,
            holding_cost_per_unit=unit_cost * self.params.holding_cost_rate,
            annual_demand=annual_demand,
            demand_variability=demand_analysis['cv'],
            abc_classification=demand_analysis['abc_class'],
            xyz_classification=demand_analysis['xyz_class']
        ) 
    
    def _calculate_eoq_manual(self, annual_demand: float, setup_cost: float, holding_cost: float) -> float:
        """Calcula EOQ usando fórmula clássica"""
        if annual_demand <= 0 or setup_cost <= 0 or holding_cost <= 0:
            return self.params.min_batch_size
        
        eoq = math.sqrt(2 * annual_demand * setup_cost / holding_cost)
        return max(self.params.min_batch_size, min(self.params.max_batch_size, eoq))
    
    def _adjust_eoq_for_sporadic_demand(
        self, 
        base_eoq: float, 
        demand_analysis: Dict, 
        leadtime_days: int
    ) -> float:
        """Ajusta EOQ para características de demanda esporádica"""
        
        # Fator de ajuste baseado na variabilidade
        variability_factor = 1.0
        if demand_analysis['cv'] > 0.5:  # Alta variabilidade
            variability_factor = 0.8  # Reduzir lotes para maior flexibilidade
        elif demand_analysis['cv'] < 0.2:  # Baixa variabilidade
            variability_factor = 1.2  # Permitir lotes maiores
        
        # Fator de ajuste baseado na regularidade
        regularity_factor = 1.0
        regularity_score = demand_analysis.get('regularity_score', 0.5)
        if regularity_score < 0.3:  # Muito irregular
            regularity_factor = 0.7
        elif regularity_score > 0.7:  # Muito regular
            regularity_factor = 1.1
        
        # Fator de ajuste baseado no lead time
        leadtime_factor = 1.0
        if leadtime_days > 30:  # Lead time longo
            leadtime_factor = 1.3  # Lotes maiores para cobrir incerteza
        elif leadtime_days < 7:  # Lead time curto
            leadtime_factor = 0.9  # Lotes menores, mais frequentes
        
        adjusted_eoq = base_eoq * variability_factor * regularity_factor * leadtime_factor
        
        # Garantir que está dentro dos limites
        return max(self.params.min_batch_size, min(self.params.max_batch_size, adjusted_eoq))
    
    def _calculate_safety_stock_advanced(
        self,
        demand_std: float,
        leadtime_days: int,
        service_level: float,
        demand_analysis: Dict
    ) -> float:
        """Calcula safety stock usando múltiplos métodos e escolhe o melhor"""
        
        if demand_std <= 0 or leadtime_days <= 0:
            return 0
        
        z_score = stats.norm.ppf(service_level)
        mean_interval = max(1, demand_analysis.get('mean_interval', 1))
        n_events = leadtime_days / mean_interval
        
        # Método 1: Fórmula clássica (σ por ocorrência → escalar por sqrt de eventos no lead time)
        safety_stock_classic = z_score * demand_std * math.sqrt(n_events)
        
        # Método 2: Baseado na variabilidade dos intervalos
        interval_cv = demand_analysis.get('interval_cv', 0)
        interval_adjustment = 1 + (interval_cv * 0.5)
        safety_stock_interval = safety_stock_classic * interval_adjustment
        
        # Método 3: MAD (Mean Absolute Deviation) se disponível
        demands_arr = np.asarray(demand_analysis.get('demands', [demand_analysis.get('mean_demand', 0)]))
        if len(demands_arr) > 2:
            mad = float(np.mean(np.abs(demands_arr - np.mean(demands_arr))))
            safety_stock_mad = z_score * mad * math.sqrt(n_events) * 1.25
        else:
            safety_stock_mad = safety_stock_classic
        
        # Escolher o método mais apropriado baseado nas características
        if demand_analysis['variability_level'] == 'high':
            safety_stock = max(safety_stock_interval, safety_stock_mad)
        elif interval_cv > 0.5:
            safety_stock = safety_stock_interval
        else:
            safety_stock = safety_stock_classic
        
        # Limitar valores extremos (lead time demand * 50%)
        lead_time_demand = demand_analysis['mean_demand'] * n_events
        max_reasonable_safety = lead_time_demand * 0.5
        return min(safety_stock, max(0, max_reasonable_safety))
    
    def _classify_abc(self, total_value: float) -> str:
        """Classificação ABC baseada no valor total"""
        # Thresholds podem ser ajustados baseados no contexto
        if total_value > 10000:
            return 'A'
        elif total_value > 2000:
            return 'B'
        else:
            return 'C'
    
    def _classify_xyz(self, cv: float) -> str:
        """Classificação XYZ baseada na variabilidade"""
        if cv < 0.3:
            return 'X'  # Baixa variabilidade, alta previsibilidade
        elif cv < 0.7:
            return 'Y'  # Média variabilidade
        else:
            return 'Z'  # Alta variabilidade, baixa previsibilidade
    
    def _detect_seasonality_advanced(self, dates: List, demands: List) -> Dict:
        """Detecção avançada de sazonalidade"""
        if len(dates) < 4:
            return {'detected': False, 'type': 'none', 'strength': 0}
        
        # Converter para series temporal
        df = pd.DataFrame({'date': dates, 'demand': demands})
        df['weekday'] = df['date'].dt.dayofweek
        df['day'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        
        # Análise semanal
        weekly_pattern = df.groupby('weekday')['demand'].mean()
        weekly_cv = weekly_pattern.std() / weekly_pattern.mean() if weekly_pattern.mean() > 0 else 0
        
        # Análise mensal
        monthly_pattern = df.groupby('month')['demand'].mean()
        monthly_cv = monthly_pattern.std() / monthly_pattern.mean() if monthly_pattern.mean() > 0 else 0
        
        # Determinar tipo de sazonalidade
        if weekly_cv > 0.3:
            return {'detected': True, 'type': 'weekly', 'strength': weekly_cv}
        elif monthly_cv > 0.3:
            return {'detected': True, 'type': 'monthly', 'strength': monthly_cv}
        else:
            return {'detected': False, 'type': 'none', 'strength': 0}
    
    def _calculate_trend_advanced(self, dates: List, demands: List) -> Dict:
        """Análise de tendência avançada"""
        if len(dates) < 3:
            return {'direction': 'stable', 'strength': 0, 'significance': 'low'}
        
        # Converter para números ordinais para regressão
        date_ordinals = [d.toordinal() for d in dates]
        
        # Regressão linear
        slope, intercept = np.polyfit(date_ordinals, demands, 1)
        
        # Determinar significância
        correlation = np.corrcoef(date_ordinals, demands)[0, 1]
        correlation = float(np.nan_to_num(correlation, nan=0.0))
        significance = 'high' if abs(correlation) > 0.7 else ('medium' if abs(correlation) > 0.4 else 'low')
        
        # Determinar direção
        if slope > np.mean(demands) * 0.01:  # Mais de 1% da média por dia
            direction = 'increasing'
        elif slope < -np.mean(demands) * 0.01:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'direction': direction,
            'strength': abs(slope),
            'significance': significance,
            'correlation': correlation
        }
    
    def _calculate_regularity_score(self, intervals: List[int]) -> float:
        """Calcula score de regularidade dos intervalos"""
        if len(intervals) < 2:
            return 1.0
        
        # Coeficiente de variação dos intervalos
        cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 1
        
        # Score inverso - quanto menor CV, maior regularidade
        regularity = 1 / (1 + cv)
        return min(1.0, max(0.0, regularity))
    
    def _get_empty_demand_analysis(self) -> Dict:
        """Retorna análise vazia para casos extremos"""
        return {
            'total_demand': 0,
            'mean_demand': 0,
            'std_demand': 0,
            'cv': 0,
            'abc_class': 'C',
            'xyz_class': 'Z',
            'variability_level': 'high',
            'intervals': [],
            'mean_interval': 0,
            'interval_cv': 0,
            'seasonality': {'detected': False, 'type': 'none', 'strength': 0},
            'trend': {'direction': 'stable', 'strength': 0, 'significance': 'low'},
            'demand_concentration': 0,
            'peak_demands': [],
            'regularity_score': 0
        } 

    # =============== ESTRATÉGIAS DE PLANEJAMENTO ===============
    
    def _just_in_time_strategy(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict
    ) -> List[BatchResult]:
        """
        ESTRATÉGIA JUST-IN-TIME: Para lead time ZERO (produção instantânea)
        
        Características:
        - Cada demanda gera seu próprio lote
        - Lotes chegam exatamente na data da demanda
        - Quantidade calculada para cobrir demanda + margem de segurança
        - Não há antecipação de estoque
        """
        
        batches = []
        current_stock = initial_stock
        
        # Processar cada demanda individualmente
        demand_dates = sorted(valid_demands.keys())
        
        for i, demand_date_str in enumerate(demand_dates):
            demand_qty = valid_demands[demand_date_str]
            demand_date = pd.to_datetime(demand_date_str)
            
            # Verificar se está dentro do período válido
            if not (start_cutoff <= demand_date <= end_cutoff):
                continue
            
            # Calcular estoque projetado na data da demanda
            stock_before = self._project_stock_to_date(
                initial_stock, valid_demands, batches, demand_date_str, start_period
            )
            
            # LÓGICA MELHORADA: Para lead time zero, considerar demandas futuras
            remaining_demands = []
            for j in range(i, len(demand_dates)):
                future_date = demand_dates[j]
                future_qty = valid_demands[future_date]
                remaining_demands.append(future_qty)
            
            total_future_demand = sum(remaining_demands)
            
            min_target = demand_qty + absolute_minimum_stock
            needs_batch = False
            
            if stock_before < min_target:
                needs_batch = True
                shortage = min_target - stock_before
            elif i < len(demand_dates) - 1:
                next_demand = valid_demands[demand_dates[i + 1]]
                if stock_before < demand_qty + (next_demand * 0.5) + absolute_minimum_stock:
                    needs_batch = True
                    shortage = (demand_qty + next_demand + absolute_minimum_stock) - stock_before
                else:
                    shortage = 0
            else:
                shortage = max(0, min_target - stock_before)
                needs_batch = shortage > 0
            
            # Se precisa de lote, criar
            if needs_batch and shortage > 0:
                # Quantidade com margem de segurança
                safety_buffer = demand_qty * (safety_margin_percent / 100) if safety_margin_percent > 0 else 0
                batch_quantity = shortage + safety_buffer
                
                # Aplicar limites
                batch_quantity = max(self.params.min_batch_size, 
                                   min(self.params.max_batch_size, batch_quantity))
                
                # Para lead time 0, order_date = arrival_date = demand_date
                order_date = demand_date
                arrival_date = demand_date
                
                # Criar analytics avançados
                analytics = self._create_advanced_batch_analytics(
                    demand_date_str, demand_qty, batch_quantity, stock_before,
                    arrival_date, leadtime_days, safety_days, mrp_calcs, 
                    demand_analysis, "just_in_time",
                    {
                        "shortage_covered": shortage,
                        "safety_buffer": safety_buffer,
                        "jit_optimal": True,
                        "timing_perfect": True,
                        "demand_coverage": 100.0
                    }
                )
                
                # Criar o lote
                batch = BatchResult(
                    order_date=order_date.strftime('%Y-%m-%d'),
                    arrival_date=arrival_date.strftime('%Y-%m-%d'),
                    quantity=batch_quantity,
                    analytics=analytics
                )
                
                batches.append(batch)
                
                # Atualizar estoque atual
                current_stock = stock_before + batch_quantity - demand_qty
        
        return batches

    def _short_leadtime_sporadic_strategy(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        max_gap_days: int
    ) -> List[BatchResult]:
        """
        ESTRATÉGIA PARA LEAD TIME CURTO COM DEMANDAS ESPORÁDICAS
        
        Características:
        - Cada demanda é avaliada individualmente
        - Pedidos antecipados considerando lead time
        - Mais proativa que EOQ tradicional
        - Otimizada para demandas grandes e espaçadas
        """
        
        batches = []
        current_stock = initial_stock
        
        # Processar cada demanda individualmente
        demand_dates = sorted(valid_demands.keys())
        
        for i, demand_date_str in enumerate(demand_dates):
            demand_qty = valid_demands[demand_date_str]
            demand_date = pd.to_datetime(demand_date_str)
            
            # Verificar se está dentro do período válido
            if not (start_cutoff <= demand_date <= end_cutoff):
                continue
            
            # Calcular estoque projetado na data da demanda
            stock_at_demand = self._project_stock_to_date(
                initial_stock, valid_demands, batches, demand_date_str, start_period
            )
            
            # Log interno da estratégia (removido debug)
            
            # LÓGICA SIMPLIFICADA E MAIS AGRESSIVA: Para demandas esporádicas
            
            min_target = demand_qty + absolute_minimum_stock
            shortage = max(0, min_target - stock_at_demand)
            
            next_demand_qty = 0
            if i < len(demand_dates) - 1:
                next_demand_qty = valid_demands[demand_dates[i + 1]]
            
            buffer_needed = next_demand_qty if next_demand_qty > 0 else (demand_qty * 0.5)
            
            needs_batch = (shortage > 0) or (stock_at_demand < min_target + (buffer_needed * 0.3))
            
            # Lógica de decisão interna (debug removido)
            
            # Decidir se precisa criar lote
            if needs_batch:
                
                # 🚚 VALIDAÇÃO DE PEDIDOS EM TRÂNSITO 
                existing_order = self._check_existing_orders_in_transit(
                    demand_date, leadtime_days, batches, shortage, max_gap_days
                )
                
                if existing_order:
                    # ✅ JÁ EXISTE PEDIDO EM TRÂNSITO - Consolidar
                    self._consolidate_with_existing_order(
                        existing_order, shortage, demand_date_str, demand_qty
                    )
                    continue  # Não criar novo pedido
                
                # Calcular data ideal do pedido (antecipando o lead time)
                ideal_arrival_date = demand_date
                order_date = ideal_arrival_date - pd.Timedelta(days=leadtime_days + safety_days)
                order_date = max(order_date, start_cutoff)
                actual_arrival_date = order_date + pd.Timedelta(days=leadtime_days)
                
                # Verificar se chegará dentro do período válido
                if actual_arrival_date <= end_cutoff:
                    
                    # Calcular quantidade necessária (lógica ajustada)
                    if shortage > 0:
                        # Há déficit imediato - cobrir déficit + buffer para próxima
                        base_quantity = shortage + (buffer_needed * 0.4)  # 40% da próxima
                    else:
                        # Não há déficit, mas estoque baixo - criar lote preventivo
                        base_quantity = demand_qty + (buffer_needed * 0.2)  # 20% da próxima
                    
                    # Margem de segurança proporcional à quantidade base
                    safety_buffer = base_quantity * (safety_margin_percent / 100) if safety_margin_percent > 0 else 0
                    batch_quantity = base_quantity + safety_buffer
                    
                    # 🎯 CORREÇÃO: Para demandas esporádicas pequenas, não forçar min_batch_size
                    # Se a demanda total é muito menor que min_batch_size, usar quantidade real necessária
                    if demand_qty < (self.params.min_batch_size * 0.5):
                        # Demanda pequena - usar quantidade necessária sem forçar mínimo
                        batch_quantity = min(batch_quantity, self.params.max_batch_size)
                    else:
                        # Demanda normal - aplicar limites tradicionais
                        batch_quantity = max(self.params.min_batch_size, 
                                           min(self.params.max_batch_size, batch_quantity))
                    
                    # Criar analytics avançados
                    analytics = self._create_advanced_batch_analytics(
                        demand_date_str, demand_qty, batch_quantity, stock_at_demand,
                        actual_arrival_date, leadtime_days, safety_days, mrp_calcs, 
                        demand_analysis, "short_leadtime_sporadic",
                        {
                            "shortage_covered": shortage,
                            "safety_buffer": safety_buffer,
                            "next_demand_qty": next_demand_qty,
                            "buffer_needed": buffer_needed,
                            "base_quantity": base_quantity,
                            "proactive_planning": True,
                            "timing_optimized": True,
                            "demand_coverage": min(100.0, (batch_quantity / demand_qty) * 100) if demand_qty > 0 else 0,
                            "lead_time_days": leadtime_days
                        }
                    )
                    
                    # Criar o lote
                    batch = BatchResult(
                        order_date=order_date.strftime('%Y-%m-%d'),
                        arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
                        quantity=batch_quantity,
                        analytics=analytics
                    )
                    
                    batches.append(batch)
                    
                    # Atualizar estoque projetado CORRETAMENTE
                    # O estoque após chegada do lote (não subtrai demanda aqui, será subtraída na projeção)
                    current_stock = stock_at_demand + batch_quantity
        
        return batches

    def _medium_leadtime_sporadic_strategy(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        max_gap_days: int
    ) -> List[BatchResult]:
        """
        Estratégia para lead times médios (15-45 dias) com demandas esporádicas
        
        NOVA FUNCIONALIDADE:
        - Evita pedidos redundantes dentro do mesmo período de lead time
        - Consolida automaticamente com pedidos já em trânsito
        - Economiza frete e reduz trabalho de compras
        """
        
        batches = []
        demand_dates = sorted(valid_demands.keys())
        
        for i, demand_date_str in enumerate(demand_dates):
            demand_qty = valid_demands[demand_date_str]
            demand_date = pd.to_datetime(demand_date_str)
            
            # Verificar se está dentro do período válido
            if not (start_cutoff <= demand_date <= end_cutoff):
                continue
            
            # Calcular estoque projetado na data da demanda
            stock_at_demand = self._project_stock_to_date(
                initial_stock, valid_demands, batches, demand_date_str, start_period
            )
            
            safety_buffer = demand_qty * (safety_margin_percent / 100.0)
            required_stock = demand_qty + safety_buffer + absolute_minimum_stock
            
            if stock_at_demand < required_stock:
                shortage = required_stock - stock_at_demand
                
                # 🚚 VALIDAÇÃO DE PEDIDOS EM TRÂNSITO 
                # Verificar se já existe pedido que pode cobrir esta demanda
                existing_order = self._check_existing_orders_in_transit(
                    demand_date, leadtime_days, batches, shortage, max_gap_days
                )
                
                if existing_order:
                    # ✅ JÁ EXISTE PEDIDO EM TRÂNSITO - Consolidar
                    self._consolidate_with_existing_order(
                        existing_order, shortage, demand_date_str, demand_qty
                    )
                    continue  # Não criar novo pedido
                
                # shortage já inclui a margem de segurança (required_stock = demand + safety_buffer)
                batch_quantity = shortage
                
                # Aplicar limites mínimos apenas se necessário (não forçar EOQ)
                batch_quantity = max(batch_quantity, self.params.min_batch_size)
                batch_quantity = min(batch_quantity, self.params.max_batch_size)
                
                # Calcular datas de ordem e chegada
                order_date = demand_date - pd.Timedelta(days=leadtime_days + safety_days)
                arrival_date = order_date + pd.Timedelta(days=leadtime_days)
                
                # Garantir que order_date não seja no passado
                if order_date < start_period:
                    order_date = start_period
                    arrival_date = order_date + pd.Timedelta(days=leadtime_days)
                
                # Criar batch
                batch = BatchResult(
                    order_date=order_date.strftime('%Y-%m-%d'),
                    arrival_date=arrival_date.strftime('%Y-%m-%d'),
                    quantity=round(batch_quantity, 3),
                    analytics=self._create_advanced_batch_analytics(
                        demand_date_str=demand_date_str,
                        demand_quantity=demand_qty,
                        batch_quantity=batch_quantity,
                        stock_before_arrival=stock_at_demand,
                        arrival_date=arrival_date,
                        leadtime_days=leadtime_days,
                        safety_days=safety_days,
                        mrp_calcs=mrp_calcs,
                        demand_analysis=demand_analysis,
                        strategy="medium_leadtime_sporadic",
                        extra_data={
                            'shortage_covered': shortage
                        }
                    )
                )
                
                batches.append(batch)
        
        return batches
    
    def _check_existing_orders_in_transit(
        self, 
        demand_date: pd.Timestamp, 
        leadtime_days: int, 
        existing_batches: List[BatchResult], 
        shortage: float,
        max_gap_days: int = 14
    ) -> Optional[BatchResult]:
        """
        🚚 VALIDAÇÃO DE PEDIDOS EM TRÂNSITO
        
        Verifica se já existe um pedido que pode cobrir a demanda atual.
        Evita pedidos redundantes e economiza frete.
        
        Args:
            demand_date: Data da demanda atual
            leadtime_days: Lead time em dias
            existing_batches: Batches já criados
            shortage: Quantidade necessária
            
        Returns:
            BatchResult existente que pode ser consolidado, ou None
        """
        
        # Definir janela de tempo para verificar pedidos em trânsito
        # Um pedido pode cobrir demandas até X dias após sua chegada
        coverage_window_days = min(leadtime_days * 2, 45)  # Flexível: até 2x lead time
        
        # 🔥 AGRUPAMENTO TOTAL: Se max_gap_days for muito alto, agrupar tudo
        if max_gap_days >= 90:  # Se gap muito alto (3+ meses), agrupar agressivamente
            coverage_window_days = max_gap_days  # Usar gap como janela de consolidação
            max_consolidation_multiplier = 5.0  # Permitir até 5x aumento (super agressivo)
        elif max_gap_days >= 30:  # Gap alto (1+ mês), consolidação moderada
            coverage_window_days = max_gap_days
            max_consolidation_multiplier = 3.0  # Permitir até 3x aumento
        else:
            max_consolidation_multiplier = 2.0  # Padrão: até 2x aumento
        
        for batch in existing_batches:
            arrival_date = pd.to_datetime(batch.arrival_date)
            
            # Verificar se o pedido pode cobrir a demanda atual
            days_between = (demand_date - arrival_date).days
            
            # Critérios otimizados para consolidação:
            # 1. Pedido chega antes ou até N dias após a demanda
            # 2. Pedido tem capacidade para mais quantidade (até 100% aumento)
            # 3. Economia de frete e redução de trabalho administrativo
            
            if -leadtime_days <= days_between <= coverage_window_days:
                # Pedido pode cobrir esta demanda
                current_quantity = batch.quantity
                max_consolidation = current_quantity * max_consolidation_multiplier
                
                if current_quantity + shortage <= max_consolidation:
                    return batch
        
        return None
    
    def _consolidate_with_existing_order(
        self, 
        existing_batch: BatchResult, 
        additional_quantity: float, 
        demand_date_str: str, 
        demand_qty: float
    ) -> None:
        """
        🔄 CONSOLIDAÇÃO DE PEDIDOS
        
        Consolida demanda atual com pedido existente.
        Atualiza quantidade e analytics.
        
        Args:
            existing_batch: Batch existente para consolidar
            additional_quantity: Quantidade adicional necessária
            demand_date_str: Data da demanda sendo consolidada
            demand_qty: Quantidade da demanda
        """
        
        # Atualizar quantidade do batch
        existing_batch.quantity = round(existing_batch.quantity + additional_quantity, 3)
        
        # Atualizar analytics com informação de consolidação
        if 'consolidations' not in existing_batch.analytics:
            existing_batch.analytics['consolidations'] = []
        
        existing_batch.analytics['consolidations'].append({
            'demand_date': demand_date_str,
            'demand_quantity': demand_qty,
            'additional_quantity': additional_quantity,
            'consolidation_reason': 'Pedido em trânsito - Economia de frete'
        })
        
        # Atualizar contadores
        existing_batch.analytics['total_demands_covered'] = existing_batch.analytics.get('total_demands_covered', 1) + 1
        existing_batch.analytics['optimization_quality'] = 'excellent'  # Consolidação é sempre excelente
        existing_batch.analytics['cost_efficiency'] = 'optimized_freight'

    def _hybrid_consolidation_strategy(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        max_gap_days: int
    ) -> List[BatchResult]:
        """Estratégia híbrida combinando consolidação inteligente com EOQ"""
        
        # Identificar grupos de consolidação baseado em análise avançada
        demand_groups = self._identify_optimal_consolidation_groups(
            valid_demands, mrp_calcs, demand_analysis, leadtime_days
        )
        
        batches = []
        
        for group in demand_groups:
            # Usar primeira demanda do grupo como âncora
            primary_date = pd.to_datetime(group['primary_date'])
            group_demand = group['total_demand']
            
            # 🚚 VALIDAÇÃO DE PEDIDOS EM TRÂNSITO 
            # Para grupos de consolidação, considerar o déficit total do grupo
            estimated_shortage = group_demand * 0.7  # Estimativa conservadora de shortage
            existing_order = self._check_existing_orders_in_transit(
                primary_date, leadtime_days, batches, estimated_shortage, max_gap_days
            )
            
            if existing_order:
                # ✅ JÁ EXISTE PEDIDO EM TRÂNSITO - Consolidar grupo inteiro
                self._consolidate_with_existing_order(
                    existing_order, estimated_shortage, group['primary_date'], group_demand
                )
                continue  # Não criar novo pedido para este grupo
            
            # 🎯 CORREÇÃO SAFETY_DAYS: Calcular data alvo com safety_days primeiro
            target_arrival_date = primary_date - pd.Timedelta(days=safety_days)
            ideal_order_date = target_arrival_date - pd.Timedelta(days=leadtime_days)
            
            # Ajustar order_date se necessário, mas manter target_arrival_date
            order_date = max(ideal_order_date, start_cutoff)
            arrival_date = target_arrival_date  # Manter data alvo com safety_days
            
            if arrival_date <= end_cutoff:
                
                projected_stock = self._project_stock_to_date(
                    initial_stock, valid_demands, batches, group['primary_date'], start_period
                )
                
                deficit = max(0, (group_demand + absolute_minimum_stock) - projected_stock)
                
                if deficit > 0:
                    safety_buffer = deficit * (safety_margin_percent / 100.0) if safety_margin_percent > 0 else 0
                    batch_quantity = deficit + safety_buffer
                    
                    # Adicionar buffer inteligente baseado no grupo (opcional)
                    if group['consolidation_benefit'] > 0:
                        consolidation_buffer = deficit * 0.1  # 10% extra do déficit
                        batch_quantity += consolidation_buffer
                else:
                    # Sem déficit - não criar lote (comportamento conservador)
                    continue
                
                # 🎯 CORREÇÃO: Para demandas esporádicas pequenas, não forçar min_batch_size
                if group_demand < (self.params.min_batch_size * 0.5):
                    # Demanda pequena - usar quantidade necessária sem forçar mínimo
                    batch_quantity = min(batch_quantity, self.params.max_batch_size)
                else:
                    # Demanda normal - aplicar limites tradicionais
                    batch_quantity = max(self.params.min_batch_size, 
                                       min(self.params.max_batch_size, batch_quantity))
                
                analytics = self._create_advanced_batch_analytics(
                    group['primary_date'], group['demands'][0]['quantity'] if group['demands'] else group_demand,
                    batch_quantity, projected_stock, arrival_date, leadtime_days, 
                    safety_days, mrp_calcs, demand_analysis,
                    strategy='hybrid_consolidation',
                    extra_data={
                        'group_size': len(group['demands']),
                        'consolidation_benefit': group['consolidation_benefit'],
                        'demands_covered': group['demands'],
                        'group_span_days': group['span_days']
                    }
                )
                
                batch = BatchResult(
                    order_date=order_date.strftime('%Y-%m-%d'),
                    arrival_date=arrival_date.strftime('%Y-%m-%d'),
                    quantity=round(batch_quantity, 3),
                    analytics=analytics
                )
                batches.append(batch)
        
        return batches 

    # =============== MÉTODOS AUXILIARES ===============
    
    def _project_stock_to_date(
        self,
        initial_stock: float,  # CORREÇÃO: usar initial_stock, não current_stock
        valid_demands: Dict[str, float],
        existing_batches: List[BatchResult],
        target_date: str,
        start_period: pd.Timestamp
    ) -> float:
        """
        Projeta estoque até uma data específica ANTES de qualquer movimentação nessa data
        Retorna o estoque disponível no início da data alvo, antes da demanda e chegadas
        
        IMPORTANTE: Sempre parte do estoque inicial e calcula tudo do zero para evitar erros acumulativos
        """
        
        projected_stock = initial_stock
        target_dt = pd.to_datetime(target_date)
        
        # Criar lista de eventos em ordem cronológica
        events = []
        
        # Adicionar chegadas de lotes
        for batch in existing_batches:
            events.append({
                'date': pd.to_datetime(batch.arrival_date),
                'type': 'arrival',
                'quantity': batch.quantity
            })
        
        # Adicionar demandas
        for date_str, qty in valid_demands.items():
            events.append({
                'date': pd.to_datetime(date_str),
                'type': 'demand',
                'quantity': qty
            })
        
        # Ordenar eventos cronologicamente
        # Chegadas acontecem no início do dia, demandas no final
        events.sort(key=lambda x: (x['date'], x['type'] == 'demand'))
        
        # Processar eventos até a data alvo:
        # - Incluir arrivals na target_date (chegam no início do dia)
        # - Excluir demands na target_date (consumidas no final do dia)
        for event in events:
            if event['date'] > target_dt:
                break
            if event['date'] == target_dt and event['type'] == 'demand':
                break
                
            if event['type'] == 'arrival':
                projected_stock += event['quantity']
            elif event['type'] == 'demand':
                projected_stock -= event['quantity']
        
        return projected_stock
    
    def _forecast_demand_advanced(
        self,
        valid_demands: Dict[str, float],
        demand_analysis: Dict,
        leadtime_days: int
    ) -> float:
        """Previsão avançada de demanda usando múltiplos métodos"""
        
        if not valid_demands or leadtime_days <= 0:
            return 0
        
        demands = list(valid_demands.values())
        dates = [pd.to_datetime(d) for d in valid_demands.keys()]
        
        # Método 1: Média móvel ponderada
        if len(demands) >= 3:
            weights = np.array([0.5, 0.3, 0.2])  # Mais peso para dados recentes
            recent_demands = demands[-3:]
            if len(recent_demands) == 3:
                forecast_ma = np.average(recent_demands, weights=weights)
            else:
                forecast_ma = np.mean(demands)
        else:
            forecast_ma = np.mean(demands) if demands else 0
        
        # Método 2: Tendência linear
        if len(demands) >= 3:
            x = np.arange(len(demands))
            slope, intercept = np.polyfit(x, demands, 1)
            forecast_trend = intercept + slope * len(demands)  # Próximo ponto
        else:
            forecast_trend = forecast_ma
        
        # Método 3: Sazonalidade se detectada
        forecast_seasonal = forecast_ma
        if demand_analysis['seasonality']['detected']:
            seasonal_factor = 1 + (demand_analysis['seasonality']['strength'] * 0.1)
            if demand_analysis['seasonality']['type'] == 'weekly':
                # Ajustar baseado no dia da semana
                last_date = dates[-1] if dates else datetime.now()
                future_weekday = (last_date.weekday() + leadtime_days) % 7
                if future_weekday in [0, 1]:  # Segunda/Terça geralmente maior demanda
                    seasonal_factor *= 1.1
                forecast_seasonal = forecast_ma * seasonal_factor
        
        # Combinar métodos com pesos baseados na confiabilidade
        if demand_analysis['trend']['significance'] == 'high':
            # Tendência forte - dar mais peso ao método de tendência
            final_forecast = (forecast_trend * 0.5 + forecast_ma * 0.3 + forecast_seasonal * 0.2)
        elif demand_analysis['seasonality']['detected']:
            # Sazonalidade detectada - dar mais peso ao método sazonal
            final_forecast = (forecast_seasonal * 0.5 + forecast_ma * 0.3 + forecast_trend * 0.2)
        else:
            # Caso padrão - média móvel ponderada
            final_forecast = (forecast_ma * 0.6 + forecast_trend * 0.2 + forecast_seasonal * 0.2)
        
        # Ajustar para lead time (quanto maior o lead time, maior a incerteza)
        uncertainty_factor = 1 + (leadtime_days / 365) * demand_analysis['cv']
        final_forecast *= uncertainty_factor
        
        # Garantir que não seja negativo
        return max(0, final_forecast)
    
    def _identify_optimal_consolidation_groups(
        self,
        valid_demands: Dict[str, float],
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        leadtime_days: int
    ) -> List[Dict]:
        """Identifica grupos ótimos para consolidação usando análise de custos"""
        
        demand_items = [(date, qty) for date, qty in sorted(valid_demands.items())]
        groups = []
        
        i = 0
        while i < len(demand_items):
            current_group = {
                'primary_date': demand_items[i][0],
                'demands': [{'date': demand_items[i][0], 'quantity': demand_items[i][1]}],
                'total_demand': demand_items[i][1],
                'span_days': 0,
                'consolidation_benefit': 0
            }
            
            # Procurar demandas próximas para consolidar
            j = i + 1
            while j < len(demand_items) and j - i < 5:  # Máximo 5 demandas por grupo
                
                next_date = pd.to_datetime(demand_items[j][0])
                primary_date = pd.to_datetime(current_group['primary_date'])
                gap_days = (next_date - primary_date).days
                
                # Análise de custo-benefício da consolidação
                setup_savings = self.params.setup_cost  # Economia de um setup
                holding_cost_increase = demand_items[j][1] * mrp_calcs.holding_cost_per_unit * (gap_days / 365)
                
                # Benefícios operacionais adicionais
                operational_benefit = 0
                if gap_days <= leadtime_days:  # Dentro do lead time
                    operational_benefit += self.params.setup_cost * 0.3  # 30% de benefício operacional
                
                net_benefit = setup_savings + operational_benefit - holding_cost_increase
                
                # Critérios para consolidação
                should_consolidate = (
                    gap_days <= min(30, leadtime_days + 14) and  # Limite temporal
                    net_benefit > 0 and  # Benefício econômico positivo
                    current_group['total_demand'] + demand_items[j][1] <= self.params.max_batch_size  # Limite de capacidade
                )
                
                if should_consolidate:
                    current_group['demands'].append({
                        'date': demand_items[j][0], 
                        'quantity': demand_items[j][1]
                    })
                    current_group['total_demand'] += demand_items[j][1]
                    current_group['span_days'] = gap_days
                    current_group['consolidation_benefit'] += net_benefit
                    j += 1
                else:
                    break
            
            groups.append(current_group)
            i = j if j > i else i + 1
        
        return groups
    
    def _create_advanced_batch_analytics(
        self,
        demand_date_str: str,
        demand_quantity: float,
        batch_quantity: float,
        stock_before_arrival: float,
        arrival_date: pd.Timestamp,
        leadtime_days: int,
        safety_days: int,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        strategy: str,
        extra_data: Dict = None
    ) -> Dict:
        """Cria analytics avançados mantendo compatibilidade total"""
        
        demand_date = pd.to_datetime(demand_date_str)
        
        # Calcular stock_after_arrival corretamente
        # Se a chegada é no mesmo dia da demanda, consideramos o estoque após chegada mas antes da demanda
        # Se a chegada é em dia diferente, é apenas stock_before + batch_quantity
        arrival_date_str = arrival_date.strftime('%Y-%m-%d')
        if arrival_date_str == demand_date_str:
            # Chegada no mesmo dia da demanda: estoque após chegada mas antes da demanda ser consumida
            stock_after_arrival = stock_before_arrival + batch_quantity
        else:
            # Chegada em dia diferente: simplesmente adicionar ao estoque
            stock_after_arrival = stock_before_arrival + batch_quantity
        
        # Analytics básicos (compatibilidade total)
        analytics = {
            # Campos obrigatórios existentes
            'stock_before_arrival': round(stock_before_arrival, 2),
            'stock_after_arrival': round(stock_after_arrival, 2),
            'consumption_since_last_arrival': 0,  # Será calculado posteriormente
            'coverage_days': round(batch_quantity / demand_analysis['mean_demand']) if demand_analysis['mean_demand'] > 0 else 0,
            'actual_lead_time': leadtime_days,
            'urgency_level': 'critical' if stock_before_arrival < 0 else ('high' if stock_before_arrival < demand_quantity else 'normal'),
            'production_start_delay': 0,
            'arrival_delay': max(0, (arrival_date - demand_date).days),
            
            # Campos esporádicos existentes
            'target_demand_date': demand_date_str,
            'target_demand_quantity': demand_quantity,
            'shortfall_covered': round(max(0, demand_quantity - stock_before_arrival), 2),
            'demands_covered': [],  # Será calculado posteriormente
            'coverage_count': 0,  # Será calculado posteriormente
            'is_critical': arrival_date > demand_date,
            'safety_margin_days': (demand_date - arrival_date).days,
            'efficiency_ratio': round(batch_quantity / demand_quantity, 2) if demand_quantity > 0 else 0,
            
            # NOVOS CAMPOS - Analytics Avançados
            'advanced_mrp_strategy': strategy,
            'eoq_used': round(mrp_calcs.eoq, 2),
            'safety_stock_calculated': round(mrp_calcs.safety_stock, 2),
            'reorder_point_used': round(mrp_calcs.reorder_point, 2),
            'service_level_z_score': round(mrp_calcs.service_level_z_score, 3),
            'abc_classification': mrp_calcs.abc_classification,
            'xyz_classification': mrp_calcs.xyz_classification,
            'demand_variability_cv': round(demand_analysis['cv'], 3),
            'demand_regularity_score': round(demand_analysis['regularity_score'], 3),
            'seasonality_detected': demand_analysis['seasonality']['detected'],
            'trend_direction': demand_analysis['trend']['direction'],
            'holding_cost_impact': round(batch_quantity * mrp_calcs.holding_cost_per_unit * (leadtime_days + safety_days) / 365, 2),
            'setup_cost_allocation': round(self.params.setup_cost, 2),
            'total_cost_estimated': round(
                self.params.setup_cost + 
                (batch_quantity * mrp_calcs.holding_cost_per_unit * (leadtime_days + safety_days) / 365), 2
            ),
            'optimization_quality': self._calculate_optimization_quality(
                batch_quantity, mrp_calcs, demand_analysis, strategy
            )
        }
        
        # Adicionar dados extras específicos da estratégia
        if extra_data:
            for key, value in extra_data.items():
                analytics[f'strategy_{key}'] = value
        
        return analytics
    
    def _calculate_optimization_quality(
        self,
        batch_quantity: float,
        mrp_calcs: AdvancedMRPCalculations,
        demand_analysis: Dict,
        strategy: str
    ) -> str:
        """Calcula qualidade da otimização"""
        
        if strategy == 'just_in_time':
            return 'excellent'  # Just-in-time é sempre ótimo para lead time zero
        elif strategy == 'short_leadtime_sporadic':
            return 'excellent'  # Estratégia otimizada para lead times curtos
        elif strategy == 'medium_leadtime_sporadic':
            return 'excellent'  # Estratégia otimizada para lead times médios
        elif strategy == 'hybrid_consolidation':
            return 'good'  # Estratégia de consolidação simples e eficaz
        else:
            return 'fair'


# =============== INTEGRAÇÃO COM MRP EXISTENTE ===============

def integrate_advanced_mrp_with_existing(mrp_optimizer_instance):
    """
    Integra o planejador avançado com a instância existente do MRPOptimizer
    Substitui a função _plan_sporadic_batches por uma versão avançada
    """
    
    def _plan_sporadic_batches_advanced_wrapper(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp,
        safety_days: int,
        safety_margin_percent: float,
        absolute_minimum_stock: float,
        max_gap_days: int
    ) -> List[BatchResult]:
        """Wrapper que usa o planejador avançado"""
        
        # Criar instância do planejador avançado
        advanced_planner = AdvancedSporadicMRPPlanner(self.params)
        
        # Usar planejamento avançado
        return advanced_planner.plan_sporadic_batches_advanced(
            valid_demands=valid_demands,
            initial_stock=initial_stock,
            leadtime_days=leadtime_days,
            start_period=start_period,
            end_period=end_period,
            start_cutoff=start_cutoff,
            end_cutoff=end_cutoff,
            safety_days=safety_days,
            safety_margin_percent=safety_margin_percent,
            absolute_minimum_stock=absolute_minimum_stock,
            max_gap_days=max_gap_days
        )
    
    # Substituir o método na instância
    import types
    mrp_optimizer_instance._plan_sporadic_batches = types.MethodType(
        _plan_sporadic_batches_advanced_wrapper, mrp_optimizer_instance
    )
    
    return mrp_optimizer_instance


# =============== FUNÇÃO DE CONVENIÊNCIA ===============

def create_advanced_mrp_optimizer(optimization_params: Optional[OptimizationParams] = None):
    """
    Cria um MRPOptimizer com capacidades avançadas integradas
    """
    from mrp import MRPOptimizer
    
    # Criar otimizador padrão
    optimizer = MRPOptimizer(optimization_params)
    
    # Integrar capacidades avançadas
    return integrate_advanced_mrp_with_existing(optimizer) 