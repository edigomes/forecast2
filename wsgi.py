#!/usr/bin/env python3
"""
WSGI Entry Point para Gunicorn

Este arquivo é usado pelo Gunicorn como ponto de entrada da aplicação Flask.
Garante que a aplicação seja inicializada corretamente em produção.
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar diretório atual ao path Python
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Configurar logging antes de importar a aplicação
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

try:
    # Importar a aplicação Flask
    from server import app
    
    # Configurações específicas para produção
    if os.getenv("ENVIRONMENT") == "production":
        # Desabilitar debug em produção
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        # Configurar SECRET_KEY se não estiver definida
        if not app.config.get('SECRET_KEY'):
            app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'forecast-secret-key-change-in-production')
            
        logger.info("🏭 Aplicação configurada para PRODUÇÃO")
        
    else:
        logger.info("🛠️  Aplicação configurada para DESENVOLVIMENTO")
    
    # Verificar se CORS está configurado
    logger.info("🌐 CORS configurado - aceita requests de qualquer origem")
    
    # Log das configurações principais
    logger.info(f"📍 Diretório de trabalho: {current_dir}")
    logger.info(f"🔧 Modo Debug: {app.config.get('DEBUG', False)}")
    logger.info(f"🌍 Ambiente: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Testar importações críticas
    try:
        from modelo import ModeloAjustado
        logger.info("✅ Modelo importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar modelo: {e}")
        raise
    
    try:
        from feriados_brasil import FeriadosBrasil
        logger.info("✅ Feriados Brasil importado com sucesso")
    except ImportError as e:
        logger.error(f"❌ Erro ao importar feriados: {e}")
        raise
    
    # Verificar dependências críticas
    try:
        import pandas as pd
        import numpy as np
        import flask_cors
        logger.info("✅ Dependências principais verificadas")
    except ImportError as e:
        logger.error(f"❌ Dependência crítica não encontrada: {e}")
        raise
    
    logger.info("🚀 Aplicação Flask pronta para Gunicorn")
    
except Exception as e:
    logger.error(f"❌ Erro ao inicializar aplicação: {e}")
    logger.error("Stack trace:", exc_info=True)
    raise

# Expor aplicação para Gunicorn
# Gunicorn procura por 'application' por padrão
application = app

# Alias para compatibilidade
if __name__ == "__main__":
    # Este bloco é executado apenas se o arquivo for executado diretamente
    # Em produção, Gunicorn importa este arquivo como módulo
    logger.info("⚠️  Executando diretamente - use Gunicorn em produção")
    app.run(debug=True, host='0.0.0.0', port=5000) 