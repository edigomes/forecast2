# 🔧 Guia de Solução de Problemas - Sistema MRP Avançado

## 🎯 Problemas Comuns e Soluções

### 1. 🚨 Duplicação de Lotes (RESOLVIDO)

**⚠️ Problema**: Batches com datas de pedido e chegada idênticas

```json
// PROBLEMA - Antes da correção
{
    "batches": [
        {
            "order_date": "2025-05-01",
            "arrival_date": "2025-07-10",
            "quantity": 9506.087
        },
        {
            "order_date": "2025-05-01",  // ❌ DUPLICADO
            "arrival_date": "2025-07-10", // ❌ DUPLICADO
            "quantity": 4800
        }
    ]
}
```

**✅ Solução Implementada**:
- Reescrita completa da estratégia de lead time longo
- Eliminação da lógica de lotes de emergência duplicados
- Sequenciamento inteligente de lotes

```json
// SOLUÇÃO - Após correção
{
    "batches": [
        {
            "order_date": "2025-05-01",
            "arrival_date": "2025-07-10",
            "quantity": 10000
        },
        {
            "order_date": "2025-06-14",  // ✅ ÚNICO
            "arrival_date": "2025-08-23", // ✅ ÚNICO
            "quantity": 10000
        }
    ]
}
```

---

### 2. ⏰ Stockouts em Lead Times Longos

**⚠️ Problema**: Lotes chegam depois das demandas críticas

**🔍 Diagnóstico**:
```bash
# Verificar se lead time é maior que janela disponível
lead_time_days = 70
available_days = (primeira_demanda - start_cutoff).days
if lead_time_days > available_days:
    print("⚠️ Lead time crítico detectado")
```

**✅ Soluções**:

1. **Compensação por Atraso Automática**:
```python
if first_batch_arrival >= first_demand_date:
    days_late = (first_batch_arrival - first_demand_date).days
    compensation = first_demand_qty * (1 + days_late * 0.1)
```

2. **Ajuste de Parâmetros**:
```json
{
    "safety_days": 5,           // Aumentar dias de segurança
    "safety_margin_percent": 15, // Aumentar margem
    "start_cutoff_date": "2025-04-01" // Antecipar cutoff
}
```

3. **Lead Time de Emergência**:
```json
{
    "leadtime_days": 45,  // Reduzir se possível
    "setup_cost": 500,    // Aceitar maior custo para urgência
    "express_delivery": true // Parâmetro customizado
}
```

---

### 3. 💰 Custos Excessivos de Manutenção

**⚠️ Problema**: `holding_cost_impact` muito alto nos lotes

**🔍 Identificação**:
```json
{
    "analytics": {
        "holding_cost_impact": 37503.47,  // ❌ Muito alto
        "setup_cost_allocation": 250      // OK
    }
}
```

**✅ Soluções**:

1. **Ajustar Taxa de Manutenção**:
```json
{
    "holding_cost_rate": 0.10,  // Reduzir de 0.20 para 0.10
    "enable_consolidation": true // Ativar consolidação
}
```

2. **Otimizar Tamanho dos Lotes**:
```json
{
    "min_batch_size": 1000,     // Aumentar mínimo
    "max_batch_size": 8000,     // Reduzir máximo
    "setup_cost": 500           // Aumentar para favorecer lotes maiores
}
```

---

### 4. 📉 Taxa de Atendimento Baixa

**⚠️ Problema**: `demand_fulfillment_rate` abaixo de 90%

**🔍 Análise**:
```json
{
    "demand_fulfillment_rate": 66.67,
    "demands_unmet_count": 1,
    "unmet_demand_details": [
        {
            "date": "2025-07-07",
            "demand": 4000,
            "shortage": 4000
        }
    ]
}
```

**✅ Soluções**:

1. **Estratégia Preventiva**:
```json
{
    "strategy": "preventive_stocking",
    "initial_stock": 3000,      // Aumentar estoque inicial
    "safety_margin_percent": 20 // Aumentar margem
}
```

2. **Multiple Suppliers**:
```json
{
    "suppliers": [
        {"leadtime_days": 30, "cost_multiplier": 1.2},
        {"leadtime_days": 70, "cost_multiplier": 1.0}
    ]
}
```

---

### 5. 🔄 Problemas de Consolidação

**⚠️ Problema**: Consolidação não funciona adequadamente

**🔍 Diagnóstico**:
```json
{
    "consolidation_savings": 0,
    "holding_cost_increase": 5000,
    "net_benefit": -5000  // ❌ Negativo
}
```

**✅ Soluções**:

1. **Ajustar Parâmetros de Consolidação**:
```json
{
    "enable_consolidation": true,
    "consolidation_window_days": 14,    // Reduzir janela
    "min_consolidation_benefit": 100,   // Reduzir benefício mínimo
    "force_consolidation_within_leadtime": true
}
```

2. **Configuração Avançada**:
```json
{
    "operational_efficiency_weight": 1.5,  // Aumentar peso operacional
    "overlap_prevention_priority": true,   // Priorizar prevenção
    "setup_cost": 400                      // Aumentar para favorecer consolidação
}
```

---

### 6. 📊 Analytics Incompletos

**⚠️ Problema**: Campos de analytics ausentes ou zerados

**🔍 Verificação**:
```python
def verify_analytics(result):
    required_fields = [
        'summary', 'stock_evolution', 'critical_points',
        'production_efficiency', 'demand_analysis'
    ]
    for field in required_fields:
        if field not in result['analytics']:
            print(f"❌ Campo ausente: {field}")
```

**✅ Soluções**:

1. **Dados Mínimos Necessários**:
```json
{
    "sporadic_demand": {
        "2025-07-01": 1000  // Mínimo 1 demanda
    },
    "initial_stock": 100,    // > 0
    "leadtime_days": 1       // > 0
}
```

2. **Verificar Compatibilidade**:
```bash
# Verificar se advanced_sporadic_mrp.py está disponível
python -c "from advanced_sporadic_mrp import AdvancedSporadicMRPPlanner; print('✅ OK')"
```

---

### 7. 🌐 Problemas de API

**⚠️ Problema**: Erro 500 - Internal Server Error

**🔍 Log de Debug**:
```bash
# Verificar logs do servidor
tail -f /var/log/mrp_server.log

# Testar conectividade
curl -X POST http://localhost:5000/mrp_advanced \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

**✅ Soluções**:

1. **Validação de Entrada**:
```python
def validate_input(data):
    required = ['sporadic_demand', 'initial_stock', 'leadtime_days']
    for field in required:
        if field not in data:
            raise ValueError(f"Campo obrigatório: {field}")
    
    if not isinstance(data['sporadic_demand'], dict):
        raise ValueError("sporadic_demand deve ser um objeto")
```

2. **Tratamento de Erros**:
```python
try:
    result = mrp_planner.calculate(data)
except Exception as e:
    return {
        "error": True,
        "message": str(e),
        "fallback_strategy": "basic_mrp"
    }
```

---

### 8. 🎯 Classificação ABC/XYZ Incorreta

**⚠️ Problema**: Classificações não fazem sentido para o negócio

**🔍 Verificação**:
```json
{
    "analytics": {
        "abc_classification": "C",  // ❌ Deveria ser A
        "xyz_classification": "Z"   // ❌ Deveria ser X
    }
}
```

**✅ Soluções**:

1. **Configurar Valores Unitários**:
```json
{
    "unit_cost": 150.0,          // Especificar custo real
    "value_threshold_a": 0.8,    // 80% para classe A
    "variability_threshold_x": 0.15  // 15% para classe X
}
```

2. **Classificação Manual**:
```json
{
    "force_classification": {
        "abc": "A",
        "xyz": "X"
    }
}
```

---

### 9. 📈 Performance Lenta

**⚠️ Problema**: Resposta do endpoint muito lenta (>10 segundos)

**🔍 Profiling**:
```python
import time
start = time.time()
result = requests.post('/mrp_advanced', json=data)
print(f"Tempo: {time.time() - start:.2f}s")
```

**✅ Otimizações**:

1. **Limitar Período**:
```json
{
    "period_start_date": "2025-06-01",
    "period_end_date": "2025-12-31",  // Máximo 12 meses
    "max_demand_points": 50           // Limitar pontos de demanda
}
```

2. **Configuração Simples**:
```json
{
    "enable_consolidation": false,    // Desabilitar se desnecessário
    "enable_seasonality_detection": false,
    "enable_abc_xyz_classification": false
}
```

---

### 10. 🔐 Problemas de CORS

**⚠️ Problema**: Erro de CORS em aplicações web

```javascript
// ❌ Erro típico
fetch('http://localhost:5000/mrp_advanced', {
    method: 'POST',
    body: JSON.stringify(data)
})
// CORS error: No 'Access-Control-Allow-Origin' header
```

**✅ Solução**:

1. **Configurar CORS no Servidor**:
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])
```

2. **Headers Corretos**:
```javascript
fetch('http://localhost:5000/mrp_advanced', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    },
    body: JSON.stringify(data)
})
```

---

## 🛠️ Ferramentas de Debug

### 1. Script de Teste Completo

```python
#!/usr/bin/env python3
"""
Script de teste e diagnóstico para MRP Avançado
"""

import requests
import json
from datetime import datetime, timedelta

def test_mrp_advanced():
    # Dados de teste básicos
    test_data = {
        "sporadic_demand": {
            "2025-07-01": 1000,
            "2025-08-01": 1500,
            "2025-09-01": 2000
        },
        "initial_stock": 500,
        "leadtime_days": 30,
        "period_start_date": "2025-06-01",
        "period_end_date": "2025-10-31",
        "start_cutoff_date": "2025-06-01",
        "end_cutoff_date": "2025-10-31"
    }
    
    try:
        response = requests.post(
            'http://localhost:5000/mrp_advanced',
            json=test_data,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Teste bem-sucedido!")
            print(f"Lotes criados: {len(result['batches'])}")
            print(f"Taxa de atendimento: {result['analytics']['summary']['demand_fulfillment_rate']}%")
        else:
            print(f"❌ Erro: {response.text}")
            
    except Exception as e:
        print(f"❌ Exceção: {e}")

if __name__ == "__main__":
    test_mrp_advanced()
```

### 2. Validador de Entrada

```python
def validate_mrp_input(data):
    """Valida entrada para MRP Avançado"""
    
    errors = []
    
    # Campos obrigatórios
    required_fields = [
        'sporadic_demand', 'initial_stock', 'leadtime_days',
        'period_start_date', 'period_end_date'
    ]
    
    for field in required_fields:
        if field not in data:
            errors.append(f"Campo obrigatório ausente: {field}")
    
    # Validações específicas
    if 'sporadic_demand' in data:
        if not isinstance(data['sporadic_demand'], dict):
            errors.append("sporadic_demand deve ser um objeto")
        elif len(data['sporadic_demand']) == 0:
            errors.append("sporadic_demand não pode estar vazio")
    
    if 'leadtime_days' in data:
        if not isinstance(data['leadtime_days'], (int, float)):
            errors.append("leadtime_days deve ser numérico")
        elif data['leadtime_days'] <= 0:
            errors.append("leadtime_days deve ser > 0")
    
    return errors

# Uso
errors = validate_mrp_input(your_data)
if errors:
    for error in errors:
        print(f"❌ {error}")
```

---

## 📞 Suporte Técnico

### Quando Contatar o Suporte

1. **🚨 Crítico**: Sistema indisponível ou dados corrompidos
2. **⚠️ Alto**: Resultados incorretos consistentes
3. **📋 Médio**: Performance degradada ou recursos não funcionam
4. **💡 Baixo**: Dúvidas sobre configuração ou otimização

### Informações para o Suporte

Sempre inclua:
- **📊 Dados de entrada**: JSON completo usado
- **🖥️ Ambiente**: Versão do Python, SO, RAM disponível
- **⏰ Timestamp**: Quando o problema ocorreu
- **📝 Logs**: Mensagens de erro completas
- **🎯 Comportamento esperado**: O que deveria acontecer

### Template de Report

```markdown
## 🐛 Bug Report - Sistema MRP Avançado

**📅 Data/Hora**: 2025-06-30 22:15:00
**🔗 Endpoint**: /mrp_advanced
**🖥️ Ambiente**: Python 3.9, Windows 10, 16GB RAM

### Problema
Descreva o problema aqui...

### Dados de Entrada
```json
{
    // Cole o JSON completo aqui
}
```

### Comportamento Atual
O que está acontecendo...

### Comportamento Esperado
O que deveria acontecer...

### Logs de Erro
```
Cole os logs aqui...
```
```

---

*Guia atualizado em: 30 de Junho de 2025* 