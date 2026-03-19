from flask import Flask, request, jsonify
import pandas as pd
import logging
import json
import traceback
from modelo import ModeloAjustado
from mrp import MRPOptimizer, OptimizationParams

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Converte tipos numpy para tipos nativos do Python para serialização JSON"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif hasattr(obj, 'item'):
        return obj.item()
    elif hasattr(obj, 'tolist'):
        return obj.tolist()
    else:
        return obj

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True) or {}
    
    sales_data = data.get("sales_data", [])
    logger.info(f"Predict chamado - registros: {len(sales_data) if sales_data else 0}")

    # Validações
    gran = data.get("granularidade", "M").upper()
    if gran not in ["M", "S", "D"]:
        return jsonify({"error":"'granularidade' deve ser 'M', 'S' ou 'D'."}), 400
    
    # Verificar se é agrupamento trimestral ou semestral
    agrupamento_trimestral = data.get("agrupamento_trimestral", False)
    agrupamento_semestral = data.get("agrupamento_semestral", False)
    
    # Validar que não sejam solicitados ambos ao mesmo tempo
    if agrupamento_trimestral and agrupamento_semestral:
        return jsonify({"error": "Não é possível usar agrupamento trimestral e semestral simultaneamente."}), 400
    
    # Para agrupamento trimestral ou semestral, forçar granularidade mensal
    if (agrupamento_trimestral or agrupamento_semestral) and gran != "M":
        tipo_agrupamento = "trimestral" if agrupamento_trimestral else "semestral"
        logger.info(f"Agrupamento {tipo_agrupamento} solicitado - forçando granularidade mensal")
        gran = "M"

    try:
        periods = int(data.get("periodos", 0))
    except (ValueError, TypeError):
        return jsonify({"error":"'periodos' deve ser inteiro."}), 400
    if periods < 1:
        return jsonify({"error":"'periodos' deve ser >= 1."}), 400

    try:
        start_date = pd.to_datetime(data.get("data_inicio",""), format="%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"error":"'data_inicio' inválido. Use YYYY-MM-DD."}), 400

    if not isinstance(sales_data, list) or not sales_data:
        return jsonify({"error":"'sales_data' deve ser lista não vazia."}), 400

    # Verifica se os dados têm as colunas necessárias
    df = pd.DataFrame(sales_data)
    if not {"item_id","timestamp","demand"}.issubset(df.columns):
        return jsonify({"error":"Cada registro precisa ter 'item_id','timestamp','demand'."}), 400

    try:
        # Prepara os dados para o modelo
        items_data = {}
        for item_id, grp in df.groupby("item_id"):
            items_data[int(item_id)] = {
                "timestamps": grp["timestamp"].tolist(),
                "demands": pd.to_numeric(grp["demand"], errors="coerce").tolist()
            }
        
        # Configurações do modelo
        seasonality_mode = data.get("seasonality_mode", "multiplicative")
        seasonal_smooth = float(data.get("seasonal_smooth", 0.7))  # Corrigido de seasonal_alpha para seasonal_smooth
        
        # Parâmetros de intervalo de confiança
        confidence_level = float(data.get("confidence_level", 0.95))
        confidence_factor = float(data.get("confidence_factor", 0.7))
        
        # Parâmetros de ajuste de valores
        growth_factor = float(data.get("growth_factor", 1.0))
        replicate_only = bool(data.get("replicate_only", False))
        
        forecast_model = data.get("forecast_model", "auto").lower()
        valid_models = ("auto", "ses", "holt_linear", "holt_winters", "decomposition")
        if forecast_model not in valid_models:
            return jsonify({"error": f"'forecast_model' deve ser um de: {', '.join(valid_models)}"}), 400
        
        # Ajustes específicos por mês
        month_adjustments = data.get("month_adjustments", {})
        if isinstance(month_adjustments, str):
            try:
                month_adjustments = json.loads(month_adjustments)
            except Exception as e:
                logger.warning(f"Erro ao processar ajustes por mês: {e}")
                month_adjustments = {}
        
        # Converter chaves string para inteiros, se necessário
        if month_adjustments and all(isinstance(k, str) for k in month_adjustments.keys()):
            month_adjustments = {int(k): float(v) for k, v in month_adjustments.items()}
            
        # Ajustes específicos por dia da semana
        day_of_week_adjustments = data.get("day_of_week_adjustments", {})
        if isinstance(day_of_week_adjustments, str):
            try:
                day_of_week_adjustments = json.loads(day_of_week_adjustments)
            except Exception as e:
                logger.warning(f"Erro ao processar ajustes por dia da semana: {e}")
                day_of_week_adjustments = {}
        
        # Converter chaves string para inteiros, se necessário
        if day_of_week_adjustments and all(isinstance(k, str) for k in day_of_week_adjustments.keys()):
            day_of_week_adjustments = {int(k): float(v) for k, v in day_of_week_adjustments.items()}
        
        logger.info(f"Aplicando fator de crescimento: {growth_factor}")
        if month_adjustments:
            logger.info(f"Ajustes específicos por mês: {month_adjustments}")
        if day_of_week_adjustments:
            # Converter números de dias para nomes para melhor legibilidade no log
            dias_semana = {0: 'Segunda', 1: 'Terça', 2: 'Quarta', 3: 'Quinta', 4: 'Sexta', 5: 'Sábado', 6: 'Domingo'}
            ajustes_legivel = {dias_semana.get(int(k), k): v for k, v in day_of_week_adjustments.items()}
            logger.info(f"Ajustes específicos por dia da semana: {ajustes_legivel}")
        
        # Configurações de feriados
        feriados_enabled = data.get("feriados_enabled", True)
        feriados_adjustments = data.get("feriados_adjustments", {})
        anos_feriados = data.get("anos_feriados", None)
        
        logger.info(f"Feriados habilitados: {feriados_enabled}")
        if feriados_adjustments:
            logger.info(f"Ajustes para feriados: {feriados_adjustments}")
        if anos_feriados:
            logger.info(f"Anos de feriados: {anos_feriados}")
            
        # Configurações de explicabilidade
        include_explanation = data.get("include_explanation", False)
        explanation_level = data.get("explanation_level", "basic")
        explanation_language = data.get("explanation_language", "pt")
        html_layout = data.get("html_layout", "full")  # NOVO: Layout do HTML
        
        # Validar parâmetros de explicabilidade
        if explanation_level not in ["basic", "detailed", "advanced"]:
            explanation_level = "basic"
            logger.warning(f"explanation_level inválido, usando 'basic'")
            
        if explanation_language not in ["pt", "en"]:
            explanation_language = "pt"
            logger.warning(f"explanation_language inválido, usando 'pt'")
            
        if html_layout not in ["full", "compact"]:
            html_layout = "full"
            logger.warning(f"html_layout inválido, usando 'full'")
            
        logger.info(f"Explicações habilitadas: {include_explanation}")
        if include_explanation:
            logger.info(f"Nível de explicação: {explanation_level}")
            logger.info(f"Idioma das explicações: {explanation_language}")
            logger.info(f"Layout HTML: {html_layout}")
            
        if agrupamento_trimestral:
            logger.info(f"MODO TRIMESTRAL ATIVADO - Períodos interpretados como trimestres")
        elif agrupamento_semestral:
            logger.info(f"MODO SEMESTRAL ATIVADO - Períodos interpretados como semestres")
        
        # Criar e treinar o modelo
        model = ModeloAjustado(
            granularity=gran, 
            seasonality_mode=seasonality_mode,
            seasonal_smooth=seasonal_smooth,
            outlier_threshold=float(data.get("outlier_threshold", 2.5)),
            trend_window=3,
            confidence_level=confidence_level,
            confidence_factor=confidence_factor,
            growth_factor=growth_factor,
            replicate_only=replicate_only,
            forecast_model=forecast_model,
            month_adjustments=month_adjustments,
            day_of_week_adjustments=day_of_week_adjustments,
            feriados_enabled=feriados_enabled,
            feriados_adjustments=feriados_adjustments,
            anos_feriados=anos_feriados,
            include_explanation=include_explanation,
            explanation_level=explanation_level,
            explanation_language=explanation_language,
            html_layout=html_layout
        )
        
        model.fit_multiple(items_data)
        
        # Gera previsões para todos os itens
        item_ids = list(items_data.keys())
        
        # Escolher método de previsão baseado no agrupamento solicitado
        if agrupamento_trimestral:
            forecast_results = model.predict_quarterly_multiple(
                items=item_ids,
                start_date=start_date.strftime("%Y-%m-%d"),
                periods=periods  # períodos = número de trimestres
            )
        elif agrupamento_semestral:
            forecast_results = model.predict_semiannually_multiple(
                items=item_ids,
                start_date=start_date.strftime("%Y-%m-%d"),
                periods=periods  # períodos = número de semestres
            )
        else:
            forecast_results = model.predict_multiple(
                items=item_ids, 
                start_date=start_date.strftime("%Y-%m-%d"), 
                periods=periods
            )
        
        logger.info(f"Previsão concluída - {len(forecast_results)} resultados gerados")
        
        return jsonify({"forecast": forecast_results})
    
    except Exception as ex:
        logger.error(f"Erro ao processar previsão: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha na previsão: {str(ex)}"}), 500

@app.route('/predict_quarterly', methods=['POST'])
def predict_quarterly():
    """
    Endpoint dedicado para previsões trimestrais (agrupadas por 3 em 3 meses)
    
    Parâmetros esperados:
    - sales_data: Lista de registros de vendas
    - data_inicio: Data de início das previsões (YYYY-MM-DD)
    - trimestres: Número de trimestres para prever
    - Outros parâmetros opcionais (mesmos do endpoint principal)
    """
    data = request.get_json(force=True) or {}
    
    data["granularidade"] = "M"
    data["agrupamento_trimestral"] = True
    data["agrupamento_semestral"] = False
    
    if "trimestres" in data:
        data["periodos"] = data["trimestres"]
    
    return predict()

@app.route('/predict_semiannually', methods=['POST'])
def predict_semiannually():
    """
    Endpoint dedicado para previsões semestrais (agrupadas por 6 em 6 meses)
    
    Parâmetros esperados:
    - sales_data: Lista de registros de vendas
    - data_inicio: Data de início das previsões (YYYY-MM-DD)
    - semestres: Número de semestres para prever
    - Outros parâmetros opcionais (mesmos do endpoint principal)
    """
    data = request.get_json(force=True) or {}
    
    data["granularidade"] = "M"
    data["agrupamento_semestral"] = True
    data["agrupamento_trimestral"] = False
    
    if "semestres" in data:
        data["periodos"] = data["semestres"]
    
    return predict()

@app.route('/generate_html', methods=['POST'])
def generate_html():
    """
    Endpoint dedicado para gerar HTML a partir dos dados de explicação
    
    Parâmetros esperados:
    - item_id: ID do item
    - prediction: Dados da previsão (yhat, yhat_lower, yhat_upper, trend, yearly, ds)
    - explanation_data: Dados de explicação (summary, components, etc.)
    - layout: "full" ou "compact" (padrão: "full")
    - is_quarterly: Se é previsão trimestral (padrão: false)
    - quarterly_info: Informações do trimestre (se aplicável)
    - is_semiannual: Se é previsão semestral (padrão: false)
    - semiannual_info: Informações do semestre (se aplicável)
    - return_html_direct: True para retornar HTML puro (padrão: False = JSON)
    
    Headers:
    - Accept: text/html -> retorna HTML puro para exibição direta no navegador
    - Accept: application/json -> retorna JSON com HTML (padrão)
    """
    try:
        data = request.get_json(force=True) or {}
        
        wants_html_direct = (
            request.headers.get('Accept', '').startswith('text/html') or
            data.get('return_html_direct', False)
        )
        
        if 'html_data' in data:
            html_data_from_db = data['html_data']
            layout = data.get('layout', 'full')
            item_id = html_data_from_db['item_id']
            prediction = html_data_from_db['prediction']
            explanation_data = html_data_from_db['explanation_data']
            is_quarterly = html_data_from_db.get('is_quarterly', False)
            quarterly_info = html_data_from_db.get('quarterly_info')
            is_semiannual = html_data_from_db.get('is_semiannual', False)
            semiannual_info = html_data_from_db.get('semiannual_info')
            
            # Converter data ISO de volta para pd.Timestamp
            try:
                date = pd.to_datetime(html_data_from_db['date_iso'])
            except Exception as e:
                if wants_html_direct:
                    return f"<html><body><h1>Erro: Data inválida em html_data: {str(e)}</h1></body></html>", 400, {'Content-Type': 'text/html; charset=utf-8'}
                return jsonify({"error": f"Data inválida em html_data: {str(e)}"}), 400
                
        else:
            # Modo completo: validar parâmetros individuais
            required_fields = ['item_id', 'prediction']
            for field in required_fields:
                if field not in data:
                    if wants_html_direct:
                        return f"<html><body><h1>Erro: Campo obrigatório '{field}' não fornecido</h1></body></html>", 400, {'Content-Type': 'text/html; charset=utf-8'}
                    return jsonify({"error": f"Campo obrigatório '{field}' não fornecido"}), 400
            
            # Extrair parâmetros individuais
            item_id = data['item_id']
            prediction = data['prediction']
            explanation_data = data.get('explanation_data', {})
            layout = data.get('layout', 'full')
            is_quarterly = data.get('is_quarterly', False)
            quarterly_info = data.get('quarterly_info')
            is_semiannual = data.get('is_semiannual', False)
            semiannual_info = data.get('semiannual_info')
            
            # Converter data string para pd.Timestamp
            try:
                date = pd.to_datetime(prediction['ds'])
            except Exception as e:
                if wants_html_direct:
                    return f"<html><body><h1>Erro: Data inválida em 'prediction.ds': {str(e)}</h1></body></html>", 400, {'Content-Type': 'text/html; charset=utf-8'}
                return jsonify({"error": f"Data inválida em 'prediction.ds': {str(e)}"}), 400
        
        if layout not in ['full', 'compact']:
            layout = 'full'
        
        # Validar prediction apenas no modo completo
        if 'html_data' not in data:
            required_prediction_fields = ['yhat', 'yhat_lower', 'yhat_upper', 'trend', 'yearly', 'ds']
            for field in required_prediction_fields:
                if field not in prediction:
                    if wants_html_direct:
                        return f"<html><body><h1>Erro: Campo obrigatório 'prediction.{field}' não fornecido</h1></body></html>", 400, {'Content-Type': 'text/html; charset=utf-8'}
                    return jsonify({"error": f"Campo obrigatório 'prediction.{field}' não fornecido"}), 400
        
        seasonality_mode = explanation_data.get('seasonality_mode', 'multiplicative')
        month_adjustments = explanation_data.get('month_adjustments', {})
        day_of_week_adjustments = explanation_data.get('day_of_week_adjustments', {})
        growth_factor = explanation_data.get('growth_factor', 1.0)
        confidence_level = explanation_data.get('confidence_level', 0.95)
        
        replicate_only = False
        if 'html_data' in data:
            replicate_only = html_data_from_db.get('replicate_only', False)
        else:
            replicate_only = data.get('replicate_only', False)
        
        modelo_temp = ModeloAjustado(
            granularity='M',
            seasonality_mode=seasonality_mode,
            include_explanation=True,
            explanation_level='detailed',
            explanation_language='pt',
            html_layout=layout,
            month_adjustments=month_adjustments,
            day_of_week_adjustments=day_of_week_adjustments,
            growth_factor=growth_factor,
            confidence_level=confidence_level,
            replicate_only=replicate_only
        )
        
        # Criar dados completos do modelo e métricas (simulados a partir dos dados de explicação)
        model_data = {
            'b': explanation_data.get('trend_slope', 0),  # Slope da tendência
            'seasonal_pattern': explanation_data.get('seasonal_pattern', {}),
            'day_of_week_pattern': explanation_data.get('day_of_week_pattern', {}),
            'mean': prediction.get('yhat', 100),
            'std': explanation_data.get('std', 10),
            'baseline': explanation_data.get('model_baseline', prediction.get('trend', 100) * 0.5)
        }
        
        metrics_data = {
            'data_points': explanation_data.get('data_points', 12),
            'confidence_score': explanation_data.get('confidence_score', 'Média'),
            'mape': explanation_data.get('mape', 15.0),
            'r2': explanation_data.get('r2', 0.7),
            'outlier_count': explanation_data.get('outlier_count', 0),
            'data_completeness': explanation_data.get('data_completeness', 100.0),
            'seasonal_strength': explanation_data.get('seasonal_strength', 0.3),
            'trend_strength': explanation_data.get('trend_strength', 0.2),
            'training_period': explanation_data.get('training_period', {
                'start': '2023-01-01',
                'end': '2023-12-01'
            })
        }
        
        # Armazenar temporariamente no modelo (necessário para as funções internas)
        modelo_temp.models[item_id] = model_data
        modelo_temp.quality_metrics[item_id] = metrics_data
        
        chart_data = html_data_from_db.get('chart_data') if 'html_data' in data else None
        if chart_data:
            modelo_temp._chart_data = {item_id: chart_data}
        
        # Determinar informações do período
        if is_quarterly and quarterly_info:
            period_name = quarterly_info.get('quarter_name', f"Q{((date.month - 1) // 3) + 1}/{date.year}")
            period_type = "trimestre"
        elif is_semiannual and semiannual_info:
            period_name = semiannual_info.get('semester_name', f"S{1 if date.month <= 6 else 2}/{date.year}")
            period_type = "semestre"
        else:
            month_name = modelo_temp._get_month_name_pt(date.month)
            period_name = f"{month_name}/{date.year}"
            period_type = "mês"
        
        # Análise de confiança
        confidence = metrics_data['confidence_score']
        confidence_color = "#28a745" if confidence == "Alta" else "#ffc107" if confidence == "Média" else "#dc3545"
        
        # Gerar HTML usando as funções internas
        if layout == "compact":
            html_content = modelo_temp._generate_compact_html(
                item_id, prediction, date, is_quarterly, quarterly_info, is_semiannual, semiannual_info,
                model_data, metrics_data, period_name, period_type, 
                confidence, confidence_color
            )
        else:
            html_content = modelo_temp._generate_html_summary(
                item_id, prediction, date, is_quarterly, quarterly_info, is_semiannual, semiannual_info, layout
            )
        
        if wants_html_direct:
            return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        else:
            return jsonify({
                "html": html_content,
                "info": {
                    "layout": layout,
                    "size_chars": len(html_content),
                    "is_quarterly": is_quarterly,
                    "is_semiannual": is_semiannual,
                    "item_id": item_id,
                    "period": period_name
                }
            })
        
    except Exception as ex:
        logger.error(f"Erro ao gerar HTML: {str(ex)}")
        logger.error(traceback.format_exc())
        
        try:
            body = request.get_json(force=True, silent=True, cache=False) or {}
            wants_html = (
                request.headers.get('Accept', '').startswith('text/html') or
                body.get('return_html_direct', False)
            )
        except Exception:
            wants_html = False
        
        if wants_html:
            return f"<html><body><h1>Erro interno: {str(ex)}</h1><p>Detalhes técnicos ocultos por segurança.</p></body></html>", 500, {'Content-Type': 'text/html; charset=utf-8'}
        else:
            return jsonify({"error": f"Falha na geração de HTML: {str(ex)}"}), 500

@app.route('/mrp_optimize', methods=['POST'])
def mrp_optimize():
    """
    Endpoint para otimização MRP usando algoritmos inteligentes de supply chain
    
    Parâmetros esperados:
    - daily_demands: Dict com demandas diárias {"YYYY-MM": demanda_média_diária}
    - initial_stock: Estoque inicial (float)
    - leadtime_days: Lead time em dias (int)
    - period_start_date: Data início do período (YYYY-MM-DD)
    - period_end_date: Data fim do período (YYYY-MM-DD)
    - start_cutoff_date: Data de corte inicial (YYYY-MM-DD)
    - end_cutoff_date: Data de corte final (YYYY-MM-DD)
    
    Parâmetros opcionais de otimização:
    - setup_cost: Custo fixo por pedido (padrão: 250.0)
    - holding_cost_rate: Taxa de custo de manutenção (padrão: 0.20)
    - stockout_cost_multiplier: Multiplicador de custo de falta (padrão: 2.5)
    - service_level: Nível de serviço desejado (padrão: 0.95)
    - min_batch_size: Tamanho mínimo do lote (padrão: 50.0)
    - max_batch_size: Tamanho máximo do lote (padrão: 10000.0)
    - review_period_days: Período de revisão em dias (padrão: 7)
    - safety_days: Dias de segurança adicional (padrão: 3)
    - consolidation_window_days: Janela para consolidar pedidos (padrão: 5)
    - daily_production_capacity: Capacidade diária de produção (padrão: infinito)
    - enable_eoq_optimization: Habilitar otimização EOQ (padrão: True)
    - enable_consolidation: Habilitar consolidação de pedidos (padrão: True)
    - ignore_safety_stock: Ignorar completamente estoque de segurança (padrão: False)
    - exact_quantity_match: Garantir que estoque total (inicial + produzido) seja exatamente igual à demanda total (padrão: False)
    
    - force_excess_production: Forçar produção real mesmo com estoque suficiente - sobreprodução (padrão: False)
    """
    try:
        data = request.get_json(force=True) or {}
        logger.info("MRP Optimize chamado")
        
        required_fields = [
            'daily_demands', 'initial_stock', 'leadtime_days',
            'period_start_date', 'period_end_date', 
            'start_cutoff_date', 'end_cutoff_date'
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório '{field}' não fornecido"}), 400
        
        # Validar tipos de dados
        try:
            initial_stock = float(data['initial_stock'])
            leadtime_days = int(data['leadtime_days'])
        except (ValueError, TypeError):
            return jsonify({"error": "initial_stock deve ser número e leadtime_days deve ser inteiro"}), 400
        
        if initial_stock < 0:
            return jsonify({"error": "initial_stock não pode ser negativo"}), 400
            
        if leadtime_days < 0:
            return jsonify({"error": "leadtime_days não pode ser negativo"}), 400
        
        # Validar daily_demands
        daily_demands = data['daily_demands']
        if not isinstance(daily_demands, dict) or not daily_demands:
            return jsonify({"error": "daily_demands deve ser dicionário não vazio"}), 400
        
        # Validar formato das demandas
        for date_key, demand_value in daily_demands.items():
            try:
                # Verificar formato da data (YYYY-MM)
                pd.to_datetime(date_key + '-01')
                # Verificar se demanda é numérica
                float(demand_value)
            except (ValueError, TypeError):
                return jsonify({"error": f"Formato inválido em daily_demands. Chave '{date_key}' deve ser YYYY-MM e valor deve ser numérico"}), 400
        
        # Validar datas
        try:
            period_start_date = data['period_start_date']
            period_end_date = data['period_end_date']
            start_cutoff_date = data['start_cutoff_date']
            end_cutoff_date = data['end_cutoff_date']
            
            start_pd = pd.to_datetime(period_start_date)
            end_pd = pd.to_datetime(period_end_date)
            start_cutoff_pd = pd.to_datetime(start_cutoff_date)
            end_cutoff_pd = pd.to_datetime(end_cutoff_date)
            
            if start_pd >= end_pd:
                return jsonify({"error": "period_start_date deve ser anterior a period_end_date"}), 400
            if start_cutoff_pd > end_cutoff_pd:
                return jsonify({"error": "start_cutoff_date deve ser anterior ou igual a end_cutoff_date"}), 400
            
        except (ValueError, TypeError, KeyError):
            return jsonify({"error": "Datas devem estar no formato YYYY-MM-DD"}), 400
        
        # Validar demandas negativas
        for date_key, demand_value in daily_demands.items():
            if float(demand_value) < 0:
                return jsonify({"error": f"Demanda em '{date_key}' não pode ser negativa"}), 400
        
        # Extrair parâmetros opcionais de otimização
        optimization_kwargs = {}
        optional_params = [
            'setup_cost', 'holding_cost_rate', 'stockout_cost_multiplier',
            'service_level', 'min_batch_size', 'max_batch_size',
            'review_period_days', 'safety_days', 'consolidation_window_days',
            'daily_production_capacity', 'enable_eoq_optimization', 'enable_consolidation',
            'include_extended_analytics', 'ignore_safety_stock', 'exact_quantity_match',
            'auto_calculate_max_batch_size', 'max_batch_multiplier',
            'force_excess_production', 'unit_value', 'leadtime_std',
            'min_stock_level'
        ]
        
        for param in optional_params:
            if param in data:
                optimization_kwargs[param] = data[param]
        
        logger.info(f"MRP Optimize params: ignore_safety_stock={optimization_kwargs.get('ignore_safety_stock', 'N/A')}, min_stock_level={optimization_kwargs.get('min_stock_level', 'N/A')}, exact_quantity_match={optimization_kwargs.get('exact_quantity_match', 'N/A')}")
        
        optimizer = MRPOptimizer()
        
        result = optimizer.calculate_batches_with_start_end_cutoff(
            daily_demands=daily_demands,
            initial_stock=initial_stock,
            leadtime_days=leadtime_days,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            start_cutoff_date=start_cutoff_date,
            end_cutoff_date=end_cutoff_date,
            **optimization_kwargs
        )
        
        logger.info(f"MRP concluído - {len(result['batches'])} lotes planejados")
        
        result_converted = convert_numpy_types(result)
        
        return jsonify(result_converted)
        
    except Exception as ex:
        logger.error(f"Erro na otimização MRP: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha na otimização MRP: {str(ex)}"}), 500

def _validate_sporadic_mrp_params(data: dict):
    """Validação compartilhada para endpoints mrp_sporadic e mrp_advanced.
    
    Retorna (params_dict, None) em sucesso ou (None, error_response) em falha.
    """
    required_fields = [
        'sporadic_demand', 'initial_stock', 'leadtime_days',
        'period_start_date', 'period_end_date',
        'start_cutoff_date', 'end_cutoff_date'
    ]
    
    for field in required_fields:
        if field not in data:
            return None, (jsonify({"error": f"Campo obrigatório '{field}' não fornecido"}), 400)
    
    try:
        initial_stock = float(data['initial_stock'])
        leadtime_days = int(data['leadtime_days'])
    except (ValueError, TypeError):
        return None, (jsonify({"error": "initial_stock deve ser número e leadtime_days deve ser inteiro"}), 400)
    
    if initial_stock < 0:
        return None, (jsonify({"error": "initial_stock não pode ser negativo"}), 400)
    if leadtime_days < 0:
        return None, (jsonify({"error": "leadtime_days não pode ser negativo"}), 400)
    
    sporadic_demand = data['sporadic_demand']
    if not isinstance(sporadic_demand, dict) or not sporadic_demand:
        return None, (jsonify({"error": "sporadic_demand deve ser dicionário não vazio"}), 400)
    
    for date_key, demand_value in sporadic_demand.items():
        try:
            pd.to_datetime(date_key)
            demand_val = float(demand_value)
            if demand_val < 0:
                return None, (jsonify({"error": f"Demanda em '{date_key}' não pode ser negativa"}), 400)
        except (ValueError, TypeError):
            return None, (jsonify({"error": f"Formato inválido em sporadic_demand. Chave '{date_key}' deve ser YYYY-MM-DD e valor deve ser numérico positivo"}), 400)
    
    try:
        period_start_date = data['period_start_date']
        period_end_date = data['period_end_date']
        start_cutoff_date = data['start_cutoff_date']
        end_cutoff_date = data['end_cutoff_date']
        
        start_pd = pd.to_datetime(period_start_date)
        end_pd = pd.to_datetime(period_end_date)
        start_cutoff_pd = pd.to_datetime(start_cutoff_date)
        end_cutoff_pd = pd.to_datetime(end_cutoff_date)
        
        if start_pd >= end_pd:
            return None, (jsonify({"error": "period_start_date deve ser anterior a period_end_date"}), 400)
        if start_cutoff_pd > end_cutoff_pd:
            return None, (jsonify({"error": "start_cutoff_date deve ser anterior ou igual a end_cutoff_date"}), 400)
    except (ValueError, TypeError, KeyError):
        return None, (jsonify({"error": "Datas devem estar no formato YYYY-MM-DD"}), 400)
    
    safety_margin_percent = float(data.get('safety_margin_percent', 8.0))
    safety_days = int(data.get('safety_days', 2))
    minimum_stock_percent = float(data.get('minimum_stock_percent', 0.0))
    max_gap_days = int(data.get('max_gap_days', 999))
    
    if safety_margin_percent < 0 or safety_margin_percent > 100:
        return None, (jsonify({"error": "safety_margin_percent deve estar entre 0 e 100"}), 400)
    if safety_days < 0:
        return None, (jsonify({"error": "safety_days não pode ser negativo"}), 400)
    if minimum_stock_percent < 0 or minimum_stock_percent > 100:
        return None, (jsonify({"error": "minimum_stock_percent deve estar entre 0 e 100"}), 400)
    if max_gap_days < 1:
        return None, (jsonify({"error": "max_gap_days deve ser pelo menos 1"}), 400)
    
    return {
        'initial_stock': initial_stock,
        'leadtime_days': leadtime_days,
        'sporadic_demand': sporadic_demand,
        'period_start_date': period_start_date,
        'period_end_date': period_end_date,
        'start_cutoff_date': start_cutoff_date,
        'end_cutoff_date': end_cutoff_date,
        'safety_margin_percent': safety_margin_percent,
        'safety_days': safety_days,
        'minimum_stock_percent': minimum_stock_percent,
        'max_gap_days': max_gap_days,
    }, None


@app.route('/mrp_sporadic', methods=['POST'])
def mrp_sporadic():
    """Endpoint para planejamento de lotes para demandas esporádicas."""
    try:
        data = request.get_json(force=True) or {}
        logger.info("MRP Sporadic chamado")
        
        params, error = _validate_sporadic_mrp_params(data)
        if error:
            return error
        
        optimization_kwargs = {}
        for param in ['setup_cost', 'holding_cost_rate', 'stockout_cost_multiplier',
                      'service_level', 'min_batch_size', 'max_batch_size',
                      'review_period_days', 'consolidation_window_days',
                      'daily_production_capacity', 'enable_eoq_optimization', 'enable_consolidation',
                      'auto_calculate_max_batch_size', 'max_batch_multiplier']:
            if param in data:
                optimization_kwargs[param] = data[param]
        
        min_stock_level = float(data.get('min_stock_level', 0.0))
        
        optimizer = MRPOptimizer()
        result = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=params['sporadic_demand'],
            initial_stock=params['initial_stock'],
            leadtime_days=params['leadtime_days'],
            period_start_date=params['period_start_date'],
            period_end_date=params['period_end_date'],
            start_cutoff_date=params['start_cutoff_date'],
            end_cutoff_date=params['end_cutoff_date'],
            safety_margin_percent=params['safety_margin_percent'],
            safety_days=params['safety_days'],
            minimum_stock_percent=params['minimum_stock_percent'],
            max_gap_days=params['max_gap_days'],
            min_stock_level=min_stock_level,
            **optimization_kwargs
        )
        
        logger.info(f"MRP Sporadic concluído - {len(result['batches'])} lotes planejados")
        return jsonify(convert_numpy_types(result))
        
    except Exception as ex:
        logger.error(f"Erro no planejamento de demanda esporádica: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha no planejamento de demanda esporádica: {str(ex)}"}), 500

@app.route('/mrp_advanced', methods=['POST'])
def mrp_advanced():
    """Endpoint MRP Avançado com Analytics Estendidos."""
    try:
        data = request.get_json(force=True) or {}
        logger.info("MRP Advanced chamado")
        
        params, error = _validate_sporadic_mrp_params(data)
        if error:
            return error
        
        # Parâmetros avançados de otimização
        optimization_params = OptimizationParams()
        
        # Parâmetros de custo
        if 'setup_cost' in data:
            optimization_params.setup_cost = float(data['setup_cost'])
        if 'holding_cost_rate' in data:
            optimization_params.holding_cost_rate = float(data['holding_cost_rate'])
        if 'stockout_cost_multiplier' in data:
            optimization_params.stockout_cost_multiplier = float(data['stockout_cost_multiplier'])
        
        # Parâmetros de serviço
        if 'service_level' in data:
            optimization_params.service_level = float(data['service_level'])
            if optimization_params.service_level < 0 or optimization_params.service_level > 1:
                return jsonify({"error": "service_level deve estar entre 0 e 1"}), 400
        
        # Parâmetros de lote
        if 'min_batch_size' in data:
            optimization_params.min_batch_size = float(data['min_batch_size'])
        if 'max_batch_size' in data:
            optimization_params.max_batch_size = float(data['max_batch_size'])
        
        # Parâmetros operacionais
        if 'review_period_days' in data:
            optimization_params.review_period_days = int(data['review_period_days'])
        if 'consolidation_window_days' in data:
            optimization_params.consolidation_window_days = int(data['consolidation_window_days'])
        if 'daily_production_capacity' in data:
            optimization_params.daily_production_capacity = float(data['daily_production_capacity'])
        
        # Parâmetros de habilitação
        if 'enable_eoq_optimization' in data:
            optimization_params.enable_eoq_optimization = bool(data['enable_eoq_optimization'])
        if 'enable_consolidation' in data:
            optimization_params.enable_consolidation = bool(data['enable_consolidation'])
        
        # Novos parâmetros avançados
        if 'force_consolidation_within_leadtime' in data:
            optimization_params.force_consolidation_within_leadtime = bool(data['force_consolidation_within_leadtime'])
        if 'min_consolidation_benefit' in data:
            optimization_params.min_consolidation_benefit = float(data['min_consolidation_benefit'])
        if 'operational_efficiency_weight' in data:
            optimization_params.operational_efficiency_weight = float(data['operational_efficiency_weight'])
        if 'overlap_prevention_priority' in data:
            optimization_params.overlap_prevention_priority = bool(data['overlap_prevention_priority'])
        
        # 🎯 NOVOS: Parâmetros de auto-calculation
        if 'auto_calculate_max_batch_size' in data:
            optimization_params.auto_calculate_max_batch_size = bool(data['auto_calculate_max_batch_size'])
        if 'max_batch_multiplier' in data:
            optimization_params.max_batch_multiplier = float(data['max_batch_multiplier'])
            if optimization_params.max_batch_multiplier < 1.0 or optimization_params.max_batch_multiplier > 10.0:
                return jsonify({"error": "max_batch_multiplier deve estar entre 1.0 e 10.0"}), 400
        
        ignore_safety_stock = data.get('ignore_safety_stock', False)
        include_extended_analytics = data.get('include_extended_analytics', True)
        min_stock_level = float(data.get('min_stock_level', 0.0))
        
        # Criar otimizador MRP avançado
        optimizer = MRPOptimizer(optimization_params)
        
        result = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=params['sporadic_demand'],
            initial_stock=params['initial_stock'],
            leadtime_days=params['leadtime_days'],
            period_start_date=params['period_start_date'],
            period_end_date=params['period_end_date'],
            start_cutoff_date=params['start_cutoff_date'],
            end_cutoff_date=params['end_cutoff_date'],
            safety_margin_percent=params['safety_margin_percent'],
            safety_days=params['safety_days'],
            minimum_stock_percent=params['minimum_stock_percent'],
            max_gap_days=params['max_gap_days'],
            ignore_safety_stock=ignore_safety_stock,
            include_extended_analytics=include_extended_analytics,
            min_stock_level=min_stock_level
        )
        
        logger.info(f"MRP Advanced concluído - {len(result['batches'])} lotes planejados")
        return jsonify(convert_numpy_types(result))
        
    except Exception as ex:
        logger.error(f"Erro no planejamento MRP avançado: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha no planejamento MRP avançado: {str(ex)}"}), 500

if __name__ == "__main__":
    logger.info("Servidor iniciando na porta 5000...")
    app.run(debug=True, port=5000, host='127.0.0.1')
