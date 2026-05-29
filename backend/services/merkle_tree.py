#!/usr/bin/env python3
"""
Production-credible Merkle Tree implementation
Used for transaction verification in LoanEase blockchain
"""

import hashlib
import json
from typing import List, Optional, Tuple

class MerkleTree:
    """Merkle Tree implementation for transaction verification"""
    
    def __init__(self, transactions: List[dict]):
        self.transactions = transactions
        self.leaves = [
            self._hash(json.dumps(tx, sort_keys=True))
            for tx in transactions
        ]
        self.root = self._build_tree(self.leaves)
    
    def _hash(self, data: str) -> str:
        """SHA-256 hash function"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _build_tree(self, nodes: List[str]) -> str:
        """Build Merkle tree from bottom up"""
        if len(nodes) == 0:
            return self._hash("")
        if len(nodes) == 1:
            return nodes[0]
        
        # Duplicate last node if odd count
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        
        next_level = []
        for i in range(0, len(nodes), 2):
            combined = nodes[i] + nodes[i+1]
            next_level.append(self._hash(combined))
        
        return self._build_tree(next_level)
    
    def get_proof(self, transaction_index: int) -> List[dict]:
        """
        Generate Merkle proof for a specific transaction
        Returns list of sibling hashes and their positions
        """
        if transaction_index >= len(self.leaves):
            raise IndexError("Transaction index out of range")
        
        proof = []
        current_level = self.leaves
        current_index = transaction_index
        
        while len(current_level) > 1:
            # Determine if current node is left or right child
            is_right_child = current_index % 2 == 1
            
            # Get sibling index
            sibling_index = current_index - 1 if is_right_child else current_index + 1
            
            # Get sibling hash (handle odd number of nodes)
            if sibling_index < len(current_level):
                sibling_hash = current_level[sibling_index]
                proof.append({
                    "hash": sibling_hash,
                    "position": "left" if is_right_child else "right"
                })
            elif len(current_level) % 2 == 1:
                # Odd number of nodes - last node is duplicated
                proof.append({
                    "hash": current_level[current_index],
                    "position": "right" if is_right_child else "left"
                })
            
            # Move to next level
            current_index = current_index // 2
            current_level = self._build_next_level(current_level)
        
        return proof
    
    def _build_next_level(self, nodes: List[str]) -> List[str]:
        """Build next level of tree"""
        if len(nodes) <= 1:
            return []
        
        # Duplicate last node if odd count
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        
        next_level = []
        for i in range(0, len(nodes), 2):
            combined = nodes[i] + nodes[i+1]
            next_level.append(self._hash(combined))
        
        return next_level
    
    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[dict], root: str) -> bool:
        """
        Verify Merkle proof
        Returns True if leaf_hash is part of tree with given root
        """
        current_hash = leaf_hash
        
        for proof_element in proof:
            sibling_hash = proof_element["hash"]
            position = proof_element["position"]
            
            if position == "left":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root
    
    def get_leaf_hash(self, transaction_index: int) -> str:
        """Get hash of specific transaction"""
        if transaction_index >= len(self.leaves):
            raise IndexError("Transaction index out of range")
        return self.leaves[transaction_index]
    
    def get_tree_size(self) -> int:
        """Get number of transactions in tree"""
        return len(self.leaves)
    
    def to_dict(self) -> dict:
        """Serialize Merkle tree to dictionary"""
        return {
            "root": self.root,
            "leaf_count": len(self.leaves),
            "transactions": self.transactions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MerkleTree':
        """Deserialize Merkle tree from dictionary"""
        return cls(data["transactions"])
