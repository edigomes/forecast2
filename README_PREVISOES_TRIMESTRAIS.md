# 📊 Previsões Trimestrais - Guia de Uso

Esta documentação explica como usar a nova funcionalidade de **previsões agrupadas por trimestre** (3 em 3 meses) implementada no sistema de forecasting.

## 🎯 O que são Previsões Trimestrais?

As previsões trimestrais agrupam as previsões mensais em blocos de 3 meses, fornecendo:
- **Visão agregada**: Valores somados por trimestre
- **Detalhes mensais**: Breakdown mês a mês dentro de cada trimestre
- **Facilidade de planejamento**: Ideal para planejamento estratégico e orçamentário

## 🚀 Como Usar

### Método 1: Endpoint Principal com Parâmetro

```json
POST /predict
{
  "agrupamento_trimestral": true,
  "periodos": 4,
  "granularidade": "M",
  "data_inicio": "2024-01-01",
  "sales_data": [
    {"item_id": 1, "timestamp": "2023-01-15", "demand": 100},
    {"item_id": 1, "timestamp": "2023-02-15", "demand": 120},
    // ... mais dados
  ],
  "seasonality_mode": "multiplicative",
  "confidence_level": 0.95
}
```

### Método 2: Endpoint Dedicado

```json
POST /predict_quarterly
{
  "trimestres": 4,
  "data_inicio": "2024-01-01",
  "sales_data": [
    {"item_id": 1, "timestamp": "2023-01-15", "demand": 100},
    {"item_id": 1, "timestamp": "2023-02-15", "demand": 120},
    // ... mais dados
  ],
  "seasonality_mode": "multiplicative",
  "confidence_level": 0.95
}
```

## 📋 Parâmetros

### Parâmetros Obrigatórios
- **`sales_data`**: Array com dados históricos de vendas
- **`data_inicio`**: Data de início das previsões (formato: YYYY-MM-DD)
- **`trimestres`** ou **`periodos`**: Número de trimestres para prever

### Parâmetros Opcionais
- **`seasonality_mode`**: "multiplicative" ou "additive" (padrão: "multiplicative")
- **`confidence_level`**: Nível de confiança (padrão: 0.95)
- **`seasonal_smooth`**: Fator de suavização sazonal (padrão: 0.7)
- **`growth_factor`**: Fator de crescimento global (padrão: 1.0)
- **`month_adjustments`**: Ajustes específicos por mês
- **`feriados_enabled`**: Considerar feriados brasileiros (padrão: true)

## 📊 Formato de Resposta

```json
{
  "forecast": [
    {
      "item_id": 1,
      "ds": "2024-01-01 00:00:00",
      "yhat": 420.50,
      "yhat_lower": 380.25,
      "yhat_upper": 460.75,
      "trend": 400.00,
      "yearly": 20.50,
      "weekly": 0.0,
      "holidays": 0.0,
      "_quarter_info": {
        "quarter_name": "Q1/2024",
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
        "monthly_details": [
          {
            "month": "2024-01",
            "yhat": 140.15,
            "yhat_lower": 126.78,
            "yhat_upper": 153.52
          },
          {
            "month": "2024-02",
            "yhat": 138.90,
            "yhat_lower": 125.65,
            "yhat_upper": 152.15
          },
          {
            "month": "2024-03",
            "yhat": 141.45,
            "yhat_lower": 127.82,
            "yhat_upper": 155.08
          }
        ]
      }
    }
  ]
}
```

## 🔍 Campos da Resposta

### Campos Principais (Compatíveis com API Original)
- **`item_id`**: ID do item
- **`ds`**: Data de início do trimestre (formato timestamp)
- **`yhat`**: Previsão total do trimestre (soma dos 3 meses)
- **`yhat_lower`**: Limite inferior do intervalo de confiança
- **`yhat_upper`**: Limite superior do intervalo de confiança
- **`trend`**: Componente de tendência agregada
- **`yearly`**: Componente sazonal agregada
- **`weekly`**: Sempre 0.0 para trimestres (compatibilidade)
- **`holidays`**: Sempre 0.0 para trimestres (compatibilidade)

### Informações Adicionais do Trimestre
- **`_quarter_info`**: Objeto com informações específicas do trimestre
  - **`quarter_name`**: Nome do trimestre (ex: "Q1/2024")
  - **`start_date`**: Data de início do trimestre
  - **`end_date`**: Data de fim do trimestre
  - **`monthly_details`**: Array com breakdown mês a mês

### Detalhes Mensais
- **`monthly_details`**: Array com breakdown mês a mês
- **`month`**: Mês no formato YYYY-MM
- **`yhat`**: Previsão individual do mês
- **`yhat_lower`**: Limite inferior mensal
- **`yhat_upper`**: Limite superior mensal

## 🎯 Exemplos Práticos

### Exemplo 1: Previsão de 4 Trimestres

```python
import requests

dados = {
    "sales_data": [
        {"item_id": 1, "timestamp": "2023-01-15", "demand": 100},
        {"item_id": 1, "timestamp": "2023-02-15", "demand": 120},
        # ... dados históricos
    ],
    "trimestres": 4,
    "data_inicio": "2024-01-01"
}

response = requests.post("http://localhost:5000/predict_quarterly", json=dados)
resultado = response.json()

for previsao in resultado['forecast']:
    print(f"Trimestre {previsao['quarter']}: {previsao['yhat']}")
```

### Exemplo 2: Com Ajustes Sazonais

```python
dados = {
    "sales_data": [...],
    "trimestres": 4,
    "data_inicio": "2024-01-01",
    "month_adjustments": {
        12: 1.5,  # Dezembro +50% (Natal)
        1: 0.8,   # Janeiro -20% (pós-feriados)
        6: 1.2    # Junho +20% (meio do ano)
    },
    "seasonality_mode": "multiplicative"
}
```

## ⚙️ Configurações Avançadas

### Ajustes por Mês
```json
{
  "month_adjustments": {
    1: 0.9,   // Janeiro -10%
    12: 1.4   // Dezembro +40%
  }
}
```

### Feriados Brasileiros
```json
{
  "feriados_enabled": true,
  "feriados_adjustments": {
    "2024-12-25": 1.8,  // Natal +80%
    "2024-01-01": 0.5   // Ano Novo -50%
  },
  "anos_feriados": [2024, 2025]
}
```

## 🔄 Comparação: Mensal vs Trimestral

| Aspecto | Previsão Mensal | Previsão Trimestral |
|---------|----------------|-------------------|
| **Granularidade** | 1 mês | 3 meses (com detalhes mensais) |
| **Uso ideal** | Controle operacional | Planejamento estratégico |
| **Visualização** | Detalhada | Agregada + Detalhada |
| **Precisão** | Alta para curto prazo | Boa para médio prazo |

## 🧪 Testando a Funcionalidade

Execute o script de exemplo:

```bash
python exemplo_previsao_trimestral.py
```

Este script irá:
1. Testar ambos os métodos de requisição
2. Comparar resultados mensais vs trimestrais
3. Mostrar exemplos de uso completos

## ❓ Casos de Uso Comuns

### 1. Planejamento Orçamentário
```python
# Prever receita por trimestre para o próximo ano
dados = {
    "trimestres": 4,
    "data_inicio": "2024-01-01",
    "sales_data": dados_historicos_vendas,
    "confidence_level": 0.90
}
```

### 2. Análise Sazonal por Trimestre
```python
# Identificar padrões sazonais trimestrais
dados = {
    "trimestres": 8,  # 2 anos
    "seasonality_mode": "multiplicative",
    "seasonal_smooth": 0.5
}
```

### 3. Comparação Ano a Ano
```python
# Comparar mesmo trimestre em anos diferentes
for ano in [2024, 2025]:
    dados = {
        "trimestres": 4,
        "data_inicio": f"{ano}-01-01"
    }
```

## 🚨 Importantes Observações

1. **Granularidade Forçada**: Para previsões trimestrais, a granularidade é automaticamente definida como mensal ("M")
2. **Mínimo de Dados**: Recomenda-se pelo menos 6 meses de dados históricos
3. **Intervalo de Confiança**: Os intervalos são calculados individualmente para cada mês e depois agregados
4. **Compatibilidade**: Todos os parâmetros do modelo original funcionam com previsões trimestrais

## 🔧 Troubleshooting

### Erro: "Dados insuficientes"
- **Causa**: Menos de 2 pontos de dados históricos
- **Solução**: Adicione mais dados históricos

### Erro: "Data de início inválida"
- **Causa**: Formato de data incorreto
- **Solução**: Use o formato YYYY-MM-DD

### Previsões muito baixas/altas
- **Causa**: Outliers nos dados ou configuração inadequada
- **Solução**: Ajuste `outlier_threshold` ou `growth_factor`

## 📈 Próximos Passos

Para usar esta funcionalidade em produção:

1. **Teste com seus dados reais**
2. **Ajuste os parâmetros conforme necessário**
3. **Monitore a precisão das previsões**
4. **Considere automação para previsões regulares**

---

📧 Para dúvidas ou sugestões, consulte a documentação do modelo principal ou entre em contato com a equipe de desenvolvimento. 