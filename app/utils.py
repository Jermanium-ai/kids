"""
PlaySync - Utility functions
QR code generation, avatars, and helpers
"""

import qrcode
import io
import base64
from PIL import Image, ImageDraw

def generate_qr_code(url, size=10, border=2):
    """
    Generate a QR code as base64 PNG for embedding in HTML.
    Returns base64-encoded PNG image.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{b64}"

def generate_avatar_svg(player_id, color):
    """
    Generate a simple avatar SVG based on player_id and color.
    Returns SVG string.
    """
    # Use player_id to generate a simple geometric pattern
    hash_val = sum(ord(c) for c in player_id) % 100
    
    # Create a simple SVG with a colored circle and initials or pattern
    svg = f"""
    <svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
        <rect width="48" height="48" rx="6" fill="{color}" opacity="0.1"/>
        <circle cx="24" cy="24" r="16" fill="{color}" opacity="0.8"/>
        <circle cx="24" cy="24" r="14" fill="white" stroke="{color}" stroke-width="1"/>
        <text x="24" y="30" text-anchor="middle" font-family="sans-serif" font-size="18" 
              font-weight="bold" fill="{color}">
            {hash_val % 26}
        </text>
    </svg>
    """
    return svg.strip()

def get_avatar_colors():
    """Return a list of pleasant teal-themed colors for avatars"""
    return [
        "#0D9488",  # Teal-700
        "#14B8A6",  # Teal-500
        "#2DD4BF",  # Teal-400
        "#06B6D4",  # Cyan-500
        "#0891B2",  # Cyan-600
        "#155E75",  # Slate-900
        "#1F2937",  # Gray-800
    ]

def get_random_avatar_color():
    """Get a random avatar color"""
    import random
    return random.choice(get_avatar_colors())

def generate_display_name():
    """Generate a random, friendly display name"""
    adjectives = [
        "Swift", "Clever", "Bold", "Brave", "Quick", "Sharp",
        "Smart", "Keen", "Alert", "Nimble", "Slick", "Deft"
    ]
    nouns = [
        "Phoenix", "Tiger", "Falcon", "Eagle", "Wolf", "Lion",
        "Raven", "Fox", "Cheetah", "Hawk", "Osprey", "Lynx"
    ]
    import random
    return f"{random.choice(adjectives)} {random.choice(nouns)}"
