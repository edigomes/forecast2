import pandas as pd
import numpy as np
from typing import List, Dict, Union, Optional, Tuple
import logging
import json
from datetime import datetime
from scipy.stats import zscore
from feriados_brasil import FeriadosBrasil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mapa de frequências para resampling
FREQ_MAP = {"M": "MS", "S": "W-MON", "D": "D"}

class ModeloAjustado:
    """
    Modelo simplificado e robusto para previsão com dados limitados.
    
    Características:
    1. Detecção e tratamento de outliers mais conservador
    2. Média móvel para suavização da tendência
    3. Sazonalidade baseada em médias mensais com proteções contra valores extremos
    4. Garantia de valores positivos com baseline mínima
    5. Limites superiores realistas
    6. Validação robusta para evitar fatores sazonais problemáticos
    """
    
    def __init__(self, granularity: str = "M", 
                 seasonality_mode: str = "multiplicative",
                 seasonal_smooth: float = 0.5,  # Reduzido para menos suavização
                 outlier_threshold: float = 3.0,  # Mais conservador
                 trend_window: int = 3,
                 confidence_level: float = 0.95,
                 confidence_factor: float = 0.7,
                 growth_factor: float = 1.0,
                 min_seasonal_factor: float = 0.3,  # NOVO: Fator sazonal mínimo
                 max_seasonal_factor: float = 3.0,  # NOVO: Fator sazonal máximo
                 use_robust_stats: bool = True,  # NOVO: Usar estatísticas robustas
                 month_adjustments: Optional[Dict[int, float]] = None,
                 day_of_week_adjustments: Optional[Dict[int, float]] = None,
                 feriados_enabled: bool = True,
                 feriados_adjustments: Optional[Dict[str, float]] = None,
                 anos_feriados: Optional[List[int]] = None,
                 # NOVOS PARÂMETROS PARA EXPLICABILIDADE
                 include_explanation: bool = False,
                 explanation_level: str = "basic",
                 explanation_language: str = "pt",
                 html_layout: str = "full"):
        """
        Inicializa o modelo ajustado
        
        Args:
            granularity: Granularidade dos dados ('M' para mensal, 'S' para semanal, 'D' para diário)
            seasonality_mode: 'multiplicative' ou 'additive'
            seasonal_smooth: Fator de suavização para sazonalidade (0-1)
            outlier_threshold: Limite de desvios padrão para considerar outlier
            trend_window: Tamanho da janela para média móvel de tendência
            confidence_level: Nível de confiança (0.95 = 95%)
            confidence_factor: Fator de ajuste (menor = intervalos mais estreitos)
            growth_factor: Fator de crescimento global (1.0 = sem ajuste)
            min_seasonal_factor: Fator sazonal mínimo para modo multiplicativo
            max_seasonal_factor: Fator sazonal máximo para modo multiplicativo
            use_robust_stats: Se deve usar mediana ao invés de média (mais robusto)
            month_adjustments: Ajustes por mês {1: 1.2, 2: 0.9, ...}
            include_explanation: Se deve incluir explicações nas previsões
            explanation_level: Nível de detalhamento ('basic', 'detailed', 'advanced')
            explanation_language: Idioma das explicações ('pt', 'en')
            html_layout: Layout do HTML ('full', 'compact') - compact para popups
        """
        if granularity not in FREQ_MAP:
            raise ValueError("'granularity' deve ser 'M', 'S' ou 'D'")
        
        if seasonality_mode not in ["multiplicative", "additive"]:
            raise ValueError("'seasonality_mode' deve ser 'multiplicative' ou 'additive'")
        
        self.granularity = granularity
        self.freq = FREQ_MAP[granularity]
        self.seasonality_mode = seasonality_mode
        self.seasonal_smooth = seasonal_smooth
        self.outlier_threshold = outlier_threshold
        self.trend_window = trend_window
        self.confidence_level = confidence_level
        self.confidence_factor = confidence_factor
        self.growth_factor = growth_factor
        self.min_seasonal_factor = min_seasonal_factor
        self.max_seasonal_factor = max_seasonal_factor
        self.use_robust_stats = use_robust_stats
        self.month_adjustments = month_adjustments or {}
        self.day_of_week_adjustments = day_of_week_adjustments or {}
        self.models = {}
        
        # NOVOS PARÂMETROS PARA EXPLICABILIDADE
        self.include_explanation = include_explanation
        self.explanation_level = explanation_level
        self.explanation_language = explanation_language
        self.html_layout = html_layout
        
        # Armazenar métricas de qualidade para explicabilidade
        self.quality_metrics = {}
        
        # Configuração de feriados
        self.feriados_enabled = feriados_enabled
        self.feriados_adjustments = feriados_adjustments or {}
        
        # Anos padrão: ano atual e próximo
        if not anos_feriados:
            ano_atual = datetime.now().year
            anos_feriados = [ano_atual, ano_atual + 1]
            
        # Inicializar gerenciador de feriados
        if self.feriados_enabled:
            self.feriados = FeriadosBrasil(anos=anos_feriados)
            
            # Se não foram fornecidos ajustes personalizados, usar os padrões
            if not self.feriados_adjustments:
                self.feriados_adjustments = self.feriados.obter_ajustes_feriados()
                
            logger.info(f"Feriados brasileiros habilitados para os anos {anos_feriados}")
            logger.info(f"Ajustes para feriados: {self.feriados_adjustments}")
    
    def _prepare_data(self, timestamps: List[str], demands: List[float]) -> pd.DataFrame:
        """Prepara os dados para modelagem"""
        logger.info(f"Preparando dados - Entradas: {len(timestamps)} timestamps, {len(demands)} valores de demanda")
        
        # Converter para DataFrame
        df = pd.DataFrame({
            "ds": pd.to_datetime(timestamps),
            "y": pd.to_numeric(demands, errors="coerce")
        }).dropna()
        
        # Remover valores negativos (não fazem sentido para demanda)
        df = df[df["y"] >= 0]
        
        # Ordenar por data
        df = df.sort_values("ds")
        
        logger.info(f"Dados após limpeza: {len(df)} pontos válidos")
        
        if len(df) < 2:
            logger.warning(f"Dados insuficientes após limpeza: apenas {len(df)} pontos válidos")
            return df
        
        # Detecção e tratamento de outliers mais conservador
        if len(df) >= 10:  # Precisamos de mais pontos para detectar outliers com segurança
            z_scores = zscore(df["y"])
            outliers = abs(z_scores) > self.outlier_threshold
            
            if any(outliers):
                outlier_indices = np.where(outliers)[0]
                logger.info(f"Detectados {sum(outliers)} outliers (z-score > {self.outlier_threshold})")
                
                # Criar cópia para tratamento
                df_fixed = df.copy()
                
                # Substituir outliers de forma mais conservadora
                for idx in outlier_indices:
                    original = df["y"].iloc[idx]
                    
                    # Usar janela de 5 pontos ou menos se não houver
                    window_start = max(0, idx - 2)
                    window_end = min(len(df), idx + 3)
                    
                    # Remover o próprio outlier da janela
                    window_values = [df["y"].iloc[i] for i in range(window_start, window_end) if i != idx]
                    
                    if window_values:
                        if self.use_robust_stats:
                            replacement = np.median(window_values)
                        else:
                            replacement = np.mean(window_values)
                    else:
                        # Fallback: usar a mediana global
                        replacement = df["y"].median()
                    
                    logger.info(f"Outlier na posição {idx} (data: {df['ds'].iloc[idx].strftime('%Y-%m-%d')}): {original:.2f} substituído por {replacement:.2f}")
                    df_fixed["y"].iloc[idx] = replacement
                
                # Salvar ambas as versões
                self.original_data = df.copy()
                return df_fixed
        else:
            logger.info("Poucos dados para detecção confiável de outliers - mantendo dados originais")
        
        return df
    
    def _extract_seasonal_pattern(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extrai o padrão sazonal dos dados com validações robustas"""
        logger.info("Extraindo padrão sazonal")
        
        # Se temos poucos dados, usar padrão neutro
        if len(df) < 6:
            logger.warning(f"Poucos dados ({len(df)} pontos) para extrair padrão sazonal. Usando padrão neutro.")
            neutral_value = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
            return {month: neutral_value for month in range(1, 13)}
        
        # Calcular estatísticas globais
        if self.use_robust_stats:
            global_level = df["y"].median()
        else:
            global_level = df["y"].mean()
        
        logger.info(f"Nível global dos dados: {global_level:.2f}")
        
        # Evitar divisão por zero
        if global_level <= 0:
            global_level = 1.0
            logger.warning("Nível global muito baixo, usando 1.0 como referência")
        
        # Agrupar por mês e calcular estatísticas
        monthly_stats = df.groupby(df["ds"].dt.month)["y"].agg(['mean', 'median', 'count']).to_dict('index')
        
        # Calcular fatores sazonais iniciais
        seasonal_pattern = {}
        for month in range(1, 13):
            if month in monthly_stats:
                stats = monthly_stats[month]
                
                # Usar estatística robusta se solicitado
                if self.use_robust_stats:
                    month_value = stats['median']
                else:
                    month_value = stats['mean']
                
                # Calcular fator sazonal
                if self.seasonality_mode == "multiplicative":
                    factor = month_value / global_level
                    # Aplicar limites para evitar fatores extremos
                    factor = max(self.min_seasonal_factor, min(self.max_seasonal_factor, factor))
                else:  # additive
                    factor = month_value - global_level
                    # Para modo aditivo, limitar baseado no desvio padrão
                    std_global = df["y"].std()
                    factor = max(-2*std_global, min(2*std_global, factor))
                
                seasonal_pattern[month] = factor
                logger.info(f"Mês {month}: {stats['count']} observações, valor={month_value:.2f}, fator={factor:.3f}")
            else:
                # Mês sem dados - usar valor neutro
                neutral_value = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
                seasonal_pattern[month] = neutral_value
                logger.warning(f"Mês {month}: sem dados, usando fator neutro {neutral_value}")
        
        # Aplicar suavização apenas se temos dados suficientes
        if len([m for m in seasonal_pattern.values() if m != (1.0 if self.seasonality_mode == "multiplicative" else 0.0)]) >= 3:
            logger.info("Aplicando suavização ao padrão sazonal")
            smoothed = self._smooth_seasonal_pattern(seasonal_pattern)
        else:
            logger.info("Poucos meses com dados - mantendo padrão sem suavização")
            smoothed = seasonal_pattern
        
        # Validação final: verificar se há fatores muito extremos
        if self.seasonality_mode == "multiplicative":
            extreme_factors = [month for month, factor in smoothed.items() 
                             if factor < self.min_seasonal_factor or factor > self.max_seasonal_factor]
            if extreme_factors:
                logger.warning(f"Ajustando fatores extremos para os meses: {extreme_factors}")
                for month in extreme_factors:
                    if smoothed[month] < self.min_seasonal_factor:
                        smoothed[month] = self.min_seasonal_factor
                    elif smoothed[month] > self.max_seasonal_factor:
                        smoothed[month] = self.max_seasonal_factor
        
        logger.info(f"Padrão sazonal final: {smoothed}")
        return smoothed
    
    def _smooth_seasonal_pattern(self, pattern: Dict[int, float]) -> Dict[int, float]:
        """Aplica suavização ao padrão sazonal"""
        smoothed = {}
        months = sorted(pattern.keys())
        
        # Para cada mês, aplicar suavização com vizinhos
        for i, month in enumerate(months):
            current = pattern[month]
            
            # Encontrar vizinhos (considerando circularidade do ano)
            prev_month = months[(i - 1) % len(months)]
            next_month = months[(i + 1) % len(months)]
            
            prev_val = pattern[prev_month]
            next_val = pattern[next_month]
            
            # Aplicar suavização
            smoothed[month] = (
                self.seasonal_smooth * current + 
                (1 - self.seasonal_smooth) * (prev_val + next_val) / 2
            )
        
        return smoothed
        
    def _extract_day_of_week_pattern(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extrai o padrão por dia da semana dos dados"""
        logger.info("Extraindo padrão por dia da semana")
        
        # Se temos poucos dados, o padrão diário pode não ser confiável
        if len(df) < 14:  # Pelo menos 2 semanas
            logger.warning(f"Poucos dados ({len(df)} pontos) para extrair padrão diário confiável. Usando padrão neutro.")
            neutral_value = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
            return {day: neutral_value for day in range(7)}
            
        # Adicionar coluna de dia da semana
        df = df.copy()
        df["weekday"] = df["ds"].dt.weekday  # 0 = Segunda, 6 = Domingo
        
        # Agrupar por dia da semana e calcular estatísticas
        if self.use_robust_stats:
            daily_values = df.groupby("weekday")["y"].median().to_dict()
            global_level = df["y"].median()
        else:
            daily_values = df.groupby("weekday")["y"].mean().to_dict()
            global_level = df["y"].mean()
        
        # Evitar divisão por zero
        if global_level <= 0:
            global_level = 1.0
        
        # Calcular os fatores relativos ao nível global
        day_of_week_pattern = {}
        for day in range(7):
            if day in daily_values:
                if self.seasonality_mode == "multiplicative":
                    factor = daily_values[day] / global_level
                    # Limitar fatores extremos
                    factor = max(0.5, min(2.0, factor))
                else:  # additive
                    factor = daily_values[day] - global_level
                    # Limitar baseado no desvio padrão
                    std_global = df["y"].std()
                    factor = max(-std_global, min(std_global, factor))
                
                day_of_week_pattern[day] = factor
            else:
                # Dia sem dados
                neutral_value = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
                day_of_week_pattern[day] = neutral_value
        
        # Log para debug
        dias_semana = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
        pattern_legivel = {dias_semana[day]: f"{factor:.3f}" for day, factor in day_of_week_pattern.items()}
        
        logger.info(f"Padrão por dia da semana extraído: {pattern_legivel}")
        return day_of_week_pattern
    
    def fit(self, item_id: int, timestamps: List[str], demands: List[float]) -> 'ModeloAjustado':
        """Treina o modelo para um item específico"""
        try:
            logger.info(f"\n{'='*40}")
            logger.info(f"TREINANDO MODELO PARA ITEM {item_id}")
            logger.info(f"{'-'*40}")
            
            # Preparar dados
            df = self._prepare_data(timestamps, demands)
            
            if len(df) < 2:
                logger.warning(f"Item {item_id}: Dados insuficientes para treinamento (mínimo 2 pontos)")
                return self
            
            # Log de estatísticas
            logger.info(f"Estatísticas dos dados:")
            logger.info(f"  Média: {df['y'].mean():.2f}")
            logger.info(f"  Mediana: {df['y'].median():.2f}")
            logger.info(f"  Desvio padrão: {df['y'].std():.2f}")
            logger.info(f"  Mínimo: {df['y'].min():.2f}")
            logger.info(f"  Máximo: {df['y'].max():.2f}")
            
            # Extrair padrão sazonal
            seasonal_pattern = self._extract_seasonal_pattern(df)
            
            # Calcular tendência de forma mais robusta
            df = df.sort_values("ds")
            
            # Usar mediana móvel se solicitado, senão média móvel
            if len(df) >= self.trend_window:
                if self.use_robust_stats:
                    df["y_smooth"] = df["y"].rolling(window=self.trend_window, min_periods=1).median()
                else:
                    df["y_smooth"] = df["y"].rolling(window=self.trend_window, min_periods=1).mean()
            else:
                df["y_smooth"] = df["y"]
            
            # Ajuste de tendência mais robusto
            t_values = np.arange(len(df))
            
            # Usar regressão robusta se poucos dados ou alta variabilidade
            if len(df) < 12 or (df["y"].std() / df["y"].mean()) > 0.5:
                # Tendência baseada na diferença entre primeiro e último terço dos dados
                first_third = df["y_smooth"].iloc[:max(1, len(df)//3)].mean()
                last_third = df["y_smooth"].iloc[-max(1, len(df)//3):].mean()
                
                # Calcular slope baseado na diferença temporal
                time_span = len(df) - 1
                if time_span > 0:
                    b = (last_third - first_third) / time_span
                else:
                    b = 0
                
                # Intercepto é a média global
                a = df["y_smooth"].mean() - b * (len(df) - 1) / 2
            else:
                # Regressão linear padrão
                b, a = np.polyfit(t_values, df["y_smooth"], deg=1)
            
            # Garantir que a tendência não seja muito negativa (evitar valores zero)
            min_trend_at_end = df["y"].quantile(0.1)  # 10º percentil
            trend_at_end = a + b * (len(df) - 1)
            
            if trend_at_end < min_trend_at_end:
                logger.warning(f"Tendência muito negativa ajustada: {trend_at_end:.2f} -> {min_trend_at_end:.2f}")
                # Recalcular slope para atingir o mínimo desejado
                b = (min_trend_at_end - a) / (len(df) - 1) if len(df) > 1 else 0
            
            # Extrair padrão por dia da semana se estivermos com granularidade diária
            day_of_week_pattern = {}
            if self.freq == 'D' and len(df) >= 14:  # Pelo menos 2 semanas
                try:
                    day_of_week_pattern = self._extract_day_of_week_pattern(df)
                    logger.info("Padrão por dia da semana extraído com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao extrair padrão por dia da semana: {e}")
            
            # Calcular baseline (valor mínimo esperado)
            baseline = max(df["y"].quantile(0.05), 0.1)  # 5º percentil ou 0.1, o que for maior
            
            # Armazenar parâmetros do modelo
            self.models[item_id] = {
                "a": a,
                "b": b,
                "seasonal_pattern": seasonal_pattern,
                "day_of_week_pattern": day_of_week_pattern,
                "last_t": len(df) - 1,
                "last_date": df["ds"].iloc[-1],
                "mean": df["y"].mean(),
                "median": df["y"].median(),
                "std": df["y"].std(),
                "min": df["y"].min(),
                "max": df["y"].max(),
                "baseline": baseline,
                "last_value": df["y"].iloc[-1]
            }
            
            # Verificar qualidade do ajuste
            df["trend"] = a + b * t_values
            
            if self.seasonality_mode == "multiplicative":
                df["prediction"] = df["trend"] * df.apply(lambda x: seasonal_pattern.get(x["ds"].month, 1.0), axis=1)
            else:  # additive
                df["prediction"] = df["trend"] + df.apply(lambda x: seasonal_pattern.get(x["ds"].month, 0.0), axis=1)
            
            # Garantir valores positivos nas previsões de teste
            df["prediction"] = np.maximum(df["prediction"], baseline)
            
            # Calcular métricas
            mae = np.mean(np.abs(df["y"] - df["prediction"]))
            mape = np.mean(np.abs((df["y"] - df["prediction"]) / np.maximum(df["y"], 0.1))) * 100
            rmse = np.sqrt(np.mean((df["y"] - df["prediction"])**2))
            
            # NOVAS MÉTRICAS PARA EXPLICABILIDADE
            r2 = 1 - (np.sum((df["y"] - df["prediction"])**2) / np.sum((df["y"] - df["y"].mean())**2))
            data_points = len(df)
            outliers_removed = hasattr(self, 'original_data') and len(getattr(self, 'original_data', [])) > len(df)
            outlier_count = len(getattr(self, 'original_data', [])) - len(df) if outliers_removed else 0
            
            # Calcular qualidade dos dados
            data_completeness = (len(df) / max(len(df), 1)) * 100  # Simplificado
            seasonal_strength = abs(df["y"].max() - df["y"].min()) / df["y"].mean() if df["y"].mean() > 0 else 0
            trend_strength = abs(b) * len(df) / df["y"].mean() if df["y"].mean() > 0 else 0
            
            # Avaliar confiança da previsão
            confidence_score = "Alta" if mape < 15 and r2 > 0.7 else "Média" if mape < 30 and r2 > 0.4 else "Baixa"
            
            # Armazenar métricas de qualidade para explicabilidade
            self.quality_metrics[item_id] = {
                "mae": mae,
                "mape": mape,
                "rmse": rmse,
                "r2": r2,
                "data_points": data_points,
                "outlier_count": outlier_count,
                "data_completeness": data_completeness,
                "seasonal_strength": seasonal_strength,
                "trend_strength": trend_strength,
                "confidence_score": confidence_score,
                "training_period": {
                    "start": df["ds"].min().strftime("%Y-%m-%d"),
                    "end": df["ds"].max().strftime("%Y-%m-%d"),
                    "months": len(df)
                }
            }
            
            logger.info(f"Parâmetros do modelo:")
            logger.info(f"  Tendência: a={a:.3f}, b={b:.3f}")
            logger.info(f"  Baseline: {baseline:.2f}")
            logger.info(f"Métricas de ajuste:")
            logger.info(f"  MAE: {mae:.2f}")
            logger.info(f"  RMSE: {rmse:.2f}")
            logger.info(f"  MAPE: {mape:.2f}%")
            logger.info(f"  R²: {r2:.3f}")
            logger.info(f"  Confiança: {confidence_score}")
            
            logger.info(f"Item {item_id}: Modelo treinado com sucesso")
            logger.info(f"{'='*40}\n")
            return self
            
        except Exception as e:
            logger.exception(f"Erro ao treinar modelo para item {item_id}")
            raise ValueError(f"Falha ao treinar modelo para item {item_id}: {str(e)}")
    
    def fit_multiple(self, items_data: Dict[int, Dict[str, List]]) -> 'ModeloAjustado':
        """Treina o modelo para múltiplos itens"""
        for item_id, data in items_data.items():
            try:
                self.fit(
                    item_id=item_id,
                    timestamps=data["timestamps"],
                    demands=data["demands"]
                )
            except Exception as e:
                logger.warning(f"Falha ao treinar item {item_id}: {e}")
        
        return self
    
    def predict(self, item_id: int, start_date: str, periods: int) -> Optional[List[Dict]]:
        """Gera previsões para um item específico"""
        if item_id not in self.models:
            logger.warning(f"Item {item_id}: Modelo não encontrado")
            return None
        
        logger.info(f"\n{'='*40}")
        logger.info(f"GERANDO PREVISÃO PARA ITEM {item_id}")
        logger.info(f"{'-'*40}")
        logger.info(f"Data de início: {start_date}")
        logger.info(f"Períodos: {periods}")
        
        try:
            model = self.models[item_id]
            a, b = model["a"], model["b"]
            seasonal_pattern = model["seasonal_pattern"]
            last_t = model["last_t"]
            mean, std = model["mean"], model["std"]
            min_val, max_val = model["min"], model["max"]
            baseline = model["baseline"]
            last_value = model["last_value"]
            
            logger.info(f"Parâmetros do modelo: a={a:.3f}, b={b:.3f}, baseline={baseline:.2f}")
            
            # Gerar datas futuras
            start = pd.to_datetime(start_date)
            future_dates = pd.date_range(start=start, periods=periods, freq=self.freq)
            
            results = []
            
            # Calcular tendência e ajustar pelo padrão sazonal
            for i, date in enumerate(future_dates, start=1):
                t_future = last_t + i
                
                # Tendência linear
                trend = a + b * t_future
                
                # Garantir que a tendência não fique muito baixa
                trend = max(trend, baseline * 0.5)
                
                # Fator sazonal
                month = date.month
                seasonal = seasonal_pattern.get(month, 1.0 if self.seasonality_mode == "multiplicative" else 0.0)
                
                # Previsão combinada
                if self.seasonality_mode == "multiplicative":
                    prediction = trend * seasonal
                    seasonal_component = prediction - trend
                else:  # additive
                    prediction = trend + seasonal
                    seasonal_component = seasonal
                    
                # Aplicar fator de crescimento global
                prediction = prediction * self.growth_factor
                
                # Aplicar ajustes específicos por mês
                month_adjustment = self.month_adjustments.get(date.month, 1.0)
                if month_adjustment != 1.0:
                    logger.info(f"Aplicando ajuste de {month_adjustment:.2f}x para o mês {date.month}")
                    prediction = prediction * month_adjustment
                    
                # Aplicar ajustes por dia da semana
                if self.freq == 'D':
                    weekday = date.weekday()
                    day_name = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][weekday]
                    
                    # Padrões históricos
                    hist_day_pattern = model.get("day_of_week_pattern", {})
                    if hist_day_pattern and weekday in hist_day_pattern:
                        day_factor = hist_day_pattern[weekday]
                        if self.seasonality_mode == "multiplicative":
                            prediction = prediction * day_factor
                        else:  # additive
                            prediction = prediction + day_factor
                    
                    # Ajustes manuais
                    if self.day_of_week_adjustments and weekday in self.day_of_week_adjustments:
                        day_adjustment = self.day_of_week_adjustments[weekday]
                        if day_adjustment != 1.0:
                            logger.info(f"Aplicando ajuste manual de {day_adjustment:.2f}x para {day_name}")
                            prediction = prediction * day_adjustment
                
                # Verificar e aplicar ajustes para feriados
                if self.feriados_enabled:
                    data_str = date.strftime("%Y-%m-%d")
                    e_feriado, descricao = self.feriados.verificar_feriado(date)
                    
                    if e_feriado:
                        feriado_adjustment = self.feriados_adjustments.get(data_str)
                        if feriado_adjustment:
                            logger.info(f"Aplicando ajuste de {feriado_adjustment:.2f}x para {data_str} ({descricao})")
                            prediction = prediction * feriado_adjustment
                
                # Garantir valor mínimo (baseline) - PRINCIPAL CORREÇÃO
                prediction = max(prediction, baseline)
                
                # Limitar valores muito altos de forma mais conservadora
                max_reasonable = max(max_val * 2, mean * 3)  # Mais conservador
                if prediction > max_reasonable:
                    logger.warning(f"Previsão para {date.strftime('%Y-%m-%d')} limitada: {prediction:.2f} -> {max_reasonable:.2f}")
                    prediction = max_reasonable
                
                # Calcular intervalos de confiança
                import scipy.stats as stats
                z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
                adjusted_std = std * self.confidence_factor
                
                lower = max(baseline * 0.5, prediction - z_score * adjusted_std)  # Garantir mínimo
                upper = prediction + z_score * adjusted_std
                
                # Criar resultado base
                result = {
                    "item_id": item_id,
                    "ds": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "yhat": round(prediction, 2),
                    "yhat_lower": round(lower, 2),
                    "yhat_upper": round(upper, 2),
                    "trend": round(trend, 2),
                    "yearly": round(seasonal_component, 2),
                    "weekly": 0.0,
                    "holidays": 0.0
                }
                
                # Adicionar explicação se solicitado
                if self.include_explanation:
                    explanation = self._generate_explanation(item_id, result, date)
                    if explanation:
                        result["_explanation"] = explanation
                
                # NOVO: Adicionar dados para geração de HTML (sempre presente)
                html_data = self._generate_html_data(item_id, result, date, is_quarterly=False, is_semiannual=False)
                if html_data:
                    result["_html_data"] = html_data
                
                results.append(result)
            
            # Log dos resultados
            if results:
                logger.info(f"Previsão gerada para {len(results)} períodos")
                logger.info(f"Primeiro período: {results[0]['ds']} - valor: {results[0]['yhat']}")
                logger.info(f"Último período: {results[-1]['ds']} - valor: {results[-1]['yhat']}")
                logger.info(f"Valor mínimo previsto: {min([r['yhat'] for r in results]):.2f}")
                logger.info(f"Valor máximo previsto: {max([r['yhat'] for r in results]):.2f}")
            
            logger.info(f"{'='*40}\n")
            return results
        
        except Exception as e:
            logger.exception(f"Erro ao gerar previsão para item {item_id}")
            raise ValueError(f"Falha ao gerar previsão para item {item_id}: {str(e)}")
    
    def predict_multiple(self, items: List[int], start_date: str, periods: int) -> List[Dict]:
        """Gera previsões para múltiplos itens"""
        results = []
        
        for item_id in items:
            forecast = self.predict(item_id, start_date, periods)
            if forecast:
                results.extend(forecast)
        
        return results
    
    def predict_quarterly(self, item_id: int, start_date: str, periods: int) -> Optional[List[Dict]]:
        """
        Gera previsões agrupadas por trimestre (3 em 3 meses)
        
        Args:
            item_id: ID do item
            start_date: Data de início das previsões
            periods: Número de trimestres para prever
            
        Returns:
            Lista de previsões agrupadas por trimestre
        """
        if item_id not in self.models:
            logger.warning(f"Item {item_id}: Modelo não encontrado")
            return None
            
        logger.info(f"\n{'='*40}")
        logger.info(f"GERANDO PREVISÃO TRIMESTRAL PARA ITEM {item_id}")
        logger.info(f"{'-'*40}")
        logger.info(f"Data de início: {start_date}")
        logger.info(f"Trimestres: {periods}")
        
        try:
            # Gerar previsões mensais para o período correspondente
            monthly_periods = periods * 3  # 3 meses por trimestre
            monthly_forecasts = self.predict(item_id, start_date, monthly_periods)
            
            if not monthly_forecasts:
                return None
            
            # Agrupar por trimestre
            quarterly_results = []
            
            for quarter in range(periods):
                quarter_start_idx = quarter * 3
                quarter_end_idx = quarter_start_idx + 3
                
                # Selecionar os 3 meses do trimestre
                quarter_forecasts = monthly_forecasts[quarter_start_idx:quarter_end_idx]
                
                if not quarter_forecasts:
                    continue
                
                # Calcular dados agregados do trimestre
                quarter_yhat = sum(f['yhat'] for f in quarter_forecasts)
                quarter_lower = sum(f['yhat_lower'] for f in quarter_forecasts)
                quarter_upper = sum(f['yhat_upper'] for f in quarter_forecasts)
                quarter_trend = sum(f['trend'] for f in quarter_forecasts)
                quarter_yearly = sum(f['yearly'] for f in quarter_forecasts)
                
                # Data de início do trimestre
                first_month = pd.to_datetime(quarter_forecasts[0]['ds'])
                last_month = pd.to_datetime(quarter_forecasts[-1]['ds'])
                
                # Nome do trimestre
                quarter_name = f"Q{(first_month.month - 1) // 3 + 1}/{first_month.year}"
                
                # MANTER COMPATIBILIDADE: Usar os mesmos campos que previsões mensais
                result = {
                    "item_id": item_id,
                    "ds": first_month.strftime("%Y-%m-%d %H:%M:%S"),  # Data de início do trimestre
                    "yhat": round(quarter_yhat, 2),
                    "yhat_lower": round(quarter_lower, 2),
                    "yhat_upper": round(quarter_upper, 2),
                    "trend": round(quarter_trend, 2),
                    "yearly": round(quarter_yearly, 2),
                    "weekly": 0.0,  # Manter compatibilidade
                    "holidays": 0.0,  # Manter compatibilidade
                    # Campos adicionais específicos para trimestres (opcionais)
                    "_quarter_info": {  # Prefixo _ indica campos internos/adicionais
                        "quarter_name": quarter_name,
                        "start_date": first_month.strftime("%Y-%m-%d"),
                        "end_date": last_month.strftime("%Y-%m-%d"),
                        "monthly_details": [
                            {
                                "month": pd.to_datetime(f['ds']).strftime("%Y-%m"),
                                "yhat": f['yhat'],
                                "yhat_lower": f['yhat_lower'],
                                "yhat_upper": f['yhat_upper']
                            }
                            for f in quarter_forecasts
                        ]
                    }
                }
                
                # Adicionar explicação trimestral se solicitado
                if self.include_explanation:
                    explanation = self._generate_quarterly_explanation(item_id, result, first_month, quarter_forecasts)
                    if explanation:
                        result["_explanation"] = explanation
                
                # NOVO: Adicionar dados para geração de HTML trimestral (sempre presente)
                html_data = self._generate_html_data(item_id, result, first_month, is_quarterly=True, quarterly_info=result.get('_quarter_info'), is_semiannual=False)
                if html_data:
                    result["_html_data"] = html_data
                
                quarterly_results.append(result)
                
                logger.info(f"Trimestre {quarter_name}: {quarter_yhat:.2f} (soma de 3 meses)")
            
            logger.info(f"Previsão trimestral gerada: {len(quarterly_results)} trimestres")
            logger.info(f"{'='*40}\n")
            
            return quarterly_results
            
        except Exception as e:
            logger.exception(f"Erro ao gerar previsão trimestral para item {item_id}")
            raise ValueError(f"Falha ao gerar previsão trimestral para item {item_id}: {str(e)}")
    
    def predict_quarterly_multiple(self, items: List[int], start_date: str, periods: int) -> List[Dict]:
        """Gera previsões trimestrais para múltiplos itens"""
        results = []
        
        for item_id in items:
            quarterly_forecast = self.predict_quarterly(item_id, start_date, periods)
            if quarterly_forecast:
                results.extend(quarterly_forecast)
        
        return results
    
    def predict_semiannually(self, item_id: int, start_date: str, periods: int) -> Optional[List[Dict]]:
        """
        Gera previsões agrupadas por semestre (6 em 6 meses)
        
        Args:
            item_id: ID do item
            start_date: Data de início das previsões
            periods: Número de semestres para prever
            
        Returns:
            Lista de previsões agrupadas por semestre
        """
        if item_id not in self.models:
            logger.warning(f"Item {item_id}: Modelo não encontrado")
            return None
            
        logger.info(f"\n{'='*40}")
        logger.info(f"GERANDO PREVISÃO SEMESTRAL PARA ITEM {item_id}")
        logger.info(f"{'-'*40}")
        logger.info(f"Data de início: {start_date}")
        logger.info(f"Semestres: {periods}")
        
        try:
            # Gerar previsões mensais para o período correspondente
            monthly_periods = periods * 6  # 6 meses por semestre
            monthly_forecasts = self.predict(item_id, start_date, monthly_periods)
            
            if not monthly_forecasts:
                return None
            
            # Agrupar por semestre
            semiannual_results = []
            
            for semester in range(periods):
                semester_start_idx = semester * 6
                semester_end_idx = semester_start_idx + 6
                
                # Selecionar os 6 meses do semestre
                semester_forecasts = monthly_forecasts[semester_start_idx:semester_end_idx]
                
                if not semester_forecasts:
                    continue
                
                # Calcular dados agregados do semestre
                semester_yhat = sum(f['yhat'] for f in semester_forecasts)
                semester_lower = sum(f['yhat_lower'] for f in semester_forecasts)
                semester_upper = sum(f['yhat_upper'] for f in semester_forecasts)
                semester_trend = sum(f['trend'] for f in semester_forecasts)
                semester_yearly = sum(f['yearly'] for f in semester_forecasts)
                
                # Data de início do semestre
                first_month = pd.to_datetime(semester_forecasts[0]['ds'])
                last_month = pd.to_datetime(semester_forecasts[-1]['ds'])
                
                # Nome do semestre
                semester_name = f"S{1 if first_month.month <= 6 else 2}/{first_month.year}"
                
                # MANTER COMPATIBILIDADE: Usar os mesmos campos que previsões mensais
                result = {
                    "item_id": item_id,
                    "ds": first_month.strftime("%Y-%m-%d %H:%M:%S"),  # Data de início do semestre
                    "yhat": round(semester_yhat, 2),
                    "yhat_lower": round(semester_lower, 2),
                    "yhat_upper": round(semester_upper, 2),
                    "trend": round(semester_trend, 2),
                    "yearly": round(semester_yearly, 2),
                    "weekly": 0.0,  # Manter compatibilidade
                    "holidays": 0.0,  # Manter compatibilidade
                    # Campos adicionais específicos para semestres (opcionais)
                    "_semester_info": {  # Prefixo _ indica campos internos/adicionais
                        "semester_name": semester_name,
                        "start_date": first_month.strftime("%Y-%m-%d"),
                        "end_date": last_month.strftime("%Y-%m-%d"),
                        "monthly_details": [
                            {
                                "month": pd.to_datetime(f['ds']).strftime("%Y-%m"),
                                "yhat": f['yhat'],
                                "yhat_lower": f['yhat_lower'],
                                "yhat_upper": f['yhat_upper']
                            }
                            for f in semester_forecasts
                        ]
                    }
                }
                
                # Adicionar explicação semestral se solicitado
                if self.include_explanation:
                    explanation = self._generate_semiannual_explanation(item_id, result, first_month, semester_forecasts)
                    if explanation:
                        result["_explanation"] = explanation
                
                # NOVO: Adicionar dados para geração de HTML semestral (sempre presente)
                html_data = self._generate_html_data(item_id, result, first_month, is_semiannual=True, semiannual_info=result.get('_semester_info'))
                if html_data:
                    result["_html_data"] = html_data
                
                semiannual_results.append(result)
                
                logger.info(f"Semestre {semester_name}: {semester_yhat:.2f} (soma de 6 meses)")
            
            logger.info(f"Previsão semestral gerada: {len(semiannual_results)} semestres")
            logger.info(f"{'='*40}\n")
            
            return semiannual_results
            
        except Exception as e:
            logger.exception(f"Erro ao gerar previsão semestral para item {item_id}")
            raise ValueError(f"Falha ao gerar previsão semestral para item {item_id}: {str(e)}")
    
    def predict_semiannually_multiple(self, items: List[int], start_date: str, periods: int) -> List[Dict]:
        """Gera previsões semestrais para múltiplos itens"""
        results = []
        
        for item_id in items:
            semiannual_forecast = self.predict_semiannually(item_id, start_date, periods)
            if semiannual_forecast:
                results.extend(semiannual_forecast)
        
        return results
    
    def _generate_explanation(self, item_id: int, prediction: Dict, date: pd.Timestamp) -> Dict:
        """
        Gera explicação detalhada para uma previsão específica
        
        Args:
            item_id: ID do item
            prediction: Dicionário com os valores da previsão
            date: Data da previsão
            
        Returns:
            Dicionário com explicações detalhadas
        """
        if item_id not in self.models or item_id not in self.quality_metrics:
            return {}
        
        model = self.models[item_id]
        metrics = self.quality_metrics[item_id]
        
        # Valores da previsão
        yhat = prediction['yhat']
        trend = prediction['trend']
        yearly = prediction['yearly']
        confidence_range = prediction['yhat_upper'] - prediction['yhat_lower']
        
        # Templates de explicação em português
        explanations = {
            "pt": {
                "summary": self._generate_summary_pt(yhat, metrics, date),
                "components": self._generate_components_explanation_pt(trend, yearly, model, date),
                "data_quality": self._generate_data_quality_pt(metrics),
                "confidence_explanation": self._generate_confidence_explanation_pt(confidence_range, metrics),
                "factors_applied": self._generate_factors_explanation_pt(item_id, date, model),
                "recommendations": self._generate_recommendations_pt(metrics)
            },
            "en": {
                "summary": f"Prediction based on {metrics['data_points']} historical data points",
                "components": {"trend_explanation": "Trend analysis", "seasonal_explanation": "Seasonal patterns"},
                "data_quality": {"confidence": metrics['confidence_score']},
                "confidence_explanation": f"Confidence interval: ±{confidence_range/2:.1f}",
                "factors_applied": ["Seasonal adjustments applied"],
                "recommendations": ["Monitor prediction accuracy"]
            }
        }
        
        lang = self.explanation_language
        base_explanation = explanations.get(lang, explanations["pt"])
        
        # Gerar resumo HTML comum para todos os níveis
        html_summary = self._generate_html_summary(item_id, prediction, date, layout=self.html_layout)
        
        # Filtrar por nível de explicação
        if self.explanation_level == "basic":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": base_explanation["summary"],
                "confidence": metrics['confidence_score'],
                "main_factors": base_explanation["factors_applied"][:2]
            }
        elif self.explanation_level == "detailed":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": base_explanation["summary"],
                "components": base_explanation["components"],
                "confidence_explanation": base_explanation["confidence_explanation"],
                "factors_applied": base_explanation["factors_applied"],
                "data_quality_summary": {
                    "historical_periods": metrics['data_points'],
                    "confidence": metrics['confidence_score'],
                    "accuracy": f"{100-metrics['mape']:.1f}%"
                }
            }
        else:  # advanced
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": base_explanation["summary"],
                "components": base_explanation["components"],
                "data_quality": base_explanation["data_quality"],
                "confidence_explanation": base_explanation["confidence_explanation"],
                "factors_applied": base_explanation["factors_applied"],
                "recommendations": base_explanation["recommendations"],
                "technical_metrics": {
                    "mae": round(metrics['mae'], 2),
                    "mape": f"{metrics['mape']:.1f}%",
                    "r2": round(metrics['r2'], 3),
                    "trend_strength": round(metrics['trend_strength'], 3),
                    "seasonal_strength": round(metrics['seasonal_strength'], 3)
                }
            }
    
    def _generate_summary_pt(self, yhat: float, metrics: Dict, date: pd.Timestamp) -> str:
        """Gera resumo em português"""
        months = metrics['data_points']
        confidence = metrics['confidence_score'].lower()
        month_name = self._get_month_name_pt(date.month)  # Nome do mês em português
        
        return f"Previsão de {yhat:.0f} unidades para {month_name} baseada em {months} meses de histórico com confiança {confidence}."
    
    def _generate_components_explanation_pt(self, trend: float, yearly: float, model: Dict, date: pd.Timestamp) -> Dict:
        """Explica os componentes da previsão em português"""
        
        # Explicação da tendência
        b = model['b']
        if abs(b) < 0.1:
            trend_text = "Tendência estável sem crescimento significativo"
        elif b > 0:
            growth_monthly = b
            growth_annual = growth_monthly * 12
            trend_text = f"Tendência de crescimento de {growth_monthly:.1f} unidades por mês ({growth_annual:.1f} unidades/ano)"
        else:
            decline_monthly = abs(b)
            decline_annual = decline_monthly * 12
            trend_text = f"Tendência de declínio de {decline_monthly:.1f} unidades por mês ({decline_annual:.1f} unidades/ano)"
        
        # Explicação da sazonalidade
        month_num = date.month
        month_name = self._get_month_name_pt(date.month)  # Nome do mês em português
        
        if self.seasonality_mode == "multiplicative":
            seasonal_pattern = model.get('seasonal_pattern', {})
            # Tentar acessar com chave inteira primeiro, depois string (compatibilidade)
            factor = seasonal_pattern.get(date.month, seasonal_pattern.get(str(date.month), 1.0))
            
            if factor > 1.05:
                seasonal_text = f"{month_name} tem historicamente {(factor-1)*100:.0f}% mais demanda que a média"
            elif factor < 0.95:
                seasonal_text = f"{month_name} tem historicamente {(1-factor)*100:.0f}% menos demanda que a média"
            else:
                # Mesmo quando próximo da média, mostrar o percentual exato se significativo
                if abs(yearly) > 10:
                    percentage_change = (factor - 1) * 100
                    seasonal_text = f"{month_name} tem {percentage_change:+.1f}% da demanda média"
                else:
                    seasonal_text = f"{month_name} tem demanda próxima à média histórica"
        else:  # additive
            if yearly > 10:
                percentage = (yearly / trend) * 100 if trend > 0 else 0
                seasonal_text = f"{month_name} tem historicamente +{yearly:.0f} unidades acima da média (+{percentage:.0f}%)"
            elif yearly < -10:
                percentage = abs(yearly / trend) * 100 if trend > 0 else 0
                seasonal_text = f"{month_name} tem historicamente {yearly:.0f} unidades abaixo da média (-{percentage:.0f}%)"
            else:
                seasonal_text = f"{month_name} tem demanda próxima à média histórica"
        
        return {
            "trend_explanation": trend_text,
            "seasonal_explanation": seasonal_text,
            "base_trend": f"Valor base da tendência: {trend:.1f}",
            "seasonal_adjustment": f"Ajuste sazonal aplicado: {yearly:+.1f}"
        }
    
    def _generate_data_quality_pt(self, metrics: Dict) -> Dict:
        """Explica a qualidade dos dados em português"""
        return {
            "historical_periods": metrics['data_points'],
            "training_period": f"Período de treino: {metrics['training_period']['start']} a {metrics['training_period']['end']}",
            "outliers_detected": metrics['outlier_count'],
            "data_completeness": f"{metrics['data_completeness']:.1f}%",
            "seasonal_variation": "Alta" if metrics['seasonal_strength'] > 0.5 else "Média" if metrics['seasonal_strength'] > 0.2 else "Baixa",
            "trend_consistency": "Alta" if metrics['trend_strength'] < 0.3 else "Média" if metrics['trend_strength'] < 0.6 else "Baixa",
            "overall_quality": metrics['confidence_score'],
            "accuracy_metrics": {
                "mae": f"Erro médio absoluto: {metrics['mae']:.1f} unidades",
                "mape": f"Erro percentual médio: {metrics['mape']:.1f}%",
                "r2": f"Coeficiente de determinação: {metrics['r2']:.3f}"
            }
        }
    
    def _generate_confidence_explanation_pt(self, confidence_range: float, metrics: Dict) -> str:
        """Explica o intervalo de confiança em português"""
        range_pct = (confidence_range / 2) / max(metrics.get('mae', 1), 1) * 100
        
        if range_pct < 20:
            certainty = "alta precisão"
        elif range_pct < 40:
            certainty = "precisão moderada"
        else:
            certainty = "alta variabilidade"
            
        return f"Intervalo de ±{confidence_range/2:.0f} unidades baseado na variabilidade histórica com {certainty}"
    
    def _generate_factors_explanation_pt(self, item_id: int, date: pd.Timestamp, model: Dict) -> List[str]:
        """Lista os fatores aplicados na previsão"""
        factors = []
        
        # Fatores sazonais
        month = date.month
        seasonal_pattern = model.get('seasonal_pattern', {})
        # Verificar se existe com chave inteira ou string
        factor = seasonal_pattern.get(month, seasonal_pattern.get(str(month)))
        if factor is not None:
            if self.seasonality_mode == "multiplicative":
                month_name = self._get_month_name_pt(date.month)
                if factor > 1.05:
                    factors.append(f"Fator sazonal {month_name}: +{(factor-1)*100:.0f}% acima da média")
                elif factor < 0.95:
                    factors.append(f"Fator sazonal {month_name}: {(1-factor)*100:.0f}% abaixo da média")
                else:
                    factors.append(f"Sazonalidade {month_name}: próxima à média anual")
        
        # Ajustes manuais
        if self.month_adjustments and month in self.month_adjustments:
            adj = self.month_adjustments[month]
            if adj != 1.0:
                month_name = self._get_month_name_pt(date.month)
                factors.append(f"Ajuste manual para {month_name}: {(adj-1)*100:+.0f}%")
        
        # Fator de crescimento global
        if self.growth_factor != 1.0:
            factors.append(f"Fator de crescimento global: {(self.growth_factor-1)*100:+.0f}%")
        
        # Verificar feriados
        if self.feriados_enabled:
            date_str = date.strftime("%Y-%m-%d")
            if hasattr(self, 'feriados'):
                is_holiday, desc = self.feriados.verificar_feriado(date)
                if is_holiday and date_str in self.feriados_adjustments:
                    adj = self.feriados_adjustments[date_str]
                    factors.append(f"Feriado {desc}: {(adj-1)*100:+.0f}%")
        
        # Padrão de dia da semana (se aplicável)
        if self.freq == 'D' and self.day_of_week_adjustments:
            weekday = date.weekday()
            if weekday in self.day_of_week_adjustments:
                adj = self.day_of_week_adjustments[weekday]
                day_name = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][weekday]
                if adj != 1.0:
                    factors.append(f"Padrão {day_name}: {(adj-1)*100:+.0f}%")
        
        if not factors:
            factors.append("Previsão baseada apenas em tendência e sazonalidade histórica")
            
        return factors
    
    def _generate_recommendations_pt(self, metrics: Dict) -> List[str]:
        """Gera recomendações baseadas nas métricas"""
        recommendations = []
        
        if metrics['confidence_score'] == "Alta":
            recommendations.append("Previsão de alta confiança devido a dados históricos consistentes")
        elif metrics['confidence_score'] == "Média":
            recommendations.append("Previsão com confiança moderada - monitore fatores externos")
        else:
            recommendations.append("Previsão de baixa confiança - considere coletar mais dados históricos")
        
        if metrics['outlier_count'] > 0:
            recommendations.append(f"{metrics['outlier_count']} outliers foram removidos dos dados de treino")
        
        if metrics['data_points'] < 6:
            recommendations.append("Poucos dados históricos - a precisão pode melhorar com mais observações")
        
        if metrics['seasonal_strength'] > 0.8:
            recommendations.append("Forte padrão sazonal detectado - considere fatores sazonais específicos")
        
        if metrics['r2'] < 0.5:
            recommendations.append("Baixa capacidade explicativa - pode haver fatores externos relevantes")
        
        recommendations.append("Considere validar previsões com conhecimento do negócio")
        
        return recommendations
    
    def _get_month_name_pt(self, month_num: int) -> str:
        """Retorna nome do mês em português"""
        months_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        return months_pt.get(month_num, f"Mês {month_num}")
    
    def _generate_html_summary(self, item_id: int, prediction: Dict, date: pd.Timestamp, 
                              is_quarterly: bool = False, quarterly_info: Dict = None,
                              is_semiannual: bool = False, semiannual_info: Dict = None, layout: str = "full") -> str:
        """
        Gera resumo HTML formatado comum para todas as explicações
        
        Args:
            item_id: ID do item
            prediction: Dicionário com valores da previsão
            date: Data da previsão
            is_quarterly: Se é previsão trimestral
            quarterly_info: Informações adicionais do trimestre
            layout: Layout do HTML ('full' ou 'compact')
            
        Returns:
            String HTML formatada com resumo completo
        """
        if item_id not in self.models or item_id not in self.quality_metrics:
            return "<p><strong>❌ Informações insuficientes para gerar resumo</strong></p>"
        
        model = self.models[item_id]
        metrics = self.quality_metrics[item_id]
        
        # Valores da previsão
        yhat = prediction['yhat']
        trend = prediction['trend']
        yearly = prediction['yearly']
        yhat_lower = prediction['yhat_lower']
        yhat_upper = prediction['yhat_upper']
        confidence_range = yhat_upper - yhat_lower
        
        # Informações do período
        if is_quarterly and quarterly_info:
            period_name = quarterly_info.get('quarter_name', 'Período')
            period_type = "trimestre"
            month_details = quarterly_info.get('monthly_details', [])
        elif is_semiannual and semiannual_info:
            period_name = semiannual_info.get('semester_name', 'Período')
            period_type = "semestre"
            month_details = semiannual_info.get('monthly_details', [])
        else:
            month_name = self._get_month_name_pt(date.month)
            year = date.year
            period_name = f"{month_name}/{year}"
            period_type = "mês"
            month_details = []
        
        # Análise de confiança
        confidence = metrics['confidence_score']
        confidence_color = "#28a745" if confidence == "Alta" else "#ffc107" if confidence == "Média" else "#dc3545"
        
        # Escolher layout baseado no parâmetro
        if layout == "compact":
            return self._generate_compact_html(
                item_id, prediction, date, is_quarterly, quarterly_info, is_semiannual, semiannual_info,
                model, metrics, period_name, period_type, confidence, confidence_color
            )
        
        # HTML formatado (layout completo)
        html = f"""
        <div style="font-family: Arial, sans-serif; zoom: 0.75; width: 100%; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f8f9fa;">
            
            <!-- Cabeçalho Principal -->
            <div style="text-align: center; margin-bottom: 25px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 6px;">
                <h2 style="margin: 0; font-size: 24px;">📊 Explicação da Previsão</h2>
                <p style="margin: 8px 0 0 0; font-size: 16px; opacity: 0.9;">Item {item_id} • {period_name}</p>
            </div>
            
            <!-- Resultado Principal -->
            <div style="background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h3 style="margin: 0 0 10px 0; color: #333; font-size: 20px;">🎯 Previsão para o {period_type}</h3>
                        <p style="margin: 0; font-size: 32px; font-weight: bold; color: #2c3e50;">{yhat:,.0f} unidades</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                            Intervalo: {yhat_lower:,.0f} - {yhat_upper:,.0f} unidades (±{confidence_range/2:,.0f})
                        </p>
                    </div>
                    <div style="text-align: center;">
                        <div style="background-color: {confidence_color}; color: white; padding: 10px 20px; border-radius: 20px; font-weight: bold;">
                            Confiança: {confidence}
                        </div>
                        <p style="margin: 8px 0 0 0; font-size: 12px; color: #666;">
                            Baseado em {metrics['data_points']} períodos históricos
                        </p>
                    </div>
                </div>
            </div>
        """
        
        # Detalhamento mensal para trimestres e semestres
        if (is_quarterly or is_semiannual) and month_details:
            title = "Detalhamento Mensal (Trimestre)" if is_quarterly else "Detalhamento Mensal (Semestre)"
            grid_cols = "repeat(3, 1fr)" if is_quarterly else "repeat(auto-fit, minmax(150px, 1fr))"
            
            html += f"""
            <!-- {title} -->
            <div style="background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; color: #333; font-size: 18px;">📅 {title}</h3>
                <div style="display: grid; grid-template-columns: {grid_cols}; gap: 15px;">
            """
            
            for detail in month_details:
                month_date = pd.to_datetime(detail['month'] + '-01')
                month_name_pt = self._get_month_name_pt(month_date.month)
                html += f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #667eea;">
                        <h4 style="margin: 0 0 8px 0; color: #333; font-size: 16px;">{month_name_pt}</h4>
                        <p style="margin: 0; font-size: 20px; font-weight: bold; color: #2c3e50;">{detail['yhat']:,.0f}</p>
                        <p style="margin: 3px 0 0 0; font-size: 12px; color: #666;">
                            {detail['yhat_lower']:,.0f} - {detail['yhat_upper']:,.0f}
                        </p>
                    </div>
                """
            
            html += "</div></div>"
        
        # Componentes da Previsão
        html += f"""
            <!-- Componentes da Previsão -->
            <div style="background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; color: #333; font-size: 18px;">🔍 Como chegamos neste valor?</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                    
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 6px; border-left: 4px solid #2196f3;">
                        <h4 style="margin: 0 0 8px 0; color: #1565c0; font-size: 16px;">📈 Tendência Base</h4>
                        <p style="margin: 0; font-size: 18px; font-weight: bold; color: #0d47a1;">{trend:,.1f} unidades</p>
        """
        
        # Explicação da tendência
        b = model['b']
        if abs(b) < 0.1:
            trend_desc = "Estável - sem crescimento significativo"
        elif b > 0:
            trend_desc = f"Crescimento de {b:,.1f} un/mês ({b*12:,.1f} un/ano)"
        else:
            trend_desc = f"Declínio de {abs(b):,.1f} un/mês ({abs(b)*12:,.1f} un/ano)"
        
        html += f"""
                        <p style="margin: 5px 0 0 0; font-size: 13px; color: #1565c0;">{trend_desc}</p>
                    </div>
                    
                    <div style="background: #fff3e0; padding: 15px; border-radius: 6px; border-left: 4px solid #ff9800;">
                        <h4 style="margin: 0 0 8px 0; color: #e65100; font-size: 16px;">🔄 Ajuste Sazonal</h4>
                        <p style="margin: 0; font-size: 18px; font-weight: bold; color: #bf360c;">{yearly:+,.1f} unidades</p>
        """
        
        # Explicação sazonal
        if is_quarterly:
            seasonal_desc = f"Padrão sazonal do {period_name}"
        elif is_semiannual:
            seasonal_desc = f"Padrão sazonal do {period_name}"
        else:
            month_name = self._get_month_name_pt(date.month)
            if self.seasonality_mode == "multiplicative":
                seasonal_pattern = model.get('seasonal_pattern', {})
                # Tentar acessar com chave inteira primeiro, depois string (compatibilidade)
                factor = seasonal_pattern.get(date.month, seasonal_pattern.get(str(date.month), 1.0))
                if factor > 1.05:
                    seasonal_desc = f"{month_name}: +{(factor-1)*100:.0f}% acima da média ({yearly:+.0f} unidades)"
                elif factor < 0.95:
                    seasonal_desc = f"{month_name}: {(1-factor)*100:.0f}% abaixo da média ({yearly:+.0f} unidades)"
                else:
                    # Mesmo quando está "próximo à média", mostrar o valor se for significativo
                    if abs(yearly) > 10:  # Se o ajuste for significativo (>10 unidades)
                        percentage_change = (factor - 1) * 100
                        seasonal_desc = f"{month_name}: {percentage_change:+.1f}% da média ({yearly:+.0f} unidades)"
                    else:
                        seasonal_desc = f"{month_name}: próximo à média histórica ({yearly:+.0f} unidades)"
            else:  # additive
                if yearly > 10:
                    # Calcular percentual baseado na tendência base
                    percentage = (yearly / trend) * 100 if trend > 0 else 0
                    seasonal_desc = f"{month_name}: +{yearly:.0f} unidades acima da média (+{percentage:.0f}%)"
                elif yearly < -10:
                    percentage = abs(yearly / trend) * 100 if trend > 0 else 0
                    seasonal_desc = f"{month_name}: {yearly:.0f} unidades abaixo da média (-{percentage:.0f}%)"
                else:
                    seasonal_desc = f"{month_name}: próximo à média histórica ({yearly:+.0f} unidades)"
        
        html += f"""
                        <p style="margin: 5px 0 0 0; font-size: 13px; color: #e65100;">{seasonal_desc}</p>
                    </div>
                </div>
            </div>
        """
        
        # Qualidade dos Dados
        accuracy = 100 - metrics['mape']
        accuracy_color = "#28a745" if accuracy > 85 else "#ffc107" if accuracy > 70 else "#dc3545"
        
        html += f"""
            <!-- Qualidade dos Dados -->
            <div style="background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; color: #333; font-size: 18px;">📊 Qualidade da Previsão</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    
                    <div style="text-align: center; padding: 15px;">
                        <div style="font-size: 28px; font-weight: bold; color: {accuracy_color};">{accuracy:.1f}%</div>
                        <div style="font-size: 14px; color: #666; margin-top: 5px;">Precisão Histórica</div>
                    </div>
                    
                    <div style="text-align: center; padding: 15px;">
                        <div style="font-size: 28px; font-weight: bold; color: #2c3e50;">{metrics['data_points']}</div>
                        <div style="font-size: 14px; color: #666; margin-top: 5px;">Períodos de Treino</div>
                    </div>
                    
                    <div style="text-align: center; padding: 15px;">
                        <div style="font-size: 28px; font-weight: bold; color: #6c757d;">{metrics['outlier_count']}</div>
                        <div style="font-size: 14px; color: #666; margin-top: 5px;">Outliers Removidos</div>
                    </div>
                </div>
            </div>
        """
        
        # Fatores Aplicados
        factors = self._generate_factors_explanation_pt(item_id, date, model)
        if factors:
            html += """
            <!-- Fatores Aplicados -->
            <div style="background: white; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin: 0 0 15px 0; color: #333; font-size: 18px;">⚙️ Fatores Considerados</h3>
                <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
            """
            
            for factor in factors[:5]:  # Mostrar até 5 fatores
                html += f"<li style='margin-bottom: 8px; color: #495057;'>{factor}</li>"
            
            html += "</ul></div>"
        
        # Recomendações
        recommendations = self._generate_recommendations_pt(metrics)
        if recommendations:
            html += """
            <!-- Recomendações -->
            <div style="background: #fff8e1; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #ffc107;">
                <h3 style="margin: 0 0 15px 0; color: #f57c00; font-size: 18px;">💡 Recomendações</h3>
                <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
            """
            
            for rec in recommendations[:3]:  # Mostrar até 3 recomendações mais importantes
                html += f"<li style='margin-bottom: 8px; color: #e65100;'>{rec}</li>"
            
            html += "</ul></div>"
        
        # Rodapé
        training_start = metrics['training_period']['start']
        training_end = metrics['training_period']['end']
        
        html += f"""
            <!-- Informações Técnicas -->
            <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #dee2e6;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; font-size: 12px; color: #6c757d;">
                    <div>
                        <strong>Período de treino:</strong> {training_start} a {training_end}
                    </div>
                    <div>
                        <strong>Modelo:</strong> {self.seasonality_mode.title()} • 
                        <strong>MAPE:</strong> {metrics['mape']:.1f}% • 
                        <strong>R²:</strong> {metrics['r2']:.3f}
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html.strip()
    
    def _generate_compact_html(self, item_id: int, prediction: Dict, date: pd.Timestamp,
                              is_quarterly: bool, quarterly_info: Dict, is_semiannual: bool, semiannual_info: Dict,
                              model: Dict, metrics: Dict, period_name: str, period_type: str, 
                              confidence: str, confidence_color: str) -> str:
        """
        Gera HTML compacto otimizado para popups
        
        Args:
            Parâmetros necessários para gerar o HTML compacto
            
        Returns:
            String HTML compacta formatada para popups
        """
        # Valores da previsão
        yhat = prediction['yhat']
        trend = prediction['trend']
        yearly = prediction['yearly']
        yhat_lower = prediction['yhat_lower']
        yhat_upper = prediction['yhat_upper']
        confidence_range = yhat_upper - yhat_lower
        
        # Explicação da tendência (simplificada)
        b = model['b']
        if abs(b) < 0.1:
            trend_desc = "Estável"
        elif b > 0:
            trend_desc = f"+{b:.1f}/mês"
        else:
            trend_desc = f"{b:.1f}/mês"
        
        # Explicação sazonal (simplificada)
        if is_quarterly:
            seasonal_desc = f"Trimestre: {yearly:+.0f}"
        else:
            month_name = self._get_month_name_pt(date.month)
            if self.seasonality_mode == "multiplicative":
                seasonal_pattern = model.get('seasonal_pattern', {})
                # Tentar acessar com chave inteira primeiro, depois string (compatibilidade)
                factor = seasonal_pattern.get(date.month, seasonal_pattern.get(str(date.month), 1.0))
                if abs(yearly) > 10:  # Se o ajuste for significativo
                    percentage_change = (factor - 1) * 100
                    seasonal_desc = f"{month_name}: {percentage_change:+.0f}%"
                else:
                    seasonal_desc = f"{month_name}: normal"
            else:  # additive
                if abs(yearly) > 10:
                    percentage = (yearly / trend) * 100 if trend > 0 else 0
                    seasonal_desc = f"{month_name}: {percentage:+.0f}%"
                else:
                    seasonal_desc = f"{month_name}: normal"
        
        # Precisão
        accuracy = 100 - metrics['mape']
        
        # HTML compacto para popup
        html = f"""
        <div style="font-family: Arial, sans-serif; width: 100%; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            
            <!-- Cabeçalho Compacto -->
            <div style="text-align: center; margin-bottom: 15px; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 6px;">
                <h3 style="margin: 0; font-size: 16px;">📊 Item {item_id}</h3>
                <p style="margin: 3px 0 0 0; font-size: 13px; opacity: 0.9;">{period_name}</p>
            </div>
            
            <!-- Resultado Principal Compacto -->
            <div style="text-align: center; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                <div style="font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;">
                    {yhat:,.0f} unidades
                </div>
                <div style="font-size: 11px; color: #666; margin-bottom: 8px;">
                    {yhat_lower:,.0f} - {yhat_upper:,.0f} (±{confidence_range/2:,.0f})
                </div>
                <div style="display: inline-block; background-color: {confidence_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                    {confidence} • {accuracy:.0f}%
                </div>
            </div>
        """
        
        # Detalhamento mensal compacto para trimestres e semestres
        if (is_quarterly and quarterly_info and quarterly_info.get('monthly_details')) or \
           (is_semiannual and semiannual_info and semiannual_info.get('monthly_details')):
            
            if is_quarterly:
                month_details = quarterly_info['monthly_details']
                title = "Detalhamento Mensal"
                grid_cols = "repeat(3, 1fr)"
            else:  # is_semiannual
                month_details = semiannual_info['monthly_details']
                title = "Detalhamento Mensal"
                grid_cols = "repeat(3, 1fr)"  # 3 colunas x 2 linhas para semestre
            
            html += f"""
            <!-- Meses do {period_type.title()} -->
            <div style="margin-bottom: 15px;">
                <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #666; text-align: center;">{title}</h4>
                <div style="display: grid; grid-template-columns: {grid_cols}; gap: 8px;">
            """
            
            for detail in month_details:
                month_date = pd.to_datetime(detail['month'] + '-01')
                month_name_pt = self._get_month_name_pt(month_date.month)[:3]  # Abreviado
                html += f"""
                    <div style="text-align: center; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 3px solid #2196f3;">
                        <div style="font-size: 10px; color: #1565c0; font-weight: bold;">{month_name_pt}</div>
                        <div style="font-size: 14px; font-weight: bold; color: #0d47a1;">{detail['yhat']:,.0f}</div>
                    </div>
                """
            
            html += "</div></div>"
        
        # Componentes Compactos
        html += f"""
            <!-- Componentes Compactos -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                <div style="text-align: center; padding: 10px; background: #e3f2fd; border-radius: 6px; border-left: 3px solid #2196f3;">
                    <div style="font-size: 11px; color: #1565c0; font-weight: bold;">📈 Tendência</div>
                    <div style="font-size: 16px; font-weight: bold; color: #0d47a1;">{trend:,.0f}</div>
                    <div style="font-size: 9px; color: #1565c0;">{trend_desc}</div>
                </div>
                
                <div style="text-align: center; padding: 10px; background: #fff3e0; border-radius: 6px; border-left: 3px solid #ff9800;">
                    <div style="font-size: 11px; color: #e65100; font-weight: bold;">🔄 Sazonal</div>
                    <div style="font-size: 16px; font-weight: bold; color: #bf360c;">{yearly:+.0f}</div>
                    <div style="font-size: 9px; color: #e65100;">{seasonal_desc}</div>
                </div>
            </div>
        """
        
        # Fatores principais (máximo 2)
        factors = self._generate_factors_explanation_pt(item_id, date, model)
        if factors:
            html += """
            <!-- Fatores Principais -->
            <div style="margin-bottom: 15px;">
                <h4 style="margin: 0 0 8px 0; font-size: 13px; color: #666;">⚙️ Principais Fatores</h4>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; border-left: 3px solid #6c757d;">
            """
            
            for factor in factors[:2]:  # Máximo 2 fatores
                html += f"<div style='font-size: 11px; color: #495057; margin-bottom: 4px;'>• {factor}</div>"
            
            html += "</div></div>"
        
        # Recomendação principal
        recommendations = self._generate_recommendations_pt(metrics)
        if recommendations:
            main_rec = recommendations[0]  # Apenas a primeira recomendação
            html += f"""
            <!-- Recomendação Principal -->
            <div style="background: #fff8e1; padding: 10px; border-radius: 6px; border-left: 3px solid #ffc107;">
                <div style="font-size: 11px; color: #f57c00; font-weight: bold; margin-bottom: 4px;">💡 Recomendação</div>
                <div style="font-size: 10px; color: #e65100; line-height: 1.4;">{main_rec}</div>
            </div>
            """
        
        # Rodapé compacto
        html += f"""
            <!-- Rodapé Compacto -->
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #dee2e6; text-align: center;">
                <div style="font-size: 9px; color: #6c757d;">
                    {metrics['data_points']} períodos • MAPE: {metrics['mape']:.1f}% • R²: {metrics['r2']:.2f}
                </div>
            </div>
        </div>
        """
        
        return html.strip()
    
    def _generate_quarterly_explanation(self, item_id: int, quarterly_result: Dict, 
                                       quarter_start: pd.Timestamp, monthly_forecasts: List[Dict]) -> Dict:
        """
        Gera explicação específica para previsões trimestrais
        
        Args:
            item_id: ID do item
            quarterly_result: Resultado da previsão trimestral
            quarter_start: Data de início do trimestre
            monthly_forecasts: Lista das previsões mensais que compõem o trimestre
            
        Returns:
            Dicionário com explicações da previsão trimestral
        """
        if item_id not in self.models or item_id not in self.quality_metrics:
            return {}
        
        metrics = self.quality_metrics[item_id]
        quarter_info = quarterly_result.get('_quarter_info', {})
        quarter_name = quarter_info.get('quarter_name', 'N/A')
        
        # Análise das previsões mensais
        monthly_values = [f['yhat'] for f in monthly_forecasts]
        monthly_trends = [f['trend'] for f in monthly_forecasts]
        monthly_seasonals = [f['yearly'] for f in monthly_forecasts]
        
        monthly_avg = sum(monthly_values) / len(monthly_values)
        trend_variation = max(monthly_trends) - min(monthly_trends)
        seasonal_variation = max(monthly_seasonals) - min(monthly_seasonals)
        
        # Gerar resumo HTML comum para todos os níveis (trimestral)
        html_summary = self._generate_html_summary(
            item_id, quarterly_result, quarter_start, 
            is_quarterly=True, quarterly_info=quarterly_result.get('_quarter_info', {}),
            layout=self.html_layout
        )
        
        if self.explanation_level == "basic":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Previsão de {quarterly_result['yhat']:.0f} unidades para o {quarter_name} (soma de 3 meses)",
                "confidence": metrics['confidence_score'],
                "monthly_average": f"Média mensal: {monthly_avg:.0f} unidades",
                "main_insight": self._get_quarterly_main_insight(monthly_values, quarter_name)
            }
        
        elif self.explanation_level == "detailed":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Previsão trimestral de {quarterly_result['yhat']:.0f} unidades para {quarter_name}",
                "quarterly_breakdown": {
                    "total_quarter": quarterly_result['yhat'],
                    "monthly_average": round(monthly_avg, 1),
                    "strongest_month": f"{monthly_forecasts[monthly_values.index(max(monthly_values))]['ds'][:7]}: {max(monthly_values):.0f}",
                    "weakest_month": f"{monthly_forecasts[monthly_values.index(min(monthly_values))]['ds'][:7]}: {min(monthly_values):.0f}"
                },
                "seasonal_analysis": self._analyze_quarterly_seasonality(monthly_forecasts, quarter_name),
                "trend_analysis": f"Variação de tendência no trimestre: {trend_variation:.1f} unidades",
                "confidence_explanation": f"Intervalo trimestral: ±{(quarterly_result['yhat_upper'] - quarterly_result['yhat_lower'])/2:.0f} unidades",
                "data_quality_summary": {
                    "historical_periods": metrics['data_points'],
                    "confidence": metrics['confidence_score'],
                    "accuracy": f"{100-metrics['mape']:.1f}%"
                }
            }
        
        else:  # advanced
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Análise avançada: Previsão trimestral de {quarterly_result['yhat']:.0f} unidades para {quarter_name}",
                "quarterly_breakdown": {
                    "total_quarter": quarterly_result['yhat'],
                    "monthly_values": [round(v, 1) for v in monthly_values],
                    "monthly_trends": [round(t, 1) for t in monthly_trends],
                    "monthly_seasonals": [round(s, 1) for s in monthly_seasonals],
                    "monthly_average": round(monthly_avg, 1),
                    "monthly_std": round(np.std(monthly_values), 1),
                    "coefficient_variation": f"{(np.std(monthly_values)/monthly_avg)*100:.1f}%"
                },
                "trend_analysis": {
                    "quarterly_trend": quarterly_result['trend'],
                    "trend_variation": round(trend_variation, 2),
                    "trend_consistency": "Alta" if trend_variation < monthly_avg * 0.1 else "Baixa"
                },
                "seasonal_analysis": {
                    "quarterly_seasonal": quarterly_result['yearly'],
                    "seasonal_variation": round(seasonal_variation, 2),
                    "dominant_pattern": self._identify_quarterly_pattern(monthly_seasonals)
                },
                "confidence_analysis": {
                    "quarterly_interval": f"±{(quarterly_result['yhat_upper'] - quarterly_result['yhat_lower'])/2:.0f}",
                    "relative_uncertainty": f"{((quarterly_result['yhat_upper'] - quarterly_result['yhat_lower'])/quarterly_result['yhat'])*100:.1f}%",
                    "confidence_source": "Agregação dos intervalos mensais"
                },
                "technical_metrics": {
                    "base_mae": round(metrics['mae'], 2),
                    "base_mape": f"{metrics['mape']:.1f}%",
                    "base_r2": round(metrics['r2'], 3),
                    "aggregation_method": "Soma das previsões mensais",
                    "seasonal_strength": round(metrics['seasonal_strength'], 3)
                },
                "recommendations": [
                    f"Monitorar especialmente {monthly_forecasts[monthly_values.index(max(monthly_values))]['ds'][:7]} (mês de maior demanda)",
                    "Considerar fatores trimestrais específicos do negócio",
                    "Validar com dados de trimestres anteriores similares"
                ]
            }
    
    def _get_quarterly_main_insight(self, monthly_values: List[float], quarter_name: str) -> str:
        """Gera insight principal para explicação básica trimestral"""
        if len(monthly_values) < 3:
            return "Dados insuficientes para análise"
        
        variation = (max(monthly_values) - min(monthly_values)) / np.mean(monthly_values)
        
        if variation < 0.1:
            return f"Demanda estável ao longo do {quarter_name}"
        elif variation < 0.3:
            return f"Pequena variação mensal no {quarter_name}"
        else:
            peak_month = monthly_values.index(max(monthly_values)) + 1
            month_names = ["primeiro", "segundo", "terceiro"]
            return f"Pico de demanda esperado no {month_names[peak_month-1]} mês do {quarter_name}"
    
    def _analyze_quarterly_seasonality(self, monthly_forecasts: List[Dict], quarter_name: str) -> str:
        """Analisa padrão sazonal dentro do trimestre"""
        seasonal_values = [f['yearly'] for f in monthly_forecasts]
        
        if len(seasonal_values) < 3:
            return "Análise sazonal indisponível"
        
        if max(seasonal_values) - min(seasonal_values) < 1:
            return f"Padrão sazonal uniforme no {quarter_name}"
        
        peak_index = seasonal_values.index(max(seasonal_values))
        months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        # Determinar mês baseado na data
        first_month_num = pd.to_datetime(monthly_forecasts[0]['ds']).month - 1
        peak_month = months[first_month_num + peak_index]
        
        return f"Sazonalidade mais forte em {peak_month} dentro do {quarter_name}"
    
    def _identify_quarterly_pattern(self, seasonal_values: List[float]) -> str:
        """Identifica padrão dominante no trimestre"""
        if len(seasonal_values) < 3:
            return "Padrão indeterminado"
        
        # Verificar se é crescente, decrescente ou variável
        if seasonal_values[0] < seasonal_values[1] < seasonal_values[2]:
            return "Crescente ao longo do trimestre"
        elif seasonal_values[0] > seasonal_values[1] > seasonal_values[2]:
            return "Decrescente ao longo do trimestre"
        elif seasonal_values[1] > seasonal_values[0] and seasonal_values[1] > seasonal_values[2]:
            return "Pico no meio do trimestre"
        else:
            return "Padrão variável"
    
    def _generate_html_data(self, item_id: int, prediction: Dict, date: pd.Timestamp,
                           is_quarterly: bool = False, quarterly_info: Dict = None,
                           is_semiannual: bool = False, semiannual_info: Dict = None) -> Dict:
        """
        Gera dados estruturados para geração de HTML posterior
        
        Args:
            item_id: ID do item
            prediction: Dados da previsão
            date: Data da previsão
            is_quarterly: Se é previsão trimestral
            quarterly_info: Informações do trimestre
            
        Returns:
            Dicionário com todos os dados necessários para gerar HTML
        """
        if item_id not in self.models or item_id not in self.quality_metrics:
            return {}
        
        model = self.models[item_id]
        metrics = self.quality_metrics[item_id]
        
        # Dados base da previsão
        prediction_data = {
            "yhat": prediction.get('yhat'),
            "yhat_lower": prediction.get('yhat_lower'),
            "yhat_upper": prediction.get('yhat_upper'),
            "trend": prediction.get('trend'),
            "yearly": prediction.get('yearly'),
            "ds": prediction.get('ds')
        }
        
        # Dados de explicação estruturados
        explanation_data = {
            "data_points": metrics.get('data_points', 0),
            "confidence_score": metrics.get('confidence_score', 'Média'),
            "mape": metrics.get('mape', 15.0),
            "r2": metrics.get('r2', 0.5),
            "outlier_count": metrics.get('outlier_count', 0),
            "data_completeness": metrics.get('data_completeness', 100.0),
            "seasonal_strength": metrics.get('seasonal_strength', 0.3),
            "trend_strength": metrics.get('trend_strength', 0.2),
            "training_period": metrics.get('training_period', {
                'start': '2023-01-01',
                'end': '2023-12-01'
            }),
            "trend_slope": model.get('b', 0),
            "seasonal_pattern": model.get('seasonal_pattern', {}),
            "std": model.get('std', 10),
            # NOVOS CAMPOS ESSENCIAIS PARA HTML
            "seasonality_mode": self.seasonality_mode,
            "model_baseline": model.get('baseline', 0),
            "model_mean": model.get('mean', 0),
            "day_of_week_pattern": model.get('day_of_week_pattern', {}),
            "month_adjustments": self.month_adjustments,
            "day_of_week_adjustments": self.day_of_week_adjustments,
            "growth_factor": self.growth_factor,
            "confidence_level": self.confidence_level,
            "freq": self.freq
        }
        
        # Dados completos para geração de HTML
        html_data = {
            "item_id": item_id,
            "prediction": prediction_data,
            "explanation_data": explanation_data,
            "is_quarterly": is_quarterly,
            "is_semiannual": is_semiannual,
            "date_iso": date.isoformat(),
            "timestamp": date.timestamp()
        }
        
        # Adicionar informações trimestrais se aplicável
        if is_quarterly and quarterly_info:
            html_data["quarterly_info"] = quarterly_info
            
        # Adicionar informações semestrais se aplicável
        if is_semiannual and semiannual_info:
            html_data["semiannual_info"] = semiannual_info
            
        return html_data
    
    def _generate_semiannual_explanation(self, item_id: int, semiannual_result: Dict, 
                                         semester_start: pd.Timestamp, monthly_forecasts: List[Dict]) -> Dict:
        """
        Gera explicação específica para previsões semestrais
        
        Args:
            item_id: ID do item
            semiannual_result: Resultado da previsão semestral
            semester_start: Data de início do semestre
            monthly_forecasts: Lista das previsões mensais que compõem o semestre
            
        Returns:
            Dicionário com explicações da previsão semestral
        """
        if item_id not in self.models or item_id not in self.quality_metrics:
            return {}
        
        metrics = self.quality_metrics[item_id]
        semester_info = semiannual_result.get('_semester_info', {})
        semester_name = semester_info.get('semester_name', 'N/A')
        
        # Análise das previsões mensais
        monthly_values = [f['yhat'] for f in monthly_forecasts]
        monthly_trends = [f['trend'] for f in monthly_forecasts]
        monthly_seasonals = [f['yearly'] for f in monthly_forecasts]
        
        monthly_avg = sum(monthly_values) / len(monthly_values)
        trend_variation = max(monthly_trends) - min(monthly_trends)
        seasonal_variation = max(monthly_seasonals) - min(monthly_seasonals)
        
        # Gerar resumo HTML comum para todos os níveis (semestral)
        html_summary = self._generate_html_summary(
            item_id, semiannual_result, semester_start, 
            is_semiannual=True, semiannual_info=semiannual_result.get('_semester_info', {}),
            layout=self.html_layout
        )
        
        if self.explanation_level == "basic":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Previsão de {semiannual_result['yhat']:.0f} unidades para o {semester_name} (soma de 6 meses)",
                "confidence": metrics['confidence_score'],
                "monthly_average": f"Média mensal: {monthly_avg:.0f} unidades",
                "main_insight": self._get_semiannual_main_insight(monthly_values, semester_name)
            }
        
        elif self.explanation_level == "detailed":
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Previsão semestral de {semiannual_result['yhat']:.0f} unidades para {semester_name}",
                "semiannual_breakdown": {
                    "total_semester": semiannual_result['yhat'],
                    "monthly_average": round(monthly_avg, 1),
                    "strongest_month": f"{monthly_forecasts[monthly_values.index(max(monthly_values))]['ds'][:7]}: {max(monthly_values):.0f}",
                    "weakest_month": f"{monthly_forecasts[monthly_values.index(min(monthly_values))]['ds'][:7]}: {min(monthly_values):.0f}"
                },
                "seasonal_analysis": self._analyze_semiannual_seasonality(monthly_forecasts, semester_name),
                "trend_analysis": f"Variação de tendência no semestre: {trend_variation:.1f} unidades",
                "confidence_explanation": f"Intervalo semestral: ±{(semiannual_result['yhat_upper'] - semiannual_result['yhat_lower'])/2:.0f} unidades",
                "data_quality_summary": {
                    "historical_periods": metrics['data_points'],
                    "confidence": metrics['confidence_score'],
                    "accuracy": f"{100-metrics['mape']:.1f}%"
                }
            }
        
        else:  # advanced
            return {
                "html_summary": html_summary,  # CAMPO COMUM PARA TODOS
                "summary": f"Análise avançada: Previsão semestral de {semiannual_result['yhat']:.0f} unidades para {semester_name}",
                "semiannual_breakdown": {
                    "total_semester": semiannual_result['yhat'],
                    "monthly_values": [round(v, 1) for v in monthly_values],
                    "monthly_trends": [round(t, 1) for t in monthly_trends],
                    "monthly_seasonals": [round(s, 1) for s in monthly_seasonals],
                    "monthly_average": round(monthly_avg, 1),
                    "monthly_std": round(np.std(monthly_values), 1),
                    "coefficient_variation": f"{(np.std(monthly_values)/monthly_avg)*100:.1f}%"
                },
                "trend_analysis": {
                    "semiannual_trend": semiannual_result['trend'],
                    "trend_variation": round(trend_variation, 2),
                    "trend_consistency": "Alta" if trend_variation < monthly_avg * 0.1 else "Baixa"
                },
                "seasonal_analysis": {
                    "semiannual_seasonal": semiannual_result['yearly'],
                    "seasonal_variation": round(seasonal_variation, 2),
                    "dominant_pattern": self._identify_semiannual_pattern(monthly_seasonals)
                },
                "confidence_analysis": {
                    "semiannual_interval": f"±{(semiannual_result['yhat_upper'] - semiannual_result['yhat_lower'])/2:.0f}",
                    "relative_uncertainty": f"{((semiannual_result['yhat_upper'] - semiannual_result['yhat_lower'])/semiannual_result['yhat'])*100:.1f}%",
                    "confidence_source": "Agregação dos intervalos mensais"
                },
                "technical_metrics": {
                    "base_mae": round(metrics['mae'], 2),
                    "base_mape": f"{metrics['mape']:.1f}%",
                    "base_r2": round(metrics['r2'], 3),
                    "aggregation_method": "Soma das previsões mensais",
                    "seasonal_strength": round(metrics['seasonal_strength'], 3)
                },
                "recommendations": [
                    f"Monitorar especialmente {monthly_forecasts[monthly_values.index(max(monthly_values))]['ds'][:7]} (mês de maior demanda)",
                    "Considerar fatores semestrais específicos do negócio",
                    "Validar com dados de semestres anteriores similares"
                ]
            }
    
    def _get_semiannual_main_insight(self, monthly_values: List[float], semester_name: str) -> str:
        """Gera insight principal para explicação básica semestral"""
        if len(monthly_values) < 6:
            return "Dados insuficientes para análise"
        
        variation = (max(monthly_values) - min(monthly_values)) / np.mean(monthly_values)
        
        if variation < 0.1:
            return f"Demanda estável ao longo do {semester_name}"
        elif variation < 0.3:
            return f"Pequena variação mensal no {semester_name}"
        else:
            peak_month = monthly_values.index(max(monthly_values)) + 1
            month_names = ["primeiro", "segundo", "terceiro", "quarto", "quinto", "sexto"]
            return f"Pico de demanda esperado no {month_names[peak_month-1]} mês do {semester_name}"
    
    def _analyze_semiannual_seasonality(self, monthly_forecasts: List[Dict], semester_name: str) -> str:
        """Analisa padrão sazonal dentro do semestre"""
        seasonal_values = [f['yearly'] for f in monthly_forecasts]
        
        if len(seasonal_values) < 6:
            return "Análise sazonal indisponível"
        
        if max(seasonal_values) - min(seasonal_values) < 1:
            return f"Padrão sazonal uniforme no {semester_name}"
        
        peak_index = seasonal_values.index(max(seasonal_values))
        months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        # Determinar mês baseado na data
        first_month_num = pd.to_datetime(monthly_forecasts[0]['ds']).month - 1
        peak_month = months[first_month_num + peak_index]
        
        return f"Sazonalidade mais forte em {peak_month} dentro do {semester_name}"
    
    def _identify_semiannual_pattern(self, seasonal_values: List[float]) -> str:
        """Identifica padrão dominante no semestre"""
        if len(seasonal_values) < 6:
            return "Padrão indeterminado"
        
        # Verificar se é crescente, decrescente ou variável
        if seasonal_values[0] < seasonal_values[1] < seasonal_values[2] < seasonal_values[3] < seasonal_values[4] < seasonal_values[5]:
            return "Crescente ao longo do semestre"
        elif seasonal_values[0] > seasonal_values[1] > seasonal_values[2] > seasonal_values[3] > seasonal_values[4] > seasonal_values[5]:
            return "Decrescente ao longo do semestre"
        elif seasonal_values[1] > seasonal_values[0] and seasonal_values[1] > seasonal_values[2] and seasonal_values[1] > seasonal_values[3] and seasonal_values[1] > seasonal_values[4] and seasonal_values[1] > seasonal_values[5]:
            return "Pico no meio do semestre"
        else:
            return "Padrão variável"
