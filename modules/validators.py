"""
validators.py
=============
Input sanitization and format-validation helpers for RentEase.

All public functions return a tuple: (is_valid: bool, error_message: str).
On success, error_message is an empty string.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Tuple


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
EMAIL_REGEX = re.compile(
    r"^(?!.*\.\.)[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$"
)
PHONE_REGEX = re.compile(r"^\d{10}$")
URL_REGEX = re.compile(
    r"^https?://"                        # scheme
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)"  # domain
    r"+[A-Z]{2,}(?:/[^\s]*)?$",
    re.IGNORECASE,
)

MIN_RENT         = 1_000       # ₹1,000 / month
MAX_RENT         = 10_000_000  # ₹1 Cr / month
MIN_DEPOSIT      = 0
MAX_DEPOSIT      = 50_000_000  # ₹5 Cr
MIN_BEDROOMS     = 1
MAX_BEDROOMS     = 20
MIN_BATHROOMS    = 1
MAX_BATHROOMS    = 20
MAX_NAME_LEN     = 100
MAX_TITLE_LEN    = 150
MAX_CITY_LEN     = 50
MAX_ADDRESS_LEN  = 1000
MAX_DESC_LEN     = 5000
MAX_MSG_LEN      = 2000
MIN_PASSWORD_LEN = 6


# ------------------------------------------------------------------
# Text / string validators
# ------------------------------------------------------------------

def validate_full_name(name: str) -> Tuple[bool, str]:
    """Validate that full_name is non-empty and within length limits."""
    name = name.strip()
    if not name:
        return False, "Full name cannot be empty."
    if len(name) > MAX_NAME_LEN:
        return False, f"Full name must be at most {MAX_NAME_LEN} characters."
    if re.search(r"[<>\"'%;()&+]", name):
        return False, "Full name contains invalid characters."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address format using RFC-compliant regex."""
    email = email.strip()
    if not email:
        return False, "Email address cannot be empty."
    if len(email) > 100:
        return False, "Email address is too long (max 100 characters)."
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address (e.g., user@example.com)."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate that phone is exactly 10 digits (Indian mobile number)."""
    phone = phone.strip()
    if not phone:
        return False, "Phone number cannot be empty."
    if not PHONE_REGEX.match(phone):
        return False, "Phone number must be exactly 10 digits (no spaces or country code)."
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password meets minimum length requirement."""
    if not password:
        return False, "Password cannot be empty."
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters long."
    return True, ""


def validate_non_empty_text(value: str, field_name: str = "Field", max_len: int = MAX_DESC_LEN) -> Tuple[bool, str]:
    """Generic non-empty text validator with length cap."""
    value = value.strip()
    if not value:
        return False, f"{field_name} cannot be empty."
    if len(value) > max_len:
        return False, f"{field_name} must be at most {max_len} characters."
    return True, ""


def validate_title(title: str) -> Tuple[bool, str]:
    """Validate property listing title."""
    return validate_non_empty_text(title, "Property title", MAX_TITLE_LEN)


def validate_city(city: str) -> Tuple[bool, str]:
    """Validate city name."""
    city = city.strip()
    if not city:
        return False, "City cannot be empty."
    if len(city) > MAX_CITY_LEN:
        return False, f"City name must be at most {MAX_CITY_LEN} characters."
    if not re.match(r"^[a-zA-Z\s\-\.]+$", city):
        return False, "City name must contain only letters, spaces, hyphens, or dots."
    return True, ""


def validate_address(address: str) -> Tuple[bool, str]:
    """Validate address text."""
    return validate_non_empty_text(address, "Address", MAX_ADDRESS_LEN)


# ------------------------------------------------------------------
# Numeric validators
# ------------------------------------------------------------------

def validate_rent(rent) -> Tuple[bool, str]:
    """Validate monthly rent is within acceptable bounds."""
    try:
        rent_val = Decimal(str(rent))
    except InvalidOperation:
        return False, "Rent must be a valid number."
    if rent_val < MIN_RENT:
        return False, f"Monthly rent must be at least ₹{MIN_RENT:,}."
    if rent_val > MAX_RENT:
        return False, f"Monthly rent cannot exceed ₹{MAX_RENT:,}."
    return True, ""


def validate_deposit(deposit) -> Tuple[bool, str]:
    """Validate security deposit is within acceptable bounds."""
    try:
        dep_val = Decimal(str(deposit))
    except InvalidOperation:
        return False, "Security deposit must be a valid number."
    if dep_val < MIN_DEPOSIT:
        return False, "Security deposit cannot be negative."
    if dep_val > MAX_DEPOSIT:
        return False, f"Security deposit cannot exceed ₹{MAX_DEPOSIT:,}."
    return True, ""


def validate_bedrooms(bedrooms: int) -> Tuple[bool, str]:
    """Validate bedroom count."""
    try:
        b = int(bedrooms)
    except (TypeError, ValueError):
        return False, "Bedroom count must be a whole number."
    if b < MIN_BEDROOMS or b > MAX_BEDROOMS:
        return False, f"Bedrooms must be between {MIN_BEDROOMS} and {MAX_BEDROOMS}."
    return True, ""


def validate_bathrooms(bathrooms: int) -> Tuple[bool, str]:
    """Validate bathroom count."""
    try:
        b = int(bathrooms)
    except (TypeError, ValueError):
        return False, "Bathroom count must be a whole number."
    if b < MIN_BATHROOMS or b > MAX_BATHROOMS:
        return False, f"Bathrooms must be between {MIN_BATHROOMS} and {MAX_BATHROOMS}."
    return True, ""


def validate_image_url(url: str) -> Tuple[bool, str]:
    """Validate that image URL starts with http/https. Empty is allowed (falls back to default)."""
    url = url.strip()
    if not url:
        return True, ""  # blank → default image applied by caller
    if not URL_REGEX.match(url):
        return False, "Image URL must be a valid HTTP/HTTPS URL."
    return True, ""


# ------------------------------------------------------------------
# Compound registration validator
# ------------------------------------------------------------------

def validate_registration_form(
    full_name: str,
    email: str,
    password: str,
    phone: str,
) -> Tuple[bool, str]:
    """
    Run all registration-field validators in sequence.
    Returns the first failure encountered, or (True, "") if all pass.
    """
    for validator, value in [
        (validate_full_name, full_name),
        (validate_email,     email),
        (validate_password,  password),
        (validate_phone,     phone),
    ]:
        ok, msg = validator(value)
        if not ok:
            return False, msg
    return True, ""


def validate_property_form(
    title: str,
    city: str,
    address: str,
    rent,
    deposit,
    bedrooms: int,
    bathrooms: int,
    image_url: str = "",
) -> Tuple[bool, str]:
    """
    Run all property-listing validators in sequence.
    Returns the first failure encountered, or (True, "") if all pass.
    """
    checks = [
        (validate_title,    (title,)),
        (validate_city,     (city,)),
        (validate_address,  (address,)),
        (validate_rent,     (rent,)),
        (validate_deposit,  (deposit,)),
        (validate_bedrooms, (bedrooms,)),
        (validate_bathrooms,(bathrooms,)),
        (validate_image_url,(image_url,)),
    ]
    for validator, args in checks:
        ok, msg = validator(*args)
        if not ok:
            return False, msg
    return True, ""
