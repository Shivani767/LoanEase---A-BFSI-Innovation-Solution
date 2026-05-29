#!/usr/bin/env python3
"""
Enhanced Blockchain Agent with Merkle Trees, Proof of Work, and Verification Dashboard
"""

import logging
import os
import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from core.session import session_store
from services.pdf_generator import generate_sanction_letter
from services.enhanced_blockchain import blockchain
from services.merkle_tree import MerkleTree
from core.config import settings

logger = logging.getLogger("loanease.blockchain")

router = APIRouter()

# Global cryptographic keys
_private_key = None
_public_key = None

# Pydantic models
class SanctionRequest(BaseModel):
    session_id: str
    applicant_name: str
    pan_number: str
    loan_amount: float
    interest_rate: float
    tenure_years: int

class SanctionResponse(BaseModel):
    transaction_id: str
    block_hash: str
    qr_code_url: str
    verification_url: str
    pdf_download_url: str

class VerifyRequest(BaseModel):
    reference_id: str

class VerifyResponse(BaseModel):
    valid: bool
    block_data: Dict[str, Any]
    verification_details: Dict[str, Any]

class ValidateRequest(BaseModel):
    document_content: str
    reference: str

class AmendmentRequest(BaseModel):
    original_reference: str
    amendment_data: Dict[str, Any]
    reason: str

def load_keys():
    """Load or generate RSA keys"""
    global _private_key, _public_key
    
    keys_dir = "keys"
    private_key_path = os.path.join(keys_dir, "private_key.pem")
    public_key_path = os.path.join(keys_dir, "public_key.pem")
    
    os.makedirs(keys_dir, exist_ok=True)
    
    if os.path.exists(private_key_path) and os.path.exists(public_key_path):
        # Load existing keys
        with open(private_key_path, "rb") as f:
            _private_key = serialization.load_pem_private_key(
                f.read(), password=None
            )
        with open(public_key_path, "rb") as f:
            _public_key = serialization.load_pem_public_key(f.read())
    else:
        # Generate new keys
        _private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        _public_key = _private_key.public_key()
        
        # Save keys
        with open(private_key_path, "wb") as f:
            f.write(_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        with open(public_key_path, "wb") as f:
            f.write(_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
    
    logger.info("RSA keys loaded successfully")

def sign_data(data: str) -> str:
    """Sign data with RSA private key"""
    signature = _private_key.sign(
        data.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature.hex()

def verify_signature(data: str, signature_hex: str) -> bool:
    """Verify RSA signature"""
    try:
        signature = bytes.fromhex(signature_hex)
        _public_key.verify(
            signature,
            data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False

def ledger_ready() -> bool:
    """Check if blockchain ledger is ready"""
    return blockchain is not None and len(blockchain.chain) > 0

def init_ledger():
    """Initialize blockchain ledger"""
    global blockchain
    load_keys()
    logger.info("Enhanced blockchain ledger initialized")

@router.post("/sanction", response_model=SanctionResponse)
async def create_sanction_letter(request: SanctionRequest):
    """Create blockchain-verified sanction letter with enhanced security"""
    try:
        # Get session data
        session = session_store.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate reference ID
        timestamp = datetime.now(timezone.utc)
        reference = f"LE-{timestamp.year}-{str(len(blockchain.chain) + 1).zfill(5)}"
        
        # Generate PDF
        pdf_content = generate_sanction_letter(
            request.applicant_name,
            request.pan_number,
            request.loan_amount,
            request.interest_rate,
            request.tenure_years,
            reference
        )
        
        # Calculate document hash
        document_hash = hashlib.sha256(pdf_content).hexdigest()
        
        # Create sanction transaction
        sanction_data = {
            "transaction_type": "SANCTION",
            "reference": reference,
            "applicant_name": request.applicant_name,
            "pan_number": request.pan_number,
            "loan_amount": request.loan_amount,
            "interest_rate": request.interest_rate,
            "tenure_years": request.tenure_years,
            "document_hash": document_hash,
            "sanction_date": timestamp.strftime("%d %b %Y, %H:%M IST"),
            "created_at": timestamp.isoformat(),
            "session_id": request.session_id
        }
        
        # Add to blockchain
        block = blockchain.add_transaction(sanction_data)
        
        # Sign the document hash
        signature = sign_data(document_hash)
        
        # Update transaction with signature
        block.transactions[-1]["digital_signature"] = signature
        
        # Generate URLs
        base_url = "http://localhost:8000"
        verification_url = f"{base_url}/blockchain/verify/{reference}"
        qr_code_url = f"{base_url}/blockchain/qr/{reference}"
        pdf_download_url = f"{base_url}/blockchain/download/{reference}"
        
        # Store PDF in session
        session_store.update(request.session_id, {
            "sanction_letter_pdf": pdf_content,
            "sanction_reference": reference,
            "block_hash": block.hash
        })
        
        logger.info(f"Sanction letter created: {reference} in block #{block.index}")
        
        return SanctionResponse(
            transaction_id=reference,
            block_hash=block.hash,
            qr_code_url=qr_code_url,
            verification_url=verification_url,
            pdf_download_url=pdf_download_url
        )
        
    except Exception as e:
        logger.error(f"Sanction letter creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sanction letter creation failed: {str(e)}")

@router.get("/verify/{reference}")
async def verify_document_page(reference: str):
    """Public verification dashboard page"""
    try:
        # Find transaction
        result = blockchain.find_transaction_by_reference(reference)
        
        if not result:
            return HTMLResponse(content="""
                <script>
                    window.location.href = '/blockchain/verify-page?ref=' + encodeURIComponent('{ref}') + '&status=not_found';
                </script>
            """.format(ref=reference))
        
        block = result["block"]
        transaction = result["transaction"]
        
        # Prepare verification data
        verification_data = {
            "status": "valid",
            "reference": reference,
            "applicant_name": transaction.get("applicant_name", "N/A"),
            "loan_amount": transaction.get("loan_amount"),
            "sanction_date": transaction.get("sanction_date"),
            "interest_rate": transaction.get("interest_rate"),
            "block_index": block.index,
            "block_hash": block.hash,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "document_hash": transaction.get("document_hash"),
            "nonce": block.nonce,
            "chain_length": len(blockchain.chain)
        }
        
        # Return HTML with embedded data
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Document Verification</title>
            <script>
                window.verificationData = {json.dumps(verification_data)};
                window.location.href = '/blockchain/verify-page?ref=' + encodeURIComponent('{reference}');
            </script>
        </head>
        <body>
            <p>Redirecting to verification page...</p>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Verification page error: {str(e)}")
        return HTMLResponse(content=f"""
            <script>
                window.location.href = '/blockchain/verify-page?ref=' + encodeURIComponent('{ref}') + '&status=error';
            </script>
        """.format(ref=reference))

@router.get("/verify-page")
async def verification_dashboard(ref: str = None, status: str = None):
    """Serve verification dashboard template"""
    try:
        # Read HTML template
        template_path = os.path.join("templates", "verification.html")
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # If we have verification data from previous step, embed it
        if ref and not status:
            result = blockchain.find_transaction_by_reference(ref)
            if result:
                block = result["block"]
                transaction = result["transaction"]
                
                # Create verification data object for JavaScript
                verification_data = {
                    "success": True,
                    "status": "valid",
                    "reference": ref,
                    "applicant_name": transaction.get("applicant_name", "N/A"),
                    "loan_amount": transaction.get("loan_amount"),
                    "sanction_date": transaction.get("sanction_date"),
                    "interest_rate": transaction.get("interest_rate"),
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "previous_hash": block.previous_hash,
                    "merkle_root": block.merkle_root,
                    "document_hash": transaction.get("document_hash"),
                    "nonce": block.nonce,
                    "chain_length": len(blockchain.chain)
                }
                
                # Add verification data to template
                template_content = template_content.replace(
                    "<script>",
                    f"<script>window.verificationData = {json.dumps(verification_data)};"
                )
        
        return HTMLResponse(content=template_content)
        
    except Exception as e:
        logger.error(f"Verification dashboard error: {str(e)}")
        return HTMLResponse(content=f"<h1>Verification Error</h1><p>{str(e)}</p>")

@router.get("/explorer")
async def blockchain_explorer():
    """Blockchain explorer endpoint - Etherscan-like view"""
    try:
        explorer_data = blockchain.get_explorer_data()
        return explorer_data
    except Exception as e:
        logger.error(f"Blockchain explorer error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Explorer error: {str(e)}")

@router.post("/validate")
async def validate_document(request: ValidateRequest):
    """Validate document hash against blockchain"""
    try:
        validation_result = blockchain.validate_document_hash(
            request.document_content, 
            request.reference
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Document validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

@router.post("/amend")
async def amend_sanction(request: AmendmentRequest):
    """Create amendment for existing sanction"""
    try:
        # Verify original exists
        original_result = blockchain.find_transaction_by_reference(request.original_reference)
        if not original_result:
            raise HTTPException(status_code=404, detail="Original sanction not found")
        
        # Create amendment block
        amendment_block = blockchain.amend_sanction(
            request.original_reference,
            request.amendment_data,
            request.reason
        )
        
        logger.info(f"Amendment created for {request.original_reference} in block #{amendment_block.index}")
        
        return {
            "success": True,
            "amendment_block": amendment_block.to_dict(),
            "original_reference": request.original_reference,
            "amendment_reason": request.reason
        }
        
    except Exception as e:
        logger.error(f"Amendment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Amendment error: {str(e)}")

@router.get("/merkle-proof/{reference}")
async def get_merkle_proof(reference: str):
    """Get Merkle proof for transaction verification"""
    try:
        proof_data = blockchain.get_merkle_proof(reference)
        
        if not proof_data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Verify the proof
        is_valid = MerkleTree.verify_proof(
            proof_data["leaf_hash"],
            proof_data["proof"],
            proof_data["merkle_root"]
        )
        
        return {
            "proof": proof_data,
            "verification": is_valid
        }
        
    except Exception as e:
        logger.error(f"Merkle proof error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Merkle proof error: {str(e)}")

@router.get("/chain/validate")
async def validate_chain():
    """Validate entire blockchain integrity"""
    try:
        is_valid = blockchain.verify_chain_integrity()
        
        return {
            "chain_valid": is_valid,
            "chain_length": len(blockchain.chain),
            "difficulty": blockchain.difficulty,
            "latest_block": blockchain.get_latest_block().to_dict() if blockchain.chain else None
        }
        
    except Exception as e:
        logger.error(f"Chain validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chain validation error: {str(e)}")

@router.get("/download/{reference}")
async def download_sanction_letter(reference: str):
    """Download original sanction letter PDF"""
    try:
        # Find transaction
        result = blockchain.find_transaction_by_reference(reference)
        if not result:
            raise HTTPException(status_code=404, detail="Reference not found")
        
        transaction = result["transaction"]
        session_id = transaction.get("session_id")
        
        if session_id:
            session = session_store.get(session_id)
            if session and "sanction_letter_pdf" in session:
                from fastapi.responses import Response
                return Response(
                    content=session["sanction_letter_pdf"],
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={reference}.pdf"}
                )
        
        # Generate PDF if not in session
        pdf_content = generate_sanction_letter(
            transaction.get("applicant_name", "N/A"),
            transaction.get("pan_number", "N/A"),
            transaction.get("loan_amount", 0),
            transaction.get("interest_rate", 0),
            transaction.get("tenure_years", 0),
            reference
        )
        
        from fastapi.responses import Response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={reference}.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

@router.get("/health")
async def blockchain_health():
    """Blockchain agent health check"""
    return {
        "status": "healthy",
        "ledger_ready": ledger_ready(),
        "chain_length": len(blockchain.chain) if blockchain else 0,
        "keys_loaded": _private_key is not None and _public_key is not None,
        "difficulty": blockchain.difficulty if blockchain else 0,
        "chain_valid": blockchain.verify_chain_integrity() if blockchain else False
    }
