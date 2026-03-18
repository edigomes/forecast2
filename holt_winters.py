import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("statsmodels não disponível - modelos de suavização desabilitados")


def _calculate_holdout_mape(test: pd.Series, forecast: pd.Series) -> float:
    """Calcula MAPE entre valores reais e previstos."""
    mask = test > 0
    if mask.any():
        return float(np.mean(np.abs((test[mask] - forecast[mask]) / test[mask])) * 100)
    return float(np.mean(np.abs(test - forecast)))


def _prepare_series(series: pd.Series, freq: str) -> pd.Series:
    """Prepara série para statsmodels: copia, infere freq, clipa zeros.
    
    Tenta usar a freq informada. Se incompatível (ex: dados end-of-month com
    freq='MS'), infere automaticamente e usa a freq detectada.
    """
    s = series.copy()
    try:
        s.index = pd.DatetimeIndex(s.index, freq=freq)
    except ValueError:
        inferred = pd.infer_freq(s.index)
        if inferred:
            s.index = pd.DatetimeIndex(s.index, freq=inferred)
        else:
            s = s.asfreq(freq)
    if (s <= 0).any():
        s = s.clip(lower=0.01)
    return s


class SimpleESModel:
    """Simple Exponential Smoothing — para séries muito curtas (3+ pontos).
    
    Sem tendência, sem sazonalidade. Apenas média ponderada exponencial
    que dá mais peso aos dados recentes.
    """
    
    MIN_POINTS = 3
    
    def __init__(self):
        self.fitted = None
        self.mape = None
    
    def can_fit(self, n_points: int) -> bool:
        return STATSMODELS_AVAILABLE and n_points >= self.MIN_POINTS
    
    def fit(self, series: pd.Series, freq: str = 'MS') -> bool:
        if not self.can_fit(len(series)):
            return False
        
        try:
            series = _prepare_series(series, freq)
            holdout_size = max(1, min(len(series) // 4, 3))
            train, test = series[:-holdout_size], series[-holdout_size:]
            
            if len(train) < 2:
                return False
            
            model = ExponentialSmoothing(
                train, trend=None, seasonal=None,
                initialization_method='estimated'
            )
            fitted = model.fit(optimized=True, use_brute=False)
            forecast = fitted.forecast(holdout_size)
            self.mape = _calculate_holdout_mape(test, forecast)
            
            full_model = ExponentialSmoothing(
                series, trend=None, seasonal=None,
                initialization_method='estimated'
            )
            self.fitted = full_model.fit(optimized=True, use_brute=False)
            logger.info(f"SES treinado: MAPE holdout={self.mape:.2f}%")
            return True
        except Exception as e:
            logger.debug(f"SES falhou: {e}")
            return False
    
    def predict(self, periods: int) -> Optional[pd.Series]:
        if self.fitted is None:
            return None
        try:
            return self.fitted.forecast(periods)
        except Exception as e:
            logger.warning(f"SES previsão falhou: {e}")
            return None
    
    def get_mape(self) -> float:
        return self.mape if self.mape is not None else float('inf')


class HoltLinearModel:
    """Holt Linear (Double Exponential Smoothing) — para séries curtas (5+ pontos).
    
    Tendência aditiva, sem sazonalidade. Captura crescimento/declínio
    linear sem precisar de ciclos sazonais completos.
    """
    
    MIN_POINTS = 5
    
    def __init__(self):
        self.fitted = None
        self.mape = None
        self.damped = False
    
    def can_fit(self, n_points: int) -> bool:
        return STATSMODELS_AVAILABLE and n_points >= self.MIN_POINTS
    
    def fit(self, series: pd.Series, freq: str = 'MS') -> bool:
        if not self.can_fit(len(series)):
            return False
        
        try:
            series = _prepare_series(series, freq)
        except Exception as e:
            logger.debug(f"Holt Linear: falha ao preparar série: {e}")
            return False
        
        holdout_size = max(1, min(len(series) // 4, 3))
        train, test = series[:-holdout_size], series[-holdout_size:]
        
        if len(train) < 3:
            return False
        
        best_mape = float('inf')
        best_damped = False
        
        for damped in [False, True]:
            try:
                model = ExponentialSmoothing(
                    train, trend='add', damped_trend=damped,
                    seasonal=None, initialization_method='estimated'
                )
                fitted = model.fit(optimized=True, use_brute=False)
                forecast = fitted.forecast(holdout_size)
                mape = _calculate_holdout_mape(test, forecast)
                
                if mape < best_mape:
                    best_mape = mape
                    best_damped = damped
            except Exception as e:
                logger.debug(f"Holt Linear (damped={damped}) falhou: {e}")
                continue
        
        if best_mape == float('inf'):
            return False
        
        try:
            full_model = ExponentialSmoothing(
                series, trend='add', damped_trend=best_damped,
                seasonal=None, initialization_method='estimated'
            )
            self.fitted = full_model.fit(optimized=True, use_brute=False)
            self.mape = best_mape
            self.damped = best_damped
            logger.info(f"Holt Linear treinado: damped={best_damped}, MAPE holdout={best_mape:.2f}%")
            return True
        except Exception as e:
            logger.warning(f"Holt Linear treino final falhou: {e}")
            return False
    
    def predict(self, periods: int) -> Optional[pd.Series]:
        if self.fitted is None:
            return None
        try:
            return self.fitted.forecast(periods)
        except Exception as e:
            logger.warning(f"Holt Linear previsão falhou: {e}")
            return None
    
    def get_mape(self) -> float:
        return self.mape if self.mape is not None else float('inf')


class HoltWintersModel:
    """Holt-Winters (Triple Exponential Smoothing) — para séries longas (24+ pontos).
    
    Tendência aditiva + sazonalidade (aditiva ou multiplicativa).
    Precisa de pelo menos 2 ciclos sazonais completos.
    """
    
    MIN_SEASONAL_PERIODS = 2
    
    def __init__(self, seasonal_periods: int = 12):
        self.seasonal_periods = seasonal_periods
        self.fitted = None
        self.mode = None
        self.mape = None
    
    @staticmethod
    def is_available() -> bool:
        return STATSMODELS_AVAILABLE
    
    def can_fit(self, n_points: int) -> bool:
        return (STATSMODELS_AVAILABLE and 
                n_points >= self.seasonal_periods * self.MIN_SEASONAL_PERIODS)
    
    def fit(self, series: pd.Series, freq: str = 'MS') -> bool:
        if not self.can_fit(len(series)):
            return False
        
        try:
            series = _prepare_series(series, freq)
        except Exception as e:
            logger.debug(f"Holt-Winters: falha ao preparar série: {e}")
            return False
        
        holdout_size = min(max(3, len(series) // 5), self.seasonal_periods)
        train, test = series[:-holdout_size], series[-holdout_size:]
        
        if len(train) < self.seasonal_periods * 2:
            return False
        
        best_mape = float('inf')
        best_model = None
        
        for mode in ['add', 'mul']:
            try:
                model = ExponentialSmoothing(
                    train, trend='add', seasonal=mode,
                    seasonal_periods=self.seasonal_periods,
                    initialization_method='estimated'
                )
                fitted = model.fit(optimized=True, use_brute=False)
                forecast = fitted.forecast(holdout_size)
                mape = _calculate_holdout_mape(test, forecast)
                
                if mape < best_mape:
                    best_mape = mape
                    best_model = (mode, 'add')
            except Exception as e:
                logger.debug(f"Holt-Winters {mode} falhou: {e}")
                continue
        
        if best_model is None:
            return False
        
        try:
            mode, trend_mode = best_model
            full_model = ExponentialSmoothing(
                series, trend=trend_mode, seasonal=mode,
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
        if self.fitted is None:
            return None
        try:
            return self.fitted.forecast(periods)
        except Exception as e:
            logger.warning(f"Holt-Winters previsão falhou: {e}")
            return None
    
    def get_mape(self) -> float:
        return self.mape if self.mape is not None else float('inf')


ForecastModel = Union[SimpleESModel, HoltLinearModel, HoltWintersModel]

MODEL_DISPLAY_NAMES = {
    'decomposition': 'Decomposição',
    'ses': 'SES',
    'holt_linear': 'Holt Linear',
    'holt_winters': 'Holt-Winters',
}


def select_best_model(
    series: pd.Series,
    decomposition_predictions: List[float],
    freq: str = 'MS',
    seasonal_periods: int = 12,
    force_model: Optional[str] = None
) -> Tuple[str, Optional[ForecastModel], float]:
    """Compara todos os modelos disponíveis e retorna o melhor por MAPE.
    
    Cascata por quantidade de dados:
      - 3+ pontos: testa SES
      - 5+ pontos: testa SES + Holt Linear
      - 24+ pontos: testa SES + Holt Linear + Holt-Winters
    
    Args:
        series: Série temporal com index DatetimeIndex
        decomposition_predictions: Previsões in-sample da decomposição
        freq: Frequência da série
        seasonal_periods: Períodos sazonais (12 mensal, 52 semanal)
        force_model: Forçar modelo específico ("ses", "holt_linear", "holt_winters")
                     None ou "auto" = seleção automática
    
    Returns:
        (model_name, model_instance_or_None, best_mape)
    """
    n = len(series)
    
    decomp_preds = np.array(decomposition_predictions[:n])
    actual = series.values[:len(decomp_preds)]
    mask = actual > 0
    decomp_mape = float(np.mean(np.abs((actual[mask] - decomp_preds[mask]) / actual[mask])) * 100) if mask.any() else 0.0
    
    if force_model and force_model != 'auto':
        return _fit_forced_model(series, freq, seasonal_periods, force_model, decomp_mape)
    
    candidates: List[Tuple[str, ForecastModel]] = []
    
    ses = SimpleESModel()
    if ses.can_fit(n):
        candidates.append(('ses', ses))
    
    holt = HoltLinearModel()
    if holt.can_fit(n):
        candidates.append(('holt_linear', holt))
    
    hw = HoltWintersModel(seasonal_periods=seasonal_periods)
    if hw.can_fit(n):
        candidates.append(('holt_winters', hw))
    
    if not candidates:
        return ('decomposition', None, decomp_mape)
    
    best_name = 'decomposition'
    best_model: Optional[ForecastModel] = None
    best_mape = decomp_mape
    
    for name, model in candidates:
        try:
            success = model.fit(series, freq=freq)
            if success:
                mape = model.get_mape()
                logger.info(f"  {name}: MAPE={mape:.2f}%")
                if mape < best_mape * 0.9:
                    best_name = name
                    best_model = model
                    best_mape = mape
        except Exception as e:
            logger.debug(f"  {name}: falha inesperada: {e}")
            continue
    
    logger.info(f"Model selection: decomp={decomp_mape:.2f}% -> winner={best_name} ({best_mape:.2f}%)")
    return (best_name, best_model, best_mape)


def _fit_forced_model(
    series: pd.Series, freq: str, seasonal_periods: int,
    force_model: str, decomp_mape: float
) -> Tuple[str, Optional[ForecastModel], float]:
    """Tenta treinar o modelo forçado pelo usuário."""
    model_map = {
        'ses': SimpleESModel,
        'holt_linear': HoltLinearModel,
        'holt_winters': lambda: HoltWintersModel(seasonal_periods),
    }
    
    if force_model == 'decomposition':
        return ('decomposition', None, decomp_mape)
    
    factory = model_map.get(force_model)
    if factory is None:
        logger.warning(f"Modelo desconhecido '{force_model}', usando auto")
        return ('decomposition', None, decomp_mape)
    
    model = factory() if callable(factory) else factory
    if not model.can_fit(len(series)):
        logger.warning(f"Dados insuficientes para '{force_model}', fallback para decomposição")
        return ('decomposition', None, decomp_mape)
    
    if model.fit(series, freq=freq):
        return (force_model, model, model.get_mape())
    
    logger.warning(f"'{force_model}' falhou no treino, fallback para decomposição")
    return ('decomposition', None, decomp_mape)
