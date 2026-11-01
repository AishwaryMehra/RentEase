"""
auth.py
=======
Authentication module for RentEase Rental Portal.

Handles:
  - Password hashing  : SHA-256 with a per-app salt (no third-party bcrypt required).
  - User registration : Validates inputs, checks uniqueness, persists new user.
  - User login        : Credential verification and session population.
  - Session helpers   : is_logged_in(), get_current_user(), logout().
"""

import hashlib
import streamlit as st

from database.db_connection import execute_query, fetch_one
from modules.validators import validate_registration_form

# ------------------------------------------------------------------
# Internal salt — not a secret, but makes rainbow-table attacks harder.
# In a production environment, use bcrypt or argon2 with per-user salts.
# ------------------------------------------------------------------
_APP_SALT = "salt_rentease_v1"


# ------------------------------------------------------------------
# Password utilities
# ------------------------------------------------------------------

def hash_password(plaintext: str) -> str:
    """
    Return a SHA-256 hex digest of (APP_SALT + plaintext).
    The stored string includes the salt prefix so it self-documents.
    """
    raw = (_APP_SALT + plaintext).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return f"{_APP_SALT}:{digest}"


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """
    Reconstruct the hash for plaintext and compare with stored_hash.
    Returns True only on an exact match (timing-safe via == is acceptable
    for SHA-256; for bcrypt use hmac.compare_digest).
    """
    expected = hash_password(plaintext)
    return expected == stored_hash


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def register_user(
    full_name: str,
    email: str,
    password: str,
    phone: str,
    role: str,          # 'tenant' | 'owner'
) -> tuple[bool, str]:
    """
    Register a new user.

    Returns
    -------
    (True,  "")            on success.
    (False, error_message) on validation failure or DB error.
    """
    # 1. Input validation
    ok, msg = validate_registration_form(full_name, email, password, phone)
    if not ok:
        return False, msg

    if role not in ("tenant", "owner"):
        return False, "Invalid role selected."

    # 2. Uniqueness check
    existing = fetch_one(
        "SELECT user_id FROM users WHERE email = %s",
        (email.strip().lower(),),
    )
    if existing:
        return False, "An account with this email already exists. Please log in."

    # 3. Hash password and persist
    pwd_hash = hash_password(password)
    new_id = execute_query(
        """INSERT INTO users (full_name, email, password_hash, phone, role)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            full_name.strip(),
            email.strip().lower(),
            pwd_hash,
            phone.strip(),
            role,
        ),
    )

    if new_id is None:
        return False, "Registration failed due to a database error. Please try again."

    return True, ""


# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------

def login_user(email: str, password: str) -> tuple[bool, str]:
    """
    Verify credentials and populate Streamlit session state on success.

    Returns
    -------
    (True,  "")            on success — session state is set.
    (False, error_message) on failure.
    """
    if not email.strip() or not password:
        return False, "Email and password are required."

    user = fetch_one(
        "SELECT user_id, full_name, email, password_hash, role FROM users WHERE email = %s",
        (email.strip().lower(),),
    )

    if user is None:
        return False, "No account found with this email address."

    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password. Please try again."

    # Populate session state
    st.session_state["logged_in"] = True
    st.session_state["user_id"]   = user["user_id"]
    st.session_state["user_name"] = user["full_name"]
    st.session_state["role"]      = user["role"]
    st.session_state["email"]     = user["email"]

    return True, ""


# ------------------------------------------------------------------
# Session helpers
# ------------------------------------------------------------------

def is_logged_in() -> bool:
    """Return True if a valid session exists."""
    return bool(st.session_state.get("logged_in", False))


def get_current_role() -> str:
    """Return the current user's role, or empty string if not logged in."""
    return st.session_state.get("role", "")


def get_current_user_id() -> int:
    """Return the current user's user_id, or 0 if not logged in."""
    return st.session_state.get("user_id", 0)


def get_current_user_name() -> str:
    """Return the display name of the currently logged-in user."""
    return st.session_state.get("user_name", "Guest")


def logout() -> None:
    """Clear all session state keys to log the user out."""
    for key in ["logged_in", "user_id", "user_name", "role", "email"]:
        st.session_state.pop(key, None)


def require_login() -> bool:
    """
    Guard function for protected pages.
    If not logged in, shows a warning and returns False.
    """
    if not is_logged_in():
        st.warning("🔒 Please log in to access this page.")
        return False
    return True


def require_role(expected_role: str) -> bool:
    """
    Guard function for role-restricted pages.
    Returns False and shows an error if the logged-in role doesn't match.
    """
    if not require_login():
        return False
    if get_current_role() != expected_role:
        st.error(f"🚫 This page is only accessible to {expected_role}s.")
        return False
    return True


# ------------------------------------------------------------------
# Profile fetch
# ------------------------------------------------------------------

def get_user_profile(user_id: int) -> dict | None:
    """Fetch the full user record by user_id for the Profile page."""
    return fetch_one(
        "SELECT user_id, full_name, email, phone, role, created_at FROM users WHERE user_id = %s",
        (user_id,),
    )


def update_user_profile(user_id: int, full_name: str, phone: str) -> tuple[bool, str]:
    """
    Update display name and phone number for the given user.

    Returns (True, "") on success, (False, error_message) on failure.
    """
    from modules.validators import validate_full_name, validate_phone

    ok, msg = validate_full_name(full_name)
    if not ok:
        return False, msg

    ok, msg = validate_phone(phone)
    if not ok:
        return False, msg

    result = execute_query(
        "UPDATE users SET full_name = %s, phone = %s WHERE user_id = %s",
        (full_name.strip(), phone.strip(), user_id),
    )
    if result is None:
        return False, "Profile update failed. Please try again."

    # Keep session name in sync
    st.session_state["user_name"] = full_name.strip()
    return True, ""


def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Change password after verifying the old one.

    Returns (True, "") on success, (False, error_message) on failure.
    """
    from modules.validators import validate_password

    user = fetch_one("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
    if user is None:
        return False, "User not found."

    if not verify_password(old_password, user["password_hash"]):
        return False, "Current password is incorrect."

    ok, msg = validate_password(new_password)
    if not ok:
        return False, msg

    new_hash = hash_password(new_password)
    result = execute_query(
        "UPDATE users SET password_hash = %s WHERE user_id = %s",
        (new_hash, user_id),
    )
    if result is None:
        return False, "Password change failed. Please try again."

    return True, ""
