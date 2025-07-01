# 📊 Sistema MRP Avançado - Documentação Completa

## 🎯 Visão Geral

O **Sistema MRP Avançado** é uma solução completa de planejamento de recursos de materiais (Material Requirements Planning) que utiliza algoritmos inteligentes de supply chain para otimizar o planejamento de produção e estoque.

### ✨ Principais Características

- **🧠 Algoritmos Inteligentes**: Múltiplas estratégias baseadas em lead time e características da demanda
- **📈 EOQ Automático**: Cálculo automático do lote econômico de compra
- **🏷️ Classificação ABC/XYZ**: Categorização automática de itens por valor e variabilidade
- **📊 Analytics Avançados**: Análise detalhada de performance e riscos
- **🔄 Consolidação Inteligente**: Agrupamento otimizado de pedidos para reduzir custos
- **⚡ API REST**: Endpoint moderno `/mrp_advanced` com resposta JSON estruturada
- **🛡️ Detecção de Sazonalidade**: Identificação automática de padrões sazonais

---

## 🚀 Início Rápido

### 1. Endpoint Principal

```http
POST /mrp_advanced
Content-Type: application/json
```

### 2. Exemplo de Requisição

```json
{
    "sporadic_demand": {
        "2025-07-07": 4000,
        "2025-08-27": 4000,
        "2025-10-17": 4000
    },
    "initial_stock": 1941,
    "leadtime_days": 70,
    "period_start_date": "2025-05-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-05-01",
    "end_cutoff_date": "2025-12-31",
    "safety_margin_percent": 8,
    "safety_days": 2,
    "minimum_stock_percent": 0,
    "enable_consolidation": true
}
```

### 3. Resposta Estruturada

A resposta inclui:
- **📦 batches**: Lista de lotes planejados com analytics detalhados
- **📊 analytics**: Métricas completas de performance e análise
- **🔍 _endpoint_info**: Informações sobre recursos utilizados

---

## 🎛️ Estratégias de Planejamento

O sistema seleciona automaticamente a melhor estratégia baseada nas características da demanda e lead time:

### 1. 🎯 Estratégia EOQ (Lead Time ≤ 14 dias)
- **Objetivo**: Otimizar custos através do lote econômico
- **Características**: 
  - Cálculo automático do EOQ
  - Ponto de reposição inteligente
  - Baixa variabilidade da demanda

### 2. 🔄 Estratégia de Buffer Dinâmico (Alta Variabilidade)
- **Objetivo**: Lidar com demandas imprevisíveis
- **Características**:
  - Estoques de segurança aumentados
  - Flexibilidade para picos de demanda
  - Monitoramento contínuo

### 3. 📅 Estratégia de Lead Time Longo (> 45 dias)
- **Objetivo**: Planejamento estratégico para horizontes longos
- **Características**:
  - Poucos lotes grandes
  - Previsão avançada de demanda
  - Mitigação de riscos de lead time

### 4. 🔗 Estratégia de Consolidação Híbrida
- **Objetivo**: Combinar eficiência operacional com otimização de custos
- **Características**:
  - Agrupamento inteligente de pedidos
  - Análise custo-benefício automática
  - Prevenção de overlap de lead time

---

## 📋 Parâmetros de Configuração

### Parâmetros Obrigatórios

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `sporadic_demand` | Object | Demandas específicas por data (formato: "YYYY-MM-DD": quantidade) |
| `initial_stock` | Number | Estoque inicial disponível |
| `leadtime_days` | Number | Lead time em dias entre pedido e chegada |
| `period_start_date` | String | Data de início do período de planejamento |
| `period_end_date` | String | Data de fim do período de planejamento |
| `start_cutoff_date` | String | Data limite para início dos pedidos |
| `end_cutoff_date` | String | Data limite para chegada dos lotes |

### Parâmetros Opcionais

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `safety_margin_percent` | Number | 8 | Margem de segurança percentual |
| `safety_days` | Number | 2 | Dias de segurança adicional |
| `minimum_stock_percent` | Number | 0 | Estoque mínimo como % da maior demanda |
| `enable_consolidation` | Boolean | true | Habilitar consolidação inteligente |
| `setup_cost` | Number | 250 | Custo fixo por pedido |
| `holding_cost_rate` | Number | 0.20 | Taxa de custo de manutenção (anual) |
| `service_level` | Number | 0.98 | Nível de serviço alvo (95-99%) |
| `min_batch_size` | Number | 200 | Tamanho mínimo do lote |
| `max_batch_size` | Number | 10000 | Tamanho máximo do lote |

---

## 📊 Analytics e Métricas

### Resumo Executivo (`analytics.summary`)

```json
{
    "initial_stock": 1941,
    "final_stock": 9047.09,
    "minimum_stock": -2059,
    "stockout_occurred": false,
    "total_batches": 2,
    "total_produced": 19106.09,
    "production_coverage_rate": "159%",
    "demand_fulfillment_rate": 100.0
}
```

### Análise de Demanda (`analytics.demand_analysis`)

- **📈 total_demand**: Demanda total do período
- **📊 average_daily_demand**: Média diária de demanda
- **📅 demand_events**: Número de eventos de demanda
- **🎯 demand_distribution**: Distribuição das demandas por data

### Métricas de Demanda Esporádica (`analytics.sporadic_demand_metrics`)

- **🎯 demand_concentration**: Concentração da demanda no período
- **📏 interval_statistics**: Estatísticas dos intervalos entre demandas
- **🔮 demand_predictability**: Nível de previsibilidade da demanda
- **⚡ peak_demand_analysis**: Análise de picos de demanda

### Eficiência de Produção (`analytics.production_efficiency`)

- **📦 average_batch_size**: Tamanho médio dos lotes
- **⚙️ production_line_utilization**: Utilização da linha de produção
- **⏱️ production_gaps**: Intervalos entre produções
- **✅ lead_time_compliance**: Conformidade com lead time

---

## 🎯 Classificações Automáticas

### Classificação ABC (Por Valor)
- **🥇 Classe A**: Itens de alto valor (>70% do valor total)
- **🥈 Classe B**: Itens de valor médio (20-70% do valor total)
- **🥉 Classe C**: Itens de baixo valor (<20% do valor total)

### Classificação XYZ (Por Variabilidade)
- **📊 Classe X**: Baixa variabilidade (CV < 0.2)
- **📈 Classe Y**: Variabilidade média (CV 0.2-0.5)
- **📉 Classe Z**: Alta variabilidade (CV > 0.5)

---

## ⚙️ Algoritmos de Otimização

### 1. Cálculo do EOQ (Economic Order Quantity)

```
EOQ = √(2 × Demanda Anual × Custo de Setup) / Custo de Manutenção
```

### 2. Estoque de Segurança

```
Safety Stock = Z-score × Desvio Padrão × √Lead Time
```

### 3. Ponto de Reposição

```
Reorder Point = (Demanda Média × Lead Time) + Safety Stock
```

### 4. Análise de Consolidação

O sistema avalia automaticamente:
- **💰 Economia de Setup**: Redução de custos fixos
- **📦 Custo de Manutenção**: Aumento do custo de carregamento
- **⚡ Benefícios Operacionais**: Simplificação e eficiência
- **🎯 Benefício Líquido**: Decisão final de consolidação

---

## 🛠️ Configuração Avançada

### Exemplo com Parâmetros Customizados

```json
{
    "sporadic_demand": {
        "2025-07-15": 5000,
        "2025-09-10": 3000,
        "2025-11-20": 4500
    },
    "initial_stock": 2000,
    "leadtime_days": 45,
    "period_start_date": "2025-06-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-06-01",
    "end_cutoff_date": "2025-12-31",
    "safety_margin_percent": 10,
    "safety_days": 3,
    "enable_consolidation": true,
    "setup_cost": 500,
    "holding_cost_rate": 0.15,
    "service_level": 0.95,
    "min_batch_size": 500,
    "max_batch_size": 15000
}
```

---

## 🎨 Recursos Visuais

### Evolução do Estoque

O sistema fornece a evolução completa do estoque dia a dia em `analytics.stock_evolution`:

```json
{
    "2025-05-01": 1941,
    "2025-05-02": 1941,
    "2025-07-10": 12247.09,
    "2025-08-27": 8247.09
}
```

### Pontos Críticos

Identificação automática de situações de risco em `analytics.critical_points`:

```json
[
    {
        "date": "2025-07-07",
        "stock": -2059,
        "days_of_coverage": -42,
        "severity": "stockout"
    }
]
```

---

## 🚨 Tratamento de Erros

### Códigos de Erro Comuns

| Código | Descrição | Solução |
|--------|-----------|---------|
| 400 | Parâmetros inválidos | Verificar formato dos dados |
| 422 | Lead time incompatível | Ajustar datas ou lead time |
| 500 | Erro interno | Verificar logs do servidor |

### Validações Automáticas

O sistema valida automaticamente:
- ✅ Formato das datas (YYYY-MM-DD)
- ✅ Consistência entre período e cutoff
- ✅ Viabilidade do lead time
- ✅ Valores numéricos positivos

---

## 🎓 Casos de Uso

### 1. 🏭 Indústria Manufacturing
- Planejamento de produção com lead times longos
- Otimização de estoques de matéria-prima
- Consolidação de ordens de compra

### 2. 🛒 Varejo e Distribuição
- Reposição de produtos sazonais
- Gestão de estoques multi-localização
- Planejamento de promoções

### 3. 📦 E-commerce
- Gestão de produtos de alta rotação
- Planejamento para picos de demanda
- Otimização de fulfillment

### 4. 🏥 Healthcare
- Gestão de medicamentos e suprimentos
- Planejamento de equipamentos críticos
- Conformidade regulatória

---

## 🔧 Integração

### Exemplo em Python

```python
import requests

response = requests.post('http://localhost:5000/mrp_advanced', 
    json=mrp_data)

if response.status_code == 200:
    result = response.json()
    batches = result['batches']
    analytics = result['analytics']
else:
    print(f"Erro: {response.status_code}")
```

### Exemplo em PHP

```php
$data = json_encode($mrp_data);
$ch = curl_init('http://localhost:5000/mrp_advanced');
curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$response = curl_exec($ch);
$result = json_decode($response, true);
```

---

## 📞 Suporte

Para suporte técnico ou dúvidas sobre implementação:

- 📧 **Email**: suporte@mrp-system.com
- 📚 **Documentação**: `/docs/api-reference`
- 🐛 **Issues**: GitHub Issues
- 💬 **Chat**: Slack #mrp-support

---

## 📝 Changelog

### v1.0 (2025-06-30)
- ✅ Lançamento inicial do sistema MRP avançado
- ✅ Algoritmos de otimização implementados
- ✅ Classificação ABC/XYZ automática
- ✅ Consolidação inteligente de pedidos
- ✅ Correção de bugs de duplicação de lotes
- ✅ Melhorias na precisão de timing de chegadas

---

*Documentação atualizada em: 30 de Junho de 2025* 