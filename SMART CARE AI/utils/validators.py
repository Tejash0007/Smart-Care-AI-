"""
SmartCare AI – Input Validation and Sanitization Module.
Provides comprehensive frontend and backend validation for:
- Full Legal Names (Unicode letters, hyphens, apostrophes, spaces; no numbers or special symbols)
- Indian Mobile Numbers (10 digits, optional +91/0 prefix, normalized standard format)
- Email Addresses (standard RFC-compliant regex, length bounds)
- Passwords (length and complexity criteria)
- Biometric Health Vitals (physiologically valid medical ranges)
"""

import re
from typing import Tuple, Optional
from datetime import date, datetime


# ==============================================================================
# NAME VALIDATION
# ==============================================================================

# Regex allowing Unicode letters, spaces, hyphens, periods (e.g. Dr. / initials), and apostrophes
NAME_REGEX = re.compile(r"^[A-Za-z\u00C0-\u024F\u0900-\u097F\s\.\'\-]{2,60}$")

def validate_name(name: Optional[str], field_label: str = "Name") -> Tuple[bool, str, str]:
    """
    Validate a person's full legal name.
    
    Rules:
    - Required field.
    - Minimum 2 characters, maximum 60 characters.
    - Allows spaces, hyphens, periods, apostrophes, and Unicode letters (English, Hindi/Devanagari, accented).
    - Rejects numbers, symbols, and numeric-only strings.
    - Trims unnecessary spaces.
    
    Returns:
        (is_valid: bool, error_message: str, cleaned_name: str)
    """
    if not name or not isinstance(name, str):
        return False, f"{field_label} is required.", ""
    
    cleaned = name.strip()
    # Normalize multiple consecutive spaces to a single space
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    if len(cleaned) < 2:
        return False, f"{field_label} must be at least 2 characters.", cleaned
    
    if len(cleaned) > 60:
        return False, f"{field_label} cannot exceed 60 characters.", cleaned
    
    # Check for numbers
    if any(ch.isdigit() for ch in cleaned):
        return False, f"{field_label} cannot contain numbers.", cleaned
    
    # Check against allowed character pattern
    if not NAME_REGEX.match(cleaned):
        return False, f"{field_label} contains invalid special characters. Only letters, spaces, hyphens, periods, and apostrophes are allowed.", cleaned
    
    # Must have at least one alphabetical letter
    if not any(ch.isalpha() for ch in cleaned):
        return False, f"{field_label} must contain alphabetical letters.", cleaned
    
    return True, "", cleaned


# ==============================================================================
# MOBILE NUMBER VALIDATION (INDIAN MOBILE STANDARDS)
# ==============================================================================

def validate_mobile(mobile: Optional[str], required: bool = True) -> Tuple[bool, str, str]:
    """
    Validate and normalize an Indian mobile telephone number.
    
    Rules:
    - Supports 10-digit Indian mobile numbers (starts with 6, 7, 8, or 9).
    - Supports optional +91, 91, or leading 0 prefix.
    - Rejects alphabetic characters, symbols, and invalid lengths.
    - Formats to consistent normalized format: '+91 XXXXX XXXXX'.
    
    Returns:
        (is_valid: bool, error_message: str, normalized_mobile: str)
    """
    if not mobile or not str(mobile).strip():
        if required:
            return False, "Mobile number is required.", ""
        return True, "", ""
    
    raw = str(mobile).strip()
    
    # Check if alphabetic characters exist
    if any(ch.isalpha() for ch in raw):
        return False, "Mobile number cannot contain letters.", ""
    
    # Extract only digits and leading +
    digits_only = re.sub(r"\D", "", raw)
    
    # Check Indian numbering plan
    # Can be 10 digits (e.g. 9876543210)
    # Can be 11 digits starting with 0 (e.g. 09876543210)
    # Can be 12 digits starting with 91 (e.g. 919876543210)
    core_10 = ""
    if len(digits_only) == 10:
        core_10 = digits_only
    elif len(digits_only) == 11 and digits_only.startswith("0"):
        core_10 = digits_only[1:]
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        core_10 = digits_only[2:]
    else:
        return False, "Invalid mobile number. Please enter a valid 10-digit Indian mobile number (e.g., 98765 43210).", ""
    
    # Indian mobile numbers must start with 6, 7, 8, or 9
    if core_10[0] not in ["6", "7", "8", "9"]:
        return False, "Indian mobile numbers must begin with 6, 7, 8, or 9.", ""
    
    normalized = f"+91 {core_10[:5]} {core_10[5:]}"
    return True, "", normalized


# ==============================================================================
# EMAIL VALIDATION
# ==============================================================================

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email(email: Optional[str]) -> Tuple[bool, str, str]:
    """
    Validate an email address format and sensible length.
    
    Returns:
        (is_valid: bool, error_message: str, cleaned_email: str)
    """
    if not email or not str(email).strip():
        return False, "Email address is required.", ""
    
    cleaned = str(email).strip().lower()
    
    if len(cleaned) > 100:
        return False, "Email address cannot exceed 100 characters.", cleaned
    
    if not EMAIL_REGEX.match(cleaned):
        return False, "Please enter a valid email address (e.g., name@example.com).", cleaned
    
    return True, "", cleaned


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

def validate_password(password: Optional[str], confirm_password: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate password length and confirmation match.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Password is required."
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    
    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match."
    
    return True, ""


# ==============================================================================
# BIOMETRIC HEALTH VITALS VALIDATION
# ==============================================================================

def validate_vitals_input(
    weight_kg: float,
    height_cm: float,
    systolic_bp: int,
    diastolic_bp: int,
    blood_glucose: float,
    heart_rate: int,
    recording_date_val: Optional[date] = None
) -> Tuple[bool, str]:
    """
    Validate physiological biometric measurements within credible medical bounds.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    # 1. Weight: 10 kg to 300 kg
    if not (10.0 <= weight_kg <= 300.0):
        return False, "Weight must be between 10.0 kg and 300.0 kg."
    
    # 2. Height: 50 cm to 250 cm
    if not (50.0 <= height_cm <= 250.0):
        return False, "Height must be between 50.0 cm and 250.0 cm."
    
    # 3. Systolic BP: 60 to 260 mmHg
    if not (60 <= systolic_bp <= 260):
        return False, "Systolic blood pressure must be between 60 mmHg and 260 mmHg."
    
    # 4. Diastolic BP: 40 to 160 mmHg
    if not (40 <= diastolic_bp <= 160):
        return False, "Diastolic blood pressure must be between 40 mmHg and 160 mmHg."
    
    # 5. Physiological constraint: Systolic must be strictly greater than Diastolic
    if systolic_bp <= diastolic_bp:
        return False, f"Systolic pressure ({systolic_bp} mmHg) must be strictly higher than diastolic pressure ({diastolic_bp} mmHg)."
    
    # Pulse pressure sanity check
    if (systolic_bp - diastolic_bp) < 10:
        return False, "Pulse pressure (Systolic - Diastolic) is unrealistically narrow (minimum 10 mmHg)."
    
    # 6. Blood Glucose: 20 mg/dL to 600 mg/dL
    if not (20.0 <= blood_glucose <= 600.0):
        return False, "Blood glucose must be between 20.0 mg/dL and 600.0 mg/dL."
    
    # 7. Resting Heart Rate: 30 BPM to 220 BPM
    if not (30 <= heart_rate <= 220):
        return False, "Resting heart rate must be between 30 BPM and 220 BPM."
    
    # 8. Date cannot be in the future
    if recording_date_val:
        today_val = date.today()
        if recording_date_val > today_val:
            return False, "Measurement date cannot be in the future."
        if recording_date_val < date(2000, 1, 1):
            return False, "Measurement date cannot be earlier than year 2000."
    
    return True, ""


# ==============================================================================
# PROVIDER CREDENTIALS VALIDATION
# ==============================================================================

def validate_provider_fields(
    specialty: str,
    hospital: str,
    license_number: str
) -> Tuple[bool, str]:
    """Validate healthcare provider professional registration details."""
    if not specialty or len(specialty.strip()) < 2:
        return False, "Clinical specialty / designation is required."
    
    if not hospital or len(hospital.strip()) < 2:
        return False, "Healthcare facility / hospital affiliation is required."
    
    if not license_number or len(license_number.strip()) < 3:
        return False, "Medical registration / license number must be at least 3 characters."
    
    return True, ""
