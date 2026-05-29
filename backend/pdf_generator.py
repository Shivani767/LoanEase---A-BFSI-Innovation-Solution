from __future__ import annotations

import io
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.lib.colors import black, blue, gray
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from blockchain import crypto_manager


class SanctionLetterGenerator:
    """Generates professional sanction letter PDFs with blockchain verification"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for the sanction letter"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=blue
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='HeaderStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=10
        ))
        
        # Reference style
        self.styles.add(ParagraphStyle(
            name='ReferenceStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_LEFT,
            spaceAfter=15
        ))
        
        # Body style
        self.styles.add(ParagraphStyle(
            name='BodyStyle',
            parent=self.styles['Normal'],
            fontSize=11,
            alignment=TA_LEFT,
            spaceAfter=12,
            leftIndent=20
        ))
        
        # Terms style
        self.styles.add(ParagraphStyle(
            name='TermsStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            spaceAfter=8,
            leftIndent=30,
            textColor=gray
        ))
        
        # Signature style
        self.styles.add(ParagraphStyle(
            name='SignatureStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=5
        ))
        
        # Verification style
        self.styles.add(ParagraphStyle(
            name='VerificationStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT,
            spaceAfter=3,
            textColor=gray,
            fontName='Helvetica-Oblique'
        ))
    
    def _format_indian_currency(self, amount: int) -> str:
        """Format amount in Indian currency format"""
        amount_str = str(amount)
        
        # Handle lakhs and crores
        if len(amount_str) <= 3:
            return f"₹{amount_str}"
        elif len(amount_str) <= 5:
            return f"₹{amount_str[:-3]},{amount_str[-3:]}"
        elif len(amount_str) <= 7:
            return f"₹{amount_str[:-5]},{amount_str[-5:-3]},{amount_str[-3:]}"
        else:
            return f"₹{amount_str[:-7]},{amount_str[-7:-5]},{amount_str[-5:-3]},{amount_str[-3:]}"
    
    def _generate_letter_content(self, loan_data: Dict[str, Any]) -> str:
        """Generate the main content of the sanction letter"""
        content = f"""
LOAN SANCTION LETTER

Date: {datetime.now(timezone.utc).strftime('%d %B %Y')}

Sanction Reference Number: {loan_data.get('sanction_reference', 'LE-2026-XXXXX')}

To,
{loan_data.get('applicant_name', 'Applicant Name')}
PAN: {loan_data.get('pan_masked', 'XXXXXX****X')}

Subject: Sanction of Personal Loan

Dear {loan_data.get('applicant_name', 'Applicant')},

We are pleased to inform you that your personal loan application has been approved and sanctioned by LoanEase AI System.

Loan Details:
• Loan Amount: {self._format_indian_currency(loan_data.get('loan_amount', 0))}
• Sanctioned Interest Rate: {loan_data.get('sanctioned_rate', 0)}% per annum
• Loan Tenure: {loan_data.get('tenure_months', 0)} months
• Monthly EMI: {self._format_indian_currency(loan_data.get('emi', 0))}
• Total Payable Amount: {self._format_indian_currency(loan_data.get('total_payable', 0))}

This sanction is based on your credit assessment with a risk score of {loan_data.get('risk_score', 0)}/100 and successful KYC verification (Reference: {loan_data.get('kyc_reference', 'KYC-XXXXX')}).

Terms and Conditions:
1. The sanctioned amount will be disbursed within 2-3 working days.
2. Interest rate is fixed for the entire loan tenure.
3. Prepayment charges apply as per RBI guidelines.
4. Loan is subject to post-disbursement documentation verification.
5. EMI payments will start from the subsequent month of disbursement.

Please acknowledge receipt of this sanction letter and confirm your acceptance of the terms and conditions.

For any queries, please contact our 24/7 customer support.

Yours sincerely,

LoanEase AI System
Digital Loan Processing Unit
"""
        return content.strip()
    
    def generate_sanction_letter(self, loan_data: Dict[str, Any], 
                             signature: str, 
                             tx_hash: str,
                             qr_code_base64: Optional[str] = None) -> bytes:
        """Generate complete sanction letter PDF with blockchain verification"""
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build PDF content
        story = []
        
        # Letter content
        content = self._generate_letter_content(loan_data)
        story.append(Paragraph(content, self.styles['BodyStyle']))
        story.append(Spacer(1, 0.5*cm))
        
        # Digital signature section
        story.append(Paragraph("Digital Authentication", self.styles['CustomTitle']))
        
        signature_short = signature[:32] + "..." if len(signature) > 32 else signature
        story.append(Paragraph(
            f"Digitally signed by LoanEase AI System", 
            self.styles['SignatureStyle']
        ))
        story.append(Paragraph(
            f"Signature: {signature_short}", 
            self.styles['VerificationStyle']
        ))
        story.append(Spacer(1, 0.3*cm))
        
        # Blockchain verification section
        story.append(Paragraph("Blockchain Verification", self.styles['CustomTitle']))
        
        document_hash = crypto_manager.compute_hash(content)
        story.append(Paragraph(
            f"Document Hash (SHA-256): {document_hash[:32]}...", 
            self.styles['VerificationStyle']
        ))
        story.append(Paragraph(
            f"Blockchain Transaction: {loan_data.get('transaction_id', 'TX-XXXXX')}", 
            self.styles['VerificationStyle']
        ))
        story.append(Paragraph(
            f"Verify at: loanease.app/verify/{loan_data.get('sanction_reference', 'LE-2026-XXXXX')}", 
            self.styles['VerificationStyle']
        ))
        
        # Add QR code if provided
        if qr_code_base64:
            story.append(Spacer(1, 0.5*cm))
            qr_data = base64.b64decode(qr_code_base64)
            qr_buffer = io.BytesIO(qr_data)
            
            # Create a simple table with QR code
            qr_table_data = [[
                Paragraph("", self.styles['Normal']),  # Empty left cell
                Paragraph("Scan to Verify", self.styles['Normal'])  # QR code label
            ]]
            
            qr_table = Table(qr_table_data, colWidths=[10*cm, 4*cm])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(qr_table)
        
        # Add footer
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            "This is a computer-generated document. No signature is required.",
            self.styles['VerificationStyle']
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def generate_simple_sanction_letter(self, loan_data: Dict[str, Any], 
                                    signature: str, 
                                    tx_hash: str) -> bytes:
        """Generate a simpler version for testing"""
        return self.generate_sanction_letter(loan_data, signature, tx_hash)


class PDFCanvas:
    """Helper class for advanced PDF canvas operations"""
    
    @staticmethod
    def create_header_footer(canvas, doc):
        """Create header and footer for each page"""
        canvas.saveState()
        
        # Header
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(blue)
        canvas.drawString(2*cm, A4[1] - 2*cm, "LoanEase - AI Powered Digital Lending")
        
        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(gray)
        canvas.drawString(2*cm, 2*cm, f"Page {doc.page}")
        canvas.drawString(A4[0] - 5*cm, 2*cm, "Confidential & Proprietary")
        
        canvas.restoreState()


# Utility function for easy usage
def generate_sanction_letter_pdf(loan_data: Dict[str, Any], 
                              signature: str, 
                              tx_hash: str,
                              qr_code_base64: Optional[str] = None) -> bytes:
    """Convenience function to generate sanction letter PDF"""
    generator = SanctionLetterGenerator()
    return generator.generate_sanction_letter(loan_data, signature, tx_hash, qr_code_base64)
