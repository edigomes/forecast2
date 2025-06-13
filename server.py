from flask import Flask, request, jsonify
import pandas as pd
import logging
import json
import traceback
from modelo import ModeloAjustado
from feriados_brasil import FeriadosBrasil

app = Flask(__name__)
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
    
    # Verificar se é agrupamento trimestral
    agrupamento_trimestral = data.get("agrupamento_trimestral", False)
    
    # Para agrupamento trimestral, forçar granularidade mensal
    if agrupamento_trimestral and gran != "M":
        logger.info("Agrupamento trimestral solicitado - forçando granularidade mensal")
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
            
        if agrupamento_trimestral:
            logger.info(f"MODO TRIMESTRAL ATIVADO - Períodos interpretados como trimestres")
            
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
            anos_feriados=anos_feriados
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
        logger.info(f"Tipo de agrupamento: {'Trimestral' if agrupamento_trimestral else 'Individual'}")
        
        # Salvar resultados completos em um arquivo JSON (com info adicional para logs)
        output_data_for_logs = {
            "forecast": forecast_results,
            "agrupamento_trimestral": agrupamento_trimestral
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
            period_type = "trimestres" if agrupamento_trimestral else "períodos"
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
    
    # Converter 'trimestres' para 'periodos' se fornecido
    if "trimestres" in data:
        data["periodos"] = data["trimestres"]
        logger.info(f"Convertendo 'trimestres' ({data['trimestres']}) para 'periodos'")
    
    # Chamar o endpoint principal com as configurações forçadas
    # O endpoint predict() já retorna no formato compatível {"forecast": [...]}
    return predict()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
