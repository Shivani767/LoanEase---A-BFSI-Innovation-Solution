from __future__ import annotations

import io
import base64
from typing import Optional

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    from qrcode.image.styles.colormasks import SquareGradiantColorMask
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("Warning: qrcode[pil] not installed. Install with: pip install qrcode[pil]")


class QRCodeGenerator:
    """Generates QR codes for blockchain verification"""
    
    def __init__(self, box_size: int = 10, border: int = 4):
        self.box_size = box_size
        self.border = border
        
        if not QR_AVAILABLE:
            raise ImportError("qrcode[pil] is required. Install with: pip install qrcode[pil]")
    
    def generate_qr_code(self, url: str, 
                       style: str = "standard") -> str:
        """Generate QR code and return as base64 string"""
        
        if style == "styled":
            # Generate styled QR code with rounded modules
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=self.box_size,
                border=self.border,
            )
            
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create styled image
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SquareGradiantColorMask()
            )
        else:
            # Standard QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=self.box_size,
                border=self.border,
            )
            
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return img_str
    
    def generate_verification_qr(self, reference: str, 
                              base_url: str = "http://localhost:8005") -> str:
        """Generate QR code for document verification"""
        url = f"{base_url}/blockchain/verify/{reference}"
        return self.generate_qr_code(url)
    
    def generate_sanction_qr(self, loan_data: dict, 
                           base_url: str = "http://localhost:8005") -> str:
        """Generate QR code for sanction letter verification"""
        reference = loan_data.get('sanction_reference', 'LE-2026-XXXXX')
        return self.generate_verification_qr(reference, base_url)


# Convenience functions for easy usage
def generate_qr_code(url: str, style: str = "standard") -> str:
    """Generate QR code and return as base64 string"""
    if not QR_AVAILABLE:
        raise ImportError("qrcode[pil] is required. Install with: pip install qrcode[pil]")
    
    generator = QRCodeGenerator()
    return generator.generate_qr_code(url, style)


def generate_verification_qr(reference: str, 
                         base_url: str = "http://localhost:8005") -> str:
    """Generate QR code for blockchain verification"""
    if not QR_AVAILABLE:
        raise ImportError("qrcode[pil] is required. Install with: pip install qrcode[pil]")
    
    generator = QRCodeGenerator()
    return generator.generate_verification_qr(reference, base_url)


def create_qr_with_logo(url: str, logo_path: Optional[str] = None) -> str:
    """Generate QR code with optional logo (advanced feature)"""
    # This would require PIL/Pillow for logo manipulation
    # For now, return standard QR code
    return generate_qr_code(url)


# Test function
def test_qr_generation():
    """Test QR code generation"""
    if not QR_AVAILABLE:
        print("QR code generation not available. Install qrcode[pil]")
        return
    
    try:
        # Test standard QR
        qr_standard = generate_qr_code("https://loanease.app/verify/LE-2026-00847")
        print(f"Standard QR generated: {len(qr_standard)} characters")
        
        # Test verification QR
        qr_verify = generate_verification_qr("LE-2026-00847")
        print(f"Verification QR generated: {len(qr_verify)} characters")
        
        return True
    except Exception as e:
        print(f"QR generation test failed: {e}")
        return False


if __name__ == "__main__":
    test_qr_generation()
