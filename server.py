from flask import Flask, request, jsonify
#from flask_cors import CORS
import pandas as pd
import logging
import json
import traceback
from modelo import ModeloAjustado
from feriados_brasil import FeriadosBrasil
from mrp import MRPOptimizer, OptimizationParams

app = Flask(__name__)

# Configurar CORS para permitir requests de qualquer URL
#CORS(app, resources={
#    r"/*": {
#        "origins": "*",  # Permite qualquer origem
#        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Métodos permitidos
#        "allow_headers": ["Content-Type", "Accept", "Authorization", "X-Requested-With"]  # Headers permitidos
#    }
#})

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True) or {}
    
    # Log COMPLETO dos dados de entrada
    logger.info("="*80)
    logger.info("DADOS DE ENTRADA COMPLETOS:")
    logger.info("-"*80)
    logger.info(f"granularidade: {data.get('granularidade', 'M')}")
    logger.info(f"periodos: {data.get('periodos', 0)}")
    logger.info(f"data_inicio: {data.get('data_inicio', '')}")
    logger.info(f"agrupamento_trimestral: {data.get('agrupamento_trimestral', False)}")
    logger.info(f"agrupamento_semestral: {data.get('agrupamento_semestral', False)}")
    logger.info(f"seasonal_smooth (se houver): {data.get('seasonal_smooth', 'não informado')}")
    logger.info(f"seasonality_mode (se houver): {data.get('seasonality_mode', 'não informado')}")
    logger.info(f"confidence_level (se houver): {data.get('confidence_level', 'não informado')}")
    logger.info(f"confidence_factor (se houver): {data.get('confidence_factor', 'não informado')}")
    logger.info(f"growth_factor (se houver): {data.get('growth_factor', 'não informado')}")
    logger.info(f"month_adjustments (se houver): {data.get('month_adjustments', 'não informado')}")
    logger.info(f"day_of_week_adjustments (se houver): {data.get('day_of_week_adjustments', 'não informado')}")
    logger.info(f"feriados_enabled (se houver): {data.get('feriados_enabled', 'não informado')}")
    logger.info(f"feriados_adjustments (se houver): {data.get('feriados_adjustments', 'não informado')}")
    logger.info(f"anos_feriados (se houver): {data.get('anos_feriados', 'não informado')}")
    logger.info(f"include_explanation (se houver): {data.get('include_explanation', 'não informado')}")
    logger.info(f"explanation_level (se houver): {data.get('explanation_level', 'não informado')}")
    logger.info(f"explanation_language (se houver): {data.get('explanation_language', 'não informado')}")
    
    # Log COMPLETO dos dados de vendas
    sales_data = data.get("sales_data", [])
    if sales_data:
        logger.info(f"Quantidade de registros: {len(sales_data)}")
        logger.info("DADOS COMPLETOS DE VENDAS:")
        
        # Salvar dados completos em um arquivo JSON
        with open('dados_entrada_completos.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Dados completos salvos em 'dados_entrada_completos.json'")
        
        # Exibir dados completos nos logs
        logger.info(f"\nTODOS OS REGISTROS DE VENDAS:\n{json.dumps(sales_data, indent=2)}")
        
        # Análise dos dados
        if sales_data and isinstance(sales_data, list):
            df = pd.DataFrame(sales_data)
            if "item_id" in df.columns:
                unique_items = df["item_id"].unique().tolist()
                logger.info(f"item_ids únicos ({len(unique_items)}): {unique_items}")
                
                # Estatísticas detalhadas por item_id
                for item in unique_items:
                    item_df = df[df['item_id'] == item]
                    logger.info(f"\nEstatísticas para item_id {item}:")
                    logger.info(f"  Número de registros: {len(item_df)}")
                    if 'timestamp' in item_df.columns:
                        dates = pd.to_datetime(item_df['timestamp'])
                        logger.info(f"  Período: {min(dates)} a {max(dates)}")
                        logger.info(f"  Intervalo: {(max(dates) - min(dates)).days} dias")
                    if 'demand' in item_df.columns:
                        try:
                            demands = pd.to_numeric(item_df['demand'], errors='coerce')
                            logger.info(f"  Demanda mínima: {demands.min()}")
                            logger.info(f"  Demanda máxima: {demands.max()}")
                            logger.info(f"  Demanda média: {demands.mean():.2f}")
                            logger.info(f"  Demanda total: {demands.sum():.2f}")
                        except Exception as e:
                            logger.error(f"Erro ao calcular estatísticas: {e}")
    
    logger.info("-"*80)

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
    except:
        return jsonify({"error":"'periodos' deve ser inteiro."}), 400
    if periods < 1:
        return jsonify({"error":"'periodos' deve ser >= 1."}), 400

    try:
        start_date = pd.to_datetime(data.get("data_inicio",""), format="%Y-%m-%d")
    except:
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
            outlier_threshold=2.5,  # Default sensível para detectar outliers
            trend_window=3,  # Janela de média móvel para suavizar tendência
            confidence_level=confidence_level,
            confidence_factor=confidence_factor,
            growth_factor=growth_factor,
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
        
        # Log COMPLETO da saída
        logger.info("="*80)
        logger.info("RESULTADOS COMPLETOS DA PREVISÃO:")
        logger.info("-"*80)
        logger.info(f"Total de previsões geradas: {len(forecast_results)}")
        tipo_agrupamento = "Trimestral" if agrupamento_trimestral else "Semestral" if agrupamento_semestral else "Individual"
        logger.info(f"Tipo de agrupamento: {tipo_agrupamento}")
        
        # Salvar resultados completos em um arquivo JSON (com info adicional para logs)
        output_data_for_logs = {
            "forecast": forecast_results,
            "agrupamento_trimestral": agrupamento_trimestral,
            "agrupamento_semestral": agrupamento_semestral
        }
        with open('resultados_completos.json', 'w', encoding='utf-8') as f:
            json.dump(output_data_for_logs, f, ensure_ascii=False, indent=4)
        logger.info(f"Resultados completos salvos em 'resultados_completos.json'")
        
        # Agrupar por item_id para um log mais organizado
        results_by_item = {}
        for result in forecast_results:
            item_id = result["item_id"]
            if item_id not in results_by_item:
                results_by_item[item_id] = []
            results_by_item[item_id].append(result)
        
        # Log COMPLETO por item
        for item_id, forecasts in results_by_item.items():
            if agrupamento_trimestral:
                period_type = "trimestres"
            elif agrupamento_semestral:
                period_type = "semestres"
            else:
                period_type = "períodos"
            logger.info(f"\nItem {item_id}: {len(forecasts)} {period_type} previstos")
            logger.info(f"TODOS OS {period_type.upper()} PARA ITEM {item_id}:")
            logger.info(json.dumps(forecasts, indent=2))
            
            # Análise estatística dos resultados
            if forecasts:
                yhats = [f['yhat'] for f in forecasts]
                
                if agrupamento_trimestral:
                    logger.info(f"\nEstatísticas das previsões trimestrais para item {item_id}:")
                    logger.info(f"  Valor mínimo previsto por trimestre: {min(yhats)}")
                    logger.info(f"  Valor máximo previsto por trimestre: {max(yhats)}")
                    logger.info(f"  Valor médio por trimestre: {sum(yhats)/len(yhats):.2f}")
                    logger.info(f"  Total previsto para todos os trimestres: {sum(yhats):.2f}")
                elif agrupamento_semestral:
                    logger.info(f"\nEstatísticas das previsões semestrais para item {item_id}:")
                    logger.info(f"  Valor mínimo previsto por semestre: {min(yhats)}")
                    logger.info(f"  Valor máximo previsto por semestre: {max(yhats)}")
                    logger.info(f"  Valor médio por semestre: {sum(yhats)/len(yhats):.2f}")
                    logger.info(f"  Total previsto para todos os semestres: {sum(yhats):.2f}")
                else:
                    trends = [f['trend'] for f in forecasts]
                    yearlys = [f['yearly'] for f in forecasts]
                    
                    logger.info(f"\nEstatísticas das previsões para item {item_id}:")
                    logger.info(f"  Valor mínimo previsto: {min(yhats)}")
                    logger.info(f"  Valor máximo previsto: {max(yhats)}")
                    logger.info(f"  Valor médio previsto: {sum(yhats)/len(yhats):.2f}")
                    logger.info(f"  Tendência inicial: {trends[0]}")
                    logger.info(f"  Tendência final: {trends[-1]}")
                    logger.info(f"  Variação da tendência: {trends[-1] - trends[0]:.2f} ({(trends[-1]/trends[0]-1)*100:.2f}%)")
                    logger.info(f"  Contribuição sazonal mínima: {min(yearlys)}")
                    logger.info(f"  Contribuição sazonal máxima: {max(yearlys)}")
        
        logger.info("="*80)
        logger.info("Previsão concluída com sucesso")
        
        # Salvar tanto a entrada quanto a saída em um único arquivo para referência
        combined_data = {
            "input": data,
            "output": output_data_for_logs
        }
        with open('dados_completos_input_output.json', 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Dados completos de entrada e saída salvos em 'dados_completos_input_output.json'")
        
        # MANTER COMPATIBILIDADE: Retornar apenas {"forecast": [...]} como antes
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
    
    logger.info("="*80)
    logger.info("ENDPOINT DEDICADO PARA PREVISÕES TRIMESTRAIS")
    logger.info("="*80)
    
    # Forçar configurações para previsão trimestral
    data["granularidade"] = "M"  # Sempre mensal para trimestres
    data["agrupamento_trimestral"] = True
    data["agrupamento_semestral"] = False  # Garantir que não conflite
    
    # Converter 'trimestres' para 'periodos' se fornecido
    if "trimestres" in data:
        data["periodos"] = data["trimestres"]
        logger.info(f"Convertendo 'trimestres' ({data['trimestres']}) para 'periodos'")
    
    # Chamar o endpoint principal com as configurações forçadas
    # O endpoint predict() já retorna no formato compatível {"forecast": [...]}
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
    
    logger.info("="*80)
    logger.info("ENDPOINT DEDICADO PARA PREVISÕES SEMESTRAIS")
    logger.info("="*80)
    
    # Forçar configurações para previsão semestral
    data["granularidade"] = "M"  # Sempre mensal para semestres
    data["agrupamento_semestral"] = True
    data["agrupamento_trimestral"] = False  # Garantir que não conflite
    
    # Converter 'semestres' para 'periodos' se fornecido
    if "semestres" in data:
        data["periodos"] = data["semestres"]
        logger.info(f"Convertendo 'semestres' ({data['semestres']}) para 'periodos'")
    
    # Chamar o endpoint principal com as configurações forçadas
    # O endpoint predict() já retorna no formato compatível {"forecast": [...]}
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
        
        logger.info("="*60)
        logger.info("ENDPOINT GERADOR DE HTML")
        logger.info("="*60)
        
        # Verificar se cliente quer HTML direto
        wants_html_direct = (
            request.headers.get('Accept', '').startswith('text/html') or
            data.get('return_html_direct', False)
        )
        
        logger.info(f"Modo retorno: {'HTML direto' if wants_html_direct else 'JSON'}")
        
        # Verificar se foi enviado html_data (modo simplificado) ou parâmetros individuais
        if 'html_data' in data:
            # Modo simplificado: usar dados do banco
            html_data_from_db = data['html_data']
            layout = data.get('layout', 'full')
            
            logger.info(f"Modo simplificado: usando html_data do banco")
            logger.info(f"Layout: {layout}")
            
            # Extrair dados do html_data
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
        
        # Validar layout
        if layout not in ['full', 'compact']:
            layout = 'full'
            logger.warning(f"Layout inválido, usando 'full'")
        
        # Validar prediction apenas no modo completo
        if 'html_data' not in data:
            required_prediction_fields = ['yhat', 'yhat_lower', 'yhat_upper', 'trend', 'yearly', 'ds']
            for field in required_prediction_fields:
                if field not in prediction:
                    if wants_html_direct:
                        return f"<html><body><h1>Erro: Campo obrigatório 'prediction.{field}' não fornecido</h1></body></html>", 400, {'Content-Type': 'text/html; charset=utf-8'}
                    return jsonify({"error": f"Campo obrigatório 'prediction.{field}' não fornecido"}), 400
        
        logger.info(f"Gerando HTML para item {item_id}")
        logger.info(f"Layout: {layout}")
        logger.info(f"Trimestral: {is_quarterly}")
        logger.info(f"Semestral: {is_semiannual}")
        
        # Criar um modelo temporário apenas para acessar as funções de geração de HTML
        # Recuperar configurações salvas no explanation_data
        seasonality_mode = explanation_data.get('seasonality_mode', 'multiplicative')
        freq = explanation_data.get('freq', 'MS')
        month_adjustments = explanation_data.get('month_adjustments', {})
        day_of_week_adjustments = explanation_data.get('day_of_week_adjustments', {})
        growth_factor = explanation_data.get('growth_factor', 1.0)
        confidence_level = explanation_data.get('confidence_level', 0.95)
        
        logger.info(f"Configurações recuperadas:")
        logger.info(f"  seasonality_mode: {seasonality_mode}")
        logger.info(f"  freq: {freq}")
        logger.info(f"  month_adjustments: {month_adjustments}")
        
        # Debug: verificar seasonal_pattern
        seasonal_pattern = explanation_data.get('seasonal_pattern', {})
        logger.info(f"  seasonal_pattern: {seasonal_pattern}")
        if seasonal_pattern:
            logger.info(f"  Fator para mês {date.month}: {seasonal_pattern.get(date.month, 'NÃO ENCONTRADO')}")
        
        # Debug: verificar prediction
        logger.info(f"Dados da previsão:")
        logger.info(f"  Data: {date}")
        logger.info(f"  Mês: {date.month}")
        logger.info(f"  Trend: {prediction.get('trend')}")
        logger.info(f"  Yearly: {prediction.get('yearly')}")
        logger.info(f"  Yhat: {prediction.get('yhat')}")
        
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
            confidence_level=confidence_level
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
        
        logger.info(f"HTML gerado com sucesso: {len(html_content)} caracteres")
        logger.info("="*60)
        
        # Retornar HTML direto ou JSON baseado na preferência do cliente
        if wants_html_direct:
            # Retornar HTML puro para exibição direta no navegador
            logger.info("Retornando HTML direto (text/html)")
            return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        else:
            # Retornar JSON (comportamento padrão)
            logger.info("Retornando JSON com HTML")
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
        
        # Tratar erros baseado na preferência do cliente
        if request.headers.get('Accept', '').startswith('text/html') or request.get_json(force=True, silent=True, cache=False).get('return_html_direct', False):
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
    """
    try:
        data = request.get_json(force=True) or {}
        
        logger.info("="*80)
        logger.info("ENDPOINT MRP OPTIMIZATION")
        logger.info("="*80)
        
        # Log dos dados de entrada
        logger.info("DADOS DE ENTRADA:")
        logger.info(f"daily_demands: {data.get('daily_demands', 'não informado')}")
        logger.info(f"initial_stock: {data.get('initial_stock', 'não informado')}")
        logger.info(f"leadtime_days: {data.get('leadtime_days', 'não informado')}")
        logger.info(f"period_start_date: {data.get('period_start_date', 'não informado')}")
        logger.info(f"period_end_date: {data.get('period_end_date', 'não informado')}")
        logger.info(f"start_cutoff_date: {data.get('start_cutoff_date', 'não informado')}")
        logger.info(f"end_cutoff_date: {data.get('end_cutoff_date', 'não informado')}")
        
        # Validações dos parâmetros obrigatórios
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
            except:
                return jsonify({"error": f"Formato inválido em daily_demands. Chave '{date_key}' deve ser YYYY-MM e valor deve ser numérico"}), 400
        
        # Validar datas
        try:
            period_start_date = data['period_start_date']
            period_end_date = data['period_end_date']
            start_cutoff_date = data['start_cutoff_date']
            end_cutoff_date = data['end_cutoff_date']
            
            # Validar formato das datas
            pd.to_datetime(period_start_date)
            pd.to_datetime(period_end_date)
            pd.to_datetime(start_cutoff_date)
            pd.to_datetime(end_cutoff_date)
            
        except:
            return jsonify({"error": "Datas devem estar no formato YYYY-MM-DD"}), 400
        
        # Extrair parâmetros opcionais de otimização
        optimization_kwargs = {}
        optional_params = [
            'setup_cost', 'holding_cost_rate', 'stockout_cost_multiplier',
            'service_level', 'min_batch_size', 'max_batch_size',
            'review_period_days', 'safety_days', 'consolidation_window_days',
            'daily_production_capacity', 'enable_eoq_optimization', 'enable_consolidation',
            'include_extended_analytics'
        ]
        
        for param in optional_params:
            if param in data:
                optimization_kwargs[param] = data[param]
        
        # Log dos parâmetros opcionais
        if optimization_kwargs:
            logger.info("PARÂMETROS DE OTIMIZAÇÃO CUSTOMIZADOS:")
            for param, value in optimization_kwargs.items():
                logger.info(f"  {param}: {value}")
        
        # Criar otimizador MRP
        optimizer = MRPOptimizer()
        
        # Executar otimização
        logger.info("Iniciando otimização MRP...")
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
        
        # Log dos resultados
        logger.info("OTIMIZAÇÃO MRP CONCLUÍDA:")
        logger.info(f"Total de lotes planejados: {len(result['batches'])}")
        logger.info(f"Produção total: {result['analytics']['summary']['total_produced']}")
        logger.info(f"Taxa de cobertura: {result['analytics']['summary']['production_coverage_rate']}")
        logger.info(f"Estoque mínimo: {result['analytics']['summary']['minimum_stock']}")
        logger.info(f"Estoque final: {result['analytics']['summary']['final_stock']}")
        logger.info(f"Stockout ocorreu: {result['analytics']['summary']['stockout_occurred']}")
        
        # Salvar resultados completos para debug
        with open('mrp_results_completos.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info("Resultados MRP salvos em 'mrp_results_completos.json'")
        
        # Log detalhado dos primeiros lotes
        if result['batches']:
            logger.info("\nPRIMEIROS LOTES PLANEJADOS:")
            for i, batch in enumerate(result['batches'][:5]):  # Mostrar até 5 primeiros
                logger.info(f"  Lote {i+1}:")
                logger.info(f"    Data pedido: {batch['order_date']}")
                logger.info(f"    Data chegada: {batch['arrival_date']}")
                logger.info(f"    Quantidade: {batch['quantity']}")
                logger.info(f"    Urgência: {batch['analytics'].get('urgency_level', 'N/A')}")
                logger.info(f"    Cobertura: {batch['analytics'].get('coverage_days', 'N/A')} dias")
        
        logger.info("="*80)
        
        # Converter tipos numpy para tipos nativos do Python para serialização JSON
        def convert_numpy_types(obj):
            """Converte tipos numpy para tipos nativos do Python"""
            if isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy array
                return obj.tolist()
            else:
                return obj
        
        result_converted = convert_numpy_types(result)
        
        return jsonify(result_converted)
        
    except Exception as ex:
        logger.error(f"Erro na otimização MRP: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha na otimização MRP: {str(ex)}"}), 500

@app.route('/mrp_sporadic', methods=['POST'])
def mrp_sporadic():
    """
    Endpoint para planejamento de lotes para demandas esporádicas
    
    Parâmetros obrigatórios:
    - sporadic_demand: Dict com demandas esporádicas {"YYYY-MM-DD": quantidade}
    - initial_stock: Estoque inicial (float)
    - leadtime_days: Lead time em dias (int)
    - period_start_date: Data início do período (YYYY-MM-DD)
    - period_end_date: Data fim do período (YYYY-MM-DD)
    - start_cutoff_date: Data de corte inicial (YYYY-MM-DD)
    - end_cutoff_date: Data de corte final (YYYY-MM-DD)
    
    Parâmetros opcionais:
    - safety_margin_percent: Margem de segurança % (padrão: 8.0)
    - safety_days: Dias de segurança (padrão: 2)
    - minimum_stock_percent: Estoque mínimo % da maior demanda (padrão: 0.0)
    - max_gap_days: Gap máximo entre lotes (padrão: 999)
    
    Parâmetros avançados de otimização (mesmos do MRP):
    - setup_cost: Custo fixo por pedido (padrão: 250.0)
    - holding_cost_rate: Taxa de custo de manutenção (padrão: 0.20)
    - service_level: Nível de serviço desejado (padrão: 0.95)
    - min_batch_size: Tamanho mínimo do lote (padrão: 200.0)
    - max_batch_size: Tamanho máximo do lote (padrão: 10000.0)
    - enable_consolidation: Habilitar consolidação de pedidos (padrão: True)
    - enable_eoq_optimization: Habilitar otimização EOQ (padrão: True)
    """
    try:
        data = request.get_json(force=True) or {}
        
        logger.info("="*80)
        logger.info("ENDPOINT MRP SPORADIC DEMAND")
        logger.info("="*80)
        
        # Log dos dados de entrada
        logger.info("DADOS DE ENTRADA:")
        logger.info(f"sporadic_demand: {data.get('sporadic_demand', 'não informado')}")
        logger.info(f"initial_stock: {data.get('initial_stock', 'não informado')}")
        logger.info(f"leadtime_days: {data.get('leadtime_days', 'não informado')}")
        logger.info(f"period_start_date: {data.get('period_start_date', 'não informado')}")
        logger.info(f"period_end_date: {data.get('period_end_date', 'não informado')}")
        logger.info(f"start_cutoff_date: {data.get('start_cutoff_date', 'não informado')}")
        logger.info(f"end_cutoff_date: {data.get('end_cutoff_date', 'não informado')}")
        
        # Validações dos parâmetros obrigatórios
        required_fields = [
            'sporadic_demand', 'initial_stock', 'leadtime_days',
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
        
        # Validar sporadic_demand
        sporadic_demand = data['sporadic_demand']
        if not isinstance(sporadic_demand, dict) or not sporadic_demand:
            return jsonify({"error": "sporadic_demand deve ser dicionário não vazio"}), 400
        
        # Validar formato das demandas esporádicas
        for date_key, demand_value in sporadic_demand.items():
            try:
                # Verificar formato da data (YYYY-MM-DD)
                pd.to_datetime(date_key)
                # Verificar se demanda é numérica e positiva
                demand_val = float(demand_value)
                if demand_val < 0:
                    return jsonify({"error": f"Demanda em '{date_key}' não pode ser negativa"}), 400
            except:
                return jsonify({"error": f"Formato inválido em sporadic_demand. Chave '{date_key}' deve ser YYYY-MM-DD e valor deve ser numérico positivo"}), 400
        
        # Validar datas
        try:
            period_start_date = data['period_start_date']
            period_end_date = data['period_end_date']
            start_cutoff_date = data['start_cutoff_date']
            end_cutoff_date = data['end_cutoff_date']
            
            # Validar formato das datas
            start_pd = pd.to_datetime(period_start_date)
            end_pd = pd.to_datetime(period_end_date)
            start_cutoff_pd = pd.to_datetime(start_cutoff_date)
            end_cutoff_pd = pd.to_datetime(end_cutoff_date)
            
            # Validar lógica das datas
            if start_pd >= end_pd:
                return jsonify({"error": "period_start_date deve ser anterior a period_end_date"}), 400
            if start_cutoff_pd > end_cutoff_pd:
                return jsonify({"error": "start_cutoff_date deve ser anterior ou igual a end_cutoff_date"}), 400
            
        except:
            return jsonify({"error": "Datas devem estar no formato YYYY-MM-DD"}), 400
        
        # Extrair parâmetros específicos de demanda esporádica
        safety_margin_percent = float(data.get('safety_margin_percent', 8.0))
        safety_days = int(data.get('safety_days', 2))
        minimum_stock_percent = float(data.get('minimum_stock_percent', 0.0))
        max_gap_days = int(data.get('max_gap_days', 999))
        
        # Validar parâmetros específicos
        if safety_margin_percent < 0 or safety_margin_percent > 100:
            return jsonify({"error": "safety_margin_percent deve estar entre 0 e 100"}), 400
        if safety_days < 0:
            return jsonify({"error": "safety_days não pode ser negativo"}), 400
        if minimum_stock_percent < 0 or minimum_stock_percent > 100:
            return jsonify({"error": "minimum_stock_percent deve estar entre 0 e 100"}), 400
        if max_gap_days < 1:
            return jsonify({"error": "max_gap_days deve ser pelo menos 1"}), 400
        
        # Extrair parâmetros avançados de otimização (opcionais)
        optimization_kwargs = {}
        optional_params = [
            'setup_cost', 'holding_cost_rate', 'stockout_cost_multiplier',
            'service_level', 'min_batch_size', 'max_batch_size',
            'review_period_days', 'consolidation_window_days',
            'daily_production_capacity', 'enable_eoq_optimization', 'enable_consolidation'
        ]
        
        for param in optional_params:
            if param in data:
                optimization_kwargs[param] = data[param]
        
        # Log dos parâmetros específicos
        logger.info("PARÂMETROS ESPECÍFICOS DE DEMANDA ESPORÁDICA:")
        logger.info(f"  safety_margin_percent: {safety_margin_percent}%")
        logger.info(f"  safety_days: {safety_days}")
        logger.info(f"  minimum_stock_percent: {minimum_stock_percent}%")
        logger.info(f"  max_gap_days: {max_gap_days}")
        
        # Log dos parâmetros de otimização (se fornecidos)
        if optimization_kwargs:
            logger.info("PARÂMETROS DE OTIMIZAÇÃO AVANÇADOS:")
            for param, value in optimization_kwargs.items():
                logger.info(f"  {param}: {value}")
        
        # Análise prévia das demandas
        demand_dates = list(sporadic_demand.keys())
        demand_values = list(sporadic_demand.values())
        total_demand = sum(demand_values)
        max_demand = max(demand_values)
        min_demand = min(demand_values)
        avg_demand = total_demand / len(demand_values)
        
        logger.info("ANÁLISE PRÉVIA DAS DEMANDAS ESPORÁDICAS:")
        logger.info(f"  Total de eventos: {len(sporadic_demand)}")
        logger.info(f"  Período das demandas: {min(demand_dates)} a {max(demand_dates)}")
        logger.info(f"  Demanda total: {total_demand}")
        logger.info(f"  Demanda média por evento: {avg_demand:.2f}")
        logger.info(f"  Demanda mínima: {min_demand}")
        logger.info(f"  Demanda máxima: {max_demand}")
        logger.info(f"  Variação: {((max_demand - min_demand) / avg_demand * 100):.1f}%")
        
        # Criar otimizador MRP
        optimizer = MRPOptimizer()
        
        # Executar planejamento de demanda esporádica
        logger.info("Iniciando planejamento de lotes para demanda esporádica...")
        result = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=sporadic_demand,
            initial_stock=initial_stock,
            leadtime_days=leadtime_days,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            start_cutoff_date=start_cutoff_date,
            end_cutoff_date=end_cutoff_date,
            safety_margin_percent=safety_margin_percent,
            safety_days=safety_days,
            minimum_stock_percent=minimum_stock_percent,
            max_gap_days=max_gap_days,
            **optimization_kwargs
        )
        
        # Log dos resultados
        analytics = result['analytics']
        summary = analytics['summary']
        sporadic_metrics = analytics['sporadic_demand_metrics']
        
        logger.info("PLANEJAMENTO ESPORÁDICO CONCLUÍDO:")
        logger.info(f"Total de lotes planejados: {len(result['batches'])}")
        logger.info(f"Produção total: {summary['total_produced']}")
        logger.info(f"Taxa de cobertura: {summary['production_coverage_rate']}")
        logger.info(f"Taxa de atendimento: {summary['demand_fulfillment_rate']}%")
        logger.info(f"Demandas atendidas: {summary['demands_met_count']}/{summary['demands_met_count'] + summary['demands_unmet_count']}")
        logger.info(f"Estoque mínimo: {summary['minimum_stock']}")
        logger.info(f"Estoque final: {summary['final_stock']}")
        logger.info(f"Stockout ocorreu: {summary['stockout_occurred']}")
        
        logger.info("MÉTRICAS ESPECÍFICAS DE DEMANDA ESPORÁDICA:")
        logger.info(f"Concentração de demanda: {sporadic_metrics['demand_concentration']['concentration_level']}")
        logger.info(f"Previsibilidade: {sporadic_metrics['demand_predictability']}")
        logger.info(f"Intervalo médio entre demandas: {sporadic_metrics['interval_statistics']['average_interval_days']} dias")
        logger.info(f"Picos de demanda detectados: {sporadic_metrics['peak_demand_analysis']['peak_count']}")
        
        # Salvar resultados completos para debug
        with open('mrp_sporadic_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info("Resultados salvos em 'mrp_sporadic_results.json'")
        
        # Log detalhado dos lotes com informações específicas
        if result['batches']:
            logger.info(f"\nLOTES PLANEJADOS PARA DEMANDAS ESPORÁDICAS:")
            for i, batch in enumerate(result['batches'], 1):
                analytics_batch = batch['analytics']
                logger.info(f"  Lote {i}:")
                logger.info(f"    Data pedido: {batch['order_date']}")
                logger.info(f"    Data chegada: {batch['arrival_date']}")
                logger.info(f"    Quantidade: {batch['quantity']}")
                logger.info(f"    Demanda alvo: {analytics_batch.get('target_demand_date', 'N/A')} ({analytics_batch.get('target_demand_quantity', 'N/A')})")
                logger.info(f"    Déficit coberto: {analytics_batch.get('shortfall_covered', 'N/A')}")
                logger.info(f"    Crítico: {'Sim' if analytics_batch.get('is_critical', False) else 'Não'}")
                logger.info(f"    Urgência: {analytics_batch.get('urgency_level', 'N/A')}")
                logger.info(f"    Margem segurança: {analytics_batch.get('safety_margin_days', 'N/A')} dias")
                logger.info(f"    Eficiência: {analytics_batch.get('efficiency_ratio', 'N/A')}")
        
        # Log de demandas não atendidas (se houver)
        if summary['unmet_demand_details']:
            logger.info(f"\nDEMANDAS NÃO ATENDIDAS ({len(summary['unmet_demand_details'])}):")
            for unmet in summary['unmet_demand_details']:
                logger.info(f"  Data: {unmet['date']}")
                logger.info(f"    Demanda: {unmet['demand']}")
                logger.info(f"    Estoque disponível: {unmet['available_stock']}")
                logger.info(f"    Déficit: {unmet['shortage']}")
        
        logger.info("="*80)
        
        # Converter tipos numpy para tipos nativos do Python
        def convert_numpy_types(obj):
            """Converte tipos numpy para tipos nativos do Python"""
            if isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy array
                return obj.tolist()
            else:
                return obj
        
        result_converted = convert_numpy_types(result)
        
        return jsonify(result_converted)
        
    except Exception as ex:
        logger.error(f"Erro no planejamento de demanda esporádica: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha no planejamento de demanda esporádica: {str(ex)}"}), 500

@app.route('/mrp_advanced', methods=['POST'])
def mrp_advanced():
    """
    Endpoint MRP Avançado com Analytics Estendidos
    
    Utiliza algoritmos avançados de supply chain incluindo:
    - EOQ (Economic Order Quantity) calculations
    - ABC/XYZ classification
    - Análise de sazonalidade e tendências
    - Múltiplas estratégias de planejamento
    - Analytics estendidos com métricas de performance
    - Integração com supplychainpy (quando disponível)
    """
    try:
        data = request.get_json(force=True) or {}
        
        # Log completo dos dados de entrada
        logger.info("="*80)
        logger.info("MRP AVANÇADO - DADOS DE ENTRADA:")
        logger.info("-"*80)
        logger.info(f"Endpoint: /mrp_advanced")
        logger.info(f"Method: POST")
        logger.info(f"Data keys: {list(data.keys())}")
        
        # Validações obrigatórias
        required_fields = ['sporadic_demand', 'initial_stock', 'leadtime_days', 
                          'period_start_date', 'period_end_date', 
                          'start_cutoff_date', 'end_cutoff_date']
        
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório '{field}' não encontrado"}), 400
        
        # Extrair parâmetros básicos
        initial_stock = float(data['initial_stock'])
        leadtime_days = int(data['leadtime_days'])
        
        # Validar valores básicos
        if initial_stock < 0:
            return jsonify({"error": "initial_stock não pode ser negativo"}), 400
        if leadtime_days < 0:
            return jsonify({"error": "leadtime_days não pode ser negativo"}), 400
        
        # Validar sporadic_demand
        sporadic_demand = data['sporadic_demand'] 
        if not isinstance(sporadic_demand, dict) or not sporadic_demand:
            return jsonify({"error": "sporadic_demand deve ser dicionário não vazio"}), 400
        
        # Validar formato das demandas esporádicas
        for date_key, demand_value in sporadic_demand.items():
            try:
                pd.to_datetime(date_key)
                demand_val = float(demand_value)
                if demand_val < 0:
                    return jsonify({"error": f"Demanda em '{date_key}' não pode ser negativa"}), 400
            except:
                return jsonify({"error": f"Formato inválido em sporadic_demand. Chave '{date_key}' deve ser YYYY-MM-DD e valor deve ser numérico positivo"}), 400
        
        # Validar datas
        try:
            period_start_date = data['period_start_date']
            period_end_date = data['period_end_date']
            start_cutoff_date = data['start_cutoff_date']
            end_cutoff_date = data['end_cutoff_date']
            
            # Validar formato das datas
            start_pd = pd.to_datetime(period_start_date)
            end_pd = pd.to_datetime(period_end_date)
            start_cutoff_pd = pd.to_datetime(start_cutoff_date)
            end_cutoff_pd = pd.to_datetime(end_cutoff_date)
            
            # Validar lógica das datas
            if start_pd >= end_pd:
                return jsonify({"error": "period_start_date deve ser anterior a period_end_date"}), 400
            if start_cutoff_pd > end_cutoff_pd:
                return jsonify({"error": "start_cutoff_date deve ser anterior ou igual a end_cutoff_date"}), 400
            
        except:
            return jsonify({"error": "Datas devem estar no formato YYYY-MM-DD"}), 400
        
        # Parâmetros específicos de demanda esporádica
        safety_margin_percent = float(data.get('safety_margin_percent', 8.0))
        safety_days = int(data.get('safety_days', 2))
        minimum_stock_percent = float(data.get('minimum_stock_percent', 0.0))
        max_gap_days = int(data.get('max_gap_days', 999))
        
        # Validar parâmetros específicos
        if safety_margin_percent < 0 or safety_margin_percent > 100:
            return jsonify({"error": "safety_margin_percent deve estar entre 0 e 100"}), 400
        if safety_days < 0:
            return jsonify({"error": "safety_days não pode ser negativo"}), 400
        if minimum_stock_percent < 0 or minimum_stock_percent > 100:
            return jsonify({"error": "minimum_stock_percent deve estar entre 0 e 100"}), 400
        if max_gap_days < 1:
            return jsonify({"error": "max_gap_days deve ser pelo menos 1"}), 400
        
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
        
        # Parâmetro para habilitar analytics estendidos (padrão: True para endpoint avançado)
        include_extended_analytics = data.get('include_extended_analytics', True)
        
        # Log dos parâmetros
        logger.info("PARÂMETROS AVANÇADOS DE OTIMIZAÇÃO:")
        logger.info(f"  setup_cost: {optimization_params.setup_cost}")
        logger.info(f"  holding_cost_rate: {optimization_params.holding_cost_rate}")
        logger.info(f"  service_level: {optimization_params.service_level}")
        logger.info(f"  enable_eoq_optimization: {optimization_params.enable_eoq_optimization}")
        logger.info(f"  enable_consolidation: {optimization_params.enable_consolidation}")
        logger.info(f"  force_consolidation_within_leadtime: {optimization_params.force_consolidation_within_leadtime}")
        logger.info(f"  min_consolidation_benefit: {optimization_params.min_consolidation_benefit}")
        logger.info(f"  include_extended_analytics: {include_extended_analytics}")
        
        # Análise prévia das demandas
        demand_dates = list(sporadic_demand.keys())
        demand_values = list(sporadic_demand.values())
        total_demand = sum(demand_values)
        max_demand = max(demand_values)
        min_demand = min(demand_values)
        avg_demand = total_demand / len(demand_values)
        
        logger.info("ANÁLISE PRÉVIA DAS DEMANDAS ESPORÁDICAS:")
        logger.info(f"  Total de eventos: {len(sporadic_demand)}")
        logger.info(f"  Período das demandas: {min(demand_dates)} a {max(demand_dates)}")
        logger.info(f"  Demanda total: {total_demand}")
        logger.info(f"  Demanda média por evento: {avg_demand:.2f}")
        logger.info(f"  Demanda mínima: {min_demand}")
        logger.info(f"  Demanda máxima: {max_demand}")
        logger.info(f"  Coeficiente de variação: {((max_demand - min_demand) / avg_demand):.2f}")
        
        # Detectar estratégia que será utilizada
        cv = (max_demand - min_demand) / avg_demand if avg_demand > 0 else 0
        if leadtime_days > 45:
            strategy_expected = "Long Lead Time Forecasting"
        elif cv > 0.5:
            strategy_expected = "Dynamic Buffer Strategy"
        elif optimization_params.enable_eoq_optimization and total_demand > optimization_params.min_batch_size * 2:
            strategy_expected = "EOQ-Based Strategy"
        else:
            strategy_expected = "Hybrid Consolidation Strategy"
        
        logger.info(f"  Estratégia esperada: {strategy_expected}")
        
        # Criar otimizador MRP avançado
        optimizer = MRPOptimizer(optimization_params)
        
        # Executar planejamento avançado
        logger.info("Iniciando planejamento MRP AVANÇADO...")
        result = optimizer.calculate_batches_for_sporadic_demand(
            sporadic_demand=sporadic_demand,
            initial_stock=initial_stock,
            leadtime_days=leadtime_days,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            start_cutoff_date=start_cutoff_date,
            end_cutoff_date=end_cutoff_date,
            safety_margin_percent=safety_margin_percent,
            safety_days=safety_days,
            minimum_stock_percent=minimum_stock_percent,
            max_gap_days=max_gap_days,
            include_extended_analytics=include_extended_analytics
        )
        
        # Log dos resultados básicos
        analytics = result['analytics']
        summary = analytics['summary']
        
        logger.info("PLANEJAMENTO MRP AVANÇADO CONCLUÍDO:")
        logger.info(f"Total de lotes planejados: {len(result['batches'])}")
        logger.info(f"Produção total: {summary['total_produced']}")
        logger.info(f"Taxa de cobertura: {summary['production_coverage_rate']}")
        logger.info(f"Taxa de atendimento: {summary['demand_fulfillment_rate']}%")
        logger.info(f"Estoque mínimo: {summary['minimum_stock']}")
        logger.info(f"Estoque final: {summary['final_stock']}")
        logger.info(f"Stockout ocorreu: {summary['stockout_occurred']}")
        
        # Log de analytics estendidos (se disponíveis)
        if include_extended_analytics and 'extended_analytics' in analytics:
            extended = analytics['extended_analytics']
            
            logger.info("ANALYTICS ESTENDIDOS:")
            
            # Métricas de performance
            if 'performance_metrics' in extended:
                perf = extended['performance_metrics']
                logger.info(f"  Nível de serviço realizado: {perf.get('realized_service_level', 'N/A')}%")
                logger.info(f"  Giro de estoque: {perf.get('inventory_turnover', 'N/A')}")
                logger.info(f"  Dias médios de estoque: {perf.get('average_days_of_inventory', 'N/A')}")
                logger.info(f"  Frequência de setup: {perf.get('setup_frequency', 'N/A')}")
                logger.info(f"  Tamanho médio de lote: {perf.get('average_batch_size', 'N/A')}")
            
            # Análise de custos
            if 'cost_analysis' in extended:
                cost = extended['cost_analysis']
                logger.info(f"  Custo total estimado: R$ {cost.get('total_cost', 'N/A')}")
                logger.info(f"  Custo de setup: R$ {cost.get('setup_cost', 'N/A')}")
                logger.info(f"  Custo de manutenção: R$ {cost.get('holding_cost', 'N/A')}")
                logger.info(f"  Custo de falta: R$ {cost.get('stockout_cost', 'N/A')}")
            
            # Métricas de otimização
            if 'optimization_metrics' in extended:
                opt = extended['optimization_metrics']
                logger.info(f"  EOQ teórico: {opt.get('theoretical_eoq', 'N/A')}")
                logger.info(f"  Lote médio real: {opt.get('actual_average_batch', 'N/A')}")
                logger.info(f"  Aderência ao EOQ: {opt.get('eoq_adherence_rate', 'N/A')}%")
                logger.info(f"  Economia de consolidação: R$ {opt.get('consolidation_savings', 'N/A')}")
            
            # Análise de sazonalidade
            if 'seasonality_analysis' in extended:
                season = extended['seasonality_analysis']
                logger.info(f"  Sazonalidade detectada: {season.get('seasonality_detected', 'N/A')}")
                if season.get('trend', {}).get('direction'):
                    trend = season['trend']
                    logger.info(f"  Tendência: {trend.get('direction', 'N/A')} ({trend.get('strength', 'N/A')})")
            
            # Recomendações
            if 'recommendations' in extended:
                recommendations = extended['recommendations']
                logger.info(f"  Recomendações geradas: {len(recommendations)}")
                for i, rec in enumerate(recommendations[:3], 1):  # Mostrar apenas as 3 primeiras
                    logger.info(f"    {i}. {rec.get('type', 'N/A')}: {rec.get('message', 'N/A')}")
        
        # Log detalhado dos lotes
        if result['batches']:
            logger.info(f"\nLOTES PLANEJADOS COM ALGORITMOS AVANÇADOS:")
            for i, batch in enumerate(result['batches'], 1):
                analytics_batch = batch['analytics']
                logger.info(f"  Lote {i}:")
                logger.info(f"    Data pedido: {batch['order_date']}")
                logger.info(f"    Data chegada: {batch['arrival_date']}")
                logger.info(f"    Quantidade: {batch['quantity']}")
                logger.info(f"    Estoque antes: {analytics_batch.get('stock_before_arrival', 'N/A')}")
                logger.info(f"    Estoque depois: {analytics_batch.get('stock_after_arrival', 'N/A')}")
                logger.info(f"    Cobertura: {analytics_batch.get('coverage_days', 'N/A')} dias")
                logger.info(f"    Urgência: {analytics_batch.get('urgency_level', 'N/A')}")
                
                # Informações específicas se consolidado
                if analytics_batch.get('consolidated_group', False):
                    logger.info(f"    ✓ CONSOLIDADO: {analytics_batch.get('group_size', 'N/A')} demandas")
                    logger.info(f"    ✓ Economia: R$ {analytics_batch.get('consolidation_savings', 'N/A')}")
                    logger.info(f"    ✓ Qualidade: {analytics_batch.get('consolidation_quality', 'N/A')}")
                
                # Informações específicas de EOQ
                if analytics_batch.get('eoq_used'):
                    logger.info(f"    ✓ EOQ: {analytics_batch.get('eoq_used', 'N/A')}")
                
                # Informações específicas de classificação ABC/XYZ
                if analytics_batch.get('abc_classification'):
                    logger.info(f"    ✓ Classificação: {analytics_batch.get('abc_classification', 'N/A')}{analytics_batch.get('xyz_classification', '')}")
        
        # Salvar resultados completos
        with open('mrp_advanced_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        logger.info("Resultados avançados salvos em 'mrp_advanced_results.json'")
        
        logger.info("="*80)
        
        # Converter tipos numpy para tipos nativos do Python
        def convert_numpy_types(obj):
            if isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif hasattr(obj, 'tolist'):  # numpy array
                return obj.tolist()
            else:
                return obj
        
        result_converted = convert_numpy_types(result)
        
        # Adicionar informações sobre o endpoint usado
        result_converted['_endpoint_info'] = {
            'endpoint': '/mrp_advanced',
            'version': '1.0',
            'features': [
                'Advanced MRP algorithms',
                'EOQ calculations',
                'ABC/XYZ classification',
                'Seasonality analysis',
                'Extended analytics',
                'Multiple planning strategies',
                'Intelligent consolidation',
                'Supply chain optimization'
            ],
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        return jsonify(result_converted)
        
    except Exception as ex:
        logger.error(f"Erro no planejamento MRP avançado: {str(ex)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Falha no planejamento MRP avançado: {str(ex)}"}), 500

if __name__ == "__main__":
    #logger.info("🌐 CORS configurado para permitir requests de qualquer URL")
    logger.info("📡 Servidor iniciando na porta 5000...")
    app.run(debug=True, port=5000, host='127.0.0.1')
