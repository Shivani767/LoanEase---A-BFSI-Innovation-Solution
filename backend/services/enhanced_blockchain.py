#!/usr/bin/env python3
"""
Production-credible blockchain implementation with Merkle trees and Proof of Work
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from services.merkle_tree import MerkleTree

# Proof of Work difficulty
DIFFICULTY = 3  # Hash must start with "000"

@dataclass
class Block:
    """Enhanced Block with Merkle tree and Proof of Work"""
    index: int
    timestamp: str
    previous_hash: str
    transactions: List[dict]
    merkle_root: str
    nonce: int = 0
    hash: str = ""
    
    def compute_hash(self) -> str:
        """Compute block hash including nonce"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self):
        """Proof of Work mining"""
        target = "0" * DIFFICULTY
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.compute_hash()
    
    def to_dict(self) -> dict:
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "hash": self.hash
        }

class EnhancedBlockchain:
    """Production-credible blockchain ledger"""
    
    def __init__(self):
        self.chain: List[Block] = []
        self.difficulty = DIFFICULTY
        self.create_genesis_block()
    
    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_transactions = [{
            "transaction_type": "GENESIS",
            "message": "LoanEase Blockchain Genesis Block",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "network": "LoanEase Production Credible System v1.0"
        }]
        
        merkle_tree = MerkleTree(genesis_transactions)
        genesis_block = Block(
            index=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            previous_hash="0" * 64,  # 64 zeros
            transactions=genesis_transactions,
            merkle_root=merkle_tree.root
        )
        
        genesis_block.mine_block()
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the most recent block"""
        return self.chain[-1] if self.chain else None
    
    def add_transaction(self, transaction_data: dict) -> Block:
        """Add new transaction to blockchain"""
        latest_block = self.get_latest_block()
        
        # Create new block
        new_block = Block(
            index=latest_block.index + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            previous_hash=latest_block.hash,
            transactions=[transaction_data],
            merkle_root=""  # Will be set after creating Merkle tree
        )
        
        # Create Merkle tree for the transaction
        merkle_tree = MerkleTree([transaction_data])
        new_block.merkle_root = merkle_tree.root
        
        # Mine the block
        new_block.mine_block()
        
        # Add to chain
        self.chain.append(new_block)
        
        return new_block
    
    def amend_sanction(self, original_reference: str, amendment_data: dict, reason: str) -> Block:
        """Create amendment block for existing sanction"""
        amendment = {
            "transaction_type": "AMENDMENT",
            "original_reference": original_reference,
            "amendment_reason": reason,
            "amended_fields": amendment_data,
            "amended_by": "HUMAN_OFFICER",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self.add_transaction(amendment)
    
    def find_transaction_by_reference(self, reference: str) -> Optional[dict]:
        """Find transaction by reference ID"""
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("reference") == reference or tx.get("original_reference") == reference:
                    return {
                        "block": block,
                        "transaction": tx,
                        "found_in_block": block.index
                    }
        return None
    
    def get_merkle_proof(self, reference: str) -> Optional[dict]:
        """Get Merkle proof for transaction"""
        result = self.find_transaction_by_reference(reference)
        if not result:
            return None
        
        block = result["block"]
        transaction = result["transaction"]
        
        # Find transaction index in block
        tx_index = block.transactions.index(transaction)
        
        # Create Merkle tree and get proof
        merkle_tree = MerkleTree(block.transactions)
        proof = merkle_tree.get_proof(tx_index)
        leaf_hash = merkle_tree.get_leaf_hash(tx_index)
        
        return {
            "proof": proof,
            "leaf_hash": leaf_hash,
            "merkle_root": block.merkle_root,
            "block_index": block.index,
            "transaction_index": tx_index
        }
    
    def verify_chain_integrity(self) -> bool:
        """Verify entire blockchain integrity"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check previous hash reference
            if current_block.previous_hash != previous_block.hash:
                return False
            
            # Check proof of work
            if not current_block.hash.startswith("0" * self.difficulty):
                return False
            
            # Check Merkle root
            merkle_tree = MerkleTree(current_block.transactions)
            if merkle_tree.root != current_block.merkle_root:
                return False
        
        return True
    
    def get_chain_summary(self) -> dict:
        """Get blockchain statistics"""
        total_sanctions = sum(1 for block in self.chain 
                             for tx in block.transactions 
                             if tx.get("transaction_type") == "SANCTION")
        total_amendments = sum(1 for block in self.chain 
                              for tx in block.transactions 
                              if tx.get("transaction_type") == "AMENDMENT")
        
        total_amount = sum(tx.get("loan_amount", 0) for block in self.chain 
                          for tx in block.transactions 
                          if tx.get("transaction_type") == "SANCTION")
        
        return {
            "total_blocks": len(self.chain),
            "total_sanctions": total_sanctions,
            "total_amendments": total_amendments,
            "total_amount_sanctioned": total_amount,
            "chain_valid": self.verify_chain_integrity(),
            "proof_of_work_difficulty": self.difficulty,
            "genesis_hash": self.chain[0].hash if self.chain else None,
            "latest_hash": self.chain[-1].hash if self.chain else None
        }
    
    def get_explorer_data(self) -> dict:
        """Get blockchain explorer data"""
        return {
            "chain_summary": self.get_chain_summary(),
            "blocks": [block.to_dict() for block in self.chain]
        }
    
    def validate_document_hash(self, document_content: str, reference: str) -> dict:
        """Validate document hash against blockchain"""
        computed_hash = hashlib.sha256(document_content.encode()).hexdigest()
        
        result = self.find_transaction_by_reference(reference)
        if not result:
            return {
                "valid": False,
                "reason": "Reference not found in blockchain",
                "computed_hash": computed_hash
            }
        
        transaction = result["transaction"]
        stored_hash = transaction.get("document_hash")
        
        if not stored_hash:
            return {
                "valid": False,
                "reason": "No document hash stored for this reference",
                "computed_hash": computed_hash
            }
        
        return {
            "valid": computed_hash == stored_hash,
            "reason": "Hash matches" if computed_hash == stored_hash else "Hash mismatch - document modified",
            "computed_hash": computed_hash,
            "stored_hash": stored_hash,
            "block_data": result["block"].to_dict()
        }

# Global blockchain instance
blockchain = EnhancedBlockchain()
