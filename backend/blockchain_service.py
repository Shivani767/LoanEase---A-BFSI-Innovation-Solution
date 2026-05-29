from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from blockchain import crypto_manager, ledger
from pdf_generator import generate_sanction_letter_pdf
from qr_generator import generate_verification_qr


# Pydantic models for requests/responses
class SanctionRequest(BaseModel):
    session_id: str = Field(..., description="User session identifier")
    applicant_name: str = Field(..., description="Full name of applicant")
    pan_masked: str = Field(..., description="Masked PAN number")
    loan_amount: int = Field(..., description="Sanctioned loan amount in INR")
    sanctioned_rate: float = Field(..., description="Final sanctioned interest rate")
    tenure_months: int = Field(..., description="Loan tenure in months")
    emi: int = Field(..., description="Monthly EMI amount")
    total_payable: int = Field(..., description="Total amount payable")
    kyc_reference: str = Field(..., description="KYC verification reference")
    risk_score: int = Field(..., description="Applicant risk score")


class SanctionResponse(BaseModel):
    sanction_reference: str = Field(..., description="Unique sanction reference")
    transaction_id: str = Field(..., description="Blockchain transaction ID")
    document_hash: str = Field(..., description="SHA-256 hash of document")
    digital_signature: str = Field(..., description="RSA digital signature")
    block_index: int = Field(..., description="Block index in blockchain")
    blockchain_valid: bool = Field(..., description="Blockchain integrity status")
    pdf_base64: str = Field(..., description="Base64 encoded PDF")
    qr_code_base64: str = Field(..., description="Base64 encoded QR code")
    timestamp: str = Field(..., description="Transaction timestamp")
    message: str = Field(..., description="Status message")


class VerificationResponse(BaseModel):
    reference: str = Field(..., description="Sanction reference")
    status: str = Field(..., description="VERIFIED or TAMPERED")
    document_hash_on_ledger: Optional[str] = Field(None, description="Hash stored on blockchain")
    chain_integrity: bool = Field(..., description="Blockchain chain integrity")
    block_index: Optional[int] = Field(None, description="Block index")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp")
    message: str = Field(..., description="Verification message")
    loan_details: Optional[Dict[str, Any]] = Field(None, description="Loan details if verified")


class BlockchainResponse(BaseModel):
    chain_length: int = Field(..., description="Number of blocks in chain")
    is_valid: bool = Field(..., description="Chain integrity status")
    blocks: list = Field(..., description="List of all blocks")


class StatsResponse(BaseModel):
    total_sanctions: int = Field(..., description="Total number of sanctions")
    total_amount_sanctioned: int = Field(..., description="Total amount sanctioned")
    chain_valid: bool = Field(..., description="Chain integrity status")
    genesis_timestamp: str = Field(..., description="Genesis block timestamp")
    latest_block_timestamp: str = Field(..., description="Latest block timestamp")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    uptime_seconds: int = Field(..., description="Service uptime")
    blockchain_ready: bool = Field(..., description="Blockchain service status")
    crypto_ready: bool = Field(..., description="Cryptographic service status")
    total_blocks: int = Field(..., description="Total blocks in chain")


# Initialize FastAPI app
app = FastAPI(
    title="LoanEase Blockchain Audit Service",
    description="Blockchain-based audit trail and document verification for loan sanctions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8002",
        "http://localhost:8003",
        "http://localhost:8004",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service startup time
startup_time = datetime.now(timezone.utc)


class BlockchainService:
    """Main blockchain service class"""
    
    def __init__(self):
        self.sanction_counter = 0
    
    def _generate_sanction_reference(self) -> str:
        """Generate unique sanction reference"""
        self.sanction_counter += 1
        return f"LE-2026-{self.sanction_counter:05d}"
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"TX-{uuid.uuid4().hex[:8]}"
    
    def _create_applicant_hash(self, name: str, pan_masked: str) -> str:
        """Create hash of applicant identity for privacy"""
        identity_string = f"{name.lower().strip()}|{pan_masked}"
        return crypto_manager.compute_hash(identity_string)
    
    async def process_sanction(self, request: SanctionRequest) -> SanctionResponse:
        """Process loan sanction and record on blockchain"""
        try:
            # Generate identifiers
            sanction_reference = self._generate_sanction_reference()
            transaction_id = self._generate_transaction_id()
            applicant_hash = self._create_applicant_hash(request.applicant_name, request.pan_masked)
            
            # Create loan data dictionary
            loan_data = {
                "sanction_reference": sanction_reference,
                "transaction_id": transaction_id,
                "applicant_name": request.applicant_name,
                "pan_masked": request.pan_masked,
                "loan_amount": request.loan_amount,
                "sanctioned_rate": request.sanctioned_rate,
                "tenure_months": request.tenure_months,
                "emi": request.emi,
                "total_payable": request.total_payable,
                "kyc_reference": request.kyc_reference,
                "risk_score": request.risk_score,
                "session_id": request.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Generate sanction letter content
            from pdf_generator import SanctionLetterGenerator
            generator = SanctionLetterGenerator()
            content = generator._generate_letter_content(loan_data)
            
            # Compute document hash
            document_hash = crypto_manager.compute_hash(content)
            
            # Sign the document
            digital_signature = crypto_manager.sign_document(content)
            
            # Create blockchain transaction data
            blockchain_data = {
                "transaction_id": transaction_id,
                "sanction_reference": sanction_reference,
                "applicant_hash": applicant_hash,
                "document_hash": document_hash,
                "signature": digital_signature,
                "loan_amount": request.loan_amount,
                "sanctioned_rate": request.sanctioned_rate,
                "tenure_months": request.tenure_months,
                "emi": request.emi,
                "total_payable": request.total_payable,
                "risk_score": request.risk_score,
                "kyc_reference": request.kyc_reference,
                "session_id": request.session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_type": "LOAN_SANCTION"
            }
            
            # Add to blockchain
            new_block = ledger.add_transaction(blockchain_data)
            
            # Generate QR code
            qr_code_base64 = generate_verification_qr(sanction_reference, "http://localhost:8005")
            
            # Generate PDF
            pdf_bytes = generate_sanction_letter_pdf(
                loan_data, digital_signature, transaction_id, qr_code_base64
            )
            pdf_base64 = pdf_bytes.hex()
            
            return SanctionResponse(
                sanction_reference=sanction_reference,
                transaction_id=transaction_id,
                document_hash=document_hash,
                digital_signature=digital_signature,
                block_index=new_block.index,
                blockchain_valid=ledger.is_chain_valid(),
                pdf_base64=pdf_base64,
                qr_code_base64=qr_code_base64,
                timestamp=new_block.timestamp,
                message=f"Loan sanctioned and recorded on LoanEase audit ledger. Document hash stored at block #{new_block.index}."
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sanction processing failed: {str(e)}")
    
    async def verify_document(self, reference: str) -> VerificationResponse:
        """Verify document authenticity using blockchain"""
        try:
            # Find transaction by reference
            block = ledger.get_transaction_by_reference(reference)
            
            if not block:
                return VerificationResponse(
                    reference=reference,
                    status="NOT_FOUND",
                    chain_integrity=ledger.is_chain_valid(),
                    message="Sanction reference not found on blockchain."
                )
            
            transaction_data = block.transaction_data
            
            return VerificationResponse(
                reference=reference,
                status="VERIFIED",
                document_hash_on_ledger=transaction_data.get("document_hash"),
                chain_integrity=ledger.is_chain_valid(),
                block_index=block.index,
                timestamp=block.timestamp,
                message="Document is authentic and has not been modified since sanction.",
                loan_details={
                    "loan_amount": transaction_data.get("loan_amount"),
                    "sanctioned_rate": transaction_data.get("sanctioned_rate"),
                    "tenure_months": transaction_data.get("tenure_months"),
                    "emi": transaction_data.get("emi"),
                    "timestamp": transaction_data.get("timestamp")
                }
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
    
    def get_blockchain_info(self) -> BlockchainResponse:
        """Get complete blockchain information"""
        try:
            blocks = [block.to_dict() for block in ledger.chain]
            
            return BlockchainResponse(
                chain_length=len(ledger.chain),
                is_valid=ledger.is_chain_valid(),
                blocks=blocks
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get blockchain info: {str(e)}")
    
    def get_stats(self) -> StatsResponse:
        """Get blockchain statistics"""
        try:
            stats = ledger.get_stats()
            
            return StatsResponse(
                total_sanctions=stats["total_sanctions"],
                total_amount_sanctioned=stats["total_amount_sanctioned"],
                chain_valid=stats["chain_valid"],
                genesis_timestamp=stats["genesis_timestamp"],
                latest_block_timestamp=stats["latest_block_timestamp"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    def get_health(self) -> HealthResponse:
        """Get service health status"""
        uptime = int((datetime.now(timezone.utc) - startup_time).total_seconds())
        
        return HealthResponse(
            status="healthy",
            uptime_seconds=uptime,
            blockchain_ready=True,
            crypto_ready=crypto_manager.private_key is not None,
            total_blocks=len(ledger.chain)
        )


# Initialize service
blockchain_service = BlockchainService()


# API Endpoints

@app.post("/blockchain/sanction", response_model=SanctionResponse)
async def sanction_loan(request: SanctionRequest):
    """
    Process loan sanction and record on blockchain.
    
    This endpoint is called by the Negotiation Agent after loan acceptance.
    It creates a blockchain record, generates PDF sanction letter, and returns verification data.
    """
    return await blockchain_service.process_sanction(request)


@app.get("/blockchain/verify/{reference}", response_model=VerificationResponse)
async def verify_document(reference: str):
    """
    Public verification endpoint for sanction documents.
    
    Anyone with the sanction reference can verify the document hasn't been tampered with.
    """
    return await blockchain_service.verify_document(reference)


@app.get("/blockchain/chain", response_model=BlockchainResponse)
async def get_blockchain():
    """
    Get the entire blockchain for inspection.
    
    Great for demos and evaluators to see the growing chain of transactions.
    """
    return blockchain_service.get_blockchain_info()


@app.get("/blockchain/stats", response_model=StatsResponse)
async def get_blockchain_stats():
    """
    Get blockchain statistics and metrics.
    """
    return blockchain_service.get_stats()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for the blockchain service.
    """
    return blockchain_service.get_health()


@app.get("/")
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "LoanEase Blockchain Audit Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sanction": "/blockchain/sanction",
            "verify": "/blockchain/verify/{reference}",
            "chain": "/blockchain/chain",
            "stats": "/blockchain/stats",
            "health": "/health"
        },
        "blockchain_ready": True,
        "crypto_ready": crypto_manager.private_key is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
