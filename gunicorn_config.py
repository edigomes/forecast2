# Configuração do Gunicorn para Produção
# Arquivo: gunicorn_config.py

import multiprocessing
import os

# Configurações básicas
bind = "0.0.0.0:5000"  # Escutar em todas as interfaces na porta 5000
workers = multiprocessing.cpu_count() * 2 + 1  # Número de workers baseado no CPU

# Configurações de worker
worker_class = "sync"  # Tipo de worker (sync para CPU-bound, gevent para I/O-bound)
worker_connections = 1000  # Conexões por worker
timeout = 30  # Timeout em segundos
keepalive = 2  # Keep-alive connections

# Configurações de processo
max_requests = 1000  # Reiniciar worker após N requests (previne memory leaks)
max_requests_jitter = 100  # Adicionar variação aleatória ao max_requests
preload_app = True  # Carregar app antes de criar workers (mais eficiente)

# Configurações de logs
accesslog = "-"  # Log de acesso no stdout
errorlog = "-"   # Log de erro no stderr
loglevel = "info"  # Nível de log (debug, info, warning, error, critical)
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %D'

# Configurações de segurança
limit_request_line = 4094  # Tamanho máximo da linha de request
limit_request_fields = 100  # Número máximo de headers
limit_request_field_size = 8190  # Tamanho máximo de cada header

# Configurações de performance
worker_tmp_dir = "/dev/shm" if os.path.exists("/dev/shm") else None  # Usar RAM para tmp (Linux)

# PID file (para gerenciamento do processo)
pidfile = "/tmp/gunicorn_forecast.pid"

# User/Group (recomendado para produção - execute como usuário não-root)
# user = "www-data"  # Descomente em produção Linux
# group = "www-data"  # Descomente em produção Linux

# Configurações de reload (apenas para desenvolvimento)
reload = False  # Não usar reload em produção
reload_extra_files = []  # Arquivos extras para monitorar

# Print config na inicialização
print_config = True

# Função de configuração dinâmica
def when_ready(server):
    """Executado quando o servidor está pronto"""
    print("🚀 Servidor Forecast API está pronto!")
    print(f"📡 Escutando em: {bind}")
    print(f"👥 Workers: {workers}")
    print("🌐 CORS habilitado para todas as origens")

def worker_int(worker):
    """Executado quando worker recebe SIGINT"""
    worker.log.info("Worker interrompido pelo usuário")

def pre_fork(server, worker):
    """Executado antes de criar um worker"""
    server.log.info(f"Worker {worker.pid} está sendo criado")

def post_fork(server, worker):
    """Executado após criar um worker"""
    server.log.info(f"Worker {worker.pid} criado com sucesso")

def pre_exec(server):
    """Executado antes de executar a aplicação"""
    server.log.info("Aplicação sendo inicializada...")

def on_exit(server):
    """Executado quando servidor é finalizado"""
    server.log.info("💀 Servidor finalizado")

def on_reload(server):
    """Executado quando servidor é recarregado"""
    server.log.info("🔄 Servidor recarregado")

# Configurações específicas para ambiente
if os.getenv("ENVIRONMENT") == "production":
    # Produção: Mais workers, logs estruturados
    workers = multiprocessing.cpu_count() * 2 + 1
    loglevel = "warning"
    preload_app = True
    max_requests = 2000
    timeout = 60
    
elif os.getenv("ENVIRONMENT") == "staging":
    # Staging: Configuração intermediária
    workers = 2
    loglevel = "info"
    max_requests = 1000
    timeout = 45
    
else:
    # Desenvolvimento/Local: Configuração mais relaxada
    workers = 2
    loglevel = "debug"
    reload = True  # Permitir reload em dev
    timeout = 30 