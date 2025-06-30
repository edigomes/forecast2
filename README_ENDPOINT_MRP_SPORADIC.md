# 📡 Endpoint `/mrp_sporadic` - API de Demanda Esporádica

## 🎯 Descrição

O endpoint `/mrp_sporadic` permite planejar lotes de insumos para demandas que ocorrem em datas específicas (demandas esporádicas), usando algoritmos avançados de supply chain.

### ✨ Principais Características

- ✅ **Planejamento otimizado** para demandas específicas por data
- 🚀 **Algoritmos avançados** de supply chain (EOQ, consolidação, etc.)
- 📊 **Métricas exclusivas** para demandas esporádicas
- 🔧 **Altamente configurável** com validações robustas
- ⚡ **Performance rápida** (< 0.1s para cenários típicos)

---

## 🌐 Informações da API

| Propriedade | Valor |
|-------------|-------|
| **URL** | `POST /mrp_sporadic` |
| **Content-Type** | `application/json` |
| **Timeout Recomendado** | 30 segundos |
| **Rate Limit** | Sem limite |

---

## 📝 Parâmetros da Requisição

### ✅ Parâmetros Obrigatórios

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `sporadic_demand` | Object | Demandas específicas por data | `{"2024-01-15": 500.0, "2024-02-05": 800.0}` |
| `initial_stock` | Number | Estoque inicial disponível | `200.0` |
| `leadtime_days` | Integer | Lead time em dias | `7` |
| `period_start_date` | String | Data início período (YYYY-MM-DD) | `"2024-01-01"` |
| `period_end_date` | String | Data fim período (YYYY-MM-DD) | `"2024-03-31"` |
| `start_cutoff_date` | String | Data limite início produção (YYYY-MM-DD) | `"2024-01-01"` |
| `end_cutoff_date` | String | Data limite chegada (YYYY-MM-DD) | `"2024-04-15"` |

### ⚙️ Parâmetros Opcionais Específicos

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `safety_margin_percent` | Number | `8.0` | Margem de segurança em % |
| `safety_days` | Integer | `2` | Dias de antecipação de segurança |
| `minimum_stock_percent` | Number | `0.0` | Estoque mínimo em % da maior demanda |
| `max_gap_days` | Integer | `999` | Gap máximo entre lotes (999 = sem limite) |

### 🚀 Parâmetros Avançados de Otimização

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `setup_cost` | Number | `250.0` | Custo fixo por pedido |
| `holding_cost_rate` | Number | `0.20` | Taxa de custo de manutenção (anual) |
| `service_level` | Number | `0.95` | Nível de serviço desejado (0-1) |
| `min_batch_size` | Number | `200.0` | Tamanho mínimo do lote |
| `max_batch_size` | Number | `10000.0` | Tamanho máximo do lote |
| `enable_consolidation` | Boolean | `true` | Habilitar consolidação de pedidos |
| `enable_eoq_optimization` | Boolean | `true` | Habilitar otimização EOQ |

---

## 🔍 Exemplo de Requisição

### Cenário Básico

```json
{
  "sporadic_demand": {
    "2024-01-15": 500.0,
    "2024-01-22": 300.0,
    "2024-02-05": 800.0,
    "2024-02-18": 400.0,
    "2024-03-10": 600.0
  },
  "initial_stock": 200.0,
  "leadtime_days": 7,
  "period_start_date": "2024-01-01",
  "period_end_date": "2024-03-31",
  "start_cutoff_date": "2024-01-01",
  "end_cutoff_date": "2024-04-15",
  "safety_margin_percent": 10.0,
  "safety_days": 2,
  "minimum_stock_percent": 5.0,
  "max_gap_days": 30
}
```

### Cenário Avançado com Otimização

```json
{
  "sporadic_demand": {
    "2024-01-08": 1200.0,
    "2024-01-15": 300.0,
    "2024-01-16": 250.0,
    "2024-02-12": 1500.0,
    "2024-03-05": 600.0
  },
  "initial_stock": 500.0,
  "leadtime_days": 10,
  "period_start_date": "2024-01-01",
  "period_end_date": "2024-03-31",
  "start_cutoff_date": "2023-12-15",
  "end_cutoff_date": "2024-04-30",
  "safety_margin_percent": 15.0,
  "safety_days": 3,
  "minimum_stock_percent": 10.0,
  "max_gap_days": 20,
  "setup_cost": 500.0,
  "holding_cost_rate": 0.18,
  "service_level": 0.98,
  "min_batch_size": 200.0,
  "max_batch_size": 3000.0,
  "enable_consolidation": true,
  "enable_eoq_optimization": true
}
```

---

## 📊 Estrutura da Resposta

### ✅ Sucesso (Status 200)

```json
{
  "batches": [
    {
      "order_date": "2024-01-06",
      "arrival_date": "2024-01-13",
      "quantity": 810.0,
      "analytics": {
        "stock_before_arrival": 200.0,
        "stock_after_arrival": 1010.0,
        "target_demand_date": "2024-01-15",
        "target_demand_quantity": 500.0,
        "shortfall_covered": 300.0,
        "is_critical": false,
        "urgency_level": "high",
        "safety_margin_days": 2,
        "efficiency_ratio": 1.62
      }
    }
  ],
  "analytics": {
    "summary": {
      "initial_stock": 200.0,
      "final_stock": 205.79,
      "minimum_stock": 200.0,
      "minimum_stock_date": "2024-01-01",
      "total_batches": 4,
      "total_produced": 2605.79,
      "demand_fulfillment_rate": 100.0,
      "demands_met_count": 5,
      "demands_unmet_count": 0,
      "stockout_occurred": false
    },
    "sporadic_demand_metrics": {
      "demand_concentration": {
        "concentration_index": 0.056,
        "concentration_level": "low"
      },
      "interval_statistics": {
        "average_interval_days": 13.8,
        "min_interval_days": 7,
        "max_interval_days": 21,
        "interval_variance": 45.2
      },
      "demand_predictability": "medium",
      "peak_demand_analysis": {
        "peak_count": 1,
        "peak_threshold": 780.0,
        "peak_dates": ["2024-02-05"],
        "average_peak_size": 800.0
      }
    },
    "production_efficiency": {
      "average_batch_size": 651.45,
      "critical_deliveries": 0,
      "batch_efficiency": 100.0,
      "average_safety_margin": 2.5
    },
    "demand_analysis": {
      "total_demand": 2600.0,
      "demand_events": 5,
      "average_demand_per_event": 520.0,
      "first_demand_date": "2024-01-15",
      "last_demand_date": "2024-03-10"
    },
    "stock_evolution": {
      "2024-01-01": 200.0,
      "2024-01-02": 200.0,
      "...": "..."
    },
    "stock_end_of_period": {
      "after_batch_arrival": [
        {
          "batch_number": 1,
          "date": "2024-01-13",
          "stock_before": 200.0,
          "batch_quantity": 810.0,
          "stock_after": 1010.0,
          "coverage_gained": 14
        }
      ],
      "monthly": [...],
      "before_batch_arrival": [...]
    },
    "order_dates": ["2024-01-06", "2024-01-28", "2024-02-25", "2024-03-01"],
    "critical_points": []
  }
}
```

### ❌ Erro (Status 400/500)

```json
{
  "error": "Campo obrigatório 'sporadic_demand' não fornecido"
}
```

---

## ⚠️ Validações e Regras

### Validações de Entrada

| Campo | Validação |
|-------|-----------|
| `sporadic_demand` | Deve ser dicionário não vazio com datas YYYY-MM-DD e valores positivos |
| `initial_stock` | Deve ser número não negativo |
| `leadtime_days` | Deve ser inteiro não negativo |
| `period_start_date` | Deve ser anterior a `period_end_date` |
| `safety_margin_percent` | Deve estar entre 0 e 100 |
| `minimum_stock_percent` | Deve estar entre 0 e 100 |
| `max_gap_days` | Deve ser pelo menos 1 |

### Regras de Negócio

- ✅ Demandas fora do período são ignoradas automaticamente
- ✅ Lotes são planejados com antecedência baseada em `safety_days`
- ✅ Consolidação automática quando `max_gap_days` é atingido
- ✅ Estoque mínimo calculado com base na maior demanda
- ✅ Otimização EOQ aplicada quando habilitada

---

## 🚀 Exemplos de Uso

### cURL

```bash
curl -X POST http://127.0.0.1:5000/mrp_sporadic \
  -H "Content-Type: application/json" \
  -d '{
    "sporadic_demand": {
      "2024-01-15": 500.0,
      "2024-02-05": 800.0
    },
    "initial_stock": 200.0,
    "leadtime_days": 7,
    "period_start_date": "2024-01-01",
    "period_end_date": "2024-03-31",
    "start_cutoff_date": "2024-01-01",
    "end_cutoff_date": "2024-04-15"
  }'
```

### Python

```python
import requests

url = "http://127.0.0.1:5000/mrp_sporadic"
data = {
    "sporadic_demand": {
        "2024-01-15": 500.0,
        "2024-02-05": 800.0,
        "2024-03-10": 600.0
    },
    "initial_stock": 200.0,
    "leadtime_days": 7,
    "period_start_date": "2024-01-01",
    "period_end_date": "2024-03-31",
    "start_cutoff_date": "2024-01-01",
    "end_cutoff_date": "2024-04-15",
    "safety_margin_percent": 10.0
}

response = requests.post(url, json=data)
result = response.json()

print(f"Lotes planejados: {len(result['batches'])}")
print(f"Taxa de atendimento: {result['analytics']['summary']['demand_fulfillment_rate']}%")
```

### JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

const data = {
  sporadic_demand: {
    "2024-01-15": 500.0,
    "2024-02-05": 800.0
  },
  initial_stock: 200.0,
  leadtime_days: 7,
  period_start_date: "2024-01-01",
  period_end_date: "2024-03-31",
  start_cutoff_date: "2024-01-01",
  end_cutoff_date: "2024-04-15"
};

fetch('http://127.0.0.1:5000/mrp_sporadic', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
})
.then(response => response.json())
.then(result => {
  console.log(`Lotes planejados: ${result.batches.length}`);
  console.log(`Taxa de atendimento: ${result.analytics.summary.demand_fulfillment_rate}%`);
});
```

### PHP

```php
<?php
$data = [
    'sporadic_demand' => [
        '2024-01-15' => 500.0,
        '2024-02-05' => 800.0
    ],
    'initial_stock' => 200.0,
    'leadtime_days' => 7,
    'period_start_date' => '2024-01-01',
    'period_end_date' => '2024-03-31',
    'start_cutoff_date' => '2024-01-01',
    'end_cutoff_date' => '2024-04-15'
];

$ch = curl_init('http://127.0.0.1:5000/mrp_sporadic');
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$result = json_decode($response, true);

echo "Lotes planejados: " . count($result['batches']) . "\n";
echo "Taxa de atendimento: " . $result['analytics']['summary']['demand_fulfillment_rate'] . "%\n";
?>
```

---

## 🎯 Casos de Uso

### 1. 🎪 Produção por Encomenda
```json
{
  "sporadic_demand": {
    "2024-01-20": 1200.0,  // Cliente A
    "2024-02-15": 800.0,   // Cliente B
    "2024-03-05": 1500.0   // Cliente C
  }
}
```

### 2. 🎄 Eventos Sazonais
```json
{
  "sporadic_demand": {
    "2024-02-14": 2000.0,  // Dia dos Namorados
    "2024-05-12": 1500.0,  // Dia das Mães
    "2024-12-25": 3000.0   // Natal
  }
}
```

### 3. 🏗️ Projetos com Marcos
```json
{
  "sporadic_demand": {
    "2024-01-31": 500.0,   // Fase 1
    "2024-03-31": 800.0,   // Fase 2
    "2024-05-31": 1200.0   // Fase 3
  }
}
```

---

## 📅 Datas de Reposição

### Como Acessar
```javascript
// Extrair datas de reposição da resposta
const batchArrivals = response.analytics.stock_end_of_period.after_batch_arrival;
const replenishmentDates = batchArrivals.map(batch => batch.date);

console.log('Datas de reposição:', replenishmentDates);
// Output: ['2024-01-13', '2024-01-28', '2024-02-25', '2024-03-01']
```

### Estrutura Detalhada
```json
{
  "after_batch_arrival": [
    {
      "batch_number": 1,
      "date": "2024-01-13",          // Data da reposição
      "stock_before": 200.0,         // Estoque antes da chegada
      "batch_quantity": 810.0,       // Quantidade do lote
      "stock_after": 1010.0,         // Estoque após a chegada
      "coverage_gained": 14          // Dias de cobertura ganhos
    }
  ]
}
```

### Casos de Uso
- ✅ **Calendário de Suprimentos**: Mostrar quando o estoque será reposto
- ✅ **Planejamento Logístico**: Coordenar recebimentos e armazenagem
- ✅ **Alertas Automáticos**: Notificar sobre chegadas de lotes
- ✅ **Dashboards**: Visualizar cronograma de reposições

## 📈 Métricas Exclusivas

### Concentração de Demanda
- **Índice**: Proporção de dias com demanda vs. total
- **Níveis**: Low/Medium/High

### Previsibilidade
- **Análise de Intervalos**: Estatísticas dos gaps entre demandas
- **Classificação**: High/Medium/Low baseada na variabilidade

### Eficiência de Lotes
- **Ratio**: Relação entre tamanho do lote e demanda específica
- **Alinhamento**: Temporal entre lotes e demandas
- **Cobertura**: Quantas demandas cada lote atende

---

## ⚡ Performance

| Cenário | Tempo Médio | Memória |
|---------|-------------|---------|
| 1-10 demandas | < 0.1s | ~5MB |
| 11-50 demandas | < 0.5s | ~10MB |
| 51-100 demandas | < 1.0s | ~15MB |
| 100+ demandas | < 2.0s | ~20MB |

---

## 🐛 Troubleshooting

### Problemas Comuns

| Problema | Solução |
|----------|---------|
| Demandas não atendidas | Verificar `start_cutoff_date` e `end_cutoff_date` |
| Muitos lotes pequenos | Aumentar `min_batch_size` ou reduzir `max_gap_days` |
| Estoque muito alto | Reduzir `safety_margin_percent` e `minimum_stock_percent` |
| Timeout | Reduzir número de demandas ou aumentar timeout |

### Códigos de Erro

| Status | Descrição |
|--------|-----------|
| 400 | Dados inválidos (ver mensagem de erro) |
| 500 | Erro interno do servidor |
| 404 | Endpoint não encontrado |

---

## 🔄 Compatibilidade

- ✅ **Função PHP Original**: 100% compatível
- ✅ **Formato JSON**: Padrão e limpo
- ✅ **UTF-8**: Suporte completo
- ✅ **Tipos**: Conversão automática de numpy
- ✅ **Browsers**: CORS configurado

---

## 📝 Logs

O servidor gera logs detalhados incluindo:

- 📊 Análise prévia das demandas
- 🔧 Parâmetros utilizados
- 📈 Resultados e métricas
- 🎯 Lotes planejados com detalhes
- ⚠️ Demandas não atendidas (se houver)

Verifique o terminal do servidor para informações detalhadas.

---

**🚀 Endpoint pronto para produção com algoritmos avançados de supply chain!** 