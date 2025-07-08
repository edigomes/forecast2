
# 🧠 Guia Rápido: Cálculo Automático Inteligente de Batch Sizes

## ⚡ Como Usar

### 1. Cálculo Direto
```python
from mrp import MRPOptimizer

optimizer = MRPOptimizer()
sizing_result = optimizer.calculate_intelligent_batch_sizes(
    daily_demands=your_demands,
    leadtime_days=3,
    setup_cost=250.0,
    holding_cost_rate=0.15,
    service_level=0.95
)

print(f"Min: {sizing_result['min_batch_size']}")
print(f"Max: {sizing_result['max_batch_size']}")
print(f"Optimal: {sizing_result['optimal_batch_size']}")
```

### 2. Integração com MRP
```python
# Calcular batch sizes
sizing = optimizer.calculate_intelligent_batch_sizes(...)

# Usar no MRP
params = OptimizationParams(
    min_batch_size=sizing['min_batch_size'],
    max_batch_size=sizing['max_batch_size']
)

optimizer = MRPOptimizer(params)
result = optimizer.calculate_batches_with_start_end_cutoff(...)
```

## 🎯 O que o Sistema Analisa

1. **Padrão de Demanda**: stable, variable, trending, intermittent
2. **Variabilidade (CV)**: Coeficiente de variação
3. **Risco**: Lead time risk + Variability risk
4. **EOQ**: Economic Order Quantity ajustado
5. **Lead Time**: Estratégia baseada no tempo

## 📊 Outputs

- `min_batch_size`: Tamanho mínimo eficiente
- `max_batch_size`: Tamanho máximo prático
- `optimal_batch_size`: Tamanho ideal
- `confidence_level`: Confiança na recomendação
- `rationale`: Explicação da lógica

## 🔧 Personalização

Você pode ajustar os pesos das abordagens:
- EOQ Weight: 40% (padrão)
- Demand Weight: 30%
- Risk Weight: 20%
- Leadtime Weight: 10%

## ✅ Benefícios

- ✅ Sem necessidade de configuração manual
- ✅ Adaptação automática ao padrão de demanda
- ✅ Consideração de riscos e variabilidade
- ✅ Explicação clara das decisões
- ✅ Integração transparente com MRP existente
