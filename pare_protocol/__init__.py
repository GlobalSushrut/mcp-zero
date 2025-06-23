"""
PARE (Protocol for Agent Retrograde Evolution) Network Chain Protocol
Provides advanced agent training capabilities for MCP-ZERO
"""

from .chain_protocol import PAREChainProtocol
from .training_block import TrainingBlock
from .sparse_matrix import NonEuclideanSparseMatrix
from .heap_consensus import FactorialVotingConsensus
from .retrograde_learning import RetrogradeLearner

__version__ = "0.1.0"
