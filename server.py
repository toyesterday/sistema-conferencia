"""
Servidor WSGI para o ambiente de demonstração
Sistema de Conferência para Pré-Impressão - Fase 4
"""

from waitress import serve
import os
import logging
from src.main import app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

if __name__ == '__main__':
    # Configurar host e porta
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 5000))
    
    # Informações de inicialização
    logger.info(f"Iniciando servidor Waitress em {host}:{port}")
    logger.info("Ambiente de demonstração do Sistema de Conferência para Pré-Impressão - Fase 4")
    
    # Iniciar servidor Waitress
    serve(app, host=host, port=port, threads=4)
