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