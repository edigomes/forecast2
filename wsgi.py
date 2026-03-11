#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

try:
    from server import app
    
    if os.getenv("ENVIRONMENT") == "production":
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        if not app.config.get('SECRET_KEY'):
            app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'forecast-secret-key-change-in-production')
    
    logger.info(f"Aplicacao inicializada - Ambiente: {os.getenv('ENVIRONMENT', 'development')}")
    
except Exception as e:
    logger.error(f"Erro ao inicializar aplicacao: {e}", exc_info=True)
    raise

application = app

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
