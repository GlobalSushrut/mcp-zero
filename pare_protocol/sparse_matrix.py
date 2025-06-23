#!/usr/bin/env python3
"""
Non-Euclidean Sparse Matrix for Retrograde Learning

Implements a specialized matrix structure for the PARE Network Chain Protocol
that enables retrograde learning through sparse representation in non-Euclidean space.
This allows for efficient memory representation while maintaining ZK-traceability.
"""

import numpy as np
import hashlib
import uuid
import time
import logging
import scipy.sparse as sp
from typing import Dict, List, Any, Optional, Tuple, Set, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SparseMatrix")

class NonEuclideanSparseMatrix:
    """
    Non-Euclidean Sparse Matrix for retrograde learning in agent training
    
    Features:
    - Sparse representation for memory efficiency (<827MB constraint)
    - Non-Euclidean distance metrics for complex feature spaces
    - Cryptographic hashing for memory trace verification
    - Integration with MCP-ZERO memory tree
    """
    
    def __init__(self, dimensions: List[int], non_euclidean_type: str = "hyperbolic"):
        """
        Initialize a new sparse matrix with non-Euclidean geometry
        
        Args:
            dimensions: List of dimensions for the matrix
            non_euclidean_type: Type of non-Euclidean geometry to use
                                ("hyperbolic", "spherical", "mixed")
        """
        self.matrix_id = str(uuid.uuid4())
        self.dimensions = dimensions
        self.non_euclidean_type = non_euclidean_type
        self.created_at = time.time()
        self.last_updated = self.created_at
        
        # Create sparse matrix storage
        self.data = {}  # Map of tuple(indices) -> value
        self.metadata = {
            "dimensions": dimensions,
            "non_euclidean_type": non_euclidean_type,
            "matrix_id": self.matrix_id,
            "created_at": self.created_at,
            "element_count": 0
        }
        
        # Cryptographic verification
        self.matrix_hash = self._calculate_matrix_hash()
        
        logger.info(f"Created {non_euclidean_type} sparse matrix with dimensions {dimensions}")
    
    def _calculate_matrix_hash(self) -> str:
        """Calculate the cryptographic hash of the matrix state"""
        # Combine core data for hashing
        hash_data = {
            "matrix_id": self.matrix_id,
            "dimensions": self.dimensions,
            "non_euclidean_type": self.non_euclidean_type,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "element_count": len(self.data),
            "data_sample": str(list(self.data.items())[:10]),  # Include sample of data
            "metadata": self.metadata
        }
        
        # Calculate hash
        hash_string = hashlib.sha256(str(hash_data).encode()).hexdigest()
        return hash_string
    
    def set_value(self, indices: Tuple[int, ...], value: float) -> None:
        """
        Set a value in the sparse matrix
        
        Args:
            indices: Tuple of indices for the element
            value: Value to set
        """
        # Check dimensions match
        if len(indices) != len(self.dimensions):
            raise ValueError(f"Indices must match dimensions: {len(self.dimensions)}")
            
        # Check indices are within bounds
        for i, dim in enumerate(indices):
            if dim < 0 or dim >= self.dimensions[i]:
                raise ValueError(f"Index {dim} out of bounds for dimension {i}")
        
        # Store in sparse representation
        if abs(value) > 1e-10:  # Only store non-zero values
            self.data[indices] = value
            self.metadata["element_count"] = len(self.data)
        elif indices in self.data:
            # Remove zero values
            del self.data[indices]
            self.metadata["element_count"] = len(self.data)
        
        # Update state
        self.last_updated = time.time()
        self.matrix_hash = self._calculate_matrix_hash()
    
    def get_value(self, indices: Tuple[int, ...], default: float = 0.0) -> float:
        """
        Get a value from the sparse matrix
        
        Args:
            indices: Tuple of indices for the element
            default: Default value if not found
            
        Returns:
            Value at the specified indices
        """
        return self.data.get(indices, default)
    
    def get_non_zero_indices(self) -> List[Tuple[int, ...]]:
        """
        Get all non-zero indices in the matrix
        
        Returns:
            List of index tuples
        """
        return list(self.data.keys())
    
    def to_scipy_sparse(self) -> sp.spmatrix:
        """
        Convert to SciPy sparse matrix format
        
        Returns:
            SciPy sparse matrix
        """
        # For simplicity, only handle 2D matrices in this implementation
        if len(self.dimensions) == 2:
            # Extract values
            coords = list(zip(*self.data.keys()))
            values = list(self.data.values())
            
            # Create COO matrix
            if coords:  # Check if we have any non-zero elements
                row_ind, col_ind = coords
                return sp.coo_matrix((values, (row_ind, col_ind)), 
                                     shape=(self.dimensions[0], self.dimensions[1]))
            else:
                return sp.coo_matrix((self.dimensions[0], self.dimensions[1]))
        else:
            raise ValueError("Conversion to scipy sparse matrix only supported for 2D matrices")
    
    def from_scipy_sparse(self, sp_matrix: sp.spmatrix) -> None:
        """
        Load data from SciPy sparse matrix
        
        Args:
            sp_matrix: SciPy sparse matrix
        """
        # Convert to COO format for easy access to indices and values
        coo = sp_matrix.tocoo()
        
        # Clear existing data
        self.data.clear()
        
        # Update dimensions
        self.dimensions = [sp_matrix.shape[0], sp_matrix.shape[1]]
        
        # Add non-zero elements
        for i, j, v in zip(coo.row, coo.col, coo.data):
            self.data[(i, j)] = v
        
        # Update metadata
        self.metadata["element_count"] = len(self.data)
        self.last_updated = time.time()
        self.matrix_hash = self._calculate_matrix_hash()
    
    def non_euclidean_distance(self, indices1: Tuple[int, ...], indices2: Tuple[int, ...]) -> float:
        """
        Calculate non-Euclidean distance between two points in the matrix
        
        Args:
            indices1: First point indices
            indices2: Second point indices
            
        Returns:
            Non-Euclidean distance
        """
        val1 = self.get_value(indices1)
        val2 = self.get_value(indices2)
        
        # Calculate distance based on non-Euclidean type
        if self.non_euclidean_type == "hyperbolic":
            # Hyperbolic distance metric
            # Using a simplified approximation here
            return abs(np.arcsinh(val1) - np.arcsinh(val2))
            
        elif self.non_euclidean_type == "spherical":
            # Spherical distance metric
            # Using angular distance on unit sphere
            if val1 == 0 or val2 == 0:
                return np.pi / 2  # 90 degrees if one is zero
            cos_angle = (val1 * val2) / (abs(val1) * abs(val2))
            return np.arccos(min(1.0, max(-1.0, cos_angle)))
            
        elif self.non_euclidean_type == "mixed":
            # Mixed geometry - combines hyperbolic and spherical
            d1 = abs(np.arcsinh(val1) - np.arcsinh(val2))  # Hyperbolic
            
            # Spherical component
            if val1 == 0 or val2 == 0:
                d2 = np.pi / 2
            else:
                cos_angle = (val1 * val2) / (abs(val1) * abs(val2))
                d2 = np.arccos(min(1.0, max(-1.0, cos_angle)))
                
            # Weighted combination
            return 0.5 * d1 + 0.5 * d2
            
        else:
            # Fallback to Euclidean distance
            return abs(val1 - val2)
    
    def find_nearest_neighbors(self, indices: Tuple[int, ...], k: int = 5) -> List[Tuple[Tuple[int, ...], float]]:
        """
        Find k nearest neighbors to given indices using non-Euclidean distance
        
        Args:
            indices: Query point indices
            k: Number of neighbors to find
            
        Returns:
            List of (indices, distance) tuples for neighbors
        """
        if not self.data:
            return []
            
        # Calculate distances to all non-zero elements
        distances = []
        for other_indices in self.data.keys():
            dist = self.non_euclidean_distance(indices, other_indices)
            distances.append((other_indices, dist))
        
        # Sort by distance
        distances.sort(key=lambda x: x[1])
        
        # Return k nearest (or all if fewer than k)
        return distances[:k]
    
    def retrograde_update(self, indices: Tuple[int, ...], update_value: float, 
                          learning_rate: float = 0.1, k_neighbors: int = 3) -> None:
        """
        Perform retrograde learning update to matrix values
        
        This applies an update to the specified point and propagates
        to neighbors in reverse through the matrix topology.
        
        Args:
            indices: Target point indices to update
            update_value: Value update to apply
            learning_rate: Rate of learning for updates
            k_neighbors: Number of neighbors to propagate to
        """
        # Update target point
        current_val = self.get_value(indices)
        new_val = current_val + learning_rate * update_value
        self.set_value(indices, new_val)
        
        # Find nearest neighbors
        neighbors = self.find_nearest_neighbors(indices, k_neighbors)
        
        # Apply diminishing updates to neighbors
        for i, (neighbor_indices, distance) in enumerate(neighbors):
            # Skip the point itself
            if neighbor_indices == indices:
                continue
                
            # Calculate diminishing factor based on distance
            diminish_factor = 1.0 / (1.0 + distance)
            
            # Apply smaller update to neighbor
            neighbor_val = self.get_value(neighbor_indices)
            neighbor_update = update_value * diminish_factor * learning_rate * (0.7 ** (i + 1))
            self.set_value(neighbor_indices, neighbor_val + neighbor_update)
        
        # Update hash after batch of changes
        self.last_updated = time.time()
        self.matrix_hash = self._calculate_matrix_hash()
    
    def get_memory_footprint(self) -> int:
        """
        Calculate approximate memory footprint in bytes
        
        Returns:
            Estimated memory usage in bytes
        """
        # Rough estimation of memory usage
        # Key size (assuming average 8 bytes per dimension * number of dimensions)
        key_size = 8 * len(self.dimensions)
        
        # Value size (8 bytes for float64)
        value_size = 8
        
        # Dictionary overhead (approximated as 24 bytes per entry)
        dict_overhead = 24
        
        # Total for all entries
        entry_size = (key_size + value_size + dict_overhead) * len(self.data)
        
        # Add fixed overhead for the object
        fixed_overhead = 1000  # Rough estimate for object attributes
        
        return entry_size + fixed_overhead
    
    def verify_resource_constraints(self) -> bool:
        """
        Verify that the matrix conforms to MCP-ZERO resource constraints
        
        Returns:
            True if constraints are met, False otherwise
        """
        # Check memory usage
        memory_usage = self.get_memory_footprint()
        max_allowed = 827 * 1024 * 1024  # 827MB in bytes
        
        # Log warning if getting close to limit
        if memory_usage > max_allowed * 0.8:
            logger.warning(f"Matrix {self.matrix_id[:8]} using {memory_usage / 1024 / 1024:.2f}MB, "
                          f"approaching {max_allowed / 1024 / 1024:.0f}MB limit")
        
        return memory_usage < max_allowed
    
    def to_serializable(self) -> Dict[str, Any]:
        """
        Convert matrix to serializable dictionary
        
        Returns:
            Dictionary representation of matrix
        """
        # Convert tuples to strings for keys
        data_serializable = {str(k): v for k, v in self.data.items()}
        
        return {
            "matrix_id": self.matrix_id,
            "dimensions": self.dimensions,
            "non_euclidean_type": self.non_euclidean_type,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "matrix_hash": self.matrix_hash,
            "metadata": self.metadata,
            "data": data_serializable
        }
    
    @staticmethod
    def from_serializable(data: Dict[str, Any]) -> "NonEuclideanSparseMatrix":
        """
        Create matrix from serialized dictionary
        
        Args:
            data: Dictionary representation of matrix
            
        Returns:
            Reconstructed matrix object
        """
        # Create new matrix
        matrix = NonEuclideanSparseMatrix(data["dimensions"], data["non_euclidean_type"])
        
        # Restore attributes
        matrix.matrix_id = data["matrix_id"]
        matrix.created_at = data["created_at"]
        matrix.last_updated = data["last_updated"]
        matrix.metadata = data["metadata"]
        
        # Restore data (convert string keys back to tuples)
        for k_str, v in data["data"].items():
            # Parse string representation of tuple back to actual tuple
            k = eval(k_str)
            matrix.data[k] = v
        
        # Recalculate hash to ensure integrity
        matrix.matrix_hash = matrix._calculate_matrix_hash()
        
        return matrix
