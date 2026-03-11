import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels não disponível - Holt-Winters desabilitado")


class HoltWintersModel:
    """Modelo Holt-Winters (Suavização Exponencial Tripla) com seleção automática."""
    
    MIN_SEASONAL_PERIODS = 2
    
    def __init__(self, seasonal_periods: int = 12):
        self.seasonal_periods = seasonal_periods
        self.model = None
        self.fitted = None
        self.mode = None
        self.mape = None
    
    @staticmethod
    def is_available() -> bool:
        return STATSMODELS_AVAILABLE
    
    def can_fit(self, n_points: int) -> bool:
        """Verifica se há dados suficientes para Holt-Winters."""
        return (STATSMODELS_AVAILABLE and 
                n_points >= self.seasonal_periods * self.MIN_SEASONAL_PERIODS)
    
    def fit(self, series: pd.Series, freq: str = 'MS') -> bool:
        """Treina Holt-Winters testando modos aditivo e multiplicativo.
        
        Returns:
            True se o modelo foi treinado com sucesso, False caso contrário.
        """
        if not self.can_fit(len(series)):
            return False
        
        series = series.copy()
        series.index = pd.DatetimeIndex(series.index, freq=freq)
        
        if (series <= 0).any():
            series = series.clip(lower=0.01)
        
        best_mape = float('inf')
        best_model = None
        best_mode = None
        
        holdout_size = min(max(3, len(series) // 5), self.seasonal_periods)
        train = series[:-holdout_size]
        test = series[-holdout_size:]
        
        if len(train) < self.seasonal_periods * 2:
            return False
        
        for mode in ['add', 'mul']:
            try:
                trend_mode = 'add'
                model = ExponentialSmoothing(
                    train,
                    trend=trend_mode,
                    seasonal=mode,
                    seasonal_periods=self.seasonal_periods,
                    initialization_method='estimated'
                )
                fitted = model.fit(optimized=True, use_brute=False)
                
                forecast = fitted.forecast(holdout_size)
                
                mask = test > 0
                if mask.any():
                    mape = np.mean(np.abs((test[mask] - forecast[mask]) / test[mask])) * 100
                else:
                    mape = np.mean(np.abs(test - forecast))
                
                if mape < best_mape:
                    best_mape = mape
                    best_mode = mode
                    best_model = (mode, trend_mode)
                    
            except Exception as e:
                logger.debug(f"Holt-Winters {mode} falhou: {e}")
                continue
        
        if best_model is None:
            return False
        
        try:
            mode, trend_mode = best_model
            full_model = ExponentialSmoothing(
                series,
                trend=trend_mode,
                seasonal=mode,
                seasonal_periods=self.seasonal_periods,
                initialization_method='estimated'
            )
            self.fitted = full_model.fit(optimized=True, use_brute=False)
            self.mode = mode
            self.mape = best_mape
            logger.info(f"Holt-Winters treinado: mode={mode}, MAPE holdout={best_mape:.2f}%")
            return True
            
        except Exception as e:
            logger.warning(f"Holt-Winters treino final falhou: {e}")
            return False
    
    def predict(self, periods: int) -> Optional[pd.Series]:
        """Gera previsões para N períodos futuros."""
        if self.fitted is None:
            return None
        
        try:
            return self.fitted.forecast(periods)
        except Exception as e:
            logger.warning(f"Holt-Winters previsão falhou: {e}")
            return None
    
    def get_mape(self) -> float:
        """Retorna MAPE do holdout."""
        return self.mape if self.mape is not None else float('inf')


def select_best_model(
    series: pd.Series,
    decomposition_predictions: List[float],
    freq: str = 'MS',
    seasonal_periods: int = 12
) -> Tuple[str, Optional[HoltWintersModel], float]:
    """Compara decomposição vs Holt-Winters e retorna o melhor.
    
    Args:
        series: Série temporal com index DatetimeIndex
        decomposition_predictions: Previsões do modelo de decomposição (in-sample)
        freq: Frequência da série
        seasonal_periods: Períodos sazonais
    
    Returns:
        Tuple de (model_name, hw_model_or_None, hw_mape)
    """
    hw = HoltWintersModel(seasonal_periods=seasonal_periods)
    
    if not hw.can_fit(len(series)):
        return ('decomposition', None, float('inf'))
    
    hw_success = hw.fit(series, freq=freq)
    
    if not hw_success:
        return ('decomposition', None, float('inf'))
    
    decomp_preds = np.array(decomposition_predictions[:len(series)])
    actual = series.values[:len(decomp_preds)]
    
    mask = actual > 0
    if mask.any():
        decomp_mape = np.mean(np.abs((actual[mask] - decomp_preds[mask]) / actual[mask])) * 100
    else:
        decomp_mape = 0.0
    
    hw_mape = hw.get_mape()
    
    logger.info(f"Model selection: decomposition MAPE={decomp_mape:.2f}%, HW MAPE={hw_mape:.2f}%")
    
    if hw_mape < decomp_mape * 0.9:
        return ('holt_winters', hw, hw_mape)
    else:
        return ('decomposition', None, hw_mape)
