"""
Interface base para provedores de status e dados.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseStatusProvider(ABC):
    @abstractmethod
    def fetch(self) -> Dict[str, Any]:
        """
        Executa a coleta de dados de forma síncrona.
        Deve retornar um dicionário contendo pelo menos:
        - "items": Lista de itens coletados
        - "new_items": Lista de novos itens desde a última checagem
        - "error": Mensagem de erro ou None
        """
        pass
