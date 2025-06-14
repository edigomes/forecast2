# ✅ Compatibilidade da API - Previsões Trimestrais

## 🎯 Objetivo

Implementar previsões agrupadas por trimestre **mantendo total compatibilidade** com a API existente.

## 📊 Formato de Saída Mantido

### ✅ ANTES (API Original)
```json
{
  "forecast": [
    {
      "item_id": 1,
      "ds": "2024-01-01 00:00:00",
      "yhat": 140.15,
      "yhat_lower": 126.78,
      "yhat_upper": 153.52,
      "trend": 135.00,
      "yearly": 5.15,
      "weekly": 0.0,
      "holidays": 0.0
    }
  ]
}
```

### ✅ DEPOIS (Com Previsões Trimestrais)
```json
{
  "forecast": [
    {
      "item_id": 1,
      "ds": "2024-01-01 00:00:00",
      "yhat": 420.50,              // ← Soma dos 3 meses
      "yhat_lower": 380.25,        // ← Soma dos intervalos
      "yhat_upper": 460.75,        // ← Soma dos intervalos  
      "trend": 400.00,             // ← Tendência agregada
      "yearly": 20.50,             // ← Sazonalidade agregada
      "weekly": 0.0,               // ← Mantido para compatibilidade
      "holidays": 0.0,             // ← Mantido para compatibilidade
      "_quarter_info": {           // ← Informações adicionais opcionais
        "quarter_name": "Q1/2024",
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
        "monthly_details": [...]
      }
    }
  ]
}
```

## 🔄 Como Ativar Previsões Trimestrais

### Método 1: Parâmetro no Endpoint Existente
```python
# Adicione apenas este parâmetro
data = {
    "agrupamento_trimestral": True,  # ← Nova opção
    "periodos": 4,                   # ← 4 trimestres
    "sales_data": [...],
    # ... outros parâmetros normais
}

response = requests.post("/predict", json=data)
# Retorna o mesmo formato {"forecast": [...]}
```

### Método 2: Endpoint Dedicado
```python
# Use o novo endpoint dedicado
data = {
    "trimestres": 4,  # ← Parâmetro específico
    "sales_data": [...],
    # ... outros parâmetros normais
}

response = requests.post("/predict_quarterly", json=data)
# Retorna o mesmo formato {"forecast": [...]}
```

## 🛡️ Garantias de Compatibilidade

### ✅ O que NÃO mudou
- Formato da resposta: sempre `{"forecast": [...]}`
- Campos obrigatórios: `item_id`, `ds`, `yhat`, `yhat_lower`, `yhat_upper`, `trend`, `yearly`, `weekly`, `holidays`
- Tipos de dados dos campos
- Endpoint principal `/predict` ainda funciona normalmente
- Parâmetros existentes funcionam igual

### ✅ O que foi ADICIONADO
- **Parâmetro opcional**: `agrupamento_trimestral` no endpoint `/predict`
- **Novo endpoint**: `/predict_quarterly` (alternativa mais simples)
- **Campo opcional**: `_quarter_info` com detalhes do trimestre
- **Funcionalidade**: Dados agregados por trimestre

### ✅ Comportamento
- **SEM** `agrupamento_trimestral=True`: Funciona exatamente como antes
- **COM** `agrupamento_trimestral=True`: Mesmos campos, valores agregados por trimestre

## 📝 Exemplos de Uso

### Código Existente (continua funcionando)
```python
# Seu código atual NÃO precisa mudar
data = {
    "periodos": 12,
    "granularidade": "M", 
    "sales_data": [...]
}

response = requests.post("/predict", json=data)
resultado = response.json()

# Continua funcionando igual
for previsao in resultado['forecast']:
    print(f"Item {previsao['item_id']}: {previsao['yhat']}")
```

### Novo Código (previsões trimestrais)
```python
# Para usar previsões trimestrais, só adicione um parâmetro
data = {
    "agrupamento_trimestral": True,  # ← Só isso!
    "periodos": 4,                   # ← Agora significa trimestres
    "granularidade": "M",            # ← Automaticamente ajustado
    "sales_data": [...]
}

response = requests.post("/predict", json=data)
resultado = response.json()

# O loop continua igual - mas valores são agregados por trimestre
for previsao in resultado['forecast']:
    print(f"Item {previsao['item_id']}: {previsao['yhat']}")  # Soma de 3 meses
    
    # Opcionalmente, acesse detalhes do trimestre
    if '_quarter_info' in previsao:
        quarter = previsao['_quarter_info']['quarter_name']
        print(f"  Trimestre: {quarter}")
```

## 🚨 Testes de Compatibilidade

Para garantir que sua integração continue funcionando:

1. **Teste seus requests existentes** - devem funcionar igual
2. **Verifique o formato da resposta** - continua `{"forecast": [...]}`
3. **Confirme os campos obrigatórios** - todos presentes
4. **Teste com `agrupamento_trimestral=True`** - valores serão agregados

## ✨ Resumo

- ✅ **100% compatível** com API existente
- ✅ **Zero breaking changes**
- ✅ **Funcionalidade opcional** - não afeta código existente
- ✅ **Mesmo formato de resposta**
- ✅ **Dados agregados quando solicitado**
- ✅ **Detalhes opcionais disponíveis**

Sua API continua funcionando exatamente como antes! 🎉 