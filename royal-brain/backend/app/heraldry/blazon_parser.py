"""Blazon Parser — Deterministic heraldic text parsing engine.

Parses blazon descriptions into structured canonical representation.
Returns explicit errors for invalid or ambiguous blazons.
No guessing; all outputs must be deterministic and rule-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class TinctureType(str, Enum):
    """Heraldic tincture categories."""
    METAL = "metal"
    COLOR = "color"
    FUR = "fur"


# Canonical tincture vocabulary with classifications
TINCTURES = {
    # Metals
    "or": {"type": TinctureType.METAL, "canonical": "Or", "aliases": ["gold"]},
    "gold": {"type": TinctureType.METAL, "canonical": "Or", "aliases": ["or"]},
    "argent": {"type": TinctureType.METAL, "canonical": "Argent", "aliases": ["silver"]},
    "silver": {"type": TinctureType.METAL, "canonical": "Argent", "aliases": ["argent"]},
    
    # Colors
    "gules": {"type": TinctureType.COLOR, "canonical": "Gules", "aliases": ["red"]},
    "red": {"type": TinctureType.COLOR, "canonical": "Gules", "aliases": ["gules"]},
    "azure": {"type": TinctureType.COLOR, "canonical": "Azure", "aliases": ["blue"]},
    "blue": {"type": TinctureType.COLOR, "canonical": "Azure", "aliases": ["azure"]},
    "sable": {"type": TinctureType.COLOR, "canonical": "Sable", "aliases": ["black"]},
    "black": {"type": TinctureType.COLOR, "canonical": "Sable", "aliases": ["sable"]},
    "vert": {"type": TinctureType.COLOR, "canonical": "Vert", "aliases": ["green"]},
    "green": {"type": TinctureType.COLOR, "canonical": "Vert", "aliases": ["vert"]},
    "purpure": {"type": TinctureType.COLOR, "canonical": "Purpure", "aliases": ["purple"]},
    "purple": {"type": TinctureType.COLOR, "canonical": "Purpure", "aliases": ["purpure"]},
    
    # Furs
    "ermine": {"type": TinctureType.FUR, "canonical": "Ermine", "aliases": []},
    "ermines": {"type": TinctureType.FUR, "canonical": "Ermines", "aliases": []},
    "erminois": {"type": TinctureType.FUR, "canonical": "Erminois", "aliases": []},
    "pean": {"type": TinctureType.FUR, "canonical": "Pean", "aliases": []},
    "vair": {"type": TinctureType.FUR, "canonical": "Vair", "aliases": []},
}

# Canonical charges (common heraldic figures)
CHARGES = [
    "lion", "eagle", "bear", "stag", "boar", "wolf", "horse", "dragon",
    "griffin", "unicorn", "fleur-de-lis", "rose", "cross", "crown", "sword",
    "star", "crescent", "sun", "tower", "castle", "ship", "anchor", "key",
    "chevron", "fess", "pale", "bend", "saltire", "chief", "base",
]

# Canonical ordinaries (geometric divisions)
ORDINARIES = [
    "chief", "fess", "pale", "bend", "bend sinister", "chevron", "cross",
    "saltire", "pale", "pall", "pile", "shakefork", "canton",
]

# Positions/attitudes for charges
POSITIONS = [
    "rampant", "passant", "statant", "couchant", "sejant", "salient",
    "displayed", "rising", "volant", "naiant", "guardant", "regardant",
    "combatant", "respectant", "addorsed", "dexter", "sinister",
]


@dataclass
class ParsedBlazon:
    """Structured representation of a parsed blazon."""
    field_tincture: str
    field_tincture_type: TinctureType
    charges: list[dict]
    ordinaries: list[dict]
    partitions: list[dict]
    valid: bool
    errors: list[str]
    raw_blazon: str
    
    def to_dict(self) -> dict:
        return {
            "field_tincture": self.field_tincture,
            "field_tincture_type": self.field_tincture_type,
            "charges": self.charges,
            "ordinaries": self.ordinaries,
            "partitions": self.partitions,
            "valid": self.valid,
            "errors": self.errors,
            "raw_blazon": self.raw_blazon,
        }


def _normalize_tincture(tincture_text: str) -> dict | None:
    """Normalize a tincture string to canonical form."""
    t = tincture_text.strip().lower()
    if t in TINCTURES:
        info = TINCTURES[t]
        return {
            "canonical": info["canonical"],
            "type": info["type"],
        }
    return None


def _extract_field_tincture(blazon: str) -> tuple[str | None, TinctureType | None, str]:
    """Extract the field (background) tincture from blazon.
    
    Returns: (canonical_tincture, tincture_type, remaining_blazon_text)
    """
    # Match patterns like "Gules," or "Azure," at start
    match = re.match(r"^([A-Za-z]+),?\s*", blazon)
    if match:
        tincture_candidate = match.group(1)
        normalized = _normalize_tincture(tincture_candidate)
        if normalized:
            remaining = blazon[match.end():].strip()
            return normalized["canonical"], normalized["type"], remaining
    
    return None, None, blazon


def _extract_charges(remaining_text: str) -> tuple[list[dict], list[str]]:
    """Extract charges from blazon text.
    
    Returns: (list of charge dicts, list of parsing errors)
    """
    charges = []
    errors = []
    
    # Simple pattern: "a {position} {charge} {tincture}"
    # Example: "a lion rampant Or"
    pattern = r"\ba\s+([a-z\s]+?)\s+([A-Z][a-z]+)\b"
    matches = re.finditer(pattern, remaining_text)
    
    for match in matches:
        charge_desc = match.group(1).strip()
        tincture_text = match.group(2).strip()
        
        # Parse position and charge name
        words = charge_desc.split()
        position = None
        charge_name = None
        
        for word in words:
            if word in POSITIONS:
                position = word
            elif word in CHARGES:
                charge_name = word
        
        if not charge_name:
            # Check if entire phrase is a charge
            if charge_desc in CHARGES:
                charge_name = charge_desc
            else:
                errors.append(f"Unrecognized charge: '{charge_desc}'")
                continue
        
        # Validate tincture
        tincture_normalized = _normalize_tincture(tincture_text)
        if not tincture_normalized:
            errors.append(f"Invalid tincture for charge: '{tincture_text}'")
            continue
        
        charges.append({
            "name": charge_name,
            "position": position,
            "tincture": tincture_normalized["canonical"],
            "tincture_type": tincture_normalized["type"],
        })
    
    return charges, errors


def parse_blazon(blazon_text: str) -> ParsedBlazon:
    """Parse a blazon string into structured representation.
    
    This is a deterministic, rule-based parser. Invalid or ambiguous
    blazons will return explicit errors.
    
    Args:
        blazon_text: Raw blazon description
        
    Returns:
        ParsedBlazon with structured data and validation status
    """
    if not blazon_text or not blazon_text.strip():
        return ParsedBlazon(
            field_tincture="",
            field_tincture_type=TinctureType.COLOR,
            charges=[],
            ordinaries=[],
            partitions=[],
            valid=False,
            errors=["Empty blazon text"],
            raw_blazon="",
        )
    
    blazon = blazon_text.strip()
    errors = []
    
    # Extract field tincture
    field_tincture, field_tincture_type, remaining = _extract_field_tincture(blazon)
    
    if not field_tincture:
        errors.append("Unable to parse field tincture from blazon")
        return ParsedBlazon(
            field_tincture="",
            field_tincture_type=TinctureType.COLOR,
            charges=[],
            ordinaries=[],
            partitions=[],
            valid=False,
            errors=errors,
            raw_blazon=blazon,
        )
    
    # Extract charges
    charges, charge_errors = _extract_charges(remaining)
    errors.extend(charge_errors)
    
    # Ordinaries and partitions parsing (simplified for now)
    ordinaries = []
    partitions = []
    
    # Check for common ordinaries in remaining text
    for ordinary in ORDINARIES:
        if ordinary in remaining.lower():
            # Extract tincture for ordinary if present
            # Pattern: "{ordinary} {tincture}"
            pattern = rf"\b{ordinary}\s+([A-Z][a-z]+)\b"
            match = re.search(pattern, remaining, re.IGNORECASE)
            if match:
                tincture_text = match.group(1)
                tincture_normalized = _normalize_tincture(tincture_text)
                if tincture_normalized:
                    ordinaries.append({
                        "type": ordinary,
                        "tincture": tincture_normalized["canonical"],
                        "tincture_type": tincture_normalized["type"],
                    })
    
    valid = len(errors) == 0
    
    return ParsedBlazon(
        field_tincture=field_tincture,
        field_tincture_type=field_tincture_type,
        charges=charges,
        ordinaries=ordinaries,
        partitions=partitions,
        valid=valid,
        errors=errors,
        raw_blazon=blazon,
    )
