#!/bin/bash
# Script para iniciar servidor em produção com Gunicorn
# Arquivo: start_production.sh

set -e  # Parar script se houver erro

echo "🚀 Iniciando Servidor Forecast API em Produção"
echo "================================================"

# Configurar variáveis de ambiente
export ENVIRONMENT="production"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verificar se arquivo de configuração existe
if [ ! -f "gunicorn_config.py" ]; then
    echo "❌ Arquivo gunicorn_config.py não encontrado!"
    exit 1
fi

# Verificar se arquivo WSGI existe
if [ ! -f "wsgi.py" ]; then
    echo "❌ Arquivo wsgi.py não encontrado!"
    exit 1
fi

# Verificar se dependências estão instaladas
echo "🔍 Verificando dependências..."
python -c "import flask, flask_cors, pandas, numpy, gunicorn" || {
    echo "❌ Dependências não encontradas. Execute: pip install -r requirements.txt"
    exit 1
}

# Criar diretório de logs se não existir
mkdir -p logs

# Limpar PID file antigo se existir
if [ -f "/tmp/gunicorn_forecast.pid" ]; then
    echo "🧹 Removendo PID file antigo..."
    rm -f /tmp/gunicorn_forecast.pid
fi

echo "✅ Verificações concluídas"
echo ""
echo "📡 Iniciando Gunicorn..."
echo "   Configuração: gunicorn_config.py"
echo "   WSGI: wsgi:application"
echo "   Ambiente: production"
echo ""

# Iniciar Gunicorn com configuração customizada
exec gunicorn \
    --config gunicorn_config.py \
    --log-file logs/gunicorn.log \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    wsgi:application

# Nota: exec substitui o processo atual pelo Gunicorn
# Isso permite que sinais (SIGTERM, etc.) sejam tratados corretamente 