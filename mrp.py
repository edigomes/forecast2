import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy import stats
from dataclasses import dataclass
import json


def clean_for_json(obj):
    """
    Converte recursivamente todos os valores para tipos compatíveis com JSON padrão
    Remove numpy types, NaN, Infinity e garante compatibilidade com PHP
    """
    if isinstance(obj, dict):
        return {key: clean_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer, np.signedinteger, np.unsignedinteger)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.complexfloating)):
        val = float(obj)
        # Converter NaN e Infinity para valores válidos
        if np.isnan(val):
            return 0.0
        elif np.isinf(val):
            return 999999999.0 if val > 0 else -999999999.0
        else:
            return round(val, 6)  # Limitar precisão para evitar problemas
    elif isinstance(obj, np.ndarray):
        return [clean_for_json(item) for item in obj.tolist()]
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, str):
        # Garantir que strings sejam válidas UTF-8
        return obj.encode('utf-8', 'replace').decode('utf-8')
    elif obj is None:
        return None
    elif isinstance(obj, float):
        # Verificar floats Python nativos também
        if np.isnan(obj):
            return 0.0
        elif np.isinf(obj):
            return 999999999.0 if obj > 0 else -999999999.0
        else:
            return round(obj, 6)
    elif isinstance(obj, int):
        return obj
    else:
        # Para outros tipos, tentar converter para string
        try:
            return str(obj)
        except:
            return None


@dataclass
class BatchResult:
    """Estrutura de dados para resultado de lote"""
    order_date: str
    arrival_date: str
    quantity: float
    analytics: Dict


@dataclass
class OptimizationParams:
    """Parâmetros de otimização com valores padrão sensatos"""
    setup_cost: float = 250.0  # Custo fixo por pedido
    holding_cost_rate: float = 0.20  # 20% ao ano do valor do produto
    stockout_cost_multiplier: float = 15  # 2.5x o valor do produto
    service_level: float = 0.98  # 95% de nível de serviço
    min_batch_size: float = 200.0  # Tamanho mínimo do lote
    max_batch_size: float = 10000.0  # Tamanho máximo do lote
    review_period_days: int = 7  # Período de revisão padrão
    safety_days: int = 15  # Dias de segurança adicional
    consolidation_window_days: int = 5  # Janela para consolidar pedidos
    daily_production_capacity: float = float('inf')  # Capacidade diária de produção
    enable_eoq_optimization: bool = True  # Habilitar otimização EOQ
    enable_consolidation: bool = True  # Habilitar consolidação de pedidos
    # NOVOS PARÂMETROS para melhor controle de consolidação
    force_consolidation_within_leadtime: bool = True  # Força consolidação dentro do lead time
    min_consolidation_benefit: float = 50.0  # Benefício mínimo para consolidar (independente de setup_cost)
    operational_efficiency_weight: float = 1.0  # Peso dos benefícios operacionais (0.5-2.0)
    overlap_prevention_priority: bool = True  # Priorizar prevenção de overlap de lead time


class MRPOptimizer:
    """
    Classe otimizada para cálculo de lotes de produção/compra
    com algoritmos inteligentes de supply chain
    """
    
    def __init__(self, optimization_params: Optional[OptimizationParams] = None):
        self.params = optimization_params or OptimizationParams()
        
    def calculate_batches_with_start_end_cutoff(
        self,
        daily_demands: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        period_start_date: str,
        period_end_date: str,
        start_cutoff_date: str,
        end_cutoff_date: str,
        include_extended_analytics: bool = False,  # Novo parâmetro
        **kwargs
    ) -> Dict:
        """
        Calcula lotes otimizados considerando múltiplos fatores de supply chain
        
        Args:
            daily_demands: Dicionário com demandas diárias {"YYYY-MM": demanda_média_diária}
            initial_stock: Estoque inicial
            leadtime_days: Lead time em dias
            period_start_date: Data início do período
            period_end_date: Data fim do período
            start_cutoff_date: Data de corte inicial
            end_cutoff_date: Data de corte final
            include_extended_analytics: Se True, inclui analytics avançados
            **kwargs: Parâmetros adicionais que sobrescrevem os padrões
            
        Returns:
            Dict com 'batches' e 'analytics' (compatível com PHP + extras opcionais)
        """
        # Atualizar parâmetros com kwargs
        self._update_params(kwargs)
        
        # Converter datas
        start_period = pd.to_datetime(period_start_date)
        end_period = pd.to_datetime(period_end_date)
        start_cutoff = pd.to_datetime(start_cutoff_date)
        end_cutoff = pd.to_datetime(end_cutoff_date)
        
        # Preparar dados de demanda
        demand_df = self._prepare_demand_data(
            daily_demands, start_period, end_period
        )
        
        # Calcular estatísticas de demanda
        demand_stats = self._calculate_demand_statistics(demand_df)
        
        # Escolher estratégia baseada no lead time
        if leadtime_days == 0:
            strategy = self._jit_strategy
        elif leadtime_days <= 3:
            strategy = self._short_leadtime_strategy
        elif leadtime_days <= 14:
            strategy = self._medium_leadtime_strategy
        else:
            strategy = self._long_leadtime_strategy
            
        # Calcular lotes usando a estratégia apropriada
        batches = strategy(
            demand_df,
            initial_stock,
            leadtime_days,
            demand_stats,
            start_cutoff,
            end_cutoff
        )
        
        # Pós-processar e otimizar consolidação
        if self.params.enable_consolidation:
            batches = self._consolidate_batches(batches, leadtime_days)
        
        # Atualizar analytics dos lotes com dados da simulação real
        batches = self._update_batch_analytics(batches, demand_df, initial_stock)
        
        # Calcular analytics básicos (compatível com PHP)
        analytics = self._calculate_analytics(
            batches, demand_df, initial_stock, demand_stats
        )
        
        # Adicionar analytics estendidos se solicitado
        if include_extended_analytics:
            analytics['extended_analytics'] = self._calculate_extended_analytics(
                batches, demand_df, initial_stock, demand_stats, analytics, leadtime_days
            )
        
        # Limpar dados para compatibilidade JSON/PHP
        result = {
            'batches': [self._batch_to_dict(b) for b in batches],
            'analytics': analytics
        }
        
        return clean_for_json(result)
    
    def _calculate_extended_analytics(
        self,
        batches: List[BatchResult],
        demand_df: pd.DataFrame,
        initial_stock: float,
        demand_stats: Dict,
        basic_analytics: Dict,
        leadtime_days: int
    ) -> Dict:
        """Calcula analytics avançados para insights adicionais"""
        
        # Verificações básicas para evitar processamento desnecessário
        if demand_stats['mean'] <= 0:
            return self._get_empty_extended_analytics()
        
        # Simular evolução do estoque (com limite de processamento)
        stock_evolution_list = self._simulate_stock_evolution(
            batches, demand_df, initial_stock
        )
        
        if not stock_evolution_list:
            return self._get_empty_extended_analytics()
        
        avg_stock = np.mean(stock_evolution_list) if stock_evolution_list else initial_stock
        stockouts = sum(1 for s in stock_evolution_list if s < 0)
        
        # Análise de variabilidade
        stock_std = np.std(stock_evolution_list) if len(stock_evolution_list) > 1 else 0
        stock_cv = stock_std / avg_stock if avg_stock > 0 else 0
        
        # Análise de sazonalidade (simplificada para datasets pequenos)
        if len(demand_df) >= 7:  # Apenas se há dados suficientes
            seasonality_analysis = self._analyze_seasonality(demand_df)
        else:
            seasonality_analysis = {'seasonality_detected': False, 'message': 'Insufficient data'}
        
        # Métricas de otimização
        optimization_metrics = self._calculate_optimization_metrics(
            batches, demand_stats, leadtime_days
        )
        
        # Análise de riscos
        risk_analysis = self._calculate_risk_metrics(
            stock_evolution_list, demand_stats, stockouts
        )
        
        # Recomendações baseadas em IA (limitadas para casos simples)
        if len(batches) <= 50:  # Limite de processamento
            recommendations = self._generate_recommendations(
                batches, demand_stats, basic_analytics, risk_analysis
            )
        else:
            recommendations = [{'type': 'info', 'message': 'Muitos lotes para análise detalhada de recomendações'}]
        
        # Custo total estimado
        total_cost = self._estimate_total_cost(
            batches, avg_stock, stockouts, demand_stats
        )
        
        # Cenários what-if (simplificados)
        if demand_stats['total'] > 0 and avg_stock > 0:
            what_if_scenarios = self._calculate_what_if_scenarios(
                demand_df, initial_stock, demand_stats
            )
        else:
            what_if_scenarios = {'message': 'Dados insuficientes para cenários what-if'}
        
        return {
            'performance_metrics': {
                'realized_service_level': round((1 - stockouts/len(stock_evolution_list)) * 100, 2) if stock_evolution_list else 100,
                'inventory_turnover': round(demand_stats['total'] / avg_stock, 2) if avg_stock > 0 else 0,
                'average_days_of_inventory': round(avg_stock / demand_stats['mean'], 1) if demand_stats['mean'] > 0 else 0,
                'setup_frequency': len(batches),
                'average_batch_size': round(sum(b.quantity for b in batches) / len(batches), 2) if batches else 0,
                'stock_variability_cv': round(stock_cv, 3),
                'perfect_order_rate': self._calculate_perfect_order_rate(batches, demand_df)
            },
            'cost_analysis': total_cost,
            'optimization_metrics': optimization_metrics,
            'risk_analysis': risk_analysis,
            'seasonality_analysis': seasonality_analysis,
            'recommendations': recommendations,
            'what_if_scenarios': what_if_scenarios,
            'optimization_parameters_used': {
                'setup_cost': float(self.params.setup_cost),
                'holding_cost_rate': float(self.params.holding_cost_rate),
                'service_level_target': float(self.params.service_level),
                'consolidation_enabled': bool(self.params.enable_consolidation),
                'eoq_optimization_enabled': bool(self.params.enable_eoq_optimization),
                'strategy_used': self._get_strategy_name(leadtime_days)
            }
        }
    
    def _get_empty_extended_analytics(self) -> Dict:
        """Retorna analytics estendidos vazios para casos extremos"""
        return {
            'performance_metrics': {
                'realized_service_level': 100.0,
                'inventory_turnover': 0,
                'average_days_of_inventory': 0,
                'setup_frequency': 0,
                'average_batch_size': 0,
                'stock_variability_cv': 0,
                'perfect_order_rate': 100.0
            },
            'cost_analysis': {
                'total_cost': 0,
                'setup_cost': 0,
                'holding_cost': 0,
                'stockout_cost': 0
            },
            'optimization_metrics': {},
            'risk_analysis': {'message': 'Dados insuficientes para análise de risco'},
            'seasonality_analysis': {'seasonality_detected': False},
            'recommendations': [],
            'what_if_scenarios': {},
            'optimization_parameters_used': {
                'setup_cost': float(self.params.setup_cost),
                'holding_cost_rate': float(self.params.holding_cost_rate),
                'service_level_target': float(self.params.service_level),
                'consolidation_enabled': bool(self.params.enable_consolidation),
                'eoq_optimization_enabled': bool(self.params.enable_eoq_optimization),
                'strategy_used': 'Dados insuficientes'
            }
        }
    
    def _analyze_seasonality(self, demand_df: pd.DataFrame) -> Dict:
        """Analisa padrões de sazonalidade na demanda"""
        if len(demand_df) < 30:
            return {'seasonality_detected': False, 'message': 'Insufficient data'}
        
        # Agrupar por dia da semana
        demand_df['weekday'] = demand_df.index.dayofweek
        weekly_pattern = demand_df.groupby('weekday')['demand'].mean()
        
        # Agrupar por dia do mês
        demand_df['day'] = demand_df.index.day
        monthly_pattern = demand_df.groupby('day')['demand'].mean()
        
        # Calcular índices de sazonalidade
        weekly_seasonality_index = {}
        overall_mean = demand_df['demand'].mean()
        
        for day, avg in weekly_pattern.items():
            day_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            weekly_seasonality_index[day_names[day]] = round(avg / overall_mean, 3) if overall_mean > 0 else 1
        
        # Detectar tendência
        x = np.arange(len(demand_df))
        y = demand_df['demand'].values
        if np.sum(y) > 0:
            slope, intercept = np.polyfit(x, y, 1)
            trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            trend_strength = abs(slope) / overall_mean if overall_mean > 0 else 0
        else:
            trend_direction = 'stable'
            trend_strength = 0
        
        return {
            'seasonality_detected': bool(max(weekly_seasonality_index.values()) > 1.1 or min(weekly_seasonality_index.values()) < 0.9),
            'weekly_pattern': weekly_seasonality_index,
            'peak_day': max(weekly_seasonality_index, key=weekly_seasonality_index.get),
            'low_day': min(weekly_seasonality_index, key=weekly_seasonality_index.get),
            'trend': {
                'direction': trend_direction,
                'strength': round(trend_strength, 4),
                'monthly_growth_rate': round(slope * 30 / overall_mean * 100, 2) if overall_mean > 0 else 0
            }
        }
    
    def _calculate_optimization_metrics(
        self, 
        batches: List[BatchResult],
        demand_stats: Dict,
        leadtime_days: int
    ) -> Dict:
        """Calcula métricas de otimização alcançadas"""
        if not batches:
            return {}
        
        total_quantity = sum(b.quantity for b in batches)
        
        # Calcular EOQ teórico
        annual_demand = demand_stats['mean'] * 365
        if annual_demand > 0 and self.params.setup_cost > 0 and self.params.holding_cost_rate > 0:
            theoretical_eoq = np.sqrt(2 * annual_demand * self.params.setup_cost / 
                                    (self.params.holding_cost_rate * 100))  # assumindo valor unitário 100
        else:
            theoretical_eoq = 0
        
        # Calcular aderência ao EOQ
        avg_batch_size = total_quantity / len(batches)
        eoq_adherence = 1 - abs(avg_batch_size - theoretical_eoq) / theoretical_eoq if theoretical_eoq > 0 else 0
        
        # Calcular economia de consolidação
        if self.params.enable_consolidation:
            # Estimar quantos pedidos teriam sem consolidação
            estimated_orders_without = len(demand_stats) // self.params.consolidation_window_days
            consolidation_savings = max(0, estimated_orders_without - len(batches)) * self.params.setup_cost
        else:
            consolidation_savings = 0
        
        return {
            'theoretical_eoq': round(theoretical_eoq, 2),
            'actual_average_batch': round(avg_batch_size, 2),
            'eoq_adherence_rate': round(eoq_adherence * 100, 2),
            'consolidation_savings': round(consolidation_savings, 2),
            'optimal_review_period': self._calculate_optimal_review_period(demand_stats, leadtime_days),
            'batches_vs_optimal': {
                'actual_batches': len(batches),
                'optimal_batches': round(demand_stats['total'] / theoretical_eoq, 1) if theoretical_eoq > 0 else 0,
                'efficiency': round(min(len(batches), demand_stats['total'] / theoretical_eoq) / 
                                  max(len(batches), demand_stats['total'] / theoretical_eoq) * 100, 2) if theoretical_eoq > 0 else 100
            }
        }
    
    def _calculate_risk_metrics(
        self,
        stock_evolution: List[float],
        demand_stats: Dict,
        stockouts: int
    ) -> Dict:
        """Calcula métricas de risco da política"""
        # Calcular VaR (Value at Risk) do estoque
        stock_array = np.array(stock_evolution)
        var_95 = np.percentile(stock_array, 5)  # 5% pior caso
        cvar_95 = stock_array[stock_array <= var_95].mean() if len(stock_array[stock_array <= var_95]) > 0 else var_95
        
        # Calcular probabilidade de ruptura
        stockout_probability = stockouts / len(stock_evolution) if len(stock_evolution) > 0 else 0
        
        # Calcular dias até ruptura (média)
        days_to_stockout = []
        for i, stock in enumerate(stock_evolution):
            if stock < demand_stats['mean'] * 5:  # Menos de 5 dias de estoque
                days_remaining = stock / demand_stats['mean'] if demand_stats['mean'] > 0 else 0
                days_to_stockout.append(days_remaining)
        
        avg_days_to_stockout = np.mean(days_to_stockout) if days_to_stockout else float('inf')
        
        return {
            'stockout_risk': {
                'probability': round(stockout_probability * 100, 2),
                'expected_stockouts_per_year': round(stockout_probability * 365, 1),
                'average_days_to_stockout': round(avg_days_to_stockout, 1),
                'severity': 'high' if stockout_probability > 0.05 else 'medium' if stockout_probability > 0.01 else 'low'
            },
            'inventory_risk': {
                'var_95': round(var_95, 2),
                'cvar_95': round(cvar_95, 2),
                'min_stock_as_days': round(min(stock_evolution) / demand_stats['mean'], 1) if demand_stats['mean'] > 0 else 0,
                'volatility': round(np.std(stock_evolution), 2)
            },
            'demand_uncertainty': {
                'coefficient_of_variation': round(demand_stats['cv'], 3),
                'predictability': 'low' if demand_stats['cv'] > 0.5 else 'medium' if demand_stats['cv'] > 0.2 else 'high',
                'forecast_error_impact': round(demand_stats['std'] * 1.96, 2)  # 95% confidence interval
            }
        }
    
    def _generate_recommendations(
        self,
        batches: List[BatchResult],
        demand_stats: Dict,
        basic_analytics: Dict,
        risk_analysis: Dict
    ) -> List[Dict]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        # Recomendação sobre nível de serviço
        if risk_analysis['stockout_risk']['probability'] > 5:
            recommendations.append({
                'type': 'service_level',
                'priority': 'high',
                'message': 'Alto risco de ruptura detectado. Considere aumentar o nível de serviço alvo.',
                'action': f"Aumentar service_level de {self.params.service_level} para {min(0.99, self.params.service_level + 0.03)}",
                'expected_impact': 'Redução de 30-50% nas rupturas de estoque'
            })
        
        # Recomendação sobre tamanho de lote
        if len(batches) > demand_stats['total'] / (demand_stats['mean'] * 7):  # Mais de 1 pedido por semana
            recommendations.append({
                'type': 'batch_size',
                'priority': 'medium',
                'message': 'Frequência de pedidos muito alta. Considere aumentar o tamanho dos lotes.',
                'action': 'Habilitar consolidação de pedidos ou aumentar min_batch_size',
                'expected_impact': f"Redução de {len(batches)} para {len(batches)//2} pedidos, economia de R$ {len(batches)//2 * self.params.setup_cost}"
            })
        
        # Recomendação sobre variabilidade
        if demand_stats['cv'] > 0.3:
            recommendations.append({
                'type': 'demand_variability',
                'priority': 'medium',
                'message': 'Alta variabilidade na demanda detectada.',
                'action': 'Implementar previsão de demanda mais sofisticada ou aumentar estoque de segurança',
                'expected_impact': 'Melhoria de 20-30% na precisão do planejamento'
            })
        
        # Recomendação sobre lead time
        leadtime_days = batches[0].analytics.get('actual_lead_time', 0) if batches else 0
        if leadtime_days > 14:
            recommendations.append({
                'type': 'lead_time',
                'priority': 'high',
                'message': 'Lead time longo identificado. Isso aumenta a incerteza e necessidade de estoque.',
                'action': 'Negociar redução de lead time com fornecedor ou buscar alternativas locais',
                'expected_impact': f"Redução de {round(leadtime_days * demand_stats['mean'] * 0.3, 0)} unidades em estoque de segurança"
            })
        
        return recommendations
    
    def _calculate_what_if_scenarios(
        self,
        demand_df: pd.DataFrame,
        initial_stock: float,
        demand_stats: Dict
    ) -> Dict:
        """Calcula cenários what-if para análise de sensibilidade"""
        scenarios = {}
        
        # Cenário 1: Aumento de 20% na demanda
        increased_demand = demand_stats['mean'] * 1.2
        safety_stock_increase = self._calculate_safety_stock(
            demand_stats['std'] * 1.2, 7, self.params.service_level
        )
        
        scenarios['demand_increase_20%'] = {
            'additional_stock_needed': round(safety_stock_increase - 
                self._calculate_safety_stock(demand_stats['std'], 7, self.params.service_level), 2),
            'additional_orders_per_month': round((increased_demand - demand_stats['mean']) * 30 / 
                                                self.params.min_batch_size, 1),
            'cost_impact': round((increased_demand - demand_stats['mean']) * 365 * 100 * 0.2, 2)
        }
        
        # Cenário 2: Redução de lead time em 50%
        current_lead_time = 7  # assumindo
        new_lead_time = current_lead_time // 2
        
        scenarios['leadtime_reduction_50%'] = {
            'safety_stock_reduction': round(
                self._calculate_safety_stock(demand_stats['std'], current_lead_time, self.params.service_level) -
                self._calculate_safety_stock(demand_stats['std'], new_lead_time, self.params.service_level), 2
            ),
            'working_capital_freed': round(
                (self._calculate_safety_stock(demand_stats['std'], current_lead_time, self.params.service_level) -
                 self._calculate_safety_stock(demand_stats['std'], new_lead_time, self.params.service_level)) * 100, 2
            ),
            'flexibility_improvement': 'Alta - resposta 50% mais rápida a mudanças de demanda'
        }
        
        # Cenário 3: Implementação de previsão perfeita
        scenarios['perfect_forecast'] = {
            'safety_stock_elimination': round(
                self._calculate_safety_stock(demand_stats['std'], 7, self.params.service_level), 2
            ),
            'cost_savings': round(
                self._calculate_safety_stock(demand_stats['std'], 7, self.params.service_level) * 100 * 0.2, 2
            ),
            'feasibility': 'Baixa - considere melhorias incrementais na previsão'
        }
        
        return scenarios
    
    def _calculate_perfect_order_rate(self, batches: List[BatchResult], demand_df: pd.DataFrame) -> float:
        """Calcula taxa de pedidos perfeitos (no prazo, quantidade correta, sem rupturas)"""
        if not batches:
            return 100.0
            
        perfect_orders = 0
        
        for batch in batches:
            # Verificar se o pedido foi perfeito
            is_perfect = True
            
            # Critério 1: Chegou no prazo esperado
            if batch.analytics.get('arrival_delay', 0) > 0:
                is_perfect = False
                
            # Critério 2: Não causou ruptura
            if batch.analytics.get('urgency_level') == 'critical':
                is_perfect = False
                
            # Critério 3: Tamanho adequado (não muito grande nem pequeno)
            if batch.quantity > self.params.max_batch_size * 0.9 or batch.quantity < self.params.min_batch_size * 1.1:
                is_perfect = False
                
            if is_perfect:
                perfect_orders += 1
                
        return round((perfect_orders / len(batches)) * 100, 2)
    
    def _calculate_optimal_review_period(self, demand_stats: Dict, leadtime_days: int) -> int:
        """Calcula período ótimo de revisão baseado nas características da demanda"""
        # Fórmula simplificada baseada em Silver-Meal
        if demand_stats['mean'] <= 0:
            return 7
            
        # Considerar variabilidade e lead time
        base_period = np.sqrt(2 * self.params.setup_cost / 
                            (self.params.holding_cost_rate * demand_stats['mean'] * 100 / 365))
        
        # Ajustar por lead time
        adjusted_period = max(leadtime_days / 2, min(base_period, leadtime_days * 2))
        
        # Arredondar para dias úteis
        if adjusted_period <= 5:
            return 5  # Semanal
        elif adjusted_period <= 15:
            return 14  # Quinzenal
        elif adjusted_period <= 30:
            return 30  # Mensal
        else:
            return 60  # Bimestral
    
    def _get_strategy_name(self, leadtime_days: int) -> str:
        """Retorna nome da estratégia usada baseado no lead time"""
        if leadtime_days == 0:
            return 'Just-In-Time (JIT)'
        elif leadtime_days <= 3:
            return 'Short Lead Time Consolidation'
        elif leadtime_days <= 14:
            return 'Medium Lead Time (s,S) Policy'
        else:
            return 'Long Lead Time MRP'
    
    def _update_params(self, kwargs):
        """Atualiza parâmetros com valores fornecidos"""
        for key, value in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)
    
    def _prepare_demand_data(
        self, 
        daily_demands: Dict[str, float],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp
    ) -> pd.DataFrame:
        """Prepara dados de demanda em DataFrame pandas"""
        # Criar série temporal completa
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df = pd.DataFrame(index=date_range, columns=['demand'])
        df['demand'] = 0.0
        
        # Preencher com demandas fornecidas
        for date_str, daily_demand in daily_demands.items():
            year_month = pd.to_datetime(date_str + '-01')
            mask = (df.index.year == year_month.year) & (df.index.month == year_month.month)
            df.loc[mask, 'demand'] = daily_demand
            
        return df
    
    def _calculate_demand_statistics(self, demand_df: pd.DataFrame) -> Dict:
        """Calcula estatísticas de demanda"""
        daily_demands = demand_df['demand'].values
        
        # Remover zeros para cálculos mais precisos
        non_zero_demands = daily_demands[daily_demands > 0]
        
        if len(non_zero_demands) == 0:
            return {
                'mean': 0,
                'std': 0,
                'cv': 0,
                'total': 0,
                'max': 0,
                'min': 0,
                'trend': 0
            }
        
        return {
            'mean': np.mean(non_zero_demands),
            'std': np.std(non_zero_demands),
            'cv': np.std(non_zero_demands) / np.mean(non_zero_demands) if np.mean(non_zero_demands) > 0 else 0,
            'total': np.sum(daily_demands),
            'max': np.max(non_zero_demands),
            'min': np.min(non_zero_demands),
            'trend': self._calculate_trend(demand_df)
        }
    
    def _calculate_trend(self, demand_df: pd.DataFrame) -> float:
        """Calcula tendência da demanda"""
        if len(demand_df) < 2:
            return 0
            
        x = np.arange(len(demand_df))
        y = demand_df['demand'].values
        
        # Regressão linear simples
        if np.sum(y) > 0:
            slope, _ = np.polyfit(x, y, 1)
            return slope
        return 0
    
    def _calculate_eoq(self, annual_demand: float, setup_cost: float, holding_cost: float) -> float:
        """Calcula Economic Order Quantity"""
        if annual_demand <= 0 or setup_cost <= 0 or holding_cost <= 0:
            return self.params.min_batch_size
            
        eoq = np.sqrt(2 * annual_demand * setup_cost / holding_cost)
        
        # Aplicar restrições sensatas
        # EOQ não deve exceder 60 dias de demanda para evitar lotes muito grandes
        max_reasonable_eoq = annual_demand / 365 * 60  # 60 dias de demanda
        eoq = min(eoq, max_reasonable_eoq)
        
        # Aplicar limites configurados
        eoq = max(self.params.min_batch_size, min(self.params.max_batch_size, eoq))
        
        return eoq
    
    def _calculate_safety_stock(
        self, 
        demand_std: float,
        leadtime_days: int,
        service_level: float = None
    ) -> float:
        """Calcula estoque de segurança baseado no nível de serviço"""
        if service_level is None:
            service_level = self.params.service_level
            
        if demand_std <= 0 or leadtime_days <= 0:
            return 0
            
        # Z-score para o nível de serviço
        z_score = stats.norm.ppf(service_level)
        
        # Estoque de segurança = Z * σ * √LT
        safety_stock = z_score * demand_std * np.sqrt(leadtime_days)
        
        return safety_stock
    
    def _calculate_reorder_point(
        self,
        avg_demand: float,
        leadtime_days: int,
        safety_stock: float
    ) -> float:
        """Calcula ponto de pedido"""
        return (avg_demand * leadtime_days) + safety_stock
    
    def _jit_strategy(
        self,
        demand_df: pd.DataFrame,
        initial_stock: float,
        leadtime_days: int,
        demand_stats: Dict,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp
    ) -> List[BatchResult]:
        """Estratégia Just-In-Time para lead time zero"""
        batches = []
        current_stock = initial_stock
        last_arrival_date = demand_df.index[0]
        
        # Para JIT, fazemos pedidos diários ou consolidados em pequenos períodos
        consolidation_days = min(3, self.params.consolidation_window_days)
        
        current_date = demand_df.index[0]
        while current_date <= demand_df.index[-1]:
            # Calcular demanda para os próximos dias de consolidação
            end_consolidation = min(
                current_date + timedelta(days=consolidation_days - 1),
                demand_df.index[-1]
            )
            
            period_demand = demand_df.loc[current_date:end_consolidation, 'demand'].sum()
            
            if period_demand > current_stock:
                # Calcular consumo desde última chegada
                if batches:
                    consumption_period = demand_df.loc[last_arrival_date:current_date]
                    consumption_since_last = consumption_period['demand'].sum()
                else:
                    consumption_since_last = initial_stock - current_stock
                
                # Precisamos pedir
                quantity = period_demand - current_stock + (demand_stats['mean'] * self.params.safety_days)
                quantity = max(self.params.min_batch_size, quantity)
                
                if current_date >= start_cutoff:
                    batch = BatchResult(
                        order_date=current_date.strftime('%Y-%m-%d'),
                        arrival_date=current_date.strftime('%Y-%m-%d'),  # Lead time zero
                        quantity=round(quantity, 3),
                        analytics={
                            'stock_before_arrival': round(current_stock, 2),
                            'stock_after_arrival': round(current_stock + quantity, 2),
                            'consumption_since_last_arrival': round(consumption_since_last, 2),
                            'coverage_days': consolidation_days,
                            'actual_lead_time': 0,
                            'urgency_level': 'jit',
                            'production_start_delay': 0,
                            'arrival_delay': 0
                        }
                    )
                    batches.append(batch)
                    current_stock += quantity
                    last_arrival_date = current_date
            
            # Consumir estoque do período
            current_stock -= period_demand
            current_date = end_consolidation + timedelta(days=1)
            
        return batches
    
    def _short_leadtime_strategy(
        self,
        demand_df: pd.DataFrame,
        initial_stock: float,
        leadtime_days: int,
        demand_stats: Dict,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp
    ) -> List[BatchResult]:
        """Estratégia para lead time curto (1-3 dias)"""
        batches = []
        current_stock = initial_stock
        
        # Calcular parâmetros mais conservadores
        safety_stock = self._calculate_safety_stock(
            demand_stats['std'], leadtime_days
        )
        
        # Usar períodos menores para lead time curto
        review_period = min(3, max(1, leadtime_days))
        
        # EOQ baseado em demanda mais realista
        monthly_demand = demand_stats['mean'] * 30
        annual_demand = monthly_demand * 12
        
        if self.params.enable_eoq_optimization and annual_demand > 0:
            # Custo de manutenção mais realista
            unit_value = 100  # Valor unitário estimado
            holding_cost_per_unit = unit_value * self.params.holding_cost_rate
            
            eoq = self._calculate_eoq(
                annual_demand,
                self.params.setup_cost,
                holding_cost_per_unit
            )
            # Limitar EOQ para não ser muito grande
            max_reasonable_eoq = demand_stats['mean'] * 30  # Máximo 30 dias de demanda
            eoq = min(eoq, max_reasonable_eoq)
        else:
            # Fallback: 10-15 dias de cobertura
            eoq = demand_stats['mean'] * 12
        
        # Simular dia a dia para melhor controle
        pending_orders = []  # (arrival_date, quantity)
        
        for current_date in pd.date_range(demand_df.index[0], demand_df.index[-1], freq='D'):
            # Processar chegadas do dia
            arrived_today = [q for d, q in pending_orders if d == current_date]
            for qty in arrived_today:
                current_stock += qty
            pending_orders = [(d, q) for d, q in pending_orders if d != current_date]
            
            # Consumir demanda do dia
            daily_demand = demand_df.loc[current_date, 'demand']
            current_stock -= daily_demand
            
            # Calcular ponto de reposição dinâmico
            reorder_point = self._calculate_reorder_point(
                demand_stats['mean'], leadtime_days, safety_stock
            )
            
            # Verificar se precisa pedir (sem pedidos pendentes)
            has_pending = any(d <= current_date + timedelta(days=leadtime_days + 1) for d, _ in pending_orders)
            
            if current_stock <= reorder_point and not has_pending:
                # Calcular quantidade necessária
                # Estoque alvo = estoque de segurança + demanda do período de cobertura
                coverage_days = max(10, min(20, eoq / demand_stats['mean'])) if demand_stats['mean'] > 0 else 15
                target_stock = safety_stock + (demand_stats['mean'] * coverage_days)
                
                quantity = max(0, target_stock - current_stock)
                quantity = max(self.params.min_batch_size, min(self.params.max_batch_size, quantity))
                
                # Ajustar para múltiplos sensatos se necessário
                if quantity > demand_stats['mean'] * 45:  # Mais que 45 dias
                    quantity = demand_stats['mean'] * 30  # Limitar a 30 dias
                
                order_date = current_date
                arrival_date = order_date + timedelta(days=leadtime_days)
                
                if order_date >= start_cutoff and arrival_date <= end_cutoff:
                    # Estoque no momento da chegada (estimado)
                    demand_until_arrival = demand_stats['mean'] * leadtime_days
                    stock_at_arrival = current_stock - demand_until_arrival
                    
                    batch = BatchResult(
                        order_date=order_date.strftime('%Y-%m-%d'),
                        arrival_date=arrival_date.strftime('%Y-%m-%d'),
                        quantity=round(quantity, 3),
                        analytics={
                            'stock_before_arrival': round(stock_at_arrival, 2),
                            'stock_after_arrival': round(stock_at_arrival + quantity, 2),
                            'coverage_days': round(quantity / demand_stats['mean']) if demand_stats['mean'] > 0 else 0,
                            'actual_lead_time': leadtime_days,
                            'urgency_level': 'high' if current_stock < safety_stock else 'normal',
                            'reorder_point': round(reorder_point, 2),
                            'safety_stock': round(safety_stock, 2),
                            'current_stock_at_order': round(current_stock, 2)
                        }
                    )
                    batches.append(batch)
                    pending_orders.append((arrival_date, quantity))
                
        return batches
    
    def _medium_leadtime_strategy(
        self,
        demand_df: pd.DataFrame,
        initial_stock: float,
        leadtime_days: int,
        demand_stats: Dict,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp
    ) -> List[BatchResult]:
        """Estratégia para lead time médio (4-14 dias)"""
        batches = []
        
        # Para lead time médio, usar política (s,S)
        safety_stock = self._calculate_safety_stock(
            demand_stats['std'], leadtime_days
        )
        
        # Calcular s (ponto de reposição) e S (nível máximo)
        s = self._calculate_reorder_point(
            demand_stats['mean'], leadtime_days, safety_stock
        )
        
        # S baseado em EOQ + estoque de segurança
        annual_demand = demand_stats['mean'] * 365
        eoq = self._calculate_eoq(
            annual_demand,
            self.params.setup_cost,
            self.params.holding_cost_rate * demand_stats['mean']
        )
        S = s + eoq
        
        # Simular com programação dinâmica simplificada
        stock_levels = [initial_stock]
        dates = pd.date_range(demand_df.index[0], demand_df.index[-1], freq='D')
        
        pending_orders = []  # (arrival_date, quantity)
        
        for i, date in enumerate(dates):
            current_stock = stock_levels[-1]
            
            # Processar chegadas
            arrived_today = [q for d, q in pending_orders if d == date]
            for qty in arrived_today:
                current_stock += qty
            pending_orders = [(d, q) for d, q in pending_orders if d != date]
            
            # Consumir demanda
            daily_demand = demand_df.loc[date, 'demand']
            current_stock -= daily_demand
            
            # Verificar se precisa pedir
            if current_stock <= s and not any(d <= date + timedelta(days=leadtime_days) for d, _ in pending_orders):
                # Fazer pedido
                quantity = S - current_stock
                quantity = max(self.params.min_batch_size, min(self.params.max_batch_size, quantity))
                
                order_date = date
                arrival_date = date + timedelta(days=leadtime_days)
                
                if order_date >= start_cutoff and arrival_date <= end_cutoff:
                    batch = BatchResult(
                        order_date=order_date.strftime('%Y-%m-%d'),
                        arrival_date=arrival_date.strftime('%Y-%m-%d'),
                        quantity=round(quantity, 3),
                        analytics={
                            'stock_before_arrival': round(current_stock, 2),
                            'stock_after_arrival': round(current_stock + quantity, 2),
                            'coverage_days': round(quantity / demand_stats['mean']) if demand_stats['mean'] > 0 else 0,
                            'actual_lead_time': leadtime_days,
                            'urgency_level': 'high' if current_stock < safety_stock else 'normal',
                            's_reorder_point': round(s, 2),
                            'S_max_level': round(S, 2),
                            'safety_stock': round(safety_stock, 2)
                        }
                    )
                    batches.append(batch)
                    pending_orders.append((arrival_date, quantity))
                    
            stock_levels.append(max(0, current_stock))
            
        return batches
    
    def _long_leadtime_strategy(
        self,
        demand_df: pd.DataFrame,
        initial_stock: float,
        leadtime_days: int,
        demand_stats: Dict,
        start_cutoff: pd.Timestamp,
        end_cutoff: pd.Timestamp
    ) -> List[BatchResult]:
        """Estratégia para lead time longo (>14 dias) usando MRP clássico com lotes grandes"""
        batches = []
        
        # Para lead time longo, calcular necessidade total e fazer poucos lotes grandes
        total_demand = demand_df['demand'].sum()
        period_days = (demand_df.index[-1] - demand_df.index[0]).days + 1
        
        # Se o estoque inicial já cobre toda a demanda + margem, não precisa produzir
        safety_margin = demand_stats['mean'] * leadtime_days * 0.5  # 50% do consumo do lead time
        if initial_stock >= total_demand + safety_margin:
            return batches
        
        # Calcular quando o estoque vai acabar
        days_of_coverage = initial_stock / demand_stats['mean'] if demand_stats['mean'] > 0 else float('inf')
        stockout_date = demand_df.index[0] + pd.Timedelta(days=int(days_of_coverage))
        
        # Primeira produção deve chegar antes da ruptura
        first_arrival_date = min(stockout_date - pd.Timedelta(days=5), demand_df.index[-1])  # 5 dias de buffer
        first_order_date = first_arrival_date - pd.Timedelta(days=leadtime_days)
        
        # Se o primeiro pedido já passou, fazer pedido urgente
        if first_order_date < start_cutoff:
            first_order_date = start_cutoff
            first_arrival_date = first_order_date + pd.Timedelta(days=leadtime_days)
        
        # Calcular quantos lotes são necessários (máximo 3-4 lotes para período de 6 meses)
        max_batch_size = self.params.max_batch_size
        quantity_needed = total_demand + safety_margin - initial_stock
        
        if quantity_needed <= 0:
            return batches
            
        # Número de lotes baseado no tamanho máximo e lead time
        # Para lead time de 50 dias, máximo 2-3 lotes por período
        num_batches = min(3, max(1, int(np.ceil(quantity_needed / max_batch_size))))
        quantity_per_batch = quantity_needed / num_batches
        
        # Ajustar para múltiplos do lote mínimo
        quantity_per_batch = max(self.params.min_batch_size, 
                               np.ceil(quantity_per_batch / self.params.min_batch_size) * self.params.min_batch_size)
        
        # Criar os lotes com espaçamento adequado
        current_order_date = first_order_date
        current_stock_projection = initial_stock
        
        for i in range(num_batches):
            # Calcular quando fazer o pedido considerando produção sequencial
            if i > 0:
                # Próximo pedido só pode ser feito após o anterior terminar
                current_order_date = batches[-1].arrival_date
                current_order_date = pd.to_datetime(current_order_date) + pd.Timedelta(days=1)  # Dia seguinte
            
            arrival_date = current_order_date + pd.Timedelta(days=leadtime_days)
            
            # Verificar se está dentro do período válido
            if arrival_date > end_cutoff:
                break
            
            # Ajustar quantidade do último lote se necessário
            if i == num_batches - 1:
                remaining_need = max(0, total_demand + safety_margin - current_stock_projection - (quantity_per_batch * i))
                if remaining_need > 0:
                    quantity_per_batch = max(self.params.min_batch_size, remaining_need)
            
            batch = BatchResult(
                order_date=current_order_date.strftime('%Y-%m-%d'),
                arrival_date=arrival_date.strftime('%Y-%m-%d'),
                quantity=round(quantity_per_batch, 3),
                analytics={
                    'stock_before_arrival': round(current_stock_projection, 2),
                    'stock_after_arrival': round(current_stock_projection + quantity_per_batch, 2),
                    'coverage_days': round(quantity_per_batch / demand_stats['mean']) if demand_stats['mean'] > 0 else 0,
                    'actual_lead_time': leadtime_days,
                    'urgency_level': 'planned',
                    'batch_sequence': i + 1,
                    'total_batches_planned': num_batches,
                    'production_strategy': 'sequential_large_batches'
                }
            )
            batches.append(batch)
            current_stock_projection += quantity_per_batch
        
        return batches
    
    def _create_mrp_table(
        self,
        demand_subset: pd.DataFrame,
        initial_stock: float,
        leadtime_days: int,
        period_days: int
    ) -> List[Dict]:
        """Cria tabela MRP para planejamento"""
        mrp_records = []
        current_stock = initial_stock
        
        # Verificar se há dados suficientes
        if len(demand_subset) == 0:
            return mrp_records
        
        # Dividir em períodos
        periods = []
        for i in range(0, len(demand_subset), period_days):
            end_idx = min(i + period_days, len(demand_subset))
            period_demand = demand_subset.iloc[i:end_idx]['demand'].sum()
            period_start = demand_subset.index[i]
            periods.append({
                'start_date': period_start,
                'demand': period_demand
            })
        
        # Verificar se há períodos válidos
        if not periods:
            return mrp_records
            
        # Calcular necessidades
        period_demands = [p['demand'] for p in periods if p['demand'] > 0]
        if period_demands:
            safety_stock = self._calculate_safety_stock(
                np.std(period_demands),
                leadtime_days
            )
        else:
            # Se não há demanda, usar estoque de segurança mínimo
            safety_stock = self.params.min_batch_size * 0.1
        
        for i, period in enumerate(periods):
            gross_req = period['demand']
            projected_stock = current_stock - gross_req
            
            net_req = 0
            planned_order = 0
            
            # Só planejar pedido se realmente necessário
            # Considerar não apenas o estoque de segurança, mas também necessidades futuras
            if projected_stock < safety_stock:
                net_req = safety_stock - projected_stock
                
                # Lot sizing - usar múltiplos do tamanho mínimo
                lot_size = max(self.params.min_batch_size, net_req * 1.2)  # 20% extra
                planned_order = np.ceil(lot_size / self.params.min_batch_size) * self.params.min_batch_size
                planned_order = min(planned_order, self.params.max_batch_size)
            elif i == 0 and len(periods) > 1:
                # Para o primeiro período, verificar se precisará de reposição nos próximos períodos
                # mesmo que o estoque atual seja alto
                future_demand = sum(p['demand'] for p in periods[:min(3, len(periods))])  # Próximos 3 períodos
                if current_stock < future_demand:
                    net_req = future_demand - current_stock + safety_stock
                    lot_size = max(self.params.min_batch_size, net_req * 1.1)  # 10% extra
                    planned_order = np.ceil(lot_size / self.params.min_batch_size) * self.params.min_batch_size
                    planned_order = min(planned_order, self.params.max_batch_size)
                
            if planned_order > 0:
                # Calcular quando fazer o pedido
                order_date = period['start_date'] - timedelta(days=leadtime_days)
                arrival_date = period['start_date']
                
                # Verificar se as datas são válidas
                if order_date >= demand_subset.index[0] - timedelta(days=leadtime_days):
                    mrp_records.append({
                        'period_start': period['start_date'],
                        'gross_requirements': gross_req,
                        'projected_stock': projected_stock,
                        'net_requirements': net_req,
                        'planned_order': planned_order,
                        'order_date': order_date,
                        'arrival_date': arrival_date
                    })
                
                current_stock = projected_stock + planned_order
            else:
                current_stock = projected_stock
                
            # Proteção: se estoque é muito alto, não precisa processar mais períodos
            # MAS só aplicar isso se já processamos alguns períodos
            if i > 2 and current_stock > safety_stock * 10:  # 10x o estoque de segurança
                break
                
        return mrp_records
    
    def _consolidate_batches(
        self,
        batches: List[BatchResult],
        leadtime_days: int
    ) -> List[BatchResult]:
        """Consolida lotes próximos para reduzir setups"""
        if len(batches) <= 1:
            return batches
            
        consolidated = []
        i = 0
        
        while i < len(batches):
            current_batch = batches[i]
            
            # Verificar se pode consolidar com próximo
            if i + 1 < len(batches):
                next_batch = batches[i + 1]
                
                # Calcular gap entre pedidos
                current_date = pd.to_datetime(current_batch.order_date)
                next_date = pd.to_datetime(next_batch.order_date)
                gap_days = (next_date - current_date).days
                
                # Consolidar se gap é menor que janela de consolidação
                if gap_days <= self.params.consolidation_window_days:
                    # Criar lote consolidado
                    consolidated_quantity = current_batch.quantity + next_batch.quantity
                    
                    # Usar data mais cedo para garantir atendimento
                    consolidated_batch = BatchResult(
                        order_date=current_batch.order_date,
                        arrival_date=current_batch.arrival_date,
                        quantity=round(consolidated_quantity, 3),
                        analytics={
                            **current_batch.analytics,
                            'consolidated': bool(True),
                            'original_batches': int(2),
                            'consolidation_savings': float(self.params.setup_cost)
                        }
                    )
                    
                    consolidated.append(consolidated_batch)
                    i += 2  # Pular próximo lote já consolidado
                    continue
                    
            consolidated.append(current_batch)
            i += 1
            
        return consolidated
    
    def _update_batch_analytics(
        self,
        batches: List[BatchResult],
        demand_df: pd.DataFrame,
        initial_stock: float
    ) -> List[BatchResult]:
        """Atualiza analytics dos lotes com dados reais da simulação"""
        updated_batches = []
        current_stock = initial_stock
        
        # Simular evolução para capturar estados reais
        arrivals = {}
        for batch in batches:
            if batch.arrival_date in arrivals:
                arrivals[batch.arrival_date] += batch.quantity
            else:
                arrivals[batch.arrival_date] = batch.quantity
        
        # Mapear estoque por data
        stock_by_date = {}
        
        for date in demand_df.index:
            date_str = date.strftime('%Y-%m-%d')
            
            # Estoque antes das chegadas do dia
            stock_before_arrivals = current_stock
            
            # Adicionar chegadas
            if date_str in arrivals:
                current_stock += arrivals[date_str]
            
            # Estoque após chegadas
            stock_after_arrivals = current_stock
            
            # Consumir demanda
            daily_demand = demand_df.loc[date, 'demand']
            current_stock -= daily_demand
            
            stock_by_date[date_str] = {
                'before_arrivals': stock_before_arrivals,
                'after_arrivals': stock_after_arrivals,
                'end_of_day': current_stock
            }
        
        # Atualizar analytics de cada lote
        last_arrival_date = None
        for i, batch in enumerate(batches):
            arrival_date = batch.arrival_date
            
            # Dados do estoque na data de chegada
            stock_data = stock_by_date.get(arrival_date, {})
            stock_before = stock_data.get('before_arrivals', 0)
            stock_after = stock_data.get('after_arrivals', 0)
            
            # Calcular consumo desde última chegada
            if last_arrival_date and last_arrival_date in stock_by_date:
                consumption_since_last = self._calculate_consumption_between_dates(
                    demand_df, last_arrival_date, arrival_date
                )
            else:
                consumption_since_last = initial_stock - stock_before
            
            # Atualizar analytics
            updated_analytics = batch.analytics.copy()
            updated_analytics.update({
                'stock_before_arrival': round(stock_before, 2),
                'stock_after_arrival': round(stock_after, 2),
                'consumption_since_last_arrival': round(consumption_since_last, 2),
                'coverage_days': round(batch.quantity / demand_df['demand'].mean()) if demand_df['demand'].mean() > 0 else 0,
                'urgency_level': 'critical' if stock_before < 0 else 'high' if stock_before < 50 else 'normal'
            })
            
            # Criar novo lote com analytics atualizados
            updated_batch = BatchResult(
                order_date=batch.order_date,
                arrival_date=batch.arrival_date,
                quantity=batch.quantity,
                analytics=updated_analytics
            )
            updated_batches.append(updated_batch)
            last_arrival_date = arrival_date
            
        return updated_batches
    
    def _calculate_consumption_between_dates(
        self, 
        demand_df: pd.DataFrame, 
        start_date: str, 
        end_date: str
    ) -> float:
        """Calcula consumo entre duas datas (exclusivo-inclusivo)"""
        start_dt = pd.to_datetime(start_date) + timedelta(days=1)  # Dia seguinte
        end_dt = pd.to_datetime(end_date)  # Até o dia da chegada
        
        if start_dt > end_dt:
            return 0.0
            
        mask = (demand_df.index >= start_dt) & (demand_df.index <= end_dt)
        return demand_df.loc[mask, 'demand'].sum()
    
    def _calculate_analytics(
        self,
        batches: List[BatchResult],
        demand_df: pd.DataFrame,
        initial_stock: float,
        demand_stats: Dict
    ) -> Dict:
        """Calcula métricas analíticas do plano - compatível com formato PHP"""
        total_produced = sum(b.quantity for b in batches)
        total_demand = demand_df['demand'].sum()
        
        # Simular evolução do estoque com dicionário de datas
        stock_evolution_list = self._simulate_stock_evolution(
            batches, demand_df, initial_stock
        )
        
        # Converter para dicionário com formato de data string
        stock_evolution = {}
        for i, date in enumerate(demand_df.index):
            stock_evolution[date.strftime('%Y-%m-%d')] = round(stock_evolution_list[i], 2)
        
        # Encontrar mínimo e sua data
        min_stock = min(stock_evolution_list)
        min_stock_idx = stock_evolution_list.index(min_stock)
        min_stock_date = demand_df.index[min_stock_idx].strftime('%Y-%m-%d')
        
        # Calcular stock_consumed (diferença entre inicial e final + produção - demanda)
        stock_consumed = initial_stock - stock_evolution_list[-1] + total_produced - total_demand
        
        # Calcular pontos críticos
        critical_points = self._calculate_critical_points(
            stock_evolution, demand_stats['mean']
        )
        
        # Calcular production_efficiency
        production_efficiency = self._calculate_production_efficiency(
            batches, demand_df, demand_stats['mean']
        )
        
        # Calcular demand_analysis por mês
        demand_by_month = {}
        for date in demand_df.index:
            month_key = date.strftime('%Y-%m')
            if month_key not in demand_by_month:
                demand_by_month[month_key] = 0
            demand_by_month[month_key] += demand_df.loc[date, 'demand']
        
        # Arredondar valores
        demand_by_month = {k: round(v, 2) for k, v in demand_by_month.items()}
        
        # Calcular stock_end_of_period
        stock_end_of_period = self._calculate_stock_end_of_period(
            stock_evolution, batches, demand_stats['mean']
        )
        
        # Extrair order_dates
        order_dates = [b.order_date for b in batches]
        
        # Montar estrutura final compatível com PHP
        return {
            'summary': {
                'initial_stock': round(initial_stock, 2),
                'final_stock': round(stock_evolution_list[-1], 2),
                'minimum_stock': round(min_stock, 2),
                'minimum_stock_date': min_stock_date,
                'stockout_occurred': bool(min_stock < 0),
                'total_batches': len(batches),
                'total_produced': round(total_produced, 2),
                'production_coverage_rate': f"{round((total_produced / total_demand * 100), 0):.0f}%",
                'stock_consumed': round(stock_consumed, 2)
            },
            'stock_evolution': stock_evolution,
            'critical_points': critical_points,
            'production_efficiency': production_efficiency,
            'demand_analysis': {
                'total_demand': round(total_demand, 2),
                'average_daily_demand': round(demand_stats['mean'], 2),
                'demand_by_month': demand_by_month,
                'period_days': len(demand_df)
            },
            'stock_end_of_period': stock_end_of_period,
            'order_dates': order_dates
        }
    
    def _simulate_stock_evolution(
        self,
        batches: List[BatchResult],
        demand_df: pd.DataFrame,
        initial_stock: float
    ) -> List[float]:
        """Simula evolução do estoque ao longo do tempo"""
        stock_levels = []
        current_stock = initial_stock
        
        # Criar dicionário de chegadas
        arrivals = {}
        for batch in batches:
            arrival_date = batch.arrival_date
            if arrival_date in arrivals:
                arrivals[arrival_date] += batch.quantity
            else:
                arrivals[arrival_date] = batch.quantity
        
        for date in demand_df.index:
            date_str = date.strftime('%Y-%m-%d')
            
            # Primeiro: adicionar chegadas do dia
            if date_str in arrivals:
                current_stock += arrivals[date_str]
                
            # Segundo: consumir demanda do dia
            daily_demand = demand_df.loc[date, 'demand']
            current_stock -= daily_demand
            
            # Registrar estoque ao final do dia
            stock_levels.append(current_stock)
            
        return stock_levels
    
    def _estimate_total_cost(
        self,
        batches: List[BatchResult],
        avg_stock: float,
        stockouts: int,
        demand_stats: Dict
    ) -> Dict:
        """Estima custo total da política"""
        # Custo de setup/pedido
        setup_cost = len(batches) * self.params.setup_cost
        
        # Custo de manutenção (assumindo valor unitário médio)
        # Nota: Em produção real, você passaria o valor unitário do produto
        unit_value = 100  # Valor placeholder
        holding_cost = avg_stock * unit_value * self.params.holding_cost_rate / 365 * 184  # ~6 meses
        
        # Custo de falta
        stockout_cost = stockouts * demand_stats['mean'] * unit_value * self.params.stockout_cost_multiplier
        
        total_cost = setup_cost + holding_cost + stockout_cost
        
        return {
            'total_cost': round(total_cost, 2),
            'setup_cost': round(setup_cost, 2),
            'holding_cost': round(holding_cost, 2),
            'stockout_cost': round(stockout_cost, 2),
            'cost_breakdown_percentage': {
                'setup': round(setup_cost / total_cost * 100, 1) if total_cost > 0 else 0,
                'holding': round(holding_cost / total_cost * 100, 1) if total_cost > 0 else 0,
                'stockout': round(stockout_cost / total_cost * 100, 1) if total_cost > 0 else 0
            }
        }
    
    def _calculate_critical_points(
        self, 
        stock_evolution: Dict[str, float],
        avg_daily_demand: float
    ) -> List[Dict]:
        """Calcula pontos críticos no estoque"""
        critical_points = []
        
        for date, stock in stock_evolution.items():
            days_of_coverage = round(stock / avg_daily_demand, 1) if avg_daily_demand > 0 else 0
            
            # Definir severidade baseada em dias de cobertura
            if stock < 0:
                severity = 'stockout'
            elif days_of_coverage < 5:
                severity = 'critical'
            elif days_of_coverage < 10:
                severity = 'warning'
            else:
                continue  # Não é ponto crítico
                
            critical_points.append({
                'date': date,
                'stock': round(stock, 2),
                'days_of_coverage': days_of_coverage,
                'severity': severity
            })
            
        return critical_points
    
    def _calculate_production_efficiency(
        self,
        batches: List[BatchResult],
        demand_df: pd.DataFrame,
        avg_daily_demand: float
    ) -> Dict:
        """Calcula métricas de eficiência de produção"""
        if len(batches) == 0:
            return {
                'average_batch_size': 0,
                'production_line_utilization': 0,
                'production_gaps': [],
                'lead_time_compliance': 100
            }
            
        total_produced = sum(b.quantity for b in batches)
        
        # Calcular gaps entre produções
        production_gaps = []
        for i in range(len(batches) - 1):
            current_arrival = pd.to_datetime(batches[i].arrival_date)
            next_order = pd.to_datetime(batches[i + 1].order_date)
            gap_days = (next_order - current_arrival).days
            
            gap_type = 'continuous' if gap_days == 0 else ('overlap' if gap_days < 0 else 'idle')
            
            production_gaps.append({
                'from_batch': i + 1,
                'to_batch': i + 2,
                'gap_days': gap_days,
                'gap_type': gap_type
            })
        
        # Calcular utilização da linha
        start_date = pd.to_datetime(demand_df.index[0])
        end_date = pd.to_datetime(demand_df.index[-1])
        total_days = (end_date - start_date).days
        
        production_days = 0
        for batch in batches:
            order_date = pd.to_datetime(batch.order_date)
            arrival_date = pd.to_datetime(batch.arrival_date)
            production_days += (arrival_date - order_date).days
            
        utilization = round((production_days / total_days * 100), 2) if total_days > 0 else 0
        
        # Lead time compliance (assumindo que todos os lotes cumprem o lead time esperado)
        lead_time_compliance = 100
        
        return {
            'average_batch_size': round(total_produced / len(batches), 2),
            'production_line_utilization': utilization,
            'production_gaps': production_gaps,
            'lead_time_compliance': lead_time_compliance
        }
    
    def _calculate_stock_end_of_period(
        self,
        stock_evolution: Dict[str, float],
        batches: List[BatchResult],
        avg_daily_demand: float
    ) -> Dict:
        """Calcula estoque ao final de cada período"""
        result = {
            'monthly': [],
            'after_batch_arrival': [],
            'before_batch_arrival': []
        }
        
        # Agrupar por mês
        monthly_stocks = {}
        for date, stock in stock_evolution.items():
            month = date[:7]  # YYYY-MM
            monthly_stocks[month] = {
                'date': date,
                'stock': stock
            }
        
        # Pegar último dia de cada mês
        for month, data in monthly_stocks.items():
            result['monthly'].append({
                'period': month,
                'end_date': data['date'],
                'stock': round(data['stock'], 2),
                'days_of_coverage': round(data['stock'] / avg_daily_demand, 1) if avg_daily_demand > 0 else 0
            })
        
        # Estoque após chegada de cada lote
        for i, batch in enumerate(batches):
            batch_number = i + 1
            arrival_date = batch.arrival_date
            
            if arrival_date in stock_evolution:
                stock_after = stock_evolution[arrival_date]
                stock_before = batch.analytics.get('stock_before_arrival', 0)
                
                result['after_batch_arrival'].append({
                    'batch_number': batch_number,
                    'date': arrival_date,
                    'stock_before': round(stock_before, 2),
                    'batch_quantity': round(batch.quantity, 3),
                    'stock_after': round(stock_after, 2),
                    'coverage_gained': batch.analytics.get('coverage_days', 0)
                })
        
        # Estoque antes da chegada do próximo lote
        for i in range(len(batches) - 1):
            next_batch_date = batches[i + 1].arrival_date
            day_before = (pd.to_datetime(next_batch_date) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            if day_before in stock_evolution:
                result['before_batch_arrival'].append({
                    'before_batch': i + 2,
                    'date': day_before,
                    'stock': round(stock_evolution[day_before], 2),
                    'days_until_arrival': 1
                })
        
        return result
    
    def _batch_to_dict(self, batch: BatchResult) -> Dict:
        """Converte BatchResult para dicionário compatível com PHP"""
        # Garantir que analytics tenha os campos esperados
        analytics = batch.analytics.copy()
        
        # Adicionar campos obrigatórios se não existirem
        default_fields = {
            'stock_before_arrival': 0,
            'stock_after_arrival': 0,
            'consumption_since_last_arrival': 0,
            'coverage_days': 0,
            'actual_lead_time': 0,
            'urgency_level': 'normal',
            'production_start_delay': 0,
            'arrival_delay': 0
        }
        
        for field, default_value in default_fields.items():
            if field not in analytics:
                analytics[field] = default_value
        
        return {
            'order_date': batch.order_date,
            'arrival_date': batch.arrival_date,
            'quantity': batch.quantity,
            'analytics': analytics
        }

    def calculate_batches_for_sporadic_demand(
        self,
        sporadic_demand: Dict[str, float],
        initial_stock: float,
        leadtime_days: int,
        period_start_date: str,
        period_end_date: str,
        start_cutoff_date: str,
        end_cutoff_date: str,
        safety_margin_percent: float = 8.0,
        safety_days: int = 2,
        minimum_stock_percent: float = 0.0,
        max_gap_days: int = 999,
        **kwargs
    ) -> Dict:
        """
        Planeja lotes para atender demanda esporádica em datas específicas.
        Versão otimizada da função PHP com algoritmos de supply chain.
        
        Args:
            sporadic_demand: Dict {"YYYY-MM-DD": quantidade específica nesta data}
            initial_stock: Estoque disponível no dia anterior ao início do período
            leadtime_days: Lead time (em dias) entre pedido e chegada
            period_start_date: Data inicial do período de cobertura ("YYYY-MM-DD")
            period_end_date: Data final do período de cobertura ("YYYY-MM-DD")
            start_cutoff_date: Data de corte para início dos pedidos ("YYYY-MM-DD")
            end_cutoff_date: Data de corte para fim das produções ("YYYY-MM-DD")
            safety_margin_percent: Margem de segurança padrão (%)
            safety_days: Dias de segurança padrão
            minimum_stock_percent: % da maior demanda como estoque mínimo
            max_gap_days: Gap máximo entre lotes (999 = sem limite)
            
        Returns:
            Dict com 'batches' e 'analytics' compatível com formato PHP
        """
        # Atualizar parâmetros com kwargs
        self._update_params(kwargs)
        
        # Converter datas para pandas Timestamp
        start_period = pd.to_datetime(period_start_date)
        end_period = pd.to_datetime(period_end_date)
        start_cutoff = pd.to_datetime(start_cutoff_date)
        end_cutoff = pd.to_datetime(end_cutoff_date)
        
        # Filtrar e ordenar demandas válidas dentro do período
        valid_demands = {}
        for date_str, quantity in sporadic_demand.items():
            demand_date = pd.to_datetime(date_str)
            if start_period <= demand_date <= end_period:
                valid_demands[date_str] = float(quantity)
        
        # Ordenar por data
        valid_demands = dict(sorted(valid_demands.items()))
        
        if not valid_demands:
            # Retorno padrão se não há demandas válidas
            return clean_for_json({
                'batches': [],
                'analytics': {
                    'summary': {
                        'initial_stock': round(initial_stock, 2),
                        'final_stock': round(initial_stock, 2),
                        'minimum_stock': round(initial_stock, 2),
                        'minimum_stock_date': period_start_date,
                        'stockout_occurred': False,
                        'total_batches': 0,
                        'total_produced': 0.0,
                        'production_coverage_rate': '0%',
                        'stock_consumed': 0.0,
                        'demand_fulfillment_rate': 100.0,
                        'demands_met_count': 0,
                        'demands_unmet_count': 0,
                        'unmet_demand_details': [],
                        'average_batch_per_demand': 0
                    },
                    'stock_evolution': {},
                    'critical_points': [],
                    'production_efficiency': {
                        'average_batch_size': 0,
                        'production_line_utilization': 0,
                        'production_gaps': [],
                        'lead_time_compliance': 100
                    },
                    'demand_analysis': {
                        'total_demand': 0.0,
                        'average_daily_demand': 0.0,
                        'demand_by_month': {},
                        'period_days': (end_period - start_period).days + 1,
                        'demand_events': 0,
                        'average_demand_per_event': 0.0,
                        'first_demand_date': None,
                        'last_demand_date': None,
                        'demand_distribution': {}
                    },
                    'sporadic_demand_metrics': {
                        'demand_concentration': {'concentration_index': 0, 'concentration_level': 'low'},
                        'interval_statistics': {
                            'average_interval_days': 0,
                            'min_interval_days': 0,
                            'max_interval_days': 0,
                            'interval_variance': 0
                        },
                        'demand_predictability': 'high',
                        'peak_demand_analysis': {
                            'peak_count': 0,
                            'peak_threshold': 0,
                            'peak_dates': [],
                            'average_peak_size': 0
                        }
                    }
                }
            })
        
        # Calcular estatísticas básicas
        total_demand = sum(valid_demands.values())
        period_days = (end_period - start_period).days + 1
        avg_daily_demand = total_demand / period_days if period_days > 0 else 0
        demand_dates = list(valid_demands.keys())
        
        # Análise de intervalos entre demandas
        demand_intervals = self._calculate_demand_intervals(demand_dates)
        
        # Análise de demanda por mês
        demand_by_month = self._group_demand_by_month(valid_demands)
        
        # Calcular estoque mínimo absoluto
        max_demand = max(valid_demands.values()) if valid_demands else 0
        absolute_minimum_stock = max_demand * (minimum_stock_percent / 100)
        
        # Planejar lotes usando algoritmo otimizado
        batches = self._plan_sporadic_batches(
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
        
        # Calcular evolução do estoque
        stock_evolution = self._calculate_sporadic_stock_evolution(
            initial_stock, valid_demands, batches, start_period, end_period
        )
        
        # Calcular métricas analíticas completas
        analytics = self._calculate_sporadic_analytics(
            batches=batches,
            valid_demands=valid_demands,
            initial_stock=initial_stock,
            stock_evolution=stock_evolution,
            demand_intervals=demand_intervals,
            demand_by_month=demand_by_month,
            avg_daily_demand=avg_daily_demand,
            period_days=period_days,
            total_demand=total_demand,
            demand_dates=demand_dates,
            start_period=start_period,
            end_period=end_period
        )
        
        # Atualizar analytics dos lotes com cobertura de demandas
        batches_with_coverage = self._update_sporadic_batch_analytics_with_coverage(
            batches, valid_demands, initial_stock, start_period
        )
        
        # Limpar resultado para compatibilidade JSON/PHP
        result = {
            'batches': [self._sporadic_batch_to_dict(b) for b in batches_with_coverage],
            'analytics': analytics
        }
        
        return clean_for_json(result)

    def _calculate_demand_intervals(self, demand_dates: List[str]) -> List[int]:
        """Calcula intervalos entre demandas consecutivas"""
        intervals = []
        for i in range(1, len(demand_dates)):
            prev_date = pd.to_datetime(demand_dates[i-1])
            curr_date = pd.to_datetime(demand_dates[i])
            interval = (curr_date - prev_date).days
            intervals.append(interval)
        return intervals
    
    def _group_demand_by_month(self, valid_demands: Dict[str, float]) -> Dict[str, float]:
        """Agrupa demandas por mês"""
        demand_by_month = {}
        for date_str, quantity in valid_demands.items():
            year_month = date_str[:7]  # YYYY-MM
            demand_by_month[year_month] = demand_by_month.get(year_month, 0) + quantity
        return {k: round(v, 2) for k, v in demand_by_month.items()}
    
    def _plan_sporadic_batches(
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
        """Algoritmo otimizado para planejar lotes esporádicos com agrupamento inteligente"""
        
        # Verificar se consolidação está habilitada
        if hasattr(self.params, 'enable_consolidation') and self.params.enable_consolidation:
            return self._plan_sporadic_batches_with_intelligent_grouping(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, max_gap_days
            )
        else:
            # Usar algoritmo original
            return self._plan_sporadic_batches_original(
                valid_demands, initial_stock, leadtime_days, start_period, end_period,
                start_cutoff, end_cutoff, safety_days, safety_margin_percent, 
                absolute_minimum_stock, max_gap_days
            )

    def _plan_sporadic_batches_with_intelligent_grouping(
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
        """Algoritmo otimizado com prevenção de stockout para lead times longos"""
        
        if not valid_demands:
            return []
        
        # Analisar grupos de consolidação
        demand_groups = self._analyze_demand_groups_for_consolidation(
            valid_demands, leadtime_days, safety_days, max_gap_days
        )
        
        # NOVA LÓGICA: Detectar cenários críticos de lead time longo
        long_leadtime_threshold = 45  # Dias
        is_long_leadtime = leadtime_days >= long_leadtime_threshold
        
        # Calcular estoque crítico baseado no lead time
        total_demand = sum(valid_demands.values())
        avg_daily_demand = total_demand / len(valid_demands) if valid_demands else 0
        
        # Para lead times longos, ser mais conservador
        if is_long_leadtime:
            critical_stock_level = max(
                avg_daily_demand * (leadtime_days + safety_days),  # Cobertura para lead time
                total_demand * 0.3  # Mínimo 30% da demanda total
            )
        else:
            critical_stock_level = avg_daily_demand * (leadtime_days + safety_days)
        
        batches = []
        current_stock = initial_stock
        
        # NOVA LÓGICA: Simulação detalhada de estoque para detectar gaps perigosos
        stock_simulation = self._simulate_stock_evolution_for_sporadic(
            valid_demands, initial_stock, demand_groups, leadtime_days, safety_days
        )
        
        # Detectar períodos de risco
        critical_periods = self._detect_critical_periods(stock_simulation, critical_stock_level)
        
        # Se há períodos críticos, ajustar grupos ou criar lotes intermediários
        if critical_periods and is_long_leadtime:
            demand_groups = self._adjust_groups_for_critical_periods(
                demand_groups, critical_periods, valid_demands, leadtime_days, safety_days
            )
        
        # Ordenar grupos por data da primeira demanda
        demand_groups.sort(key=lambda g: min(pd.to_datetime(date) for date in g['demand_dates']))
        
        for group in demand_groups:
            # Calcular data alvo para o grupo (primeira demanda)
            primary_date = pd.to_datetime(group['primary_demand_date'])
            target_arrival_date = primary_date - pd.Timedelta(days=safety_days)
            
            # Data do pedido considerando lead time
            order_date = target_arrival_date - pd.Timedelta(days=leadtime_days)
            
            # Verificar se o pedido pode ser feito dentro do período de planejamento
            if order_date < start_cutoff:
                # Ajustar para o início do período de planejamento
                order_date = start_cutoff
                actual_arrival_date = order_date + pd.Timedelta(days=leadtime_days)
            else:
                actual_arrival_date = target_arrival_date
            
            # Calcular déficit até a chegada do lote
            stock_before_arrival = self._calculate_stock_at_date(
                batches, current_stock, valid_demands, actual_arrival_date
            )
            
            # NOVA LÓGICA: Para lead times longos, ser mais agressivo na quantidade
            group_demand = group['total_demand']
            shortfall = max(0, group_demand - stock_before_arrival)
            
            if is_long_leadtime:
                # CORREÇÃO CRÍTICA: Para lead times longos, calcular cobertura mais ampla
                remaining_demands_after_group = []
                group_dates_set = set(group['demand_dates'])
                
                # Encontrar próxima demanda após este grupo
                next_demand_date = None
                for date_str in sorted(valid_demands.keys()):
                    if date_str not in group_dates_set and pd.to_datetime(date_str) > actual_arrival_date:
                        next_demand_date = pd.to_datetime(date_str)
                        break
                
                # Se há próxima demanda, calcular gap
                if next_demand_date:
                    gap_to_next = (next_demand_date - actual_arrival_date).days
                    
                    # Se o gap é maior que o lead time, precisamos de mais estoque
                    if gap_to_next > leadtime_days:
                        # Calcular quantas demandas futuras precisamos cobrir
                        coverage_window = min(gap_to_next + leadtime_days, 120)  # Máximo 120 dias
                        future_demand_in_coverage = 0
                        
                        for date_str, qty in valid_demands.items():
                            if date_str not in group_dates_set:
                                demand_date = pd.to_datetime(date_str)
                                days_from_arrival = (demand_date - actual_arrival_date).days
                                if 0 < days_from_arrival <= coverage_window:
                                    # Fator de importância decrescente com distância
                                    coverage_factor = max(0.2, 1 - (days_from_arrival / coverage_window))
                                    future_demand_in_coverage += qty * coverage_factor
                        
                        # Buffer crítico para lead times longos
                        critical_buffer = group_demand * 0.5  # 50% extra para segurança
                        lead_time_safety = avg_daily_demand * min(leadtime_days * 0.3, 45)
                        
                        batch_quantity = (shortfall + 
                                        group_demand * (safety_margin_percent / 100) +
                                        critical_buffer +
                                        lead_time_safety +
                                        future_demand_in_coverage)
                    else:
                        # Gap normal, usar lógica padrão melhorada
                        safety_buffer = group_demand * (safety_margin_percent / 100)
                        lead_time_buffer = avg_daily_demand * min(leadtime_days * 0.2, 30)
                        future_demand = self._calculate_future_demand_in_window(
                            valid_demands, actual_arrival_date, min(leadtime_days + 30, 90), group['demand_dates']
                        )
                        batch_quantity = shortfall + safety_buffer + lead_time_buffer + (future_demand * 0.4)
                else:
                    # Último grupo ou sem demandas futuras
                    safety_buffer = group_demand * (safety_margin_percent / 100)
                    lead_time_buffer = avg_daily_demand * min(leadtime_days * 0.2, 30)
                    batch_quantity = shortfall + safety_buffer + lead_time_buffer
            else:
                batch_quantity = self._calculate_optimal_sporadic_batch_quantity(
                    shortfall=shortfall,
                    valid_demands=valid_demands,
                    target_demand_date=group['primary_demand_date'],
                    arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
                    projected_stock=stock_before_arrival,
                    existing_batches=batches,
                    initial_stock=initial_stock,
                    safety_margin_percent=safety_margin_percent
                )
            
            # Aplicar limites
            batch_quantity = max(batch_quantity, getattr(self.params, 'min_batch_size', 200))
            batch_quantity = min(batch_quantity, getattr(self.params, 'max_batch_size', 15000))
            
            # Criar analytics do lote
            batch_analytics = self._create_sporadic_batch_analytics(
                demand_date_str=group['primary_demand_date'],
                demand_quantity=group_demand,
                shortfall=shortfall,
                batch_quantity=batch_quantity,
                stock_before_arrival=stock_before_arrival,
                actual_arrival_date=actual_arrival_date,
                target_arrival_date=target_arrival_date,
                leadtime_days=leadtime_days,
                safety_days=safety_days
            )
            
            # Adicionar informações específicas de consolidação
            if len(group['demand_dates']) > 1:
                batch_analytics['consolidated_group'] = True
                batch_analytics['group_size'] = len(group['demand_dates'])
                batch_analytics['demands_covered'] = [
                    {'date': date, 'quantity': valid_demands.get(date, 0)} 
                    for date in group['demand_dates']
                ]
                batch_analytics['consolidation_savings'] = group.get('consolidation_savings', 0)
                batch_analytics['holding_cost_increase'] = group.get('holding_cost_increase', 0)
                batch_analytics['operational_benefits'] = group.get('operational_benefits', 0)
                batch_analytics['lead_time_efficiency'] = group.get('lead_time_efficiency', 0)
                batch_analytics['overlap_prevention'] = group.get('lead_time_efficiency', 0) > 0
                batch_analytics['consolidation_quality'] = 'high' if group.get('operational_benefits', 0) > 0 else 'medium'
                batch_analytics['net_savings'] = (
                    group.get('consolidation_savings', 0) + 
                    group.get('operational_benefits', 0) - 
                    group.get('holding_cost_increase', 0)
                )
            else:
                batch_analytics['consolidated_group'] = False
            
            # NOVA INFORMAÇÃO: Marcar se é lote para lead time longo
            if is_long_leadtime:
                batch_analytics['long_leadtime_optimization'] = True
                batch_analytics['critical_stock_level'] = critical_stock_level
                batch_analytics['future_demand_considered'] = future_demand if 'future_demand' in locals() else 0
            
            # Criar resultado do lote
            batch = BatchResult(
                order_date=order_date.strftime('%Y-%m-%d'),
                arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
                quantity=round(batch_quantity, 3),
                analytics=batch_analytics
            )
            
            batches.append(batch)
            
            # Atualizar estoque simulado
            current_stock = stock_before_arrival + batch_quantity
        
        # NOVA VALIDAÇÃO: Verificar se ainda há riscos de stockout
        final_validation = self._validate_no_stockout_risk(
            batches, initial_stock, valid_demands, leadtime_days
        )
        
        if not final_validation['is_safe'] and is_long_leadtime:
            # Criar lote de emergência se necessário
            emergency_batch = self._create_emergency_batch_if_needed(
                final_validation, batches, valid_demands, leadtime_days, start_cutoff, safety_days
            )
            if emergency_batch:
                batches.append(emergency_batch)
                batches.sort(key=lambda b: pd.to_datetime(b.arrival_date))
        
        return batches

    def _plan_sporadic_batches_original(
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
        """Algoritmo original para planejar lotes esporádicos (mantido para compatibilidade)"""
        batches = []
        production_line_available = start_cutoff
        
        for demand_date_str, demand_quantity in valid_demands.items():
            demand_date = pd.to_datetime(demand_date_str)
            
            # Calcular estoque projetado na data da demanda
            projected_stock = self._calculate_projected_stock_sporadic(
                initial_stock, valid_demands, batches, demand_date_str, start_period
            )
            
            # Verificar se precisa de lote
            stock_after_demand = projected_stock - demand_quantity
            needs_batch = (
                projected_stock < demand_quantity or 
                stock_after_demand < absolute_minimum_stock
            )
            
            if needs_batch:
                # Calcular déficit
                shortfall = max(
                    demand_quantity - max(0, projected_stock),
                    absolute_minimum_stock - max(0, stock_after_demand)
                )
                
                # Determinar datas de chegada e produção
                target_arrival_date = demand_date - timedelta(days=safety_days)
                if target_arrival_date > demand_date:
                    target_arrival_date = demand_date
                if target_arrival_date < start_period:
                    target_arrival_date = start_period
                    
                target_order_date = target_arrival_date - timedelta(days=leadtime_days)
                actual_order_date = max(production_line_available, target_order_date)
                
                if actual_order_date < start_cutoff:
                    actual_order_date = start_cutoff
                    
                actual_arrival_date = actual_order_date + timedelta(days=leadtime_days)
                
                # Verificar viabilidade
                if actual_arrival_date > end_cutoff:
                    days_after_cutoff = (actual_arrival_date - end_cutoff).days
                    if days_after_cutoff > 30:  # Limite de tolerância
                        continue
                
                # Calcular quantidade otimizada do lote
                batch_quantity = self._calculate_optimal_sporadic_batch_quantity(
                    shortfall=shortfall,
                    valid_demands=valid_demands,
                    target_demand_date=demand_date_str,
                    arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
                    projected_stock=projected_stock,
                    existing_batches=batches,
                    initial_stock=initial_stock,
                    safety_margin_percent=safety_margin_percent
                )
                
                # Calcular métricas do lote
                stock_before_arrival = self._calculate_projected_stock_sporadic(
                    initial_stock, valid_demands, batches, 
                    actual_arrival_date.strftime('%Y-%m-%d'), start_period
                )
                
                # Criar analytics do lote
                batch_analytics = self._create_sporadic_batch_analytics(
                    demand_date_str=demand_date_str,
                    demand_quantity=demand_quantity,
                    shortfall=shortfall,
                    batch_quantity=batch_quantity,
                    stock_before_arrival=stock_before_arrival,
                    actual_arrival_date=actual_arrival_date,
                    target_arrival_date=target_arrival_date,
                    leadtime_days=leadtime_days,
                    safety_days=safety_days
                )
                
                # Criar resultado do lote
                batch = BatchResult(
                    order_date=actual_order_date.strftime('%Y-%m-%d'),
                    arrival_date=actual_arrival_date.strftime('%Y-%m-%d'),
                    quantity=round(batch_quantity, 3),
                    analytics=batch_analytics
                )
                
                batches.append(batch)
                
                # Atualizar disponibilidade da linha
                production_line_available = actual_order_date + timedelta(days=1)
        
        return batches

    def _calculate_projected_stock_sporadic(
        self,
        initial_stock: float,
        valid_demands: Dict[str, float],
        existing_batches: List[BatchResult],
        target_date: str,
        start_period: pd.Timestamp
    ) -> float:
        """Calcula estoque projetado para uma data específica"""
        current_stock = initial_stock
        target_dt = pd.to_datetime(target_date)
        current_date = start_period
        
        # Criar mapa de chegadas
        arrivals = {}
        for batch in existing_batches:
            arrival_date = batch.arrival_date
            if arrival_date not in arrivals:
                arrivals[arrival_date] = 0
            arrivals[arrival_date] += batch.quantity
        
        # Simular até a data alvo
        while current_date < target_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Adicionar chegadas
            if date_str in arrivals:
                current_stock += arrivals[date_str]
                
            # Subtrair demanda
            if date_str in valid_demands:
                current_stock -= valid_demands[date_str]
                
            current_date += timedelta(days=1)
            
        return current_stock
    
    def _calculate_optimal_sporadic_batch_quantity(
        self,
        shortfall: float,
        valid_demands: Dict[str, float],
        target_demand_date: str,
        arrival_date: str,
        projected_stock: float,
        existing_batches: List[BatchResult],
        initial_stock: float,
        safety_margin_percent: float
    ) -> float:
        """Calcula quantidade otimizada considerando demandas futuras"""
        base_quantity = shortfall
        
        # Aplicar margem de segurança
        safety_margin = base_quantity * (safety_margin_percent / 100)
        quantity_with_safety = base_quantity + safety_margin
        
        # Considerar demandas futuras próximas (próximos 30 dias)
        arrival_dt = pd.to_datetime(arrival_date)
        future_demand = 0
        
        for demand_date_str, demand_qty in valid_demands.items():
            demand_dt = pd.to_datetime(demand_date_str)
            days_after_arrival = (demand_dt - arrival_dt).days
            
            if 0 < days_after_arrival <= 30:  # Próximos 30 dias
                future_demand += demand_qty
        
        # Considerar uma fração da demanda futura
        future_demand_factor = min(0.3, future_demand / base_quantity) if base_quantity > 0 else 0
        
        # Quantidade final otimizada
        optimal_quantity = quantity_with_safety + (future_demand * future_demand_factor)
        
        # Aplicar limites mínimos e máximos
        optimal_quantity = max(optimal_quantity, self.params.min_batch_size)
        optimal_quantity = min(optimal_quantity, self.params.max_batch_size)
        
        return optimal_quantity
    
    def _calculate_demands_covered_sporadic(
        self,
        batch: BatchResult,
        valid_demands: Dict[str, float],
        initial_stock: float,
        existing_batches: List[BatchResult],
        start_period: pd.Timestamp
    ) -> List[Dict]:
        """
        Calcula quais demandas específicas este lote está cobrindo.
        Retorna lista de objetos com date e quantity das demandas cobertas por este lote.
        """
        demands_covered = []
        arrival_date = pd.to_datetime(batch.arrival_date)
        
        # Simular estoque até a chegada do lote
        current_stock = self._calculate_projected_stock_sporadic(
            initial_stock, valid_demands, existing_batches, batch.arrival_date, start_period
        )
        
        # Adicionar quantidade do lote atual
        current_stock += batch.quantity
        
        # Verificar demandas após a chegada do lote, em ordem cronológica
        future_demands = {}
        for date_str, quantity in valid_demands.items():
            demand_date = pd.to_datetime(date_str)
            if demand_date >= arrival_date:
                future_demands[date_str] = quantity
        
        # Ordenar demandas futuras por data
        sorted_future_demands = dict(sorted(future_demands.items()))
        
        # Determinar quais demandas este lote pode cobrir
        for demand_date_str, demand_qty in sorted_future_demands.items():
            if current_stock >= demand_qty:
                demands_covered.append({
                    "date": demand_date_str,
                    "quantity": round(demand_qty, 2)
                })
                current_stock -= demand_qty
            else:
                # Se não consegue cobrir completamente, ainda pode cobrir parcialmente
                # Mas para simplicidade, vamos considerar apenas cobertura completa
                break
        
        return demands_covered

    def _update_sporadic_batch_analytics_with_coverage(
        self,
        batches: List[BatchResult],
        valid_demands: Dict[str, float],
        initial_stock: float,
        start_period: pd.Timestamp
    ) -> List[BatchResult]:
        """
        Atualiza os analytics dos lotes esporádicos com informações de cobertura,
        incluindo demands_covered para cada lote.
        """
        updated_batches = []
        
        for i, batch in enumerate(batches):
            # Lotes existentes até este ponto (não incluindo o atual)
            existing_batches = batches[:i]
            
            # Calcular demandas cobertas por este lote
            demands_covered = self._calculate_demands_covered_sporadic(
                batch, valid_demands, initial_stock, existing_batches, start_period
            )
            
            # Atualizar analytics
            updated_analytics = batch.analytics.copy()
            updated_analytics['demands_covered'] = demands_covered
            updated_analytics['coverage_count'] = len(demands_covered)
            
            # Calcular dias de cobertura baseado nas demandas específicas cobertas
            if demands_covered:
                first_covered = pd.to_datetime(demands_covered[0]["date"])
                last_covered = pd.to_datetime(demands_covered[-1]["date"])
                coverage_days_span = (last_covered - pd.to_datetime(batch.arrival_date)).days + 1
                updated_analytics['coverage_days'] = max(1, coverage_days_span)
            else:
                updated_analytics['coverage_days'] = 0
            
            # Criar novo lote com analytics atualizados
            updated_batch = BatchResult(
                order_date=batch.order_date,
                arrival_date=batch.arrival_date,
                quantity=batch.quantity,
                analytics=updated_analytics
            )
            updated_batches.append(updated_batch)
        
        return updated_batches

    def _create_sporadic_batch_analytics(
        self,
        demand_date_str: str,
        demand_quantity: float,
        shortfall: float,
        batch_quantity: float,
        stock_before_arrival: float,
        actual_arrival_date: pd.Timestamp,
        target_arrival_date: pd.Timestamp,
        leadtime_days: int,
        safety_days: int
    ) -> Dict:
        """Cria analytics específicos para lotes esporádicos"""
        demand_date = pd.to_datetime(demand_date_str)
        stock_after_arrival = stock_before_arrival + batch_quantity
        
        # Determinar criticidade
        is_critical = actual_arrival_date > demand_date
        arrival_delay = max(0, (actual_arrival_date - target_arrival_date).days)
        safety_margin_days = (demand_date - actual_arrival_date).days
        
        # Nível de urgência
        if stock_before_arrival < 0:
            urgency_level = 'critical'
        elif stock_before_arrival < demand_quantity:
            urgency_level = 'high'
        else:
            urgency_level = 'normal'
            
        # Ratio de eficiência
        efficiency_ratio = round(batch_quantity / demand_quantity, 2) if demand_quantity > 0 else 0
        
        return {
            'stock_before_arrival': round(stock_before_arrival, 2),
            'stock_after_arrival': round(stock_after_arrival, 2),
            'consumption_since_last_arrival': 0,  # Será calculado posteriormente
            'coverage_days': 0,  # Será calculado na função _update_sporadic_batch_analytics_with_coverage
            'actual_lead_time': leadtime_days,
            'urgency_level': urgency_level,
            'production_start_delay': 0,  # Será calculado posteriormente
            'arrival_delay': arrival_delay,
            # Métricas específicas para demanda esporádica
            'target_demand_date': demand_date_str,
            'target_demand_quantity': demand_quantity,
            'shortfall_covered': round(shortfall, 2),
            'demands_covered': [],  # Será calculado na função _update_sporadic_batch_analytics_with_coverage
            'coverage_count': 0,  # Será calculado na função _update_sporadic_batch_analytics_with_coverage
            'is_critical': is_critical,
            'safety_margin_days': safety_margin_days,
            'efficiency_ratio': efficiency_ratio
        }
    
    def _calculate_sporadic_stock_evolution(
        self,
        initial_stock: float,
        valid_demands: Dict[str, float],
        batches: List[BatchResult],
        start_period: pd.Timestamp,
        end_period: pd.Timestamp
    ) -> Dict[str, float]:
        """Calcula evolução detalhada do estoque para demandas esporádicas"""
        stock_evolution = {}
        current_stock = initial_stock
        current_date = start_period
        
        # Criar mapa de chegadas
        arrivals = {}
        for batch in batches:
            arrival_date = batch.arrival_date
            if arrival_date not in arrivals:
                arrivals[arrival_date] = 0
            arrivals[arrival_date] += batch.quantity
        
        # Simular dia a dia
        while current_date <= end_period:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Adicionar chegadas do dia
            if date_str in arrivals:
                current_stock += arrivals[date_str]
                
            # Subtrair demanda do dia
            if date_str in valid_demands:
                current_stock -= valid_demands[date_str]
                
            # Registrar estoque ao final do dia
            stock_evolution[date_str] = round(current_stock, 2)
            
            current_date += timedelta(days=1)
            
        return stock_evolution
    
    def _sporadic_batch_to_dict(self, batch: BatchResult) -> Dict:
        """Converte BatchResult esporádico para dicionário compatível com PHP"""
        analytics = batch.analytics.copy()
        
        # Garantir campos obrigatórios para demanda esporádica
        sporadic_fields = {
            'target_demand_date': '',
            'target_demand_quantity': 0,
            'shortfall_covered': 0,
            'demands_covered': [],
            'coverage_count': 0,
            'is_critical': False,
            'safety_margin_days': 0,
            'efficiency_ratio': 0
        }
        
        for field, default_value in sporadic_fields.items():
            if field not in analytics:
                analytics[field] = default_value
        
        return {
            'order_date': batch.order_date,
            'arrival_date': batch.arrival_date,
            'quantity': batch.quantity,
            'analytics': analytics
        }

    def _calculate_sporadic_analytics(
        self,
        batches: List[BatchResult],
        valid_demands: Dict[str, float],
        initial_stock: float,
        stock_evolution: Dict[str, float],
        demand_intervals: List[int],
        demand_by_month: Dict[str, float],
        avg_daily_demand: float,
        period_days: int,
        total_demand: float,
        demand_dates: List[str],
        start_period: pd.Timestamp,
        end_period: pd.Timestamp
    ) -> Dict:
        """Calcula analytics completos para demandas esporádicas"""
        
        # Encontrar estoque mínimo
        stock_values = list(stock_evolution.values())
        min_stock = min(stock_values) if stock_values else initial_stock
        min_stock_date = None
        for date, stock in stock_evolution.items():
            if stock == min_stock:
                min_stock_date = date
                break
        
        # Calcular totais
        total_produced = sum(b.quantity for b in batches)
        final_stock = stock_values[-1] if stock_values else initial_stock
        
        # Análise de atendimento de demandas
        demand_fulfillment = self._analyze_sporadic_demand_fulfillment(
            valid_demands, stock_evolution
        )
        
        # Pontos críticos
        critical_points = []
        for date, stock in stock_evolution.items():
            days_coverage = stock / avg_daily_demand if avg_daily_demand > 0 else 0
            if stock < 0 or days_coverage < 10:
                severity = 'stockout' if stock < 0 else ('critical' if days_coverage < 5 else 'warning')
                critical_points.append({
                    'date': date,
                    'stock': stock,
                    'days_of_coverage': round(days_coverage, 1),
                    'severity': severity,
                    'demand_on_date': valid_demands.get(date, 0)
                })
        
        # Métricas de produção
        production_efficiency = self._calculate_sporadic_production_efficiency(
            batches, valid_demands, avg_daily_demand, start_period, end_period
        )
        
        # Métricas específicas para demanda esporádica
        sporadic_metrics = self._calculate_sporadic_specific_metrics(
            valid_demands, demand_intervals, period_days, batches
        )
        
        # Calcular datas de reposição (similar à função MRP normal)
        stock_end_of_period = self._calculate_sporadic_stock_end_of_period(
            stock_evolution, batches, avg_daily_demand
        )
        
        # Extrair order_dates (compatível com função MRP normal)
        order_dates = [b.order_date for b in batches]
        
        # Analytics finais
        return {
            'summary': {
                'initial_stock': round(initial_stock, 2),
                'final_stock': round(final_stock, 2),
                'minimum_stock': round(min_stock, 2),
                'minimum_stock_date': min_stock_date,
                'stockout_occurred': bool(min_stock < 0),
                'total_batches': len(batches),
                'total_produced': round(total_produced, 2),
                'production_coverage_rate': f"{round((total_produced / total_demand * 100), 0):.0f}%" if total_demand > 0 else "100%",
                'stock_consumed': round(total_demand, 2),
                'demand_fulfillment_rate': demand_fulfillment['fulfillment_rate'],
                'demands_met_count': demand_fulfillment['demands_met'],
                'demands_unmet_count': demand_fulfillment['demands_unmet'],
                'unmet_demand_details': demand_fulfillment['unmet_details'],
                'average_batch_per_demand': round(len(batches) / len(valid_demands), 2) if valid_demands else 0
            },
            'stock_evolution': stock_evolution,
            'critical_points': critical_points,
            'production_efficiency': production_efficiency,
            'demand_analysis': {
                'total_demand': round(total_demand, 2),
                'average_daily_demand': round(avg_daily_demand, 2),
                'demand_by_month': demand_by_month,
                'period_days': period_days,
                'demand_events': len(valid_demands),
                'average_demand_per_event': round(total_demand / len(valid_demands), 2) if valid_demands else 0,
                'first_demand_date': demand_dates[0] if demand_dates else None,
                'last_demand_date': demand_dates[-1] if demand_dates else None,
                'demand_distribution': valid_demands
            },
            'sporadic_demand_metrics': sporadic_metrics,
            'stock_end_of_period': stock_end_of_period
        }
    
    def _analyze_sporadic_demand_fulfillment(
        self, 
        valid_demands: Dict[str, float], 
        stock_evolution: Dict[str, float]
    ) -> Dict:
        """Analisa atendimento das demandas esporádicas"""
        demands_met = 0
        demands_unmet = 0
        unmet_details = []
        
        for date, demand in valid_demands.items():
            stock_available = stock_evolution.get(date, 0)
            if stock_available >= demand:
                demands_met += 1
            else:
                demands_unmet += 1
                shortage = demand - max(0, stock_available)
                unmet_details.append({
                    'date': date,
                    'demand': demand,
                    'available_stock': max(0, stock_available),
                    'shortage': round(shortage, 2)
                })
        
        total_demands = len(valid_demands)
        fulfillment_rate = round((demands_met / total_demands * 100), 2) if total_demands > 0 else 100
        
        return {
            'fulfillment_rate': fulfillment_rate,
            'demands_met': demands_met,
            'demands_unmet': demands_unmet,
            'unmet_details': unmet_details
        }
    
    def _calculate_sporadic_production_efficiency(
        self,
        batches: List[BatchResult],
        valid_demands: Dict[str, float],
        avg_daily_demand: float,
        start_period: pd.Timestamp,
        end_period: pd.Timestamp
    ) -> Dict:
        """Calcula eficiência de produção para demandas esporádicas"""
        if not batches:
            return {
                'average_batch_size': 0,
                'production_line_utilization': 0,
                'production_gaps': [],
                'lead_time_compliance': 100,
                'batch_efficiency': 0,
                'critical_deliveries': 0,
                'average_safety_margin': 0
            }
        
        total_produced = sum(b.quantity for b in batches)
        avg_batch_size = total_produced / len(batches)
        
        # Calcular gaps de produção
        production_gaps = []
        for i in range(len(batches) - 1):
            current_arrival = pd.to_datetime(batches[i].arrival_date)
            next_order = pd.to_datetime(batches[i + 1].order_date)
            gap_days = (next_order - current_arrival).days
            
            gap_type = 'continuous' if gap_days == 0 else ('idle' if gap_days > 7 else 'normal')
            production_gaps.append({
                'from_batch': i + 1,
                'to_batch': i + 2,
                'gap_days': gap_days,
                'gap_type': gap_type
            })
        
        # Calcular entregas críticas
        critical_deliveries = sum(1 for b in batches if b.analytics.get('is_critical', False))
        
        # Calcular margem de segurança média
        safety_margins = [b.analytics.get('safety_margin_days', 0) for b in batches]
        avg_safety_margin = round(sum(safety_margins) / len(safety_margins), 1) if safety_margins else 0
        
        # Utilização da linha (simplificado)
        total_days = (end_period - start_period).days + 1
        production_days = len(batches)  # Simplificação
        utilization = round((production_days / total_days * 100), 2) if total_days > 0 else 0
        
        return {
            'average_batch_size': round(avg_batch_size, 2),
            'production_line_utilization': utilization,
            'production_gaps': production_gaps,
            'lead_time_compliance': 100,  # Assumindo 100% para simplificar
            'batch_efficiency': round((total_produced / sum(valid_demands.values()) * 100), 2) if valid_demands else 100,
            'critical_deliveries': critical_deliveries,
            'average_safety_margin': avg_safety_margin
        }
    
    def _calculate_sporadic_specific_metrics(
        self,
        valid_demands: Dict[str, float],
        demand_intervals: List[int],
        period_days: int,
        batches: List[BatchResult]
    ) -> Dict:
        """Calcula métricas específicas para demanda esporádica"""
        avg_demand_per_event = sum(valid_demands.values()) / len(valid_demands) if valid_demands else 0
        
        # Estatísticas de intervalos
        interval_stats = {
            'average_interval_days': round(sum(demand_intervals) / len(demand_intervals), 1) if demand_intervals else 0,
            'min_interval_days': min(demand_intervals) if demand_intervals else 0,
            'max_interval_days': max(demand_intervals) if demand_intervals else 0,
            'interval_variance': round(np.var(demand_intervals), 2) if demand_intervals else 0
        }
        
        # Previsibilidade da demanda
        cv = interval_stats['interval_variance'] / interval_stats['average_interval_days'] if interval_stats['average_interval_days'] > 0 else 0
        predictability = 'high' if cv < 0.2 else ('medium' if cv < 0.5 else 'low')
        
        # Análise de picos de demanda
        peak_threshold = avg_demand_per_event * 1.5
        peak_demands = [(date, qty) for date, qty in valid_demands.items() if qty > peak_threshold]
        
        return {
            'demand_concentration': self._calculate_demand_concentration(valid_demands, period_days),
            'interval_statistics': interval_stats,
            'demand_predictability': predictability,
            'peak_demand_analysis': {
                'peak_count': len(peak_demands),
                'peak_threshold': round(peak_threshold, 2),
                'peak_dates': [date for date, _ in peak_demands],
                'average_peak_size': round(sum(qty for _, qty in peak_demands) / len(peak_demands), 2) if peak_demands else 0
            }
        }
    
    def _calculate_demand_concentration(
        self, 
        valid_demands: Dict[str, float], 
        period_days: int
    ) -> Dict:
        """Calcula concentração da demanda"""
        if not valid_demands or period_days == 0:
            return {'concentration_index': 0, 'concentration_level': 'low'}
        
        # Índice de concentração: % de dias com demanda vs total de dias
        days_with_demand = len(valid_demands)
        concentration_index = round((days_with_demand / period_days), 3)
        
        if concentration_index > 0.5:
            concentration_level = 'high'
        elif concentration_index > 0.2:
            concentration_level = 'medium'
        else:
            concentration_level = 'low'
            
        return {
            'concentration_index': concentration_index,
            'concentration_level': concentration_level,
            'days_with_demand': days_with_demand,
            'total_period_days': period_days
        }
    
    def _calculate_sporadic_stock_end_of_period(
        self,
        stock_evolution: Dict[str, float],
        batches: List[BatchResult],
        avg_daily_demand: float
    ) -> Dict:
        """
        Calcula estoque ao final de cada período para demandas esporádicas
        Inclui as datas de reposição (after_batch_arrival)
        """
        result = {
            'monthly': [],
            'after_batch_arrival': [],
            'before_batch_arrival': []
        }
        
        # Agrupar por mês
        monthly_stocks = {}
        for date, stock in stock_evolution.items():
            month = date[:7]  # YYYY-MM
            if month not in monthly_stocks or date > monthly_stocks[month]['date']:
                monthly_stocks[month] = {
                    'date': date,
                    'stock': stock
                }
        
        # Pegar último dia de cada mês
        for month, data in sorted(monthly_stocks.items()):
            result['monthly'].append({
                'period': month,
                'end_date': data['date'],
                'stock': round(data['stock'], 2),
                'days_of_coverage': round(data['stock'] / avg_daily_demand, 1) if avg_daily_demand > 0 else 0
            })
        
        # Estoque após chegada de cada lote (DATAS DE REPOSIÇÃO)
        for i, batch in enumerate(batches):
            batch_number = i + 1
            arrival_date = batch.arrival_date
            
            if arrival_date in stock_evolution:
                stock_after = stock_evolution[arrival_date]
                stock_before = batch.analytics.get('stock_before_arrival', 0)
                
                result['after_batch_arrival'].append({
                    'batch_number': batch_number,
                    'date': arrival_date,
                    'stock_before': round(stock_before, 2),
                    'batch_quantity': round(batch.quantity, 3),
                    'stock_after': round(stock_after, 2),
                    'coverage_gained': batch.analytics.get('coverage_days', 0)
                })
        
        # Estoque antes da chegada do próximo lote
        for i in range(len(batches) - 1):
            next_batch_date = batches[i + 1].arrival_date
            day_before = (pd.to_datetime(next_batch_date) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            if day_before in stock_evolution:
                result['before_batch_arrival'].append({
                    'before_batch': i + 2,
                    'date': day_before,
                    'stock': round(stock_evolution[day_before], 2),
                    'days_until_arrival': 1
                })
        
        return result

    def _calculate_stock_at_date(
        self,
        batches: List[BatchResult],
        current_stock: float,
        valid_demands: Dict[str, float],
        target_date: pd.Timestamp
    ) -> float:
        """Calcula o estoque em uma data específica considerando os lotes planejados"""
        stock_before_arrival = current_stock
        target_date_str = target_date.strftime('%Y-%m-%d')
        for batch in batches:
            if batch.arrival_date <= target_date_str:
                stock_before_arrival += batch.quantity
        return stock_before_arrival

    def _calculate_future_demand_in_window(
        self,
        valid_demands: Dict[str, float],
        from_date: pd.Timestamp,
        window_days: int,
        exclude_dates: List[str]
    ) -> float:
        """Calcula demanda futura numa janela de tempo, excluindo datas já consideradas"""
        
        window_end = from_date + pd.Timedelta(days=window_days)
        future_demand = 0
        
        for date_str, quantity in valid_demands.items():
            if date_str in exclude_dates:
                continue
                
            demand_date = pd.to_datetime(date_str)
            if from_date < demand_date <= window_end:
                future_demand += quantity
        
        return future_demand

    def _validate_no_stockout_risk(
        self,
        batches: List[BatchResult],
        initial_stock: float,
        valid_demands: Dict[str, float],
        leadtime_days: int
    ) -> Dict:
        """Valida se há risco de stockout com os lotes planejados"""
        
        # Simular estoque com os lotes planejados
        stock_evolution = {}
        current_stock = initial_stock
        
        # Ordenar todas as datas
        all_dates = set()
        for date_str in valid_demands.keys():
            all_dates.add(date_str)
        for batch in batches:
            all_dates.add(batch.arrival_date)
        
        # Adicionar datas intermediárias para verificação completa
        if all_dates:
            start_date = min(pd.to_datetime(d) for d in all_dates)
            end_date = max(pd.to_datetime(d) for d in all_dates)
            
            current_date = start_date
            while current_date <= end_date:
                all_dates.add(current_date.strftime('%Y-%m-%d'))
                current_date += pd.Timedelta(days=1)
        
        # Criar dicionários para lookup rápido
        batch_arrivals = {batch.arrival_date: batch.quantity for batch in batches}
        
        min_stock = initial_stock
        min_stock_date = None
        stockout_detected = False
        
        for date_str in sorted(all_dates):
            # Adicionar chegadas de lotes
            if date_str in batch_arrivals:
                current_stock += batch_arrivals[date_str]
            
            # Subtrair demandas
            if date_str in valid_demands:
                current_stock -= valid_demands[date_str]
            
            stock_evolution[date_str] = current_stock
            
            # Acompanhar estoque mínimo
            if current_stock < min_stock:
                min_stock = current_stock
                min_stock_date = date_str
                
                if current_stock < 0:
                    stockout_detected = True
        
        return {
            'is_safe': not stockout_detected,
            'min_stock': min_stock,
            'min_stock_date': min_stock_date,
            'stock_evolution': stock_evolution,
            'stockout_detected': stockout_detected
        }

    def _create_emergency_batch_if_needed(
        self,
        validation_result: Dict,
        existing_batches: List[BatchResult],
        valid_demands: Dict[str, float],
        leadtime_days: int,
        start_cutoff: pd.Timestamp,
        safety_days: int
    ) -> Optional[BatchResult]:
        """Cria um lote de emergência se houver risco de stockout"""
        
        if validation_result['is_safe']:
            return None
        
        min_stock_date = pd.to_datetime(validation_result['min_stock_date'])
        min_stock = validation_result['min_stock']
        
        # Calcular quando o lote de emergência deve chegar
        emergency_arrival = min_stock_date - pd.Timedelta(days=safety_days)
        emergency_order = emergency_arrival - pd.Timedelta(days=leadtime_days)
        
        # Verificar se é viável fazer o pedido
        if emergency_order < start_cutoff:
            emergency_order = start_cutoff
            emergency_arrival = emergency_order + pd.Timedelta(days=leadtime_days)
        
        # Calcular quantidade necessária
        deficit = abs(min_stock) if min_stock < 0 else 0
        
        # Adicionar buffer para demandas próximas
        future_demand = 0
        for date_str, qty in valid_demands.items():
            demand_date = pd.to_datetime(date_str)
            if emergency_arrival < demand_date <= emergency_arrival + pd.Timedelta(days=30):
                future_demand += qty
        
        emergency_quantity = deficit + future_demand * 0.5
        emergency_quantity = max(emergency_quantity, getattr(self.params, 'min_batch_size', 200))
        emergency_quantity = min(emergency_quantity, getattr(self.params, 'max_batch_size', 15000))
        
        # Analytics para lote de emergência
        emergency_analytics = {
            'emergency_batch': True,
            'reason': 'stockout_prevention',
            'original_min_stock': min_stock,
            'target_coverage': 30,
            'is_critical': True,
            'urgency_level': 'emergency',
            'actual_lead_time': leadtime_days,
            'efficiency_ratio': 1.0,
            'consolidated_group': False
        }
        
        emergency_batch = BatchResult(
            order_date=emergency_order.strftime('%Y-%m-%d'),
            arrival_date=emergency_arrival.strftime('%Y-%m-%d'),
            quantity=round(emergency_quantity, 3),
            analytics=emergency_analytics
        )
        
        return emergency_batch

    def _analyze_demand_groups_for_consolidation(
        self,
        valid_demands: Dict[str, float],
        leadtime_days: int,
        safety_days: int,
        max_gap_days: int
    ) -> List[Dict]:
        """Analisa demandas para identificar grupos otimizados de consolidação com análise de lead time overlap"""
        
        # Converter para lista ordenada por data
        demand_list = []
        for date_str, quantity in sorted(valid_demands.items()):
            demand_list.append({
                'date': date_str,
                'date_obj': pd.to_datetime(date_str),
                'quantity': quantity,
                'processed': False
            })
        
        groups = []
        
        # Parâmetros de agrupamento mais flexíveis
        max_consolidation_window = min(max_gap_days, 60)  # Janela maior para consolidação
        min_economic_batch_size = getattr(self.params, 'min_batch_size', 200)
        setup_cost = getattr(self.params, 'setup_cost', 250)
        holding_cost_rate = getattr(self.params, 'holding_cost_rate', 0.002)  # Por dia
        
        # Fatores adicionais para consolidação mais inteligente
        lead_time_buffer = leadtime_days + safety_days  # Buffer total de tempo
        
        i = 0
        while i < len(demand_list):
            if demand_list[i]['processed']:
                i += 1
                continue
                
            # Iniciar novo grupo com a demanda atual
            current_group = {
                'primary_demand_date': demand_list[i]['date'],
                'demand_dates': [demand_list[i]['date']],
                'total_demand': demand_list[i]['quantity'],
                'consolidation_savings': 0,
                'holding_cost_increase': 0,
                'lead_time_efficiency': 0,
                'operational_benefits': 0
            }
            
            demand_list[i]['processed'] = True
            current_primary_date = demand_list[i]['date_obj']
            
            # Procurar demandas próximas para consolidar
            j = i + 1
            while j < len(demand_list):
                if demand_list[j]['processed']:
                    j += 1
                    continue
                
                # Calcular gap em dias
                gap_days = (demand_list[j]['date_obj'] - demand_list[i]['date_obj']).days
                
                if gap_days > max_consolidation_window:
                    break  # Demandas muito distantes
                
                # NOVA LÓGICA: Análise de overlap de lead time
                # Se a demanda j está dentro do lead time de um lote que atenderia demanda i,
                # então é muito provável que seja eficiente consolidar
                within_lead_time_window = gap_days <= lead_time_buffer
                
                # Calcular viabilidade econômica da consolidação
                consolidation_savings = setup_cost  # Economia de um setup
                
                # Custo adicional de carregamento (mais refinado)
                additional_holding_days = gap_days
                holding_cost_increase = demand_list[j]['quantity'] * holding_cost_rate * additional_holding_days
                
                # NOVA LÓGICA: Benefícios operacionais adicionais
                operational_benefits = 0
                
                # Benefício 1: Evitar overlap de lead time (muito importante!)
                if within_lead_time_window:
                    overlap_benefit = setup_cost * 0.5  # 50% de benefício adicional por evitar overlap
                    if getattr(self.params, 'overlap_prevention_priority', True):
                        overlap_benefit += getattr(self.params, 'min_consolidation_benefit', 50.0)
                    operational_benefits += overlap_benefit
                
                # Benefício 2: Simplificação operacional
                if gap_days <= 14:  # Demandas muito próximas
                    operational_benefits += setup_cost * 0.2  # 20% de benefício por simplicidade
                
                # Benefício 3: Utilização de capacidade
                combined_quantity = current_group['total_demand'] + demand_list[j]['quantity']
                if combined_quantity >= min_economic_batch_size * 1.5:  # Lote de tamanho econômico
                    operational_benefits += setup_cost * 0.1  # 10% de benefício por escala
                
                # Aplicar peso dos benefícios operacionais
                operational_efficiency_weight = getattr(self.params, 'operational_efficiency_weight', 1.0)
                operational_benefits *= operational_efficiency_weight
                
                # Critério de consolidação mais inteligente
                total_benefits = consolidation_savings + operational_benefits
                net_benefit = total_benefits - holding_cost_increase
                
                # Benefício mínimo configurável (importante para setup_cost baixo)
                min_benefit_threshold = getattr(self.params, 'min_consolidation_benefit', 50.0)
                
                # NOVA LÓGICA: Critérios múltiplos para consolidação
                should_consolidate = False
                
                # Critério 1: Benefício econômico líquido positivo
                if net_benefit > 0:
                    should_consolidate = True
                
                # Critério 2: Benefício mínimo absoluto (independente de setup_cost)
                elif total_benefits >= min_benefit_threshold:
                    should_consolidate = True
                
                # Critério 3: Demandas dentro do lead time (evitar overlap) - FORÇADO se habilitado
                elif (within_lead_time_window and 
                      getattr(self.params, 'force_consolidation_within_leadtime', True) and
                      holding_cost_increase < setup_cost * 1.5):
                    should_consolidate = True
                
                # Critério 4: Demandas muito próximas (< 7 dias) mesmo com custo alto
                elif gap_days <= 7 and holding_cost_increase < setup_cost * 1.2:
                    should_consolidate = True
                
                # Critério 5: Lotes pequenos próximos (eficiência operacional)
                elif (gap_days <= 14 and 
                      current_group['total_demand'] < min_economic_batch_size * 2 and
                      demand_list[j]['quantity'] < min_economic_batch_size * 2 and
                      holding_cost_increase < min_benefit_threshold * 2):
                    should_consolidate = True
                
                # Critério 6: Setup cost muito baixo - consolidar mais agressivamente
                elif setup_cost < 100 and gap_days <= 21 and holding_cost_increase < 200:
                    should_consolidate = True
                
                if should_consolidate:
                    current_group['demand_dates'].append(demand_list[j]['date'])
                    current_group['total_demand'] += demand_list[j]['quantity']
                    current_group['consolidation_savings'] += consolidation_savings
                    current_group['holding_cost_increase'] += holding_cost_increase
                    current_group['operational_benefits'] += operational_benefits
                    
                    # Calcular eficiência de lead time
                    if within_lead_time_window:
                        current_group['lead_time_efficiency'] += 1
                    
                    demand_list[j]['processed'] = True
                
                j += 1
            
            groups.append(current_group)
            i += 1
        
        return groups

    def _detect_critical_periods(
        self, 
        stock_simulation: Dict[str, float], 
        critical_level: float
    ) -> List[Dict]:
        """Detecta períodos onde o estoque fica abaixo do nível crítico"""
        
        critical_periods = []
        in_critical_period = False
        period_start = None
        
        for date_str, stock in stock_simulation.items():
            if stock < critical_level and not in_critical_period:
                # Início de período crítico
                in_critical_period = True
                period_start = date_str
            elif stock >= critical_level and in_critical_period:
                # Fim de período crítico
                in_critical_period = False
                critical_periods.append({
                    'start_date': period_start,
                    'end_date': date_str,
                    'min_stock': min(stock_simulation[d] for d in stock_simulation.keys() 
                                   if period_start <= d <= date_str),
                    'duration_days': (pd.to_datetime(date_str) - pd.to_datetime(period_start)).days
                })
        
        # Se terminou em período crítico
        if in_critical_period and period_start:
            last_date = max(stock_simulation.keys())
            critical_periods.append({
                'start_date': period_start,
                'end_date': last_date,
                'min_stock': min(stock_simulation[d] for d in stock_simulation.keys() 
                               if period_start <= d <= last_date),
                'duration_days': (pd.to_datetime(last_date) - pd.to_datetime(period_start)).days
            })
        
        return critical_periods

    def _adjust_groups_for_critical_periods(
        self,
        demand_groups: List[Dict],
        critical_periods: List[Dict],
        valid_demands: Dict[str, float],
        leadtime_days: int,
        safety_days: int
    ) -> List[Dict]:
        """Ajusta grupos de demanda para evitar períodos críticos"""
        
        adjusted_groups = demand_groups.copy()
        
        for period in critical_periods:
            if period['duration_days'] > 14:  # Período crítico longo
                # Identificar se há demandas no período crítico que podem ser atendidas antecipadamente
                period_start = pd.to_datetime(period['start_date'])
                period_end = pd.to_datetime(period['end_date'])
                
                # Procurar demandas próximas ao período crítico
                for demand_date_str, demand_qty in valid_demands.items():
                    demand_date = pd.to_datetime(demand_date_str)
                    
                    if period_start <= demand_date <= period_end + pd.Timedelta(days=leadtime_days):
                        # Esta demanda pode precisar de um lote antecipado
                        # Criar um grupo separado se não estiver em um grupo grande
                        
                        current_group = None
                        for group in adjusted_groups:
                            if demand_date_str in group['demand_dates']:
                                current_group = group
                                break
                        
                        if current_group and len(current_group['demand_dates']) > 2:
                            # Separar esta demanda em um grupo próprio
                            adjusted_groups.remove(current_group)
                            
                            # Grupo original sem esta demanda
                            remaining_dates = [d for d in current_group['demand_dates'] if d != demand_date_str]
                            if remaining_dates:
                                remaining_group = {
                                    'primary_demand_date': min(remaining_dates),
                                    'demand_dates': remaining_dates,
                                    'total_demand': sum(valid_demands[d] for d in remaining_dates),
                                    'consolidation_savings': current_group['consolidation_savings'] * 0.7,
                                    'holding_cost_increase': current_group['holding_cost_increase'] * 0.7,
                                    'lead_time_efficiency': current_group.get('lead_time_efficiency', 0),
                                    'operational_benefits': current_group.get('operational_benefits', 0) * 0.7
                                }
                                adjusted_groups.append(remaining_group)
                            
                            # Novo grupo para demanda crítica
                            critical_group = {
                                'primary_demand_date': demand_date_str,
                                'demand_dates': [demand_date_str],
                                'total_demand': demand_qty,
                                'consolidation_savings': 0,
                                'holding_cost_increase': 0,
                                'lead_time_efficiency': 0,
                                'operational_benefits': 100,  # Benefício por evitar stockout
                                'critical_timing': True  # Marcar como crítico
                            }
                            adjusted_groups.append(critical_group)
        
        return adjusted_groups

    def _simulate_stock_evolution_for_sporadic(
        self,
        valid_demands: Dict[str, float],
        initial_stock: float,
        demand_groups: List[Dict],
        leadtime_days: int,
        safety_days: int
    ) -> Dict[str, float]:
        """Simula evolução do estoque para detectar gaps perigosos em demandas esporádicas"""
        
        # Criar cronograma de chegadas baseado nos grupos
        arrivals = []
        for group in demand_groups:
            primary_date = pd.to_datetime(group['primary_demand_date'])
            target_arrival = primary_date - pd.Timedelta(days=safety_days)
            arrivals.append({
                'date': target_arrival,
                'quantity': group['total_demand'] * 1.2  # Estimativa conservadora
            })
        
        # Simular estoque dia a dia
        start_date = min(pd.to_datetime(date) for date in valid_demands.keys()) - pd.Timedelta(days=leadtime_days)
        end_date = max(pd.to_datetime(date) for date in valid_demands.keys()) + pd.Timedelta(days=30)
        
        stock_evolution = {}
        current_stock = initial_stock
        current_date = start_date
        
        arrivals_dict = {arr['date'].strftime('%Y-%m-%d'): arr['quantity'] for arr in arrivals}
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Adicionar chegadas
            if date_str in arrivals_dict:
                current_stock += arrivals_dict[date_str]
            
            # Subtrair demandas
            if date_str in valid_demands:
                current_stock -= valid_demands[date_str]
            
            stock_evolution[date_str] = current_stock
            current_date += pd.Timedelta(days=1)
        
        return stock_evolution


# Exemplo de uso e funções auxiliares

def optimize_mrp_from_php_data(
    daily_demands: Dict[str, float],
    initial_stock: float,
    leadtime_days: int,
    period_start_date: str,
    period_end_date: str,
    start_cutoff_date: str,
    end_cutoff_date: str,
    **custom_params
) -> str:
    """
    Função wrapper para facilitar integração com PHP
    Retorna JSON string limpo e compatível com PHP
    """
    try:
        # Criar otimizador com parâmetros customizados se fornecidos
        optimizer = MRPOptimizer()
        
        # Executar otimização
        result = optimizer.calculate_batches_with_start_end_cutoff(
            daily_demands=daily_demands,
            initial_stock=initial_stock,
            leadtime_days=leadtime_days,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            start_cutoff_date=start_cutoff_date,
            end_cutoff_date=end_cutoff_date,
            **custom_params
        )
        
        # O resultado já vem limpo pela função calculate_batches_with_start_end_cutoff
        # Converter para JSON com configurações específicas para PHP
        return json.dumps(
            result, 
            ensure_ascii=False,  # Permitir caracteres UTF-8
            separators=(',', ':'),  # Sem espaços extras
            sort_keys=True  # Ordenar chaves para consistência
        )
        
    except Exception as e:
        # Em caso de erro, retornar JSON de erro válido
        error_result = {
            'error': True,
            'message': str(e),
            'batches': [],
            'analytics': {
                'summary': {
                    'initial_stock': float(initial_stock),
                    'final_stock': 0.0,
                    'minimum_stock': 0.0,
                    'minimum_stock_date': '',
                    'stockout_occurred': True,
                    'total_batches': 0,
                    'total_produced': 0.0,
                    'production_coverage_rate': '0%',
                    'stock_consumed': 0.0
                }
            }
        }
        return json.dumps(error_result, ensure_ascii=False, separators=(',', ':'))