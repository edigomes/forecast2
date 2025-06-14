# Configuração de CORS - API Forecast

## ✅ Status Atual

O servidor Flask está configurado com **CORS liberado** para aceitar requests de **qualquer URL/origem**.

## 🔧 Configuração Implementada

```python
from flask_cors import CORS

# Configurar CORS para permitir requests de qualquer URL
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Permite qualquer origem
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Métodos permitidos
        "allow_headers": ["Content-Type", "Accept", "Authorization", "X-Requested-With"]  # Headers permitidos
    }
})
```

## 🌐 O que isso permite

### ✅ Origens Aceitas
- ✅ `http://localhost:3000` (React dev server)
- ✅ `https://meuapp.vercel.app` (Vercel)
- ✅ `https://app.exemplo.com` (Domínio customizado)
- ✅ `http://192.168.1.100:8080` (IP local)
- ✅ `https://frontend.herokuapp.com` (Heroku)
- ✅ **Qualquer outra origem**

### ✅ Métodos HTTP Suportados
- `GET` - Para consultas
- `POST` - Para previsões e geração de HTML
- `PUT` - Para atualizações
- `DELETE` - Para remoções
- `OPTIONS` - Para preflight requests

### ✅ Headers Permitidos
- `Content-Type` - Para JSON/HTML
- `Accept` - Para especificar formato de resposta
- `Authorization` - Para autenticação (futuro)
- `X-Requested-With` - Para AJAX requests

## 🧪 Testes Realizados

O arquivo `teste_cors.py` executou 3 baterias de testes:

1. **✅ Headers CORS**: Verifica se servidor retorna headers corretos
2. **✅ POST Request**: Testa request real com origem diferente
3. **✅ Múltiplas Origens**: Testa 5 origens diferentes simultaneamente

**Resultado**: 🎉 **3/3 testes passaram**

## 🚀 Como Usar no Frontend

### JavaScript/Fetch
```javascript
// Request simples - CORS funciona automaticamente
fetch('http://localhost:5000/generate_html', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/html'  // Para HTML direto
    },
    body: JSON.stringify({
        html_data: dados_do_banco,
        layout: 'compact',
        return_html_direct: true
    })
})
.then(response => response.text())  // HTML direto
.then(html => {
    document.getElementById('popup').innerHTML = html;
});
```

### React/Axios
```javascript
import axios from 'axios';

// Configurar baseURL se necessário
const api = axios.create({
    baseURL: 'http://localhost:5000'
});

// Request para gerar HTML
const response = await api.post('/generate_html', {
    html_data: dadosDoBanco,
    layout: 'compact'
});

// HTML está em response.data.html
setPopupContent(response.data.html);
```

### Vue.js
```javascript
// Método no componente Vue
async gerarHTML() {
    try {
        const response = await this.$http.post('http://localhost:5000/generate_html', {
            html_data: this.dadosDoBanco,
            layout: 'compact',
            return_html_direct: true
        }, {
            headers: {
                'Accept': 'text/html'
            }
        });
        
        // response.data é HTML puro
        this.htmlContent = response.data;
    } catch (error) {
        console.error('Erro ao gerar HTML:', error);
    }
}
```

### Angular
```typescript
import { HttpClient } from '@angular/common/http';

// No serviço Angular
gerarHTML(dadosDoBanco: any): Observable<string> {
    return this.http.post('http://localhost:5000/generate_html', {
        html_data: dadosDoBanco,
        layout: 'compact',
        return_html_direct: true
    }, {
        headers: {
            'Accept': 'text/html'
        },
        responseType: 'text'  // Importante para HTML direto
    });
}
```

## 🔒 Considerações de Segurança

### ⚠️ Para Produção
```python
# Recomendado: Limitar origens específicas
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://meuapp.com",
            "https://app.meudominio.com",
            "https://meuapp.vercel.app"
        ],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Accept"]
    }
})
```

### 🛡️ Benefícios de Limitar Origens
- Previne uso não autorizado da API
- Reduz possíveis ataques CSRF
- Controla quais sites podem consumir a API
- Melhora logs e monitoramento

## 📊 Monitoramento

### Logs de CORS
O servidor registra automaticamente:
- Origens que fazem requests
- Headers enviados e retornados
- Status das respostas

### Headers de Resposta
Todas as respostas incluem:
```
Access-Control-Allow-Origin: [origem_do_request]
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Accept, Authorization, X-Requested-With
```

## 🎯 Casos de Uso Comuns

### 1. Frontend React (localhost:3000)
```javascript
// Desenvolvimento local
const response = await fetch('http://localhost:5000/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dadosPrevisao)
});
```

### 2. App em Produção (vercel.app)
```javascript
// Produção
const response = await fetch('https://api.forecast.com/generate_html', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        'Accept': 'text/html'
    },
    body: JSON.stringify({ html_data: dados, layout: 'compact' })
});
```

### 3. Iframe/WebView
```html
<!-- HTML pode ser carregado diretamente -->
<iframe src="https://api.forecast.com/generate_html" 
        width="500" height="400">
</iframe>
```

---

**Status**: ✅ **CORS Configurado e Testado**  
**Última atualização**: Dezembro 2024  
**Compatibilidade**: Todos os navegadores modernos 