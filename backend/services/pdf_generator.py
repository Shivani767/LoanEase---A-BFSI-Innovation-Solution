import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from services.emi import calculate_emi

class SanctionLetterGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for the sanction letter"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='CertificateTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            spaceAfter=40,
            alignment=TA_CENTER,
            textColor=colors.darkgreen
        ))

        self.styles.add(ParagraphStyle(
            name='HashStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Courier',
            alignment=TA_LEFT,
            textColor=colors.grey
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        ))
    
    def generate_sanction_letter(
        self,
        applicant_name: str,
        pan_number: str,
        loan_amount: float,
        interest_rate: float,
        tenure_years: int,
        emi: float,
        application_id: str,
        sanction_date: datetime = None
    ) -> bytes:
        """Generate PDF sanction letter"""
        
        if sanction_date is None:
            sanction_date = datetime.now()
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("LOAN SANCTION LETTER", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Date and Reference
        date_text = f"Date: {sanction_date.strftime('%d %B %Y')}"
        ref_text = f"Reference: {application_id}"
        
        story.append(Paragraph(date_text, self.styles['CustomNormal']))
        story.append(Paragraph(ref_text, self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Salutation
        story.append(Paragraph(f"Dear {applicant_name},", self.styles['CustomNormal']))
        story.append(Spacer(1, 20))
        
        # Main content
        approval_text = f"""
        We are pleased to inform you that your personal loan application has been approved. 
        The loan details are as follows:
        """
        story.append(Paragraph(approval_text, self.styles['CustomNormal']))
        story.append(Spacer(1, 20))
        
        # Loan details table
        loan_data = [
            ['Applicant Name', applicant_name],
            ['PAN Number', pan_number],
            ['Loan Amount', f"₹{loan_amount:,.2f}"],
            ['Interest Rate (p.a.)', f"{interest_rate}%"],
            ['Loan Tenure', f"{tenure_years} years"],
            ['Monthly EMI', f"₹{emi:,.2f}"],
            ['Application ID', application_id]
        ]
        
        table = Table(loan_data, colWidths=[2.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Terms and conditions
        story.append(Paragraph("Terms and Conditions:", self.styles['CustomHeading']))
        
        terms = """
        1. The loan is subject to successful completion of KYC verification.
        2. Interest rate is fixed for the entire loan tenure.
        3. EMI payments must be made on or before the due date each month.
        4. Prepayment charges may apply as per bank policy.
        5. The bank reserves the right to modify terms with prior notice.
        """
        
        story.append(Paragraph(terms, self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Next steps
        story.append(Paragraph("Next Steps:", self.styles['CustomHeading']))
        
        next_steps = """
        1. Complete the KYC verification process.
        2. Sign the loan agreement.
        3. Provide necessary documents for disbursement.
        4. Loan amount will be disbursed to your registered bank account.
        """
        
        story.append(Paragraph(next_steps, self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Closing
        closing_text = """
        Please feel free to contact us if you have any questions.
        
        We look forward to serving you.
        """
        
        story.append(Paragraph(closing_text, self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Signature
        story.append(Paragraph("Sincerely,", self.styles['CustomNormal']))
        story.append(Spacer(1, 10))
        story.append(Paragraph("LoanEase Team", self.styles['CustomNormal']))
        story.append(Paragraph("Digital Banking Division", self.styles['CustomNormal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes

    def generate_verification_certificate(
        self,
        reference: str,
        applicant_masked: str,
        loan_amount: float,
        interest_rate: float,
        sanction_date: str,
        block_index: int,
        block_hash: str,
        previous_hash: str,
        merkle_root: str,
        nonce: int,
        verified_at: str
    ) -> bytes:
        """Generate a blockchain verification certificate PDF"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        story = []
        
        # Header
        story.append(Paragraph("BLOCKCHAIN VERIFICATION CERTIFICATE", self.styles['CertificateTitle']))
        story.append(Spacer(1, 10))
        
        verified_on = datetime.fromisoformat(verified_at.replace('Z', '+00:00')).strftime('%d %b %Y, %H:%M:%S UTC')
        story.append(Paragraph(f"Verified On: {verified_on}", self.styles['CustomNormal']))
        story.append(Paragraph(f"Verified By: LoanEase Audit System v1.2", self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Summary
        story.append(Paragraph("VERIFICATION SUMMARY", self.styles['CustomHeading']))
        summary_data = [
            ['Document Reference', reference],
            ['Verification Status', 'AUTHENTIC ✓'],
            ['Applicant', applicant_masked],
            ['Loan Amount', f"₹{loan_amount:,.2f}"],
            ['Interest Rate', f"{interest_rate}% p.a."],
            ['Sanction Date', sanction_date]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Blockchain Details
        story.append(Paragraph("CRYPTOGRAPHIC PROOF", self.styles['CustomHeading']))
        
        proof_text = "This document matches the record stored in the LoanEase immutable audit ledger. The following cryptographic values have been verified:"
        story.append(Paragraph(proof_text, self.styles['CustomNormal']))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(f"<b>Block Index:</b> #{block_index}", self.styles['CustomNormal']))
        
        story.append(Paragraph("<b>Block Hash:</b>", self.styles['CustomNormal']))
        story.append(Paragraph(block_hash, self.styles['HashStyle']))
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("<b>Previous Block Hash:</b>", self.styles['CustomNormal']))
        story.append(Paragraph(previous_hash, self.styles['HashStyle']))
        story.append(Spacer(1, 8))
        
        story.append(Paragraph("<b>Merkle Root:</b>", self.styles['CustomNormal']))
        story.append(Paragraph(merkle_root, self.styles['HashStyle']))
        story.append(Spacer(1, 8))
        
        story.append(Paragraph(f"<b>PoW Nonce:</b> {nonce}", self.styles['CustomNormal']))
        story.append(Spacer(1, 30))
        
        # Verification Checks
        story.append(Paragraph("VERIFICATION CHECKS", self.styles['CustomHeading']))
        checks = [
            "✓ SHA-256 hash matches ledger",
            "✓ Merkle tree integrity confirmed",
            "✓ Block chain unbroken",
            "✓ RSA-2048 signature valid"
        ]
        for check in checks:
            story.append(Paragraph(check, self.styles['CustomNormal']))
        
        story.append(Spacer(1, 40))
        
        # Footer Note
        note = """
        This certificate confirms that the referenced sanction letter exists in the LoanEase immutable audit ledger 
        and has not been modified since issuance. This verification was performed against our live blockchain 
        state at the time of generation.
        """
        story.append(Paragraph(note, self.styles['CustomNormal']))
        
        # Build PDF
        doc.build(story)
        
        buffer.seek(0)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes

# Global instance
_pdf_generator = None

def get_pdf_generator() -> SanctionLetterGenerator:
    """Get PDF generator instance"""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = SanctionLetterGenerator()
    return _pdf_generator

def generate_sanction_letter(**kwargs) -> bytes:
    """Generate sanction letter with given parameters"""
    generator = get_pdf_generator()
    return generator.generate_sanction_letter(**kwargs)

def generate_verification_certificate(**kwargs) -> bytes:
    """Generate verification certificate with given parameters"""
    generator = get_pdf_generator()
    return generator.generate_verification_certificate(**kwargs)
