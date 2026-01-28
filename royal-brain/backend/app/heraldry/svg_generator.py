"""SVG Generator — Deterministic heraldic coat of arms SVG generation.

Generates SVG from validated parsed blazon structure.
Completely deterministic and regenerable.
Invalid arms must NOT generate SVG.
"""
from __future__ import annotations

from app.heraldry.blazon_parser import ParsedBlazon, TinctureType


# SVG color mappings for heraldic tinctures
TINCTURE_COLORS = {
    "Or": "#FFD700",  # Gold
    "Argent": "#FFFFFF",  # Silver/White
    "Gules": "#DA0000",  # Red
    "Azure": "#0000CD",  # Blue
    "Sable": "#000000",  # Black
    "Vert": "#008000",  # Green
    "Purpure": "#800080",  # Purple
    "Ermine": "#FFFFFF",  # White with black spots
    "Ermines": "#000000",  # Black with white spots
    "Erminois": "#FFD700",  # Gold with black spots
    "Pean": "#000000",  # Black with gold spots
    "Vair": "#FFFFFF",  # Blue and white pattern
}

# Shield path (standard heater shield)
SHIELD_PATH = """
M 50 10
C 20 10, 10 20, 10 60
C 10 100, 30 140, 50 180
C 70 140, 90 100, 90 60
C 90 20, 80 10, 50 10
Z
"""

# Charge SVG templates (simplified geometric representations)
CHARGE_TEMPLATES = {
    "lion": """
        <g transform="translate({x}, {y}) scale(0.3)">
            <path d="M 20 30 L 25 25 L 30 30 L 35 20 L 40 30 L 50 25 L 45 35 L 50 40 L 40 45 L 35 50 L 25 45 L 20 40 L 15 35 Z" 
                  fill="{color}" stroke="#000" stroke-width="1"/>
        </g>
    """,
    "eagle": """
        <g transform="translate({x}, {y}) scale(0.3)">
            <path d="M 30 20 L 40 15 L 50 20 L 55 30 L 50 40 L 40 45 L 30 40 L 25 30 Z M 20 25 L 10 25 M 60 25 L 70 25" 
                  fill="{color}" stroke="#000" stroke-width="1"/>
        </g>
    """,
    "fleur-de-lis": """
        <g transform="translate({x}, {y}) scale(0.25)">
            <path d="M 40 10 L 42 20 L 45 15 L 43 25 L 47 30 L 40 35 L 33 30 L 37 25 L 35 15 L 38 20 Z M 40 35 L 40 50" 
                  fill="{color}" stroke="#000" stroke-width="1"/>
        </g>
    """,
    "crown": """
        <g transform="translate({x}, {y}) scale(0.3)">
            <rect x="20" y="30" width="40" height="5" fill="{color}" stroke="#000"/>
            <polygon points="20,25 30,20 40,25 50,20 60,25 60,30 20,30" fill="{color}" stroke="#000"/>
        </g>
    """,
    "cross": """
        <g transform="translate({x}, {y}) scale(0.4)">
            <rect x="35" y="10" width="10" height="60" fill="{color}" stroke="#000"/>
            <rect x="10" y="35" width="60" height="10" fill="{color}" stroke="#000"/>
        </g>
    """,
    "star": """
        <g transform="translate({x}, {y}) scale(0.3)">
            <polygon points="40,10 44,28 62,28 48,38 52,56 40,46 28,56 32,38 18,28 36,28" 
                     fill="{color}" stroke="#000" stroke-width="1"/>
        </g>
    """,
}

# Ordinary SVG templates
ORDINARY_TEMPLATES = {
    "chief": '<rect x="10" y="10" width="80" height="25" fill="{color}" stroke="#000"/>',
    "fess": '<rect x="10" y="60" width="80" height="20" fill="{color}" stroke="#000"/>',
    "pale": '<rect x="40" y="10" width="20" height="170" fill="{color}" stroke="#000"/>',
    "bend": '<rect x="10" y="10" width="100" height="20" transform="rotate(45 50 100)" fill="{color}" stroke="#000"/>',
    "chevron": '<polygon points="50,60 10,120 20,120 50,80 80,120 90,120" fill="{color}" stroke="#000"/>',
}


def _get_charge_position(charge_index: int, total_charges: int) -> tuple[int, int]:
    """Calculate deterministic position for a charge based on count and index."""
    if total_charges == 1:
        return 50, 90  # Centered
    elif total_charges == 2:
        return (30 if charge_index == 0 else 70, 90)
    elif total_charges == 3:
        if charge_index == 0:
            return 50, 60  # Top center
        return (30 if charge_index == 1 else 70, 110)  # Bottom left/right
    elif total_charges == 4:
        row = charge_index // 2
        col = charge_index % 2
        return (30 if col == 0 else 70, 60 + row * 50)
    else:
        # Arrange in rows
        row = charge_index // 3
        col = charge_index % 3
        return (25 + col * 25, 50 + row * 40)


def generate_svg(parsed_blazon: ParsedBlazon, *, valid: bool = False) -> str | None:
    """Generate deterministic SVG coat of arms from parsed blazon.
    
    Args:
        parsed_blazon: Validated parsed blazon structure
        valid: Whether the arms passed validation (must be True to generate)
        
    Returns:
        SVG string if valid and parseable, None otherwise
    """
    if not valid or not parsed_blazon.valid:
        return None
    
    # Start SVG with viewBox
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 200" width="300" height="600">',
        '<desc>Generated coat of arms: ' + parsed_blazon.raw_blazon + '</desc>',
    ]
    
    # Draw shield outline
    field_color = TINCTURE_COLORS.get(parsed_blazon.field_tincture, "#CCCCCC")
    svg_parts.append(f'<path d="{SHIELD_PATH.strip()}" fill="{field_color}" stroke="#000" stroke-width="2"/>')
    
    # Add ordinaries (drawn first, under charges)
    for ordinary in parsed_blazon.ordinaries:
        ordinary_type = ordinary["type"]
        ordinary_color = TINCTURE_COLORS.get(ordinary["tincture"], "#CCCCCC")
        
        template = ORDINARY_TEMPLATES.get(ordinary_type)
        if template:
            svg_parts.append('<g clip-path="url(#shield-clip)">')
            svg_parts.append(template.format(color=ordinary_color))
            svg_parts.append('</g>')
    
    # Add charges
    total_charges = len(parsed_blazon.charges)
    for i, charge in enumerate(parsed_blazon.charges):
        charge_name = charge["name"]
        charge_color = TINCTURE_COLORS.get(charge["tincture"], "#CCCCCC")
        
        template = CHARGE_TEMPLATES.get(charge_name)
        if template:
            x, y = _get_charge_position(i, total_charges)
            svg_parts.append(template.format(x=x, y=y, color=charge_color))
    
    # Close SVG
    svg_parts.append('</svg>')
    
    return '\n'.join(svg_parts)


def generate_svg_from_dict(parsed_structure: dict, *, valid: bool = False) -> str | None:
    """Generate SVG from dictionary representation of parsed blazon.
    
    Used for regenerating SVG from database-stored parsed_structure.
    """
    if not valid or not parsed_structure:
        return None
    
    # Reconstruct ParsedBlazon from dict
    from app.heraldry.blazon_parser import ParsedBlazon, TinctureType
    
    try:
        parsed = ParsedBlazon(
            field_tincture=parsed_structure.get("field_tincture", ""),
            field_tincture_type=TinctureType(parsed_structure.get("field_tincture_type", "color")),
            charges=parsed_structure.get("charges", []),
            ordinaries=parsed_structure.get("ordinaries", []),
            partitions=parsed_structure.get("partitions", []),
            valid=parsed_structure.get("valid", False),
            errors=parsed_structure.get("errors", []),
            raw_blazon=parsed_structure.get("raw_blazon", ""),
        )
        return generate_svg(parsed, valid=valid)
    except (KeyError, ValueError, TypeError):
        return None
