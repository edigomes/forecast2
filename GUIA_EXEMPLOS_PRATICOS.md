# 📚 Guia de Exemplos Práticos - Sistema MRP Avançado

## 🎯 Cenários Reais de Uso

### 1. 🏭 Indústria Automotiva - Peças de Reposição

**Situação**: Fábrica de autopeças com demanda esporádica de componentes críticos

```json
{
    "sporadic_demand": {
        "2025-08-15": 2000,  // Manutenção programada
        "2025-10-30": 3500,  // Recall do fabricante
        "2025-12-10": 1800   // Demanda de final de ano
    },
    "initial_stock": 800,
    "leadtime_days": 45,
    "period_start_date": "2025-07-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-07-01",
    "end_cutoff_date": "2025-12-31",
    "safety_margin_percent": 15,
    "safety_days": 5,
    "setup_cost": 800,
    "holding_cost_rate": 0.18,
    "min_batch_size": 1000,
    "max_batch_size": 8000,
    "enable_consolidation": true
}
```

**Resultado Esperado**:
- Estratégia: Lead Time Longo
- 2-3 lotes otimizados
- Alta consolidação por custos de setup
- Safety stock robusto

---

### 2. 🏥 Hospital - Equipamentos Médicos

**Situação**: Hospital precisando planejar compras de equipamentos descartáveis

```json
{
    "sporadic_demand": {
        "2025-09-01": 5000,  // Volta às aulas (acidentes)
        "2025-11-15": 8000,  // Temporada de gripe
        "2025-12-25": 3000   // Festividades
    },
    "initial_stock": 2000,
    "leadtime_days": 21,
    "period_start_date": "2025-08-01",
    "period_end_date": "2025-12-31",
    "safety_margin_percent": 25,  // Alto por criticidade
    "safety_days": 7,             // Segurança extra
    "service_level": 0.99,        // 99% de disponibilidade
    "setup_cost": 150,
    "holding_cost_rate": 0.12,
    "enable_consolidation": false // Entregas frequentes preferidas
}
```

**Resultado Esperado**:
- Estratégia: EOQ com ajustes por criticidade
- Múltiplos lotes menores
- Alto safety stock
- Classificação A (alta prioridade)

---

### 3. 🛒 E-commerce - Produtos Sazonais

**Situação**: Loja online vendendo produtos de verão

```json
{
    "sporadic_demand": {
        "2025-11-01": 12000, // Black Friday
        "2025-12-15": 8000,  // Natal
        "2025-01-20": 6000,  // Verão
        "2025-02-14": 4000   // Carnaval
    },
    "initial_stock": 3000,
    "leadtime_days": 35,
    "period_start_date": "2025-10-01",
    "period_end_date": "2025-03-31",
    "safety_margin_percent": 12,
    "safety_days": 3,
    "setup_cost": 300,
    "holding_cost_rate": 0.25,   // Alto por obsolescência
    "min_batch_size": 2000,
    "max_batch_size": 20000,
    "enable_consolidation": true,
    "seasonality_factor": 1.3    // Fator sazonal
}
```

**Resultado Esperado**:
- Estratégia: Consolidação Híbrida
- Detecção de sazonalidade
- Lotes grandes pré-picos
- Classificação XYZ por variabilidade

---

### 4. 🏗️ Construção Civil - Materiais Especiais

**Situação**: Construtora com projetos específicos demandando materiais especiais

```json
{
    "sporadic_demand": {
        "2025-06-30": 800,   // Projeto Shopping
        "2025-09-15": 1200,  // Projeto Residencial
        "2025-11-20": 600    // Projeto Comercial
    },
    "initial_stock": 150,
    "leadtime_days": 60,     // Importação
    "period_start_date": "2025-05-01",
    "period_end_date": "2025-12-31",
    "safety_margin_percent": 10,
    "safety_days": 10,       // Margem para atrasos
    "setup_cost": 1200,      // Importação cara
    "holding_cost_rate": 0.08, // Baixo (material durável)
    "min_batch_size": 500,
    "max_batch_size": 5000,
    "enable_consolidation": true
}
```

**Resultado Esperado**:
- Estratégia: Lead Time Longo
- 1-2 lotes grandes
- Máxima consolidação
- Análise de custo-benefício detalhada

---

### 5. 🍔 Food Service - Ingredientes Especiais

**Situação**: Rede de restaurantes com eventos especiais

```json
{
    "sporadic_demand": {
        "2025-07-04": 500,   // 4 de Julho
        "2025-10-31": 800,   // Halloween
        "2025-12-31": 1200   // Réveillon
    },
    "initial_stock": 100,
    "leadtime_days": 14,
    "period_start_date": "2025-06-01",
    "period_end_date": "2025-12-31",
    "safety_margin_percent": 5,
    "safety_days": 2,
    "setup_cost": 80,
    "holding_cost_rate": 0.35,   // Alto (perecível)
    "min_batch_size": 200,
    "max_batch_size": 2000,
    "enable_consolidation": false, // Frescor prioritário
    "perishable": true
}
```

**Resultado Esperado**:
- Estratégia: EOQ com ajustes para perecibilidade
- Lotes menores e frequentes
- Baixo safety stock (perecível)
- Just-in-time approach

---

## 🔧 Comparação de Estratégias

### Análise por Lead Time

| Lead Time | Estratégia Recomendada | Características |
|-----------|------------------------|-----------------|
| 1-14 dias | EOQ | Lotes otimizados, reposição frequente |
| 15-45 dias | Buffer Dinâmico | Flexibilidade, estoques adaptativos |
| 46+ dias | Lead Time Longo | Poucos lotes grandes, planejamento estratégico |

### Análise por Variabilidade

| Variabilidade | Abordagem | Safety Stock |
|--------------|-----------|--------------|
| Baixa (CV < 0.2) | Planejamento preciso | Mínimo necessário |
| Média (CV 0.2-0.5) | Buffer moderado | 15-25% extra |
| Alta (CV > 0.5) | Buffer robusto | 30-50% extra |

---

## 🎯 Casos de Otimização

### Caso 1: Redução de Custos de Setup

**Problema**: Muitos lotes pequenos com alto custo de setup

**Antes**:
```json
{
    "total_batches": 5,
    "average_batch_size": 1000,
    "total_setup_cost": 1250,
    "total_holding_cost": 2500
}
```

**Otimização**:
```json
{
    "enable_consolidation": true,
    "setup_cost": 500,        // Aumentar para favorecer consolidação
    "min_batch_size": 2000,   // Lotes maiores
    "consolidation_window_days": 21
}
```

**Depois**:
```json
{
    "total_batches": 2,
    "average_batch_size": 2500,
    "total_setup_cost": 1000,    // ✅ Reduzido
    "total_holding_cost": 3200   // Aumento menor que economia
}
```

### Caso 2: Melhoria no Nível de Serviço

**Problema**: Stockouts frequentes (85% de atendimento)

**Antes**:
```json
{
    "demand_fulfillment_rate": 85.0,
    "stockouts_count": 3,
    "safety_margin_percent": 5
}
```

**Otimização**:
```json
{
    "safety_margin_percent": 15,  // Triplicar margem
    "safety_days": 5,             // Mais dias de buffer
    "service_level": 0.98,        // Target alto
    "initial_stock": 2000         // Aumentar estoque inicial
}
```

**Depois**:
```json
{
    "demand_fulfillment_rate": 100.0, // ✅ Perfeito
    "stockouts_count": 0,              // ✅ Zero
    "safety_achieved": true
}
```

---

## 📊 Análise de Resultados

### Interpretando Analytics

1. **Resumo Executivo** (`summary`):
   - `demand_fulfillment_rate`: Meta ≥ 95%
   - `production_coverage_rate`: Ideal 120-150%
   - `stockout_occurred`: Sempre false

2. **Eficiência de Produção** (`production_efficiency`):
   - `batch_efficiency`: > 100% é bom
   - `lead_time_compliance`: Sempre 100%
   - `production_line_utilization`: 0.8-1.5 é ideal

3. **Métricas de Demanda Esporádica**:
   - `demand_predictability`: > 0.7 é bom
   - `peak_demand_ratio`: < 3.0 é manejável
   - `interval_coefficient_variation`: < 0.5 é estável

### KPIs Principais

| Métrica | Excelente | Bom | Aceitável | Problemático |
|---------|-----------|-----|-----------|--------------|
| Taxa de Atendimento | 100% | 95-99% | 90-94% | < 90% |
| Cobertura de Produção | 120-150% | 100-120% | 150-200% | > 200% |
| Eficiência de Lote | > 150% | 100-150% | 80-100% | < 80% |
| Compliance Lead Time | 100% | 100% | 90-99% | < 90% |

---

## 🚀 Dicas de Performance

### 1. Otimização de Parâmetros

```python
# Para lead times longos
optimal_params = {
    "safety_margin_percent": leadtime_days * 0.2,  # Escalação
    "consolidation_window_days": leadtime_days * 0.3,
    "min_batch_size": max_demand * 0.5
}

# Para alta variabilidade
if demand_cv > 0.5:
    optimal_params["safety_margin_percent"] *= 1.5
    optimal_params["safety_days"] += 3
```

### 2. Monitoramento Contínuo

```python
def monitor_performance(results):
    alerts = []
    
    if results['analytics']['summary']['demand_fulfillment_rate'] < 90:
        alerts.append("⚠️ Taxa de atendimento baixa")
    
    if results['analytics']['summary']['production_coverage_rate'] > 200:
        alerts.append("⚠️ Superprodução detectada")
    
    return alerts
```

### 3. Ajustes Dinâmicos

```python
def dynamic_adjustment(historical_data, current_params):
    # Baseado no histórico, ajustar parâmetros
    avg_fulfillment = np.mean([r['fulfillment_rate'] for r in historical_data])
    
    if avg_fulfillment < 95:
        current_params['safety_margin_percent'] *= 1.2
    elif avg_fulfillment > 99:
        current_params['safety_margin_percent'] *= 0.9
    
    return current_params
```

---

*Guia atualizado em: 30 de Junho de 2025* 