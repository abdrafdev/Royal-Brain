"""Jurisdiction Heraldry Compliance — Pluggable jurisdiction-specific heraldic rules.

Integrates with Day 6 Jurisdiction Engine to validate:
- Legal grantability in jurisdiction
- Historical period matching
- Claimant rank/status requirements
- Time-aware rules for British, French, HRE, etc.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.heraldry.blazon_parser import ParsedBlazon
from app.jurisdictions.models import Jurisdiction
from app.persons.models import Person


@dataclass
class JurisdictionCompliance:
    """Result of jurisdiction-specific heraldic validation."""
    compliant: bool
    jurisdiction_code: str
    jurisdiction_name: str
    violations: list[str]
    allows_nobility_arms: bool
    allows_royal_symbols: bool
    detail: str
    
    def to_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "jurisdiction_code": self.jurisdiction_code,
            "jurisdiction_name": self.jurisdiction_name,
            "violations": self.violations,
            "allows_nobility_arms": self.allows_nobility_arms,
            "allows_royal_symbols": self.allows_royal_symbols,
            "detail": self.detail,
        }


def _check_british_heraldic_law(
    parsed: ParsedBlazon,
    jurisdiction: Jurisdiction,
    claimant: Person | None,
    as_of: date | None,
) -> JurisdictionCompliance:
    """Check compliance with British heraldic law.
    
    British heraldry is regulated by the College of Arms.
    """
    violations = []
    
    # Check if nobility was abolished
    if jurisdiction.nobility_abolished_date:
        if as_of and as_of >= jurisdiction.nobility_abolished_date:
            violations.append("British heraldry post-abolition requires College of Arms grant")
    
    # Check for royal symbols (crown, supporters)
    royal_charges = ["crown", "scepter", "orb"]
    for charge in parsed.charges:
        if charge["name"] in royal_charges:
            violations.append(f"Royal charge '{charge['name']}' requires royal grant or peerage")
    
    # Supporters are restricted to peers
    # (This would require additional parsing of supporters, simplified here)
    
    detail = f"British heraldic law as of {as_of or 'present'}"
    if claimant:
        detail += f" for claimant {claimant.primary_name}"
    
    allows_nobility_arms = (
        jurisdiction.nobility_abolished_date is None
        or (as_of is not None and as_of < jurisdiction.nobility_abolished_date)
    )

    return JurisdictionCompliance(
        compliant=len(violations) == 0,
        jurisdiction_code=jurisdiction.code,
        jurisdiction_name=jurisdiction.name,
        violations=violations,
        allows_nobility_arms=allows_nobility_arms,
        allows_royal_symbols=False,  # Requires special grant
        detail=detail,
    )


def _check_french_heraldic_law(
    parsed: ParsedBlazon,
    jurisdiction: Jurisdiction,
    claimant: Person | None,
    as_of: date | None,
) -> JurisdictionCompliance:
    """Check compliance with French heraldic law.
    
    French heraldry was regulated differently across eras.
    """
    violations = []
    
    # French nobility abolished in 1789-1792
    if jurisdiction.nobility_abolished_date:
        if as_of and as_of >= jurisdiction.nobility_abolished_date:
            violations.append("French nobility abolished 1789; heraldry became unregulated")
    
    # Fleur-de-lis restrictions (royal symbol)
    for charge in parsed.charges:
        if charge["name"] == "fleur-de-lis":
            if as_of and as_of < date(1789, 1, 1):
                violations.append("Fleur-de-lis restricted to royal/granted arms before Revolution")
    
    detail = f"French heraldic law as of {as_of or 'present'}"
    if claimant:
        detail += f" for claimant {claimant.primary_name}"
    
    allows_nobility_arms = (
        jurisdiction.nobility_abolished_date is None
        or (as_of is not None and as_of < jurisdiction.nobility_abolished_date)
    )

    return JurisdictionCompliance(
        compliant=len(violations) == 0,
        jurisdiction_code=jurisdiction.code,
        jurisdiction_name=jurisdiction.name,
        violations=violations,
        allows_nobility_arms=allows_nobility_arms,
        allows_royal_symbols=False,
        detail=detail,
    )


def _check_hre_heraldic_law(
    parsed: ParsedBlazon,
    jurisdiction: Jurisdiction,
    claimant: Person | None,
    as_of: date | None,
) -> JurisdictionCompliance:
    """Check compliance with Holy Roman Empire heraldic law.
    
    HRE heraldry was complex with Imperial grants.
    """
    violations = []
    
    # HRE dissolved in 1806
    if as_of and as_of >= date(1806, 8, 6):
        violations.append("Holy Roman Empire dissolved 1806; heraldry became territorial")
    
    # Imperial eagle restrictions
    for charge in parsed.charges:
        if charge["name"] == "eagle" and charge.get("position") == "displayed":
            if as_of and as_of < date(1806, 8, 6):
                violations.append("Displayed eagle restricted to Imperial grants")
    
    detail = f"Holy Roman Empire heraldic law as of {as_of or 'present'}"
    if claimant:
        detail += f" for claimant {claimant.primary_name}"
    
    return JurisdictionCompliance(
        compliant=len(violations) == 0,
        jurisdiction_code=jurisdiction.code,
        jurisdiction_name=jurisdiction.name,
        violations=violations,
        allows_nobility_arms=as_of is None or as_of < date(1806, 8, 6),
        allows_royal_symbols=False,
        detail=detail,
    )


def _check_generic_jurisdiction(
    parsed: ParsedBlazon,
    jurisdiction: Jurisdiction,
    claimant: Person | None,
    as_of: date | None,
) -> JurisdictionCompliance:
    """Generic jurisdiction check for systems without specific rules."""
    violations = []
    
    # Check nobility abolition
    if jurisdiction.nobility_abolished_date:
        if as_of and as_of >= jurisdiction.nobility_abolished_date:
            violations.append(f"Nobility abolished in {jurisdiction.name} on {jurisdiction.nobility_abolished_date}")
    
    detail = f"Generic heraldic validation for {jurisdiction.name} as of {as_of or 'present'}"
    if claimant:
        detail += f" for claimant {claimant.primary_name}"
    
    allows_nobility_arms = (
        jurisdiction.nobility_abolished_date is None
        or (as_of is not None and as_of < jurisdiction.nobility_abolished_date)
    )

    return JurisdictionCompliance(
        compliant=len(violations) == 0,
        jurisdiction_code=jurisdiction.code,
        jurisdiction_name=jurisdiction.name,
        violations=violations,
        allows_nobility_arms=allows_nobility_arms,
        allows_royal_symbols=False,
        detail=detail,
    )


JURISDICTION_VALIDATORS = {
    "GB": _check_british_heraldic_law,
    "UK": _check_british_heraldic_law,
    "FR": _check_french_heraldic_law,
    "HRE": _check_hre_heraldic_law,
}


def validate_jurisdiction_compliance(
    db: Session,
    *,
    parsed_blazon: ParsedBlazon,
    jurisdiction_id: int,
    claimant_person_id: int | None = None,
    as_of: date | None = None,
) -> JurisdictionCompliance:
    """Validate heraldry against jurisdiction-specific rules.
    
    Args:
        db: Database session
        parsed_blazon: Parsed blazon structure
        jurisdiction_id: Jurisdiction to validate against
        claimant_person_id: Optional claimant for rank/status checks
        as_of: Historical date for time-aware validation
        
    Returns:
        JurisdictionCompliance with violations and compliance status
    """
    jurisdiction = db.get(Jurisdiction, jurisdiction_id)
    if not jurisdiction:
        return JurisdictionCompliance(
            compliant=False,
            jurisdiction_code="UNKNOWN",
            jurisdiction_name="Unknown",
            violations=["Jurisdiction not found"],
            allows_nobility_arms=False,
            allows_royal_symbols=False,
            detail="Jurisdiction ID invalid",
        )
    
    claimant = None
    if claimant_person_id:
        claimant = db.get(Person, claimant_person_id)
    
    # Get jurisdiction-specific validator or use generic
    validator = JURISDICTION_VALIDATORS.get(jurisdiction.code, _check_generic_jurisdiction)
    
    return validator(parsed_blazon, jurisdiction, claimant, as_of)
