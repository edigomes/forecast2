# Endpoint MRP - Otimização de Lotes de Produção/Compra

## Visão Geral

O endpoint `/mrp_optimize` fornece otimização inteligente de lotes de produção/compra usando algoritmos avançados de supply chain, incluindo estratégias Just-In-Time, EOQ (Economic Order Quantity), políticas (s,S) e MRP clássico.

## URL do Endpoint

```
POST http://127.0.0.1:5000/mrp_optimize
```

## Parâmetros Obrigatórios

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `daily_demands` | Dict | Demandas diárias por mês no formato `{"YYYY-MM": valor}` |
| `initial_stock` | Float | Estoque inicial disponível |
| `leadtime_days` | Integer | Lead time em dias (tempo de entrega) |
| `period_start_date` | String | Data início do período de planejamento (YYYY-MM-DD) |
| `period_end_date` | String | Data fim do período de planejamento (YYYY-MM-DD) |
| `start_cutoff_date` | String | Data de corte inicial para pedidos (YYYY-MM-DD) |
| `end_cutoff_date` | String | Data de corte final para pedidos (YYYY-MM-DD) |

## Parâmetros Opcionais de Otimização

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `setup_cost` | Float | 250.0 | Custo fixo por pedido/setup |
| `holding_cost_rate` | Float | 0.20 | Taxa de custo de manutenção de estoque (20% ao ano) |
| `stockout_cost_multiplier` | Float | 2.5 | Multiplicador do custo de falta de estoque |
| `service_level` | Float | 0.95 | Nível de serviço desejado (95%) |
| `min_batch_size` | Float | 50.0 | Tamanho mínimo do lote |
| `max_batch_size` | Float | 10000.0 | Tamanho máximo do lote |
| `review_period_days` | Integer | 7 | Período de revisão padrão em dias |
| `safety_days` | Integer | 3 | Dias de segurança adicional |
| `consolidation_window_days` | Integer | 5 | Janela em dias para consolidar pedidos |
| `daily_production_capacity` | Float | Infinito | Capacidade diária de produção |
| `enable_eoq_optimization` | Boolean | true | Habilitar otimização EOQ |
| `enable_consolidation` | Boolean | true | Habilitar consolidação de pedidos |

## Estratégias de Otimização

O sistema escolhe automaticamente a melhor estratégia baseada no lead time:

- **Lead Time = 0**: Estratégia Just-In-Time (JIT)
- **Lead Time 1-3 dias**: Estratégia de lead time curto com revisão semanal
- **Lead Time 4-14 dias**: Estratégia (s,S) com política de reposição
- **Lead Time >14 dias**: MRP clássico com horizonte de planejamento

## Exemplo de Requisição

### Requisição Básica
```json
{
  "daily_demands": {
    "2024-01": 56.18,
    "2024-02": 62.50,
    "2024-03": 58.75,
    "2024-04": 71.20
  },
  "initial_stock": 329.0,
  "leadtime_days": 5,
  "period_start_date": "2024-01-01",
  "period_end_date": "2024-04-30",
  "start_cutoff_date": "2024-01-01",
  "end_cutoff_date": "2024-04-30"
}
```

### Requisição com Parâmetros Customizados
```json
{
  "daily_demands": {
    "2024-01": 56.18,
    "2024-02": 62.50,
    "2024-03": 58.75
  },
  "initial_stock": 329.0,
  "leadtime_days": 5,
  "period_start_date": "2024-01-01",
  "period_end_date": "2024-03-31",
  "start_cutoff_date": "2024-01-01",
  "end_cutoff_date": "2024-03-31",
  
  "setup_cost": 300.0,
  "service_level": 0.98,
  "enable_consolidation": true,
  "consolidation_window_days": 7,
  "min_batch_size": 100.0,
  "safety_days": 5
}
```

## Estrutura da Resposta

A resposta contém duas seções principais: `batches` (lotes planejados) e `analytics` (análises).

### Exemplo de Resposta
```json
{
  "batches": [
    {
      "order_date": "2024-01-15",
      "arrival_date": "2024-01-20",
      "quantity": 450.5,
      "analytics": {
        "stock_before_arrival": 25.3,
        "stock_after_arrival": 475.8,
        "coverage_days": 8,
        "actual_lead_time": 5,
        "urgency_level": "normal",
        "reorder_point": 150.0,
        "safety_stock": 45.2
      }
    }
  ],
  "analytics": {
    "summary": {
      "initial_stock": 329.0,
      "final_stock": 234.5,
      "minimum_stock": 15.2,
      "maximum_stock": 675.8,
      "average_stock": 387.4,
      "stockout_occurred": false,
      "total_batches": 3,
      "total_produced": 1250.0,
      "total_demand": 1344.6,
      "production_coverage_rate": 92.96
    },
    "performance_metrics": {
      "realized_service_level": 97.5,
      "inventory_turnover": 3.47,
      "average_days_of_inventory": 105.2,
      "setup_frequency": 3,
      "average_batch_size": 416.67
    },
    "cost_analysis": {
      "total_cost": 2847.50,
      "setup_cost": 900.0,
      "holding_cost": 1547.50,
      "stockout_cost": 400.0
    },
    "demand_analysis": {
      "average_daily_demand": 62.11,
      "demand_std_deviation": 6.34,
      "coefficient_of_variation": 0.102,
      "demand_trend": 0.125
    }
  }
}
```

## Campos dos Lotes (batches)

| Campo | Descrição |
|-------|-----------|
| `order_date` | Data em que o pedido deve ser feito |
| `arrival_date` | Data prevista de chegada do lote |
| `quantity` | Quantidade do lote |
| `analytics.stock_before_arrival` | Estoque antes da chegada |
| `analytics.stock_after_arrival` | Estoque após a chegada |
| `analytics.coverage_days` | Dias de cobertura do lote |
| `analytics.urgency_level` | Nível de urgência: `jit`, `normal`, `high`, `planned` |

## Campos das Análises (analytics)

### Summary
- **initial_stock**: Estoque inicial
- **final_stock**: Estoque final projetado
- **minimum_stock**: Menor nível de estoque no período
- **stockout_occurred**: Se houve falta de estoque

### Performance Metrics
- **realized_service_level**: Nível de serviço realizado (%)
- **inventory_turnover**: Giro de estoque
- **average_days_of_inventory**: Dias médios de estoque

### Cost Analysis
- **total_cost**: Custo total estimado
- **setup_cost**: Custo total de setups
- **holding_cost**: Custo de manutenção de estoque
- **stockout_cost**: Custo de falta de estoque

## Como Testar

1. **Inicie o servidor**:
```bash
python server.py
```

2. **Execute o teste**:
```bash
python teste_mrp_endpoint.py
```

3. **Ou faça uma requisição manual**:
```bash
curl -X POST http://127.0.0.1:5000/mrp_optimize \
  -H "Content-Type: application/json" \
  -d '{
    "daily_demands": {"2024-01": 50, "2024-02": 55},
    "initial_stock": 200,
    "leadtime_days": 3,
    "period_start_date": "2024-01-01",
    "period_end_date": "2024-02-29",
    "start_cutoff_date": "2024-01-01",
    "end_cutoff_date": "2024-02-29"
  }'
```

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Parâmetros inválidos ou obrigatórios faltando |
| 500 | Erro interno do servidor durante otimização |

### Exemplos de Erros Comuns

```json
{
  "error": "Campo obrigatório 'daily_demands' não fornecido"
}
```

```json
{
  "error": "initial_stock deve ser número e leadtime_days deve ser inteiro"
}
```

```json
{
  "error": "Formato inválido em daily_demands. Chave '2024-13' deve ser YYYY-MM e valor deve ser numérico"
}
```

## Logs e Debug

O endpoint gera logs detalhados incluindo:
- Parâmetros de entrada
- Estratégia escolhida baseada no lead time
- Resultados da otimização
- Métricas de performance
- Primeiros lotes planejados

Os resultados completos são salvos em `mrp_results_completos.json` para análise posterior.

## Integração com PHP

Para integração com sistemas PHP, use a função wrapper disponível no módulo MRP:

```python
from mrp import optimize_mrp_from_php_data

# Retorna JSON string
result_json = optimize_mrp_from_php_data(
    daily_demands={"2024-01": 50.0},
    initial_stock=200.0,
    leadtime_days=3,
    period_start_date="2024-01-01",
    period_end_date="2024-01-31",
    start_cutoff_date="2024-01-01",
    end_cutoff_date="2024-01-31"
)
``` 