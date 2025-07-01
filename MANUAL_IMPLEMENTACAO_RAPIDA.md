# ⚡ Manual de Implementação Rápida - Sistema MRP Avançado

## 🚀 Começando em 5 Minutos

### Passo 1: Verificar Dependências

```bash
# Verificar Python
python --version  # Requer Python 3.8+

# Verificar dependências básicas
pip list | grep -E "(pandas|numpy|flask|requests)"
```

### Passo 2: Instalar Dependências

```bash
# Instalar dependências básicas
pip install -r requirements.txt

# Para recursos avançados (opcional)
pip install supplychainpy scipy
```

### Passo 3: Iniciar o Servidor

```bash
# Modo desenvolvimento
python server.py

# Ou modo produção
gunicorn -c gunicorn_config.py wsgi:app
```

### Passo 4: Testar o Sistema

```bash
# Teste básico
curl -X POST http://localhost:5000/mrp_advanced \
  -H "Content-Type: application/json" \
  -d '{
    "sporadic_demand": {"2025-08-01": 1000},
    "initial_stock": 500,
    "leadtime_days": 30,
    "period_start_date": "2025-07-01",
    "period_end_date": "2025-12-31"
  }'

# Se retornar JSON estruturado, sistema está funcionando! ✅
```

---

## 🎯 Configuração Básica

### Exemplo Mínimo Funcional

```json
{
    "sporadic_demand": {
        "2025-08-15": 2000,
        "2025-10-10": 1500
    },
    "initial_stock": 800,
    "leadtime_days": 21,
    "period_start_date": "2025-07-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-07-01",
    "end_cutoff_date": "2025-12-31"
}
```

### Configuração Recomendada Para Produção

```json
{
    "sporadic_demand": {
        "2025-08-15": 2000,
        "2025-10-10": 1500
    },
    "initial_stock": 800,
    "leadtime_days": 21,
    "period_start_date": "2025-07-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-07-01",
    "end_cutoff_date": "2025-12-31",
    "safety_margin_percent": 10,
    "safety_days": 3,
    "enable_consolidation": true,
    "setup_cost": 300,
    "holding_cost_rate": 0.20,
    "service_level": 0.95
}
```

---

## 🔧 Integração com Sistemas Existentes

### Python Integration

```python
import requests
import json

class MRPClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
    
    def calculate_mrp(self, demand_data):
        """Calcular MRP avançado"""
        try:
            response = requests.post(
                f"{self.base_url}/mrp_advanced",
                json=demand_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

# Uso
mrp = MRPClient()
result = mrp.calculate_mrp(your_demand_data)

# Verificar resultado
if "error" not in result:
    batches = result["batches"]
    analytics = result["analytics"]
    print(f"✅ {len(batches)} lotes planejados")
else:
    print(f"❌ Erro: {result['error']}")
```

### PHP Integration

```php
<?php
class MRPClient {
    private $baseUrl;
    
    public function __construct($baseUrl = "http://localhost:5000") {
        $this->baseUrl = $baseUrl;
    }
    
    public function calculateMRP($demandData) {
        $ch = curl_init();
        
        curl_setopt_array($ch, [
            CURLOPT_URL => $this->baseUrl . "/mrp_advanced",
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($demandData),
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Accept: application/json'
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 30
        ]);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode === 200) {
            return json_decode($response, true);
        } else {
            return ["error" => "HTTP $httpCode: $response"];
        }
    }
}

// Uso
$mrp = new MRPClient();
$result = $mrp->calculateMRP($demandData);

if (!isset($result['error'])) {
    $batches = $result['batches'];
    $analytics = $result['analytics'];
    echo "✅ " . count($batches) . " lotes planejados\n";
} else {
    echo "❌ Erro: " . $result['error'] . "\n";
}
?>
```

### JavaScript/Node.js Integration

```javascript
const axios = require('axios');

class MRPClient {
    constructor(baseUrl = 'http://localhost:5000') {
        this.baseUrl = baseUrl;
    }
    
    async calculateMRP(demandData) {
        try {
            const response = await axios.post(
                `${this.baseUrl}/mrp_advanced`,
                demandData,
                {
                    headers: { 'Content-Type': 'application/json' },
                    timeout: 30000
                }
            );
            
            return response.data;
            
        } catch (error) {
            if (error.response) {
                return { error: `HTTP ${error.response.status}: ${error.response.data}` };
            } else {
                return { error: `Erro de conexão: ${error.message}` };
            }
        }
    }
}

// Uso
const mrp = new MRPClient();

mrp.calculateMRP(demandData).then(result => {
    if (!result.error) {
        const batches = result.batches;
        const analytics = result.analytics;
        console.log(`✅ ${batches.length} lotes planejados`);
    } else {
        console.log(`❌ Erro: ${result.error}`);
    }
});
```

---

## 📊 Templates de Configuração

### Template 1: Indústria (Lead Time Longo)

```json
{
    "sporadic_demand": {
        "2025-09-01": 5000,
        "2025-11-15": 3000,
        "2025-12-20": 4000
    },
    "initial_stock": 1000,
    "leadtime_days": 60,
    "period_start_date": "2025-08-01",
    "period_end_date": "2025-12-31",
    "start_cutoff_date": "2025-08-01",
    "end_cutoff_date": "2025-12-31",
    "safety_margin_percent": 15,
    "safety_days": 7,
    "setup_cost": 800,
    "holding_cost_rate": 0.18,
    "min_batch_size": 2000,
    "max_batch_size": 10000,
    "enable_consolidation": true,
    "service_level": 0.95
}
```

### Template 2: Varejo (Reposição Rápida)

```json
{
    "sporadic_demand": {
        "2025-08-10": 1200,
        "2025-08-25": 800,
        "2025-09-15": 1000,
        "2025-10-05": 1500
    },
    "initial_stock": 400,
    "leadtime_days": 14,
    "period_start_date": "2025-08-01",
    "period_end_date": "2025-10-31",
    "start_cutoff_date": "2025-08-01",
    "end_cutoff_date": "2025-10-31",
    "safety_margin_percent": 8,
    "safety_days": 2,
    "setup_cost": 150,
    "holding_cost_rate": 0.25,
    "min_batch_size": 500,
    "max_batch_size": 5000,
    "enable_consolidation": false,
    "service_level": 0.98
}
```

### Template 3: E-commerce (Alta Variabilidade)

```json
{
    "sporadic_demand": {
        "2025-11-29": 15000,  // Black Friday
        "2025-12-15": 8000,   // Natal
        "2025-01-05": 3000    // Pós-feriados
    },
    "initial_stock": 2000,
    "leadtime_days": 25,
    "period_start_date": "2025-11-01",
    "period_end_date": "2025-01-31",
    "start_cutoff_date": "2025-11-01",
    "end_cutoff_date": "2025-01-31",
    "safety_margin_percent": 20,
    "safety_days": 5,
    "setup_cost": 400,
    "holding_cost_rate": 0.30,
    "min_batch_size": 1000,
    "max_batch_size": 20000,
    "enable_consolidation": true,
    "service_level": 0.97
}
```

---

## 🎯 Configuração por Setor

### 🏭 Manufacturing

```json
{
    "safety_margin_percent": 12,
    "safety_days": 5,
    "setup_cost": 600,
    "holding_cost_rate": 0.18,
    "service_level": 0.95,
    "enable_consolidation": true,
    "min_batch_size": 1000
}
```

### 🏥 Healthcare

```json
{
    "safety_margin_percent": 25,
    "safety_days": 7,
    "setup_cost": 200,
    "holding_cost_rate": 0.15,
    "service_level": 0.99,
    "enable_consolidation": false,
    "min_batch_size": 200
}
```

### 🛒 Retail

```json
{
    "safety_margin_percent": 8,
    "safety_days": 2,
    "setup_cost": 100,
    "holding_cost_rate": 0.25,
    "service_level": 0.97,
    "enable_consolidation": false,
    "min_batch_size": 300
}
```

### 🍔 Food Service

```json
{
    "safety_margin_percent": 5,
    "safety_days": 1,
    "setup_cost": 80,
    "holding_cost_rate": 0.35,
    "service_level": 0.98,
    "enable_consolidation": false,
    "min_batch_size": 100
}
```

---

## 🔍 Validação e Testes

### Script de Validação Rápida

```python
#!/usr/bin/env python3
"""
Script de validação para implementação MRP
"""

import requests
import json
from datetime import datetime, timedelta

def validate_mrp_system():
    """Validação completa do sistema MRP"""
    
    print("🔍 Iniciando validação do sistema MRP...")
    
    # Teste 1: Conectividade
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        print("✅ Servidor acessível")
    except:
        print("❌ Servidor não acessível")
        return False
    
    # Teste 2: Endpoint MRP Avançado
    test_data = {
        "sporadic_demand": {"2025-08-01": 1000},
        "initial_stock": 500,
        "leadtime_days": 21,
        "period_start_date": "2025-07-01",
        "period_end_date": "2025-12-31",
        "start_cutoff_date": "2025-07-01",
        "end_cutoff_date": "2025-12-31"
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/mrp_advanced",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Endpoint MRP avançado funcionando")
            
            # Teste 3: Estrutura da resposta
            required_fields = ['batches', 'analytics', '_endpoint_info']
            if all(field in result for field in required_fields):
                print("✅ Estrutura de resposta válida")
            else:
                print("❌ Estrutura de resposta inválida")
                return False
                
            # Teste 4: Analytics básicos
            analytics = result['analytics']
            if 'summary' in analytics and 'demand_analysis' in analytics:
                print("✅ Analytics básicos presentes")
            else:
                print("❌ Analytics básicos ausentes")
                return False
                
            # Teste 5: Lotes criados
            batches = result['batches']
            if len(batches) > 0:
                print(f"✅ {len(batches)} lote(s) criado(s)")
            else:
                print("❌ Nenhum lote criado")
                return False
                
        else:
            print(f"❌ Erro no endpoint: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return False
    
    print("🎉 Validação concluída com sucesso!")
    return True

if __name__ == "__main__":
    validate_mrp_system()
```

### Testes de Carga

```python
import concurrent.futures
import time

def load_test_mrp(num_requests=10):
    """Teste de carga básico"""
    
    def single_request():
        test_data = {
            "sporadic_demand": {"2025-08-01": 1000},
            "initial_stock": 500,
            "leadtime_days": 21,
            "period_start_date": "2025-07-01",
            "period_end_date": "2025-12-31"
        }
        
        start_time = time.time()
        response = requests.post(
            "http://localhost:5000/mrp_advanced",
            json=test_data,
            timeout=30
        )
        end_time = time.time()
        
        return {
            "status_code": response.status_code,
            "response_time": end_time - start_time,
            "size": len(response.content)
        }
    
    print(f"🔄 Executando teste de carga com {num_requests} requisições...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda x: single_request(), range(num_requests)))
    
    # Análise dos resultados
    successful = sum(1 for r in results if r["status_code"] == 200)
    avg_time = sum(r["response_time"] for r in results) / len(results)
    
    print(f"✅ {successful}/{num_requests} requisições bem-sucedidas")
    print(f"⏱️ Tempo médio de resposta: {avg_time:.2f}s")
    print(f"🚀 RPS aproximado: {num_requests/sum(r['response_time'] for r in results):.1f}")

load_test_mrp(20)
```

---

## 📈 Monitoramento de Produção

### Métricas Essenciais

```python
def monitor_mrp_performance(result):
    """Monitorar performance do MRP"""
    
    alerts = []
    analytics = result.get('analytics', {})
    summary = analytics.get('summary', {})
    
    # Verificar taxa de atendimento
    fulfillment_rate = summary.get('demand_fulfillment_rate', 0)
    if fulfillment_rate < 90:
        alerts.append(f"⚠️ Taxa de atendimento baixa: {fulfillment_rate}%")
    
    # Verificar stockouts
    if summary.get('stockout_occurred', False):
        alerts.append("🚨 Stockout detectado!")
    
    # Verificar superprodução
    coverage_rate = float(summary.get('production_coverage_rate', '0%').replace('%', ''))
    if coverage_rate > 200:
        alerts.append(f"⚠️ Superprodução: {coverage_rate}%")
    
    # Verificar número de lotes
    total_batches = summary.get('total_batches', 0)
    if total_batches > 10:
        alerts.append(f"⚠️ Muitos lotes: {total_batches}")
    
    return alerts

# Uso
alerts = monitor_mrp_performance(mrp_result)
for alert in alerts:
    print(alert)
```

### Logs Estruturados

```python
import logging
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mrp_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('MRP_System')

def log_mrp_request(input_data, result, processing_time):
    """Log estruturado de requisições MRP"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "input": {
            "total_demand": sum(input_data.get('sporadic_demand', {}).values()),
            "leadtime_days": input_data.get('leadtime_days'),
            "initial_stock": input_data.get('initial_stock')
        },
        "output": {
            "total_batches": len(result.get('batches', [])),
            "fulfillment_rate": result.get('analytics', {}).get('summary', {}).get('demand_fulfillment_rate'),
            "strategy_used": result.get('analytics', {}).get('advanced_analytics', {}).get('advanced_mrp_strategy')
        },
        "performance": {
            "processing_time_seconds": processing_time,
            "success": "error" not in result
        }
    }
    
    logger.info(f"MRP_REQUEST: {json.dumps(log_entry)}")

# Uso
start_time = time.time()
result = mrp_client.calculate_mrp(input_data)
processing_time = time.time() - start_time

log_mrp_request(input_data, result, processing_time)
```

---

## 🚀 Deploy em Produção

### Docker

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  mrp-system:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - WORKERS=4
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mrp-system
```

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream mrp_backend {
        server mrp-system:5000;
    }
    
    server {
        listen 80;
        
        location /mrp_advanced {
            proxy_pass http://mrp_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_connect_timeout 30s;
            proxy_read_timeout 30s;
        }
        
        location /health {
            proxy_pass http://mrp_backend;
        }
    }
}
```

### Systemd Service

```ini
# /etc/systemd/system/mrp-system.service
[Unit]
Description=MRP Advanced System
After=network.target

[Service]
Type=exec
User=mrp
Group=mrp
WorkingDirectory=/opt/mrp-system
ExecStart=/opt/mrp-system/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar serviço
sudo systemctl enable mrp-system
sudo systemctl start mrp-system
sudo systemctl status mrp-system
```

---

## 📞 Suporte e Manutenção

### Checklist de Health Check

- [ ] Servidor responde em `GET /`
- [ ] Endpoint `/mrp_advanced` retorna JSON válido
- [ ] Logs não mostram erros críticos
- [ ] CPU e memória dentro dos limites
- [ ] Tempo de resposta < 10 segundos
- [ ] Taxa de erro < 1%

### Comandos Úteis

```bash
# Verificar status
curl http://localhost:5000/

# Teste rápido
python test_stockout_fix.py

# Logs em tempo real
tail -f mrp_system.log

# Métricas de sistema
htop
free -h
df -h
```

---

*Manual atualizado em: 30 de Junho de 2025* 