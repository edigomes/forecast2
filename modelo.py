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
    1. Detecção e tratamento de outliers
    2. Média móvel para suavização da tendência
    3. Sazonalidade baseada em médias mensais com suavização
    4. Garantia de valores positivos
    5. Limites superiores realistas
    """
    
    def __init__(self, granularity: str = "M", 
                 seasonality_mode: str = "multiplicative",
                 seasonal_smooth: float = 0.7,
                 outlier_threshold: float = 2.5,
                 trend_window: int = 3,
                 confidence_level: float = 0.95,
                 confidence_factor: float = 0.7,
                 growth_factor: float = 1.0,
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
            adjustment_factor: Fator de ajuste para controlar os valores previstos
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
        self.growth_factor = growth_factor  # Fator de crescimento global (1.0 = sem ajuste)
        self.month_adjustments = month_adjustments or {}  # Ajustes por mês {1: 1.2, 2: 0.9, ...}
        self.day_of_week_adjustments = day_of_week_adjustments or {}  # Ajustes por dia da semana {0: 1.2, 1: 0.9, ...}
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
        
        # Ordenar por data
        df = df.sort_values("ds")
        
        logger.info(f"Dados após limpeza: {len(df)} pontos válidos")
        
        if len(df) < 2:
            logger.warning(f"Dados insuficientes após limpeza: apenas {len(df)} pontos válidos")
            return df
        
        # Detecção e tratamento de outliers
        if len(df) >= 5:  # Precisamos de alguns pontos para detectar outliers
            z_scores = zscore(df["y"])
            outliers = abs(z_scores) > self.outlier_threshold
            
            if any(outliers):
                outlier_indices = np.where(outliers)[0]
                logger.info(f"Detectados {sum(outliers)} outliers (z-score > {self.outlier_threshold})")
                
                # Criar cópia para tratamento
                df_fixed = df.copy()
                
                # Substituir outliers pela média dos pontos vizinhos
                for idx in outlier_indices:
                    if idx > 0 and idx < len(df) - 1:
                        # Média dos pontos vizinhos
                        neighbors = [df["y"].iloc[idx-1], df["y"].iloc[idx+1]]
                        replacement = sum(neighbors) / len(neighbors)
                    elif idx == 0:
                        # Primeiro ponto, usar o próximo
                        replacement = df["y"].iloc[1]
                    else:
                        # Último ponto, usar o anterior
                        replacement = df["y"].iloc[idx-1]
                    
                    original = df["y"].iloc[idx]
                    logger.info(f"Outlier na posição {idx} (data: {df['ds'].iloc[idx].strftime('%Y-%m-%d')}): {original:.2f} substituído por {replacement:.2f}")
                    df_fixed["y"].iloc[idx] = replacement
                
                # Salvar ambas as versões
                self.original_data = df.copy()
                return df_fixed
        
        return df
    
    def _extract_seasonal_pattern(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extrai o padrão sazonal dos dados"""
        logger.info("Extraindo padrão sazonal")
        
        # Se temos poucos dados, o padrão sazonal pode não ser confiável
        if len(df) < 12:
            logger.warning(f"Poucos dados ({len(df)} pontos) para extrair padrão sazonal confiável. Usando padrão simplificado.")
        
        # Adicionar coluna de tempo para ajuste de tendência
        df = df.copy()
        df["t"] = np.arange(len(df))
        
        # Ajuste de tendência linear: y = a + b*t
        b, a = np.polyfit(df["t"], df["y"], deg=1)
        logger.info(f"Tendência linear: y = {a:.2f} + {b:.2f} * t")
        
        # Estimar tendência
        df["trend"] = a + b * df["t"]
        
        # Calcular fatores sazonais
        if self.seasonality_mode == "multiplicative":
            # Evitar divisão por zero
            df["ratio"] = df["y"] / df["trend"].replace(0, np.nan)
            df["ratio"] = df["ratio"].fillna(1.0)
        else:  # additive
            df["ratio"] = df["y"] - df["trend"]
        
        # Agrupar por mês e calcular média
        seasonal_pattern = df.groupby(df["ds"].dt.month)["ratio"].mean().to_dict()
        
        # Aplicar suavização para meses consecutivos
        months = sorted(seasonal_pattern.keys())
        smoothed = {}
        
        # Inicializar com o primeiro mês
        prev = seasonal_pattern[months[0]]
        smoothed[months[0]] = seasonal_pattern[months[0]]
        
        # Aplicar suavização nos meses seguintes
        for m in months[1:]:
            smoothed[m] = self.seasonal_smooth * seasonal_pattern[m] + (1 - self.seasonal_smooth) * prev
            prev = smoothed[m]
        
        # Verificar se há alguma entrada faltando (deveria ter 12 meses)
        for m in range(1, 13):
            if m not in smoothed:
                smoothed[m] = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
        
        logger.info(f"Padrão sazonal extraído: {smoothed}")
        return smoothed
        
    def _extract_day_of_week_pattern(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extrai o padrão por dia da semana dos dados"""
        logger.info("Extraindo padrão por dia da semana")
        
        # Se temos poucos dados, o padrão diário pode não ser confiável
        if len(df) < 7:
            logger.warning(f"Poucos dados ({len(df)} pontos) para extrair padrão diário confiável. Usando padrão simplificado.")
            return {}
            
        # Adicionar coluna de dia da semana
        df = df.copy()
        df["weekday"] = df["ds"].dt.weekday  # 0 = Segunda, 6 = Domingo
        
        # Agrupar por dia da semana e calcular média
        daily_values = df.groupby("weekday")["y"].mean().to_dict()
        
        # Calcular a média global
        global_mean = np.mean(list(daily_values.values()))
        if global_mean == 0:
            global_mean = 1.0  # Evitar divisão por zero
        
        # Calcular os fatores relativos à média global
        day_of_week_pattern = {}
        for day, value in daily_values.items():
            if self.seasonality_mode == "multiplicative":
                day_of_week_pattern[day] = value / global_mean
            else:  # additive
                day_of_week_pattern[day] = value - global_mean
        
        # Verificar se há algum dia faltando (deveria ter 7 dias)
        for day in range(7):
            if day not in day_of_week_pattern:
                day_of_week_pattern[day] = 1.0 if self.seasonality_mode == "multiplicative" else 0.0
        
        # Converter os dias para nomes para melhor legibilidade em logs
        dias_semana = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
        pattern_legivel = {dias_semana[day]: f"{factor:.2f}" for day, factor in day_of_week_pattern.items()}
        
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
            logger.info(f"  Desvio padrão: {df['y'].std():.2f}")
            logger.info(f"  Mínimo: {df['y'].min():.2f}")
            logger.info(f"  Máximo: {df['y'].max():.2f}")
            
            # Extrair padrão sazonal
            seasonal_pattern = self._extract_seasonal_pattern(df)
            
            # Calcular tendência com média móvel para suavização
            df = df.sort_values("ds")
            if len(df) >= self.trend_window:
                # Média móvel para suavizar a tendência
                df["y_smooth"] = df["y"].rolling(window=self.trend_window, min_periods=1).mean()
            else:
                df["y_smooth"] = df["y"]
            
            # Ajuste de tendência linear: y = a + b*t
            t_values = np.arange(len(df))
            b, a = np.polyfit(t_values, df["y_smooth"], deg=1)
            
            # Extrair padrão por dia da semana se estivermos com granularidade diária
            day_of_week_pattern = {}
            if self.freq == 'D' and len(df) >= 7:  # Pelo menos uma semana de dados
                try:
                    day_of_week_pattern = self._extract_day_of_week_pattern(df)
                    logger.info("Padrão por dia da semana extraído com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao extrair padrão por dia da semana: {e}")
            
            # Armazenar parâmetros do modelo
            self.models[item_id] = {
                "a": a,
                "b": b,
                "seasonal_pattern": seasonal_pattern,
                "day_of_week_pattern": day_of_week_pattern,
                "last_t": len(df) - 1,
                "last_date": df["ds"].iloc[-1],
                "mean": df["y"].mean(),
                "std": df["y"].std(),
                "min": df["y"].min(),
                "max": df["y"].max(),
                "last_value": df["y"].iloc[-1]
            }
            
            # Verificar qualidade do ajuste
            df["trend"] = a + b * t_values
            
            if self.seasonality_mode == "multiplicative":
                df["prediction"] = df["trend"] * df.apply(lambda x: seasonal_pattern.get(x["ds"].month, 1.0), axis=1)
            else:  # additive
                df["prediction"] = df["trend"] + df.apply(lambda x: seasonal_pattern.get(x["ds"].month, 0.0), axis=1)
            
            # Calcular métricas
            mae = np.mean(np.abs(df["y"] - df["prediction"]))
            mape = np.mean(np.abs((df["y"] - df["prediction"]) / df["y"])) * 100
            rmse = np.sqrt(np.mean((df["y"] - df["prediction"])**2))
            
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
            last_value = model["last_value"]
            
            # Gerar datas futuras
            start = pd.to_datetime(start_date)
            future_dates = pd.date_range(start=start, periods=periods, freq=self.freq)
            
            results = []
            
            # Calcular tendência e ajustar pelo padrão sazonal
            for i, date in enumerate(future_dates, start=1):
                t_future = last_t + i
                
                # Tendência linear
                trend = a + b * t_future
                
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
                    
                # Aplicar fator de crescimento global (para todos os meses)
                prediction = prediction * self.growth_factor
                
                # Aplicar ajustes específicos por mês (se existirem)
                month_adjustment = self.month_adjustments.get(date.month, 1.0)
                if month_adjustment != 1.0:
                    logger.info(f"Aplicando ajuste de {month_adjustment:.2f}x para o mês {date.month}")
                    prediction = prediction * month_adjustment
                    
                # Aplicar ajustes por dia da semana
                if self.freq == 'D':
                    # weekday() retorna 0-6 (Segunda=0, Domingo=6)
                    weekday = date.weekday()
                    day_name = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][weekday]
                    
                    # Primeiro verificar se temos padrões históricos
                    hist_day_pattern = model.get("day_of_week_pattern", {})
                    if hist_day_pattern and weekday in hist_day_pattern:
                        day_factor = hist_day_pattern[weekday]
                        logger.info(f"Aplicando ajuste histórico de {day_factor:.2f}x para {day_name}")
                        if self.seasonality_mode == "multiplicative":
                            prediction = prediction * day_factor
                        else:  # additive
                            prediction = prediction + day_factor
                    
                    # Depois aplicar ajustes manuais, se existirem (prioridade mais alta)
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
                        # Verificar se existe um ajuste específico para esta data
                        feriado_adjustment = self.feriados_adjustments.get(data_str)
                        
                        if feriado_adjustment:
                            logger.info(f"Aplicando ajuste de {feriado_adjustment:.2f}x para {data_str} ({descricao})")
                            prediction = prediction * feriado_adjustment
                
                # Garantir valores positivos e realistas
                prediction = max(0, prediction)  # Garantir positivo
                
                # Limitar valores muito altos (3x o máximo histórico)
                if prediction > 3 * max_val:
                    logger.warning(f"Previsão para {date.strftime('%Y-%m-%d')} limitada: {prediction:.2f} -> {3 * max_val:.2f}")
                    prediction = 3 * max_val
                
                # Calcular z-score com base no nível de confiança
                # Para 95% de confiança, z_score = 1.96
                # Para 90% de confiança, z_score = 1.645
                # Para 80% de confiança, z_score = 1.28
                import scipy.stats as stats
                z_score = stats.norm.ppf((1 + self.confidence_level) / 2)
                
                # Ajustar o desvio padrão com o fator de confiança
                # Um fator menor torna os intervalos mais estreitos
                adjusted_std = std * self.confidence_factor
                
                # Intervalos de confiança ajustados
                lower = max(0, prediction - z_score * adjusted_std)
                upper = prediction + z_score * adjusted_std
                
                logger.info(f"Intervalo de confiança para {date.strftime('%Y-%m-%d')}: "
                           f"nível={self.confidence_level*100:.1f}%, "
                           f"z-score={z_score:.3f}, "
                           f"fator={self.confidence_factor}")
                
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
