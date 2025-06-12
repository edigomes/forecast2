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
                 anos_feriados: Optional[List[int]] = None):
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
            
            logger.info(f"Parâmetros do modelo:")
            logger.info(f"  Tendência: a={a:.3f}, b={b:.3f}")
            logger.info(f"  Baseline: {baseline:.2f}")
            logger.info(f"Métricas de ajuste:")
            logger.info(f"  MAE: {mae:.2f}")
            logger.info(f"  RMSE: {rmse:.2f}")
            logger.info(f"  MAPE: {mape:.2f}%")
            
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
                
                results.append({
                    "item_id": item_id,
                    "ds": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "yhat": round(prediction, 2),
                    "yhat_lower": round(lower, 2),
                    "yhat_upper": round(upper, 2),
                    "trend": round(trend, 2),
                    "yearly": round(seasonal_component, 2),
                    "weekly": 0.0,
                    "holidays": 0.0
                })
            
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
