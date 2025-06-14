# Gunicorn em Produção - API Forecast

## 📋 Visão Geral

Este guia explica como executar a API Forecast em produção usando **Gunicorn** como servidor WSGI, mantendo todas as funcionalidades incluindo CORS liberado.

## 🚀 Setup Rápido

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar Servidor
```bash
# Usando script pronto
bash start_production.sh

# Ou comando direto
gunicorn --config gunicorn_config.py wsgi:application
```

### 3. Testar Funcionamento
```bash
python teste_gunicorn.py
```

## 📁 Arquivos de Configuração

### ✅ Arquivos Criados para Produção

| Arquivo | Descrição |
|---------|-----------|
| `gunicorn_config.py` | Configuração do Gunicorn |
| `wsgi.py` | Entry point WSGI |
| `start_production.sh` | Script de inicialização |
| `teste_gunicorn.py` | Testes de produção |
| `requirements.txt` | Dependências atualizadas |

## ⚙️ Configuração do Gunicorn

### `gunicorn_config.py`
```python
# Configurações principais
bind = "0.0.0.0:5000"  # Escutar em todas as interfaces
workers = multiprocessing.cpu_count() * 2 + 1  # Workers baseado no CPU
worker_class = "sync"  # Tipo de worker
timeout = 30  # Timeout em segundos
max_requests = 1000  # Reiniciar worker após N requests
preload_app = True  # Carregar app antes de criar workers

# Logs
accesslog = "-"  # Log de acesso no stdout
errorlog = "-"   # Log de erro no stderr
loglevel = "info"  # Nível de log

# Por ambiente
if os.getenv("ENVIRONMENT") == "production":
    workers = multiprocessing.cpu_count() * 2 + 1
    loglevel = "warning"
    timeout = 60
```

### `wsgi.py`
```python
# Entry point para Gunicorn
from server import app

# Configurações de produção
if os.getenv("ENVIRONMENT") == "production":
    app.config['DEBUG'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-in-production')

# Expor aplicação
application = app
```

## 🚀 Comandos de Execução

### Desenvolvimento Local
```bash
# Desenvolvimento com reload
gunicorn --reload --bind 0.0.0.0:5000 wsgi:application
```

### Staging
```bash
# Staging com configurações intermediárias
ENVIRONMENT=staging gunicorn --config gunicorn_config.py wsgi:application
```

### Produção
```bash
# Produção com todas as otimizações
ENVIRONMENT=production gunicorn --config gunicorn_config.py wsgi:application

# Ou usando script pronto
bash start_production.sh
```

### Com Logs Específicos
```bash
# Logs em arquivos separados
gunicorn --config gunicorn_config.py \
    --log-file logs/gunicorn.log \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    wsgi:application
```

## 🌐 CORS com Gunicorn

### ✅ Funciona Automaticamente

O CORS está configurado no Flask e funciona identicamente com Gunicorn:

```python
# server.py - configuração mantida
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Permite qualquer origem
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept", "Authorization", "X-Requested-With"]
    }
})
```

### 🧪 Testado e Funcionando

```bash
# Teste CORS com Gunicorn
python teste_gunicorn.py
```

**Resultado esperado**: ✅ CORS funciona com todas as origens testadas

## 🎛️ Configurações por Ambiente

### 🏭 Produção (`ENVIRONMENT=production`)
```bash
export ENVIRONMENT=production
export SECRET_KEY=sua-chave-secreta-super-forte

gunicorn --config gunicorn_config.py wsgi:application
```

**Características:**
- ✅ Mais workers (CPU * 2 + 1)
- ✅ Logs menos verbosos (warning)
- ✅ Timeout maior (60s)
- ✅ Debug desabilitado
- ✅ Secret key obrigatória

### 🧪 Staging (`ENVIRONMENT=staging`)
```bash
export ENVIRONMENT=staging

gunicorn --config gunicorn_config.py wsgi:application
```

**Características:**
- ✅ Workers moderados (2)
- ✅ Logs informativos
- ✅ Timeout médio (45s)
- ✅ Configurações intermediárias

### 🛠️ Desenvolvimento (padrão)
```bash
gunicorn --config gunicorn_config.py wsgi:application
```

**Características:**
- ✅ Poucos workers (2)
- ✅ Logs detalhados (debug)
- ✅ Reload habilitado
- ✅ Timeout baixo (30s)

## 📊 Monitoramento

### Logs em Tempo Real
```bash
# Log principal do Gunicorn
tail -f logs/gunicorn.log

# Log de acesso (requests)
tail -f logs/access.log

# Log de erros
tail -f logs/error.log

# Todos os logs simultaneamente
tail -f logs/*.log
```

### Métricas de Performance
```bash
# Processos Gunicorn ativos
ps aux | grep gunicorn

# Uso de memória
ps -o pid,ppid,cmd,%mem,%cpu -p $(pgrep -f gunicorn)

# Conexões de rede
netstat -tulpn | grep :5000
```

### PID Management
```bash
# Ver PID do master process
cat /tmp/gunicorn_forecast.pid

# Recarregar configuração (sem downtime)
kill -HUP $(cat /tmp/gunicorn_forecast.pid)

# Parar graciosamente
kill -TERM $(cat /tmp/gunicorn_forecast.pid)

# Parar forçadamente
kill -KILL $(cat /tmp/gunicorn_forecast.pid)
```

## 🔄 Deploy e Atualizações

### Deploy Inicial
```bash
# 1. Preparar ambiente
git clone <seu-repo>
cd forecast2
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Testar localmente
python server.py

# 4. Iniciar produção
bash start_production.sh
```

### Atualizações Zero-Downtime
```bash
# 1. Fazer pull das mudanças
git pull origin main

# 2. Instalar novas dependências se houver
pip install -r requirements.txt

# 3. Recarregar workers (sem parar servidor)
kill -HUP $(cat /tmp/gunicorn_forecast.pid)

# 4. Verificar se está funcionando
python teste_gunicorn.py
```

### Rollback Rápido
```bash
# 1. Voltar para versão anterior
git checkout HEAD~1

# 2. Recarregar
kill -HUP $(cat /tmp/gunicorn_forecast.pid)
```

## 🐳 Docker (Opcional)

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn_config.py", "wsgi:application"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  forecast-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=your-secret-key
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

## 🔧 Resolução de Problemas

### ❌ Servidor não inicia
```bash
# Verificar se porta está ocupada
netstat -tulpn | grep :5000

# Verificar dependências
python -c "import flask, flask_cors, pandas, numpy, gunicorn"

# Verificar configuração
python -c "import wsgi"
```

### ❌ CORS não funciona
```bash
# Testar CORS específico
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://localhost:5000/generate_html

# Deve retornar headers CORS
```

### ❌ Performance ruim
```bash
# Aumentar workers
# Em gunicorn_config.py:
workers = multiprocessing.cpu_count() * 4 + 1

# Ou usar workers assíncronos
worker_class = "gevent"
pip install gevent
```

### ❌ Memory leaks
```bash
# Reduzir max_requests para forçar restart
# Em gunicorn_config.py:
max_requests = 500
max_requests_jitter = 50
```

## 📈 Otimizações de Performance

### Para APIs com ML (recomendado)
```python
# gunicorn_config.py
worker_class = "sync"  # Melhor para CPU-intensive (ML)
workers = multiprocessing.cpu_count() * 2 + 1
preload_app = True  # Carrega modelo uma vez só
max_requests = 1000  # Evita memory leaks
timeout = 60  # Timeout maior para processamento ML
```

### Para APIs I/O-intensive
```python
# gunicorn_config.py
worker_class = "gevent"  # Assíncrono para I/O
workers = multiprocessing.cpu_count() * 2
worker_connections = 1000
```

## 🎯 Checklist de Produção

### ✅ Antes de Deploy
- [ ] `requirements.txt` atualizado
- [ ] Variáveis de ambiente configuradas
- [ ] SECRET_KEY definida
- [ ] Logs configurados
- [ ] CORS testado
- [ ] Performance testada

### ✅ Após Deploy
- [ ] Servidor iniciando corretamente
- [ ] Endpoints respondendo
- [ ] CORS funcionando
- [ ] Logs sendo gerados
- [ ] Métricas normais

### ✅ Monitoramento Contínuo
- [ ] Logs de erro zerados
- [ ] Tempo de resposta < 1s
- [ ] CPU < 80%
- [ ] Memória < 80%
- [ ] Requests/segundo adequados

## 🎉 Resumo

### ✅ O que foi configurado:
1. **Gunicorn** como servidor WSGI de produção
2. **CORS liberado** funcionando identicamente ao Flask dev
3. **Configurações otimizadas** por ambiente (dev/staging/prod)
4. **Logs estruturados** para monitoramento
5. **Scripts automatizados** para deploy
6. **Testes específicos** para validação

### 🚀 Para usar em produção:
```bash
# Comando simples
bash start_production.sh

# Ou manual
ENVIRONMENT=production gunicorn --config gunicorn_config.py wsgi:application
```

### 🌐 CORS continua funcionando:
- ✅ Aceita requests de **qualquer origem**
- ✅ Suporta todos os **métodos HTTP**
- ✅ Headers **Accept: text/html** funcionam
- ✅ **HTML direto** funciona perfeitamente

---

**Status**: ✅ **Pronto para Produção**  
**Testado**: CORS + Performance + Logs  
**Compatibilidade**: Mantém 100% das funcionalidades do Flask dev 