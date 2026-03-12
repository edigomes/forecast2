# Forecast API

API de previsão de demanda e planejamento MRP (Material Requirements Planning).

Combina modelos estatísticos (decomposição clássica + Holt-Winters) com algoritmos de otimização de supply chain para gerar previsões de demanda e planejamento inteligente de lotes de produção.

## Estrutura do Projeto

```
forecast2/
├── server.py                 # Endpoints Flask (API principal)
├── modelo.py                 # Motor de previsão (decomposição, Holt-Winters, sazonalidade)
├── holt_winters.py           # Modelo Holt-Winters e seleção automática de modelo
├── mrp.py                    # Otimizador MRP (EOQ, safety stock, consolidação)
├── monte_carlo.py            # Simulação Monte Carlo para análise de risco
├── advanced_sporadic_mrp.py  # MRP avançado para demandas esporádicas
├── feriados_brasil.py        # Calendário de feriados brasileiros
├── wsgi.py                   # Entry point WSGI (produção)
├── gunicorn_config.py        # Configuração Gunicorn
└── requirements.txt          # Dependências Python
```

## Instalação

### Pré-requisitos

- Python 3.10+

### Desenvolvimento

```bash
# Clonar o repositório
git clone <url-do-repo>
cd forecast2

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor de desenvolvimento
python wsgi.py
```

O servidor inicia em `http://localhost:5000` com debug ativado.

### Produção

#### Opção 1: Gunicorn (Linux/macOS)

```bash
pip install -r requirements.txt

# Iniciar com configuração padrão
ENVIRONMENT=production gunicorn -c gunicorn_config.py wsgi:app

# Ou com parâmetros customizados
ENVIRONMENT=production gunicorn \
  --workers 4 \
  --bind 0.0.0.0:5000 \
  --timeout 60 \
  wsgi:app
```

#### Opção 2: Waitress (Windows)

```bash
pip install waitress
ENVIRONMENT=production waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

#### Variáveis de Ambiente

| Variável      | Valores                              | Descrição                         |
|---------------|--------------------------------------|-----------------------------------|
| `ENVIRONMENT` | `production`, `staging`, `development` | Define o ambiente de execução   |
| `SECRET_KEY`  | string aleatória                     | Chave secreta Flask (produção)    |

---

## Endpoints

### 1. `POST /predict` — Previsão de Demanda

Gera previsões de demanda para um ou mais itens com base no histórico de vendas.

**Parâmetros obrigatórios:**

| Campo         | Tipo   | Descrição                               |
|---------------|--------|-----------------------------------------|
| `sales_data`  | array  | Lista de registros `{item_id, timestamp, demand}` |
| `data_inicio` | string | Data de início das previsões (`YYYY-MM-DD`)       |
| `periodos`    | int    | Número de períodos para prever                    |

**Parâmetros opcionais:**

| Campo                    | Tipo    | Padrão           | Descrição                                    |
|--------------------------|---------|------------------|----------------------------------------------|
| `granularidade`          | string  | `"M"`            | `"M"` (mensal), `"S"` (semanal), `"D"` (diário) |
| `seasonality_mode`       | string  | `"multiplicative"` | `"multiplicative"` ou `"additive"`          |
| `seasonal_smooth`        | float   | `0.7`            | Fator de suavização sazonal (0-1)            |
| `confidence_level`       | float   | `0.95`           | Nível de confiança dos intervalos            |
| `confidence_factor`      | float   | `0.7`            | Largura dos intervalos (menor = mais estreitos) |
| `growth_factor`          | float   | `1.0`            | Fator de crescimento global (ex: `1.05` = +5%) |
| `replicate_only`         | bool    | `false`          | Replicar média histórica sem modelagem (só aplica `growth_factor`) |
| `forecast_model`         | string  | `"auto"`         | Modelo de previsão: `"auto"`, `"ses"`, `"holt_linear"`, `"holt_winters"`, `"decomposition"` |
| `month_adjustments`      | object  | `{}`             | Ajustes por mês `{1: 1.2, 12: 0.8}` (1=Jan, 12=Dez)  |
| `day_of_week_adjustments`| object  | `{}`             | Ajustes por dia da semana `{0: 1.1}` (0=Seg) |
| `feriados_enabled`       | bool    | `true`           | Considerar feriados brasileiros              |
| `feriados_adjustments`   | object  | `{}`             | Ajustes por feriado `{"2026-12-25": 0.5}`    |
| `anos_feriados`          | array   | `null`           | Anos para calcular feriados                  |
| `agrupamento_trimestral` | bool    | `false`          | Agrupar previsões por trimestre              |
| `agrupamento_semestral`  | bool    | `false`          | Agrupar previsões por semestre               |
| `include_explanation`    | bool    | `false`          | Incluir explicações textuais/HTML            |
| `explanation_level`      | string  | `"basic"`        | `"basic"`, `"detailed"` ou `"advanced"`      |
| `explanation_language`   | string  | `"pt"`           | `"pt"` ou `"en"`                             |
| `html_layout`            | string  | `"full"`         | `"full"` ou `"compact"` (para popups)        |

**Exemplo — previsão padrão:**

```json
POST /predict
{
  "sales_data": [
    {"item_id": 1, "timestamp": "2025-01-01", "demand": 100},
    {"item_id": 1, "timestamp": "2025-02-01", "demand": 120},
    {"item_id": 1, "timestamp": "2025-03-01", "demand": 110}
  ],
  "data_inicio": "2025-04-01",
  "periodos": 6,
  "granularidade": "M",
  "growth_factor": 1.05,
  "include_explanation": true,
  "explanation_level": "detailed"
}
```

**Exemplo — modo replicação simples:**

```json
POST /predict
{
  "sales_data": [...],
  "data_inicio": "2025-04-01",
  "periodos": 6,
  "replicate_only": true,
  "growth_factor": 1.05
}
```

No modo `replicate_only`, a API pega a média histórica de cada período correspondente (ex: média de todos os Janeiros para prever Janeiro futuro) e aplica apenas o `growth_factor`. Nenhuma modelagem estatística é usada.

**Resposta:**

```json
[
  {
    "item_id": 1,
    "ds": "2025-04-01 00:00:00",
    "yhat": 115.5,
    "yhat_lower": 98.2,
    "yhat_upper": 132.8,
    "trend": 112.0,
    "yearly": 3.5,
    "weekly": 0.0,
    "holidays": 0.0,
    "_html_data": { ... },
    "_explanation": { ... }
  }
]
```

| Campo       | Descrição                                    |
|-------------|----------------------------------------------|
| `yhat`      | Previsão pontual                             |
| `yhat_lower`| Limite inferior do intervalo de confiança    |
| `yhat_upper`| Limite superior do intervalo de confiança    |
| `trend`     | Componente de tendência                      |
| `yearly`    | Componente sazonal                           |
| `_html_data`| Dados para gerar HTML via `/generate_html`   |
| `_explanation`| Explicação textual (se `include_explanation: true`) |

---

### 2. `POST /predict_quarterly` — Previsão Trimestral

Atalho para `/predict` com agrupamento trimestral.

| Campo        | Tipo | Descrição                          |
|--------------|------|------------------------------------|
| `trimestres` | int  | Número de trimestres (mapeia para `periodos`) |

Demais parâmetros são os mesmos do `/predict`.

---

### 3. `POST /predict_semiannually` — Previsão Semestral

Atalho para `/predict` com agrupamento semestral.

| Campo       | Tipo | Descrição                          |
|-------------|------|------------------------------------|
| `semestres` | int  | Número de semestres (mapeia para `periodos`) |

---

### 4. `POST /generate_html` — Geração de HTML de Explicação

Gera HTML formatado a partir dos dados de explicação retornados pelo `/predict`.

**Modo 1 — Passando `_html_data` do predict:**

```json
POST /generate_html
{
  "html_data": { ... _html_data do /predict ... },
  "layout": "full"
}
```

**Modo 2 — Passando dados individuais:**

```json
POST /generate_html
{
  "item_id": 1,
  "prediction": {
    "yhat": 115.5,
    "yhat_lower": 98.2,
    "yhat_upper": 132.8,
    "trend": 112.0,
    "yearly": 3.5,
    "ds": "2025-04-01"
  },
  "explanation_data": {
    "data_points": 12,
    "confidence_score": "Alta",
    "mape": 8.5,
    "r2": 0.85,
    "trend_slope": 2.1,
    "seasonal_pattern": {1: 0.95, 2: 0.88, 3: 1.05},
    "growth_factor": 1.05
  },
  "layout": "full"
}
```

**Parâmetros:**

| Campo               | Tipo   | Padrão  | Descrição                              |
|---------------------|--------|---------|----------------------------------------|
| `layout`            | string | `"full"`| `"full"` (completo) ou `"compact"` (popup) |
| `return_html_direct`| bool   | `false` | Retorna HTML puro ao invés de JSON     |

Para receber HTML puro, envie `Accept: text/html` no header ou `"return_html_direct": true`.

---

### 5. `POST /mrp_optimize` — Otimização MRP

Calcula lotes de produção otimizados com base na demanda prevista.

**Parâmetros obrigatórios:**

| Campo               | Tipo   | Descrição                                      |
|---------------------|--------|-------------------------------------------------|
| `daily_demands`     | object | Demandas médias diárias `{"YYYY-MM": valor}`    |
| `initial_stock`     | float  | Estoque inicial                                 |
| `leadtime_days`     | int    | Lead time em dias                               |
| `period_start_date` | string | Início do período (`YYYY-MM-DD`)                |
| `period_end_date`   | string | Fim do período (`YYYY-MM-DD`)                   |
| `start_cutoff_date` | string | Data de corte inicial para produção             |
| `end_cutoff_date`   | string | Data de corte final para produção               |

**Parâmetros opcionais:**

| Campo                        | Tipo  | Padrão   | Descrição                                  |
|------------------------------|-------|----------|--------------------------------------------|
| `setup_cost`                 | float | `250.0`  | Custo fixo por pedido                      |
| `holding_cost_rate`          | float | `0.20`   | Taxa anual de custo de manutenção          |
| `unit_value`                 | float | `100.0`  | Valor unitário do item (para cálculo EOQ)  |
| `stockout_cost_multiplier`   | float | `2.5`    | Multiplicador de custo de falta            |
| `service_level`              | float | `0.95`   | Nível de serviço desejado (0-1)            |
| `safety_days`                | int   | `3`      | Dias adicionais de segurança               |
| `leadtime_std`               | float | `0.0`    | Desvio padrão do lead time (variabilidade) |
| `min_batch_size`             | float | `50.0`   | Tamanho mínimo do lote                     |
| `max_batch_size`             | float | `10000.0`| Tamanho máximo do lote                     |
| `enable_eoq_optimization`    | bool  | `true`   | Habilitar otimização EOQ                   |
| `enable_consolidation`       | bool  | `true`   | Consolidar pedidos próximos                |
| `consolidation_window_days`  | int   | `5`      | Janela de consolidação em dias             |
| `ignore_safety_stock`        | bool  | `false`  | Ignorar estoque de segurança               |
| `exact_quantity_match`       | bool  | `false`  | Estoque final = demanda exata              |
| `force_excess_production`    | bool  | `false`  | Forçar produção mesmo com estoque suficiente |
| `include_extended_analytics` | bool  | `false`  | Incluir analytics estendidos (custo, risco, what-if) |
| `daily_production_capacity`  | float | infinito | Capacidade diária de produção              |

**Exemplo:**

```json
POST /mrp_optimize
{
  "daily_demands": {"2025-08": 40.10},
  "initial_stock": 1609,
  "leadtime_days": 50,
  "period_start_date": "2025-08-01",
  "period_end_date": "2025-08-31",
  "start_cutoff_date": "2025-07-17",
  "end_cutoff_date": "2025-12-31",
  "include_extended_analytics": true,
  "service_level": 0.95,
  "unit_value": 150.0
}
```

**Resposta (resumida):**

```json
{
  "batches": [
    {
      "order_date": "2025-08-16",
      "arrival_date": "2025-10-05",
      "quantity": 1243.15,
      "analytics": {
        "consumo_lote": 1243.15,
        "estoque_inicial": 1609.0,
        "estoque_final": 1609.0,
        "coverage_days": 31,
        "excess_production": true
      }
    }
  ],
  "analytics": {
    "summary": { ... },
    "stock_evolution": { "2025-08-01": 1568.9, ... },
    "demand_analysis": { ... },
    "extended_analytics": {
      "cost_analysis": { ... },
      "optimization_metrics": { ... },
      "risk_analysis": { ... },
      "what_if_scenarios": { ... },
      "recommendations": [ ... ]
    }
  }
}
```

---

### 6. `POST /mrp_sporadic` — MRP para Demanda Esporádica

Para itens com demandas pontuais (não contínuas).

**Parâmetros obrigatórios:**

| Campo               | Tipo   | Descrição                                   |
|---------------------|--------|----------------------------------------------|
| `sporadic_demand`   | object | Demandas pontuais `{"YYYY-MM-DD": quantidade}` |
| `initial_stock`     | float  | Estoque inicial                              |
| `leadtime_days`     | int    | Lead time em dias                            |
| `period_start_date` | string | Início do período                            |
| `period_end_date`   | string | Fim do período                               |
| `start_cutoff_date` | string | Data de corte inicial                        |
| `end_cutoff_date`   | string | Data de corte final                          |

**Parâmetros opcionais adicionais:**

| Campo                    | Tipo  | Padrão | Descrição                           |
|--------------------------|-------|--------|-------------------------------------|
| `safety_margin_percent`  | float | `8.0`  | Margem de segurança (%)             |
| `minimum_stock_percent`  | float | `0.0`  | Estoque mínimo (% da maior demanda) |
| `max_gap_days`           | int   | `999`  | Gap máximo entre lotes              |

---

### 7. `POST /mrp_advanced` — MRP Avançado

Combina demanda esporádica com algoritmos avançados (EOQ, classificação ABC/XYZ, análise de sazonalidade). Aceita os mesmos parâmetros de `/mrp_sporadic` mais os opcionais de `/mrp_optimize`.

---

## Modelos de Previsão

A API seleciona automaticamente o melhor modelo conforme a quantidade de dados (`forecast_model: "auto"`), ou permite forçar um modelo específico:

| Modelo             | Mínimo de dados | Parâmetro            | Descrição                                                       |
|--------------------|-----------------|----------------------|-----------------------------------------------------------------|
| SES                | 3 pontos        | `"ses"`              | Simple Exponential Smoothing — sem tendência, sem sazonalidade  |
| Holt Linear        | 5 pontos        | `"holt_linear"`      | Tendência aditiva (com/sem damping), sem sazonalidade           |
| Holt-Winters       | 24 pontos       | `"holt_winters"`     | Tendência + sazonalidade (aditiva ou multiplicativa)            |
| Decomposição       | 3 pontos        | `"decomposition"`    | Tendência linear + sazonalidade por médias mensais (modelo base)|
| Auto (padrão)      | qualquer        | `"auto"`             | Testa todos os disponíveis e escolhe por menor MAPE             |

Cascata automática:
- **3-4 pontos**: SES vs decomposição
- **5-23 pontos**: SES + Holt Linear vs decomposição
- **24+ pontos**: SES + Holt Linear + Holt-Winters vs decomposição

## Funcionalidades Adicionais de Previsão

| Funcionalidade                    | Descrição                                                    |
|-----------------------------------|--------------------------------------------------------------|
| Detecção de sazonalidade          | Via autocorrelação (ACF) — ativada automaticamente           |
| Detecção de outliers              | Ensemble: Z-score + IQR + MAD (voto 2/3)                    |
| Intervalos de confiança fan-out   | Alargam conforme o horizonte de previsão                     |
| Verificação de completude         | Detecta gaps e dados faltantes no histórico                  |
| Feriados brasileiros              | Ajuste automático para feriados nacionais                    |
| Modo replicação (`replicate_only`)| Replica histórico sem modelagem, só `growth_factor`          |

## Funcionalidades do MRP

| Funcionalidade                | Descrição                                               |
|-------------------------------|---------------------------------------------------------|
| EOQ otimizado                 | Fórmula corrigida com `unit_value` configurável         |
| Safety stock com variabilidade| Fórmula completa com desvio padrão do lead time (σ_LT)  |
| Consolidação de pedidos       | Agrupa pedidos próximos para reduzir custos de setup     |
| Simulação Monte Carlo         | VaR, CVaR, probabilidade de stockout                    |
| Analytics estendidos          | Custo, risco, what-if, recomendações                    |
| Produção em excesso           | `force_excess_production` para produzir além da demanda  |

## Códigos de Erro

| Código | Descrição                                       |
|--------|-------------------------------------------------|
| `400`  | Parâmetro inválido ou ausente                   |
| `500`  | Erro interno no processamento                   |

Todos os erros retornam JSON: `{"error": "mensagem descritiva"}`.
