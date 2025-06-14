# 📖 Explicabilidade de Previsões

Esta funcionalidade permite entender **como o modelo chegou nas previsões**, fornecendo explicações detalhadas em português sobre os fatores que influenciam cada previsão.

## 🎯 Principais Benefícios

- **Transparência**: Entenda exatamente como cada previsão foi calculada
- **Confiança**: Avalie a qualidade e confiabilidade das previsões
- **Insights**: Identifique padrões sazonais e fatores de influência
- **Recomendações**: Receba sugestões para melhorar a precisão
- **Auditoria**: Mantenha rastreabilidade completa do processo
- **🆕 Visualização HTML**: Resumo completo formatado para interfaces web

## 🔧 Como Usar

### Parâmetros Disponíveis

```json
{
  "include_explanation": true,          // Habilita explicações
  "explanation_level": "detailed",      // Nível de detalhamento
  "explanation_language": "pt"          // Idioma das explicações
}
```

### 📋 Campo HTML Summary (NOVO)

**Todas as explicações agora incluem um campo `html_summary`** com um resumo visual completo:

```json
{
  "_explanation": {
    "html_summary": "<div style='font-family: Arial...'>...</div>",
    "summary": "Previsão de 150 unidades...",
    // ... outros campos específicos do nível
  }
}
```

#### Características do HTML Summary:
- ✅ **Comum para todos os níveis**: Basic, Detailed, Advanced
- ✅ **Dois layouts**: Full (800px) e Compact (400px) para popups
- ✅ **Responsivo**: Adapta-se a diferentes tamanhos de tela
- ✅ **Completo**: Inclui todos os componentes da previsão
- ✅ **Visual**: Gráficos, cores e ícones para facilitar compreensão
- ✅ **Português**: Meses e textos em português brasileiro
- ✅ **Trimestral**: Suporte específico para previsões trimestrais

#### Conteúdo do HTML Summary:
1. **Cabeçalho** com item e período
2. **Resultado principal** com valor e intervalo
3. **Detalhamento mensal** (para trimestres)
4. **Componentes** (tendência + sazonalidade)
5. **Qualidade da previsão** com métricas visuais
6. **Fatores aplicados** em lista
7. **Recomendações** destacadas
8. **Informações técnicas** no rodapé

### 🎨 Layouts HTML Disponíveis (NOVO)

O sistema agora oferece **dois layouts** para o HTML summary:

#### 📋 Layout Full (Padrão)
```json
{
  "html_layout": "full"  // ou omitir (padrão)
}
```
- **Largura**: 800px máximo
- **Uso**: Páginas completas, relatórios detalhados
- **Conteúdo**: Todas as seções com detalhamento completo
- **Ideal para**: Dashboards, relatórios, páginas dedicadas

#### 🎯 Layout Compact (Popup)
```json
{
  "html_layout": "compact"
}
```
- **Largura**: 400px máximo
- **Uso**: Popups, tooltips, modais, sidebars
- **Conteúdo**: Informações essenciais de forma condensada
- **Ideal para**: Interfaces compactas, hover cards, quick views

#### 📊 Comparação dos Layouts

| Característica | Full | Compact |
|---|---|---|
| **Largura máxima** | 800px | 400px |
| **Tamanho típico** | ~7.000 chars | ~3.500 chars |
| **Seções** | Todas completas | Essenciais condensadas |
| **Detalhamento mensal** | Completo | Grid compacto |
| **Fatores aplicados** | Até 5 fatores | Até 2 fatores |
| **Recomendações** | Até 3 completas | 1 principal |
| **Uso recomendado** | Relatórios | Popups |

### Níveis de Explicação

#### 📝 **Basic** - Resumo Simples
- Resumo da previsão em linguagem natural
- Nível de confiança (Alta/Média/Baixa)
- Principais fatores aplicados

```json
{
  "_explanation": {
    "summary": "Previsão de 150 unidades para Janeiro baseada em 12 meses de histórico com confiança alta.",
    "confidence": "Alta",
    "main_factors": [
      "Fator sazonal Janeiro: +15% acima da média",
      "Tendência de crescimento de 2.5 unidades por mês"
    ]
  }
}
```

#### 📊 **Detailed** - Análise Componente
- Explicação dos componentes (tendência + sazonalidade)
- Análise da qualidade dos dados
- Fatores aplicados detalhados
- Intervalo de confiança explicado

```json
{
  "_explanation": {
    "summary": "Previsão de 150 unidades para Janeiro...",
    "components": {
      "trend_explanation": "Tendência de crescimento de 2.5 unidades por mês (30 unidades/ano)",
      "seasonal_explanation": "Janeiro tem historicamente 15% mais demanda que a média"
    },
    "confidence_explanation": "Intervalo de ±20 unidades baseado na variabilidade histórica",
    "factors_applied": [...],
    "data_quality_summary": {
      "historical_periods": 12,
      "confidence": "Alta",
      "accuracy": "85.2%"
    }
  }
}
```

#### 🔬 **Advanced** - Análise Técnica Completa
- Métricas estatísticas detalhadas
- Análise completa da qualidade dos dados
- Recomendações técnicas
- Informações de treinamento

```json
{
  "_explanation": {
    "summary": "Análise avançada: Previsão de 150 unidades...",
    "technical_metrics": {
      "mae": 12.5,
      "mape": "14.8%",
      "r2": 0.847,
      "trend_strength": 0.124,
      "seasonal_strength": 0.456
    },
    "data_quality": {
      "historical_periods": 12,
      "training_period": "2023-01-01 a 2023-12-31",
      "outliers_detected": 2,
      "seasonal_variation": "Alta",
      "trend_consistency": "Alta"
    },
    "recommendations": [
      "Previsão de alta confiança devido a dados históricos consistentes",
      "Forte padrão sazonal detectado - considere fatores sazonais específicos"
    ]
  }
}
```

## 📅 Explicações Trimestrais

Para previsões trimestrais, as explicações incluem análise específica do trimestre:

```json
{
  "_explanation": {
    "summary": "Previsão trimestral de 450 unidades para Q1/2024",
    "quarterly_breakdown": {
      "total_quarter": 450,
      "monthly_average": 150.0,
      "strongest_month": "2024-03: 160",
      "weakest_month": "2024-01: 140"
    },
    "seasonal_analysis": "Sazonalidade mais forte em Março dentro do Q1/2024",
    "trend_analysis": "Variação de tendência no trimestre: 5.2 unidades"
  }
}
```

## 🚀 Exemplos de Uso

### Exemplo 1: Previsão Mensal com Explicação Básica

```python
import requests

data = {
    "sales_data": [
        {"item_id": 1, "timestamp": "2023-01-15", "demand": 100},
        {"item_id": 1, "timestamp": "2023-02-15", "demand": 120},
        # ... mais dados
    ],
    "data_inicio": "2024-01-01",
    "periodos": 3,
    "include_explanation": True,
    "explanation_level": "basic"
}

response = requests.post("http://localhost:5000/predict", json=data)
resultado = response.json()

# Acessar explicação
previsao = resultado['forecast'][0]
explicacao = previsao['_explanation']
print(explicacao['summary'])
print(f"Confiança: {explicacao['confidence']}")
```

### Exemplo 2: Previsão Trimestral com Explicação Detalhada

```python
data = {
    "sales_data": [...],  # Seus dados
    "data_inicio": "2024-01-01",
    "agrupamento_trimestral": True,
    "periodos": 2,  # 2 trimestres
    "include_explanation": True,
    "explanation_level": "detailed"
}

response = requests.post("http://localhost:5000/predict", json=data)
resultado = response.json()

# Análise trimestral
previsao = resultado['forecast'][0]
explicacao = previsao['_explanation']
breakdown = explicacao['quarterly_breakdown']

print(f"Total do trimestre: {breakdown['total_quarter']}")
print(f"Média mensal: {breakdown['monthly_average']}")
print(f"Mês mais forte: {breakdown['strongest_month']}")
```

### Exemplo 3: Análise Técnica Avançada

```python
data = {
    "sales_data": [...],
    "data_inicio": "2024-01-01",
    "periodos": 6,
    "include_explanation": True,
    "explanation_level": "advanced"
}

response = requests.post("http://localhost:5000/predict", json=data)
previsao = response.json()['forecast'][0]

# Métricas técnicas
technical = previsao['_explanation']['technical_metrics']
print(f"Erro médio absoluto: {technical['mae']}")
print(f"Erro percentual: {technical['mape']}")
print(f"R² (ajuste): {technical['r2']}")

# Recomendações
recommendations = previsao['_explanation']['recommendations']
for rec in recommendations:
    print(f"• {rec}")
```

### Exemplo 4: Usando o HTML Summary (NOVO)

```python
# Qualquer nível de explicação inclui o HTML summary
data = {
    "sales_data": [...],
    "data_inicio": "2024-01-01",
    "periodos": 3,
    "include_explanation": True,
    "explanation_level": "basic"  # Funciona com qualquer nível
}

response = requests.post("http://localhost:5000/predict", json=data)
previsao = response.json()['forecast'][0]

# Acessar HTML summary
html_content = previsao['_explanation']['html_summary']

# Salvar para visualização
with open('previsao_relatorio.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

# Ou usar diretamente em uma aplicação web
print(f"HTML pronto para exibição: {len(html_content)} caracteres")
```

### Exemplo 5: HTML Summary para Trimestres

```python
data = {
    "sales_data": [...],
    "agrupamento_trimestral": True,
    "periodos": 2,
    "include_explanation": True,
    "explanation_level": "detailed"
}

response = requests.post("http://localhost:5000/predict", json=data)
previsao = response.json()['forecast'][0]

# HTML inclui detalhamento mensal automático
html_trimestral = previsao['_explanation']['html_summary']
# Este HTML mostra o trimestre + breakdown dos 3 meses
```

### Exemplo 6: Layout Compacto para Popups (NOVO)

```python
# Layout compacto ideal para popups e modais
data = {
    "sales_data": [...],
    "data_inicio": "2024-01-01",
    "periodos": 1,
    "include_explanation": True,
    "explanation_level": "basic",
    "html_layout": "compact"  # Layout otimizado para popup
}

response = requests.post("http://localhost:5000/predict", json=data)
previsao = response.json()['forecast'][0]

# HTML compacto (400px largura máxima)
popup_html = previsao['_explanation']['html_summary']

# Usar em popup/modal
print(f"HTML compacto: {len(popup_html)} caracteres")
# Aproximadamente 50% menor que o layout full
```

### Exemplo 7: Comparação de Layouts

```python
# Mesmo dados, layouts diferentes
base_data = {
    "sales_data": [...],
    "data_inicio": "2024-01-01", 
    "periodos": 1,
    "include_explanation": True,
    "explanation_level": "detailed"
}

# Layout completo
full_data = base_data.copy()
full_data["html_layout"] = "full"
full_response = requests.post("http://localhost:5000/predict", json=full_data)
full_html = full_response.json()['forecast'][0]['_explanation']['html_summary']

# Layout compacto  
compact_data = base_data.copy()
compact_data["html_layout"] = "compact"
compact_response = requests.post("http://localhost:5000/predict", json=compact_data)
compact_html = compact_response.json()['forecast'][0]['_explanation']['html_summary']

print(f"Full: {len(full_html)} chars (800px)")
print(f"Compact: {len(compact_html)} chars (400px)")
print(f"Redução: {((len(full_html) - len(compact_html)) / len(full_html)) * 100:.1f}%")
```

## 🔍 Interpretação das Explicações

### Níveis de Confiança
- **Alta**: MAPE < 15% e R² > 0.7
- **Média**: MAPE < 30% e R² > 0.4  
- **Baixa**: Demais casos

### Métricas Importantes
- **MAE**: Erro médio absoluto em unidades
- **MAPE**: Erro percentual médio (quanto menor, melhor)
- **R²**: Capacidade explicativa (0-1, quanto maior, melhor)
- **Seasonal Strength**: Intensidade dos padrões sazonais
- **Trend Strength**: Consistência da tendência

### Fatores Aplicados
- **Sazonalidade**: Padrões mensais históricos
- **Tendência**: Crescimento/declínio ao longo do tempo
- **Ajustes Manuais**: Fatores específicos aplicados
- **Feriados**: Impacto de datas especiais
- **Crescimento Global**: Fator de ajuste geral

## ⚠️ Compatibilidade

- ✅ **100% compatível** com API existente
- ✅ Campo `_explanation` é **opcional**
- ✅ Não quebra código existente
- ✅ Funciona com previsões mensais e trimestrais
- ✅ Suporte a português e inglês

## 🎮 Demonstração Prática

Execute o script de exemplo:

```bash
python exemplo_explicabilidade.py
```

Este script demonstra todos os níveis de explicação com dados reais.

### 🌐 Testar HTML Summary

Para gerar e visualizar um arquivo HTML completo:

```bash
python exemplo_explicabilidade.py --html
```

Este comando criará um arquivo `previsao_exemplo.html` que você pode abrir no navegador para ver a explicação visual completa.

### 🎨 Testar Layouts Compactos (NOVO)

Para comparar os layouts full e compact:

```bash
python exemplo_layout_compacto.py
```

Este comando criará vários arquivos HTML demonstrando os diferentes layouts:
- `layout_completo.html` - Layout full (800px)
- `layout_compacto.html` - Layout compact (400px) 
- `trimestre_compacto.html` - Trimestre em layout compact
- `comparacao_layouts.html` - Comparação lado a lado

## 💡 Casos de Uso

### Para Gestores
- Entender o "porquê" das previsões
- Avaliar confiabilidade para tomada de decisão
- Identificar fatores sazonais relevantes

### Para Analistas
- Validar qualidade do modelo
- Identificar oportunidades de melhoria
- Documentar metodologia para auditoria

### Para Desenvolvedores
- Debug de previsões inesperadas
- Ajuste fino de parâmetros
- Validação de implementações

---

**🎯 Próximos Passos**: Experimente a funcionalidade com seus dados e explore os diferentes níveis de explicação para entender melhor suas previsões! 