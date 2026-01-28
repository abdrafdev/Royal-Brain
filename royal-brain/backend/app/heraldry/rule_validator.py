"""Heraldic Rule Validator — Formal heraldry rules engine.

Implements classical heraldic rules including:
- Rule of Tincture
- Metal vs Color conflicts
- Charge count validity
- Ordinary placement rules
- Illegitimate combinations
- Temporal rules (rules that changed by era)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.heraldry.blazon_parser import ParsedBlazon, TinctureType


class ViolationSeverity(str, Enum):
    """Severity levels for heraldic rule violations."""
    WARNING = "WARNING"  # Traditional preference, not strictly invalid
    INVALID = "INVALID"  # Violates formal heraldic rules
    FRAUD_INDICATIVE = "FRAUD_INDICATIVE"  # Strong indicator of fraudulent arms


@dataclass
class RuleViolation:
    """A heraldic rule violation."""
    rule_name: str
    severity: ViolationSeverity
    message: str
    element: str | None = None  # Which element violated the rule
    
    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "element": self.element,
        }


@dataclass
class ValidationResult:
    """Result of heraldic validation."""
    valid: bool
    violations: list[RuleViolation]
    warnings: list[RuleViolation]
    pass_rules: list[str]
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "pass_rules": self.pass_rules,
        }


def _check_rule_of_tincture(parsed: ParsedBlazon) -> list[RuleViolation]:
    """Check the Rule of Tincture: metal must not be placed on metal, color on color.
    
    The most fundamental heraldic rule.
    """
    violations = []
    
    field_type = parsed.field_tincture_type
    
    # Check charges against field
    for charge in parsed.charges:
        charge_type = charge.get("tincture_type")
        
        if field_type == TinctureType.METAL and charge_type == TinctureType.METAL:
            violations.append(RuleViolation(
                rule_name="Rule of Tincture",
                severity=ViolationSeverity.INVALID,
                message=f"Metal on metal: {charge['tincture']} charge on {parsed.field_tincture} field",
                element=f"charge:{charge['name']}",
            ))
        elif field_type == TinctureType.COLOR and charge_type == TinctureType.COLOR:
            violations.append(RuleViolation(
                rule_name="Rule of Tincture",
                severity=ViolationSeverity.INVALID,
                message=f"Color on color: {charge['tincture']} charge on {parsed.field_tincture} field",
                element=f"charge:{charge['name']}",
            ))
    
    # Check ordinaries against field
    for ordinary in parsed.ordinaries:
        ordinary_type = ordinary.get("tincture_type")
        
        if field_type == TinctureType.METAL and ordinary_type == TinctureType.METAL:
            violations.append(RuleViolation(
                rule_name="Rule of Tincture",
                severity=ViolationSeverity.INVALID,
                message=f"Metal on metal: {ordinary['tincture']} {ordinary['type']} on {parsed.field_tincture} field",
                element=f"ordinary:{ordinary['type']}",
            ))
        elif field_type == TinctureType.COLOR and ordinary_type == TinctureType.COLOR:
            violations.append(RuleViolation(
                rule_name="Rule of Tincture",
                severity=ViolationSeverity.INVALID,
                message=f"Color on color: {ordinary['tincture']} {ordinary['type']} on {parsed.field_tincture} field",
                element=f"ordinary:{ordinary['type']}",
            ))
    
    return violations


def _check_charge_count(parsed: ParsedBlazon) -> list[RuleViolation]:
    """Check charge count validity.
    
    Historical heraldry has conventions about charge counts (e.g., 3 lions is valid, 5 is unusual).
    """
    violations = []
    warnings = []
    
    charge_count = len(parsed.charges)
    
    if charge_count > 6:
        violations.append(RuleViolation(
            rule_name="Charge Count",
            severity=ViolationSeverity.WARNING,
            message=f"Unusual number of charges: {charge_count} (typically ≤6)",
            element="charges",
        ))
    
    # Check for duplicate charge types (uncommon but not invalid)
    charge_names = [c["name"] for c in parsed.charges]
    if len(charge_names) != len(set(charge_names)):
        warnings.append(RuleViolation(
            rule_name="Charge Variety",
            severity=ViolationSeverity.WARNING,
            message="Multiple charges of the same type detected",
            element="charges",
        ))
    
    return violations + warnings


def _check_ordinary_placement(parsed: ParsedBlazon) -> list[RuleViolation]:
    """Check ordinary placement rules.
    
    Ordinaries have traditional placement rules.
    """
    violations = []
    
    # Check for conflicting ordinaries (e.g., multiple chiefs)
    ordinary_types = [o["type"] for o in parsed.ordinaries]
    
    if "chief" in ordinary_types and ordinary_types.count("chief") > 1:
        violations.append(RuleViolation(
            rule_name="Ordinary Placement",
            severity=ViolationSeverity.INVALID,
            message="Multiple chiefs detected (only one chief allowed)",
            element="ordinary:chief",
        ))
    
    if "fess" in ordinary_types and "pale" in ordinary_types:
        # This creates a cross, which is valid, but should be blazoned as "cross"
        violations.append(RuleViolation(
            rule_name="Ordinary Combination",
            severity=ViolationSeverity.WARNING,
            message="Fess and pale combined; consider blazoning as 'cross'",
            element="ordinaries",
        ))
    
    return violations


def _check_temporal_rules(parsed: ParsedBlazon, as_of: date | None) -> list[RuleViolation]:
    """Check temporal rules (rules that changed over eras).
    
    Some heraldic conventions changed over time.
    """
    violations = []
    
    # Example: Before 1400, certain furs were rare in non-royal arms
    if as_of and as_of < date(1400, 1, 1):
        for charge in parsed.charges:
            if charge.get("tincture_type") == TinctureType.FUR:
                violations.append(RuleViolation(
                    rule_name="Temporal Legitimacy",
                    severity=ViolationSeverity.WARNING,
                    message=f"Fur tincture '{charge['tincture']}' rare in arms before 1400",
                    element=f"charge:{charge['name']}",
                ))
    
    return violations


def _check_fraudulent_patterns(parsed: ParsedBlazon) -> list[RuleViolation]:
    """Check for patterns indicative of fraudulent or self-styled arms."""
    violations = []
    
    # Arms with no charges or ordinaries are suspicious (too simple)
    if len(parsed.charges) == 0 and len(parsed.ordinaries) == 0:
        violations.append(RuleViolation(
            rule_name="Fraud Detection",
            severity=ViolationSeverity.FRAUD_INDICATIVE,
            message="Arms contain only field tincture with no charges or ordinaries (suspicious simplicity)",
            element="structure",
        ))
    
    # Check for royal indicators without proper context
    royal_charges = ["crown", "scepter", "orb"]
    for charge in parsed.charges:
        if charge["name"] in royal_charges:
            violations.append(RuleViolation(
                rule_name="Fraud Detection",
                severity=ViolationSeverity.FRAUD_INDICATIVE,
                message=f"Royal charge '{charge['name']}' requires jurisdictional validation",
                element=f"charge:{charge['name']}",
            ))
    
    return violations


def validate_heraldry(
    parsed_blazon: ParsedBlazon,
    *,
    as_of: date | None = None,
    strict_mode: bool = True,
) -> ValidationResult:
    """Validate parsed blazon against formal heraldic rules.
    
    Args:
        parsed_blazon: Parsed blazon structure
        as_of: Historical date for temporal rule validation
        strict_mode: If True, treat warnings as failures
        
    Returns:
        ValidationResult with violations, warnings, and pass status
    """
    if not parsed_blazon.valid:
        # Parser already found errors
        return ValidationResult(
            valid=False,
            violations=[
                RuleViolation(
                    rule_name="Blazon Parsing",
                    severity=ViolationSeverity.INVALID,
                    message=error,
                    element="blazon",
                )
                for error in parsed_blazon.errors
            ],
            warnings=[],
            pass_rules=[],
        )
    
    all_violations = []
    all_warnings = []
    pass_rules = []
    
    # Run all validation rules
    tincture_violations = _check_rule_of_tincture(parsed_blazon)
    all_violations.extend([v for v in tincture_violations if v.severity != ViolationSeverity.WARNING])
    all_warnings.extend([v for v in tincture_violations if v.severity == ViolationSeverity.WARNING])
    
    if not tincture_violations:
        pass_rules.append("Rule of Tincture")
    
    charge_violations = _check_charge_count(parsed_blazon)
    all_violations.extend([v for v in charge_violations if v.severity != ViolationSeverity.WARNING])
    all_warnings.extend([v for v in charge_violations if v.severity == ViolationSeverity.WARNING])
    
    if not charge_violations:
        pass_rules.append("Charge Count")
    
    ordinary_violations = _check_ordinary_placement(parsed_blazon)
    all_violations.extend([v for v in ordinary_violations if v.severity != ViolationSeverity.WARNING])
    all_warnings.extend([v for v in ordinary_violations if v.severity == ViolationSeverity.WARNING])
    
    if not ordinary_violations:
        pass_rules.append("Ordinary Placement")
    
    temporal_violations = _check_temporal_rules(parsed_blazon, as_of)
    all_warnings.extend(temporal_violations)  # Temporal rules are usually warnings
    
    if not temporal_violations:
        pass_rules.append("Temporal Legitimacy")
    
    fraud_violations = _check_fraudulent_patterns(parsed_blazon)
    all_violations.extend(fraud_violations)
    
    if not fraud_violations:
        pass_rules.append("Fraud Detection")
    
    # Determine overall validity
    valid = len(all_violations) == 0
    if strict_mode:
        valid = valid and len(all_warnings) == 0
    
    return ValidationResult(
        valid=valid,
        violations=all_violations,
        warnings=all_warnings,
        pass_rules=pass_rules,
    )
