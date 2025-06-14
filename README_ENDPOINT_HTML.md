# 🎨 Endpoint para Geração de HTML

## Visão Geral

O endpoint `/generate_html` permite gerar HTML formatado de explicações de previsões sem precisar armazenar o HTML no serviço que consome a API. Isso proporciona maior flexibilidade e separação de responsabilidades. **NOVIDADE**: Agora suporta retorno direto de HTML (`text/html`) para exibição imediata no navegador.

## 🔧 Endpoint

```
POST /generate_html
```

## 📝 Parâmetros

### Obrigatórios

```json
{
  "item_id": 1,
  "prediction": {
    "yhat": 150.5,
    "yhat_lower": 130.2,
    "yhat_upper": 170.8,
    "trend": 145.0,
    "yearly": 5.5,
    "ds": "2024-01-01"
  }
}
```

### Opcionais

```json
{
  "explanation_data": {
    "data_points": 12,
    "confidence_score": "Alta",
    "mape": 8.5,
    "r2": 0.85,
    "outlier_count": 1,
    "trend_slope": 2.5,
    "seasonal_pattern": {1: 1.1, 2: 0.9, 3: 1.0},
    "training_period": {
      "start": "2023-01-01",
      "end": "2023-12-01"
    }
  },
  "layout": "compact",
  "is_quarterly": false,
  "quarterly_info": {
    "quarter_name": "Q1/2024",
    "start_date": "2024-01-01",
    "end_date": "2024-03-01",
    "monthly_details": [...]
  }
}
```

## 📤 Resposta

```json
{
  "html": "<div style='...'>...</div>",
  "info": {
    "layout": "compact",
    "size_chars": 3616,
    "is_quarterly": false,
    "item_id": 1,
    "period": "Janeiro/2024"
  }
}
```

## 🎯 Casos de Uso

### 1. Geração de Popup Compacto

```python
import requests

dados = {
    "item_id": 1,
    "prediction": {
        "yhat": 150.5,
        "yhat_lower": 130.2,
        "yhat_upper": 170.8,
        "trend": 145.0,
        "yearly": 5.5,
        "ds": "2024-01-01"
    },
    "explanation_data": {
        "confidence_score": "Alta",
        "mape": 8.5,
        "data_points": 12
    },
    "layout": "compact"
}

response = requests.post("http://localhost:5000/generate_html", json=dados)
html_popup = response.json()['html']

# Usar em popup/modal
```

### 2. Relatório Completo

```python
dados = {
    "item_id": 2,
    "prediction": {...},
    "explanation_data": {...},
    "layout": "full"  # Layout completo
}

response = requests.post("http://localhost:5000/generate_html", json=dados)
html_relatorio = response.json()['html']

# Usar em página de relatório
```

### 3. Previsão Trimestral

```python
dados = {
    "item_id": 3,
    "prediction": {...},
    "explanation_data": {...},
    "layout": "compact",
    "is_quarterly": True,
    "quarterly_info": {
        "quarter_name": "Q2/2024",
        "monthly_details": [
            {"month": "2024-04", "yhat": 120},
            {"month": "2024-05", "yhat": 135},
            {"month": "2024-06", "yhat": 145}
        ]
    }
}

response = requests.post("http://localhost:5000/generate_html", json=dados)
html_trimestre = response.json()['html']
```

## 📊 Comparação de Layouts

| Característica | Full | Compact |
|---|---|---|
| **Largura** | Responsivo (zoom 0.75) | 100% |
| **Tamanho típico** | ~6.800 chars | ~3.600 chars |
| **Seções** | Todas completas | Essenciais |
| **Uso ideal** | Relatórios | Popups |

## 🔄 Fluxo de Uso Recomendado

### Opção 1: Campo _html_data (NOVO - RECOMENDADO)
```python
# 1. Fazer previsão (sempre retorna _html_data)
response = requests.post("/predict", json={...})
previsao = response.json()['forecast'][0]

# 2. Armazenar _html_data no banco
html_data_para_banco = previsao['_html_data']
# Salvar html_data_para_banco em campo JSON/TEXT do banco

# 3. Gerar HTML quando necessário
html_response = requests.post("/generate_html", json={
    "html_data": html_data_do_banco,  # Recuperado do banco
    "layout": "compact"  # ou "full"
})
```

### Opção 2: Parâmetros Individuais
1. Fazer previsão com `include_explanation: false`
2. Armazenar dados da previsão individualmente
3. Gerar HTML passando parâmetros separados via `/generate_html`

### Opção 3: HTML Direto
1. Fazer previsão com `include_explanation: true`
2. Usar `html_summary` diretamente

## ⚙️ Parâmetros de explanation_data

```json
{
  "data_points": 12,           // Número de períodos históricos
  "confidence_score": "Alta",  // "Alta", "Média", "Baixa"
  "mape": 8.5,                // Erro percentual médio
  "r2": 0.85,                 // Coeficiente de determinação
  "outlier_count": 1,         // Outliers removidos
  "trend_slope": 2.5,         // Inclinação da tendência
  "seasonal_strength": 0.4,   // Força da sazonalidade
  "trend_strength": 0.3,      // Força da tendência
  "seasonal_pattern": {...},  // Padrão sazonal por mês
  "training_period": {        // Período de treinamento
    "start": "2023-01-01",
    "end": "2023-12-01"
  }
}
```

## 🚨 Códigos de Erro

- **400**: Parâmetros obrigatórios ausentes
- **400**: Formato de data inválido
- **500**: Erro interno na geração do HTML

## 🧪 Teste

Execute o exemplo completo:

```bash
python exemplo_generate_html.py
```

## 📦 Campo _html_data (NOVO)

O endpoint `/predict` agora **sempre retorna** um campo `_html_data` com todos os dados necessários para gerar HTML posteriormente:

```json
{
  "forecast": [
    {
      "item_id": 1,
      "yhat": 150.5,
      "ds": "2024-01-01 00:00:00",
      "_html_data": {
        "item_id": 1,
        "prediction": {
          "yhat": 150.5,
          "yhat_lower": 130.2,
          "yhat_upper": 170.8,
          "trend": 145.0,
          "yearly": 5.5,
          "ds": "2024-01-01"
        },
        "explanation_data": {
          "data_points": 12,
          "confidence_score": "Alta",
          "mape": 8.5,
          "r2": 0.85,
          "trend_slope": 2.5,
          "seasonal_pattern": {...}
        },
        "is_quarterly": false,
        "date_iso": "2024-01-01T00:00:00",
        "timestamp": 1704067200.0
      }
    }
  ]
}
```

### 🗄️ Armazenamento no Banco

```sql
CREATE TABLE previsoes (
    id SERIAL PRIMARY KEY,
    item_id INTEGER,
    data_previsao DATE,
    yhat DECIMAL(10,2),
    html_data JSONB  -- Armazenar o campo _html_data aqui
);

INSERT INTO previsoes (item_id, data_previsao, yhat, html_data)
VALUES (1, '2024-01-01', 150.5, '{"item_id": 1, "prediction": {...}}');
```

### 🎨 Geração de HTML do Banco

```python
# Recuperar do banco
html_data_do_banco = row['html_data']  # JSON do banco

# Gerar HTML
response = requests.post("/generate_html", json={
    "html_data": html_data_do_banco,
    "layout": "compact"
})

popup_html = response.json()['html']
```

## 💡 Vantagens

✅ **Flexibilidade**: Gera HTML sob demanda  
✅ **Performance**: Não armazena HTML desnecessário  
✅ **Separação**: Lógica de apresentação separada  
✅ **Customização**: Diferentes layouts conforme necessidade  
✅ **Compatibilidade**: Funciona com dados existentes  
✅ **Banco otimizado**: Armazena apenas dados estruturados  
✅ **Regeneração**: Permite gerar HTML quando necessário 

## Funcionalidades

### ✅ Recursos Disponíveis

1. **Geração de HTML**: Converte dados de explicação em HTML formatado
2. **Layouts Flexíveis**: Suporte para layouts `full` e `compact`
3. **Previsões Mensais e Trimestrais**: Funciona com ambos os tipos
4. **Múltiplos Formatos de Entrada**: html_data ou parâmetros individuais
5. **🆕 Retorno HTML Direto**: HTML puro (`text/html`) ou JSON (padrão)

### 🎯 Modos de Retorno

| Modo | Content-Type | Uso Ideal |
|------|-------------|-----------|
| **JSON** (padrão) | `application/json` | APIs, processamento programático |
| **🆕 HTML Direto** | `text/html` | Navegadores, iframes, downloads |

## Métodos de Uso

### 1. 🆕 HTML Direto com Parâmetro

```python
payload = {
    "html_data": dados_do_banco,
    "layout": "compact",
    "return_html_direct": True  # 🆕 Novo parâmetro
}

response = requests.post("/generate_html", json=payload)
# response.text contém HTML puro pronto para uso
```

### 2. 🆕 HTML Direto com Header

```python
payload = {
    "html_data": dados_do_banco,
    "layout": "full"
}

response = requests.post(
    "/generate_html", 
    json=payload,
    headers={"Accept": "text/html"}  # 🆕 Header especial
)
# response.text contém HTML puro
```

### 3. JSON Tradicional (Padrão)

```python
payload = {
    "html_data": dados_do_banco,
    "layout": "compact"
}

response = requests.post("/generate_html", json=payload)
json_data = response.json()
html_content = json_data["html"]  # HTML dentro do JSON
```

## Formatos de Entrada

### Formato 1: html_data (Dados do Banco) - **RECOMENDADO**

```python
{
    "html_data": {
        "item_id": 1687,
        "prediction": {
            "ds": "2025-07-01 00:00:00",
            "yhat": 1227.22,
            "yhat_lower": 502.75,
            "yhat_upper": 1951.69,
            "trend": 1380.92,
            "yearly": -153.7
        },
        "explanation_data": {
            "confidence_score": "Média",
            "data_points": 29,
            "mape": 23.16,
            "r2": 0.40,
            "seasonal_pattern": {...},
            "training_period": {...}
        },
        "is_quarterly": false,
        "date_iso": "2025-07-01T00:00:00",
        "timestamp": 1751328000
    },
    "layout": "compact",
    "return_html_direct": true  # 🆕 Opcional
}
```

### Formato 2: Parâmetros Individuais

```python
{
    "item_id": 1687,
    "prediction": {
        "ds": "2025-07-01 00:00:00",
        "yhat": 1227.22,
        "yhat_lower": 502.75,
        "yhat_upper": 1951.69,
        "trend": 1380.92,
        "yearly": -153.7
    },
    "explanation_data": {
        "confidence_score": "Média",
        "data_points": 29,
        # ... outros campos
    },
    "layout": "full",
    "is_quarterly": false,
    "return_html_direct": true  # 🆕 Opcional
}
```

## Layouts Disponíveis

### Layout Full (Padrão)
- **Tamanho**: ~800px largura, ~6.800 caracteres
- **Uso**: Páginas completas, relatórios detalhados
- **Conteúdo**: Cabeçalho, detalhamento completo, gráficos, recomendações

### Layout Compact
- **Tamanho**: ~400px largura, ~3.600 caracteres  
- **Uso**: Popups, modais, widgets
- **Conteúdo**: Informações essenciais, design otimizado

## 🆕 Casos de Uso do HTML Direto

### 1. 🔗 Link Direto para Relatório
```javascript
// Frontend: Abrir relatório em nova aba
window.open('/generate_html_url', '_blank');
```

### 2. 🖼️ Iframe Incorporado
```html
<!-- Incorporar em modal ou popup -->
<iframe src="/api/generate_html" width="450" height="600"></iframe>
```

### 3. 💾 Download de Arquivo HTML
```python
response = requests.post("/generate_html", json=payload, headers={"Accept": "text/html"})
with open("relatorio.html", "w", encoding="utf-8") as f:
    f.write(response.text)
```

### 4. 📱 WebView Mobile
```java
// Android
webView.loadData(htmlContent, "text/html", "UTF-8");
```

### 5. 📧 Email HTML
```python
# Layout compact ideal para email
payload = {"html_data": dados, "layout": "compact", "return_html_direct": True}
html_email = requests.post("/generate_html", json=payload).text
send_email(to="user@email.com", html_body=html_email)
```

## Respostas

### 🆕 Resposta HTML Direto
```
Status: 200 OK
Content-Type: text/html; charset=utf-8

<div style="font-family: Arial, sans-serif; ...">
    <!-- HTML formatado pronto para uso -->
</div>
```

### Resposta JSON (Padrão)
```json
{
    "html": "<div style=\"font-family: Arial...\">...</div>",
    "info": {
        "layout": "compact",
        "size_chars": 3640,
        "is_quarterly": false,
        "item_id": 1687,
        "period": "Julho/2025"
    }
}
```

## 🔄 Fluxo Completo Recomendado

### 1. Na Previsão (Armazenar no Banco)
```python
# Endpoint /predict retorna campo _html_data
response = requests.post("/predict", json={"sales_data": [...]})
forecast = response.json()["forecast"][0]
html_data = forecast["_html_data"]  # 🗃️ Salvar no banco
```

### 2. Na Exibição (Gerar HTML)
```python
# Usar dados do banco para gerar HTML
payload = {
    "html_data": html_data_do_banco,
    "layout": "compact",
    "return_html_direct": True  # 🆕 HTML direto
}
html_response = requests.post("/generate_html", json=payload)
# html_response.text é HTML puro pronto para uso
```

## Tratamento de Erros

### HTML Direto
```
Status: 400 Bad Request
Content-Type: text/html; charset=utf-8

<html>
<body>
    <h1>Erro: Campo obrigatório 'item_id' não fornecido</h1>
</body>
</html>
```

### JSON (Padrão)
```json
{
    "error": "Campo obrigatório 'item_id' não fornecido"
}
```

## Performance e Considerações

### 📊 Comparação de Tamanhos
| Layout | Tamanho HTML | Uso de Banda | Tempo de Renderização |
|--------|-------------|---------------|----------------------|
| Full | ~6.800 chars | Alto | Moderado |
| Compact | ~3.600 chars | Baixo | Rápido |

### 🎯 Recomendações
- **Popups/Modais**: Use `layout: "compact"`
- **Páginas Completas**: Use `layout: "full"`
- **Mobile**: Prefira `compact` por performance
- **Email**: Sempre `compact` + HTML direto
- **Relatórios**: `full` para máximo detalhamento

## Exemplo Completo

```python
import requests

# Dados do banco (campo _html_data)
html_data = {
    "item_id": 1687,
    "prediction": {
        "ds": "2025-07-01 00:00:00",
        "yhat": 1227.22,
        "yhat_lower": 502.75,
        "yhat_upper": 1951.69,
        "trend": 1380.92,
        "yearly": -153.7
    },
    "explanation_data": {
        "confidence_score": "Média",
        "data_points": 29,
        "mape": 23.16,
        "r2": 0.40,
        "seasonal_pattern": {
            "1": 0.68, "2": 0.73, "3": 0.91, "4": 0.80,
            "5": 0.69, "6": 0.80, "7": 0.89, "8": 0.95,
            "9": 1.19, "10": 1.51, "11": 1.55, "12": 1.12
        },
        "seasonal_strength": 1.74,
        "std": 528.05,
        "training_period": {
            "start": "2023-01-31",
            "end": "2025-05-31",
            "months": 29
        },
        "trend_slope": 18.63,
        "trend_strength": 0.47
    },
    "is_quarterly": False,
    "date_iso": "2025-07-01T00:00:00",
    "timestamp": 1751328000
}

# Gerar HTML direto
response = requests.post(
    "http://localhost:5000/generate_html",
    json={
        "html_data": html_data,
        "layout": "compact",
        "return_html_direct": True
    }
)

if response.status_code == 200:
    # HTML pronto para uso
    html_content = response.text
    print(f"HTML gerado: {len(html_content)} caracteres")
    
    # Salvar como arquivo
    with open("explicacao.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("✅ HTML salvo em explicacao.html")
else:
    print(f"❌ Erro: {response.text}")
```

## 🎉 Vantagens do HTML Direto

1. **🚀 Performance**: Menos processamento no frontend
2. **🌐 Compatibilidade**: Funciona em qualquer navegador
3. **📱 Versatilidade**: Ideal para WebViews, emails, PDFs
4. **⚡ Simplicidade**: HTML pronto para uso, sem parsing
5. **🔗 Integração**: Perfeito para iframes e incorporações
6. **💾 Eficiência**: Menos bytes transferidos que JSON

---

**Versão**: 1.2.0 - Suporte a HTML Direto  
**Data**: Dezembro 2024 