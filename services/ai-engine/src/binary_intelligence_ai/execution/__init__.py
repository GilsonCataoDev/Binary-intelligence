"""Fronteira de execução; somente o adaptador simulado está habilitado."""

from .gateway import (
    ExecutionGateway, ExecutionIntent, ExecutionMode, ExecutionPreflight, ExecutionReceipt,
    ExecutionProvider, SimulatedExecutionProvider, UnavailableLiveExecutionProvider,
)

__all__ = [
    "ExecutionGateway", "ExecutionIntent", "ExecutionMode", "ExecutionPreflight", "ExecutionReceipt",
    "ExecutionProvider", "SimulatedExecutionProvider", "UnavailableLiveExecutionProvider",
]
