"""
owner_ops.py
============
Owner-facing database operations for RentEase Rental Portal.

Covers:
  - Listing management  : Create, read, update, delete properties.
  - Availability toggle : Mark a property as available / unavailable.
  - Request management  : View incoming applications, approve, reject.
  - Statistics          : Quick KPI counts for the owner dashboard.
"""

from typing import Any, Dict, List, Optional, Tuple

from database.db_connection import execute_query, fetch_all, fetch_one
from modules.validators import validate_property_form

# ------------------------------------------------------------------
# Default fallback image
# ------------------------------------------------------------------
DEFAULT_IMAGE_URL = "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800"


# ------------------------------------------------------------------
# Property CRUD
# ------------------------------------------------------------------

def add_property(
    owner_id: int,
    title: str,
    description: str,
    property_type: str,
    address: str,
    city: str,
    rent_monthly: float,
    security_deposit: float,
    bedrooms: int,
    bathrooms: int,
    furnishing_status: str,
    image_url: str = "",
) -> Tuple[bool, str]:
    """
    Create a new property listing for the given owner.

    Returns
    -------
    (True,  "")            on success.
    (False, error_message) on validation or DB failure.
    """
    ok, msg = validate_property_form(
        title, city, address, rent_monthly, security_deposit, bedrooms, bathrooms, image_url
    )
    if not ok:
        return False, msg

    if not image_url.strip():
        image_url = DEFAULT_IMAGE_URL

    new_id = execute_query(
        """INSERT INTO properties
               (owner_id, title, description, property_type, address, city,
                rent_monthly, security_deposit, bedrooms, bathrooms,
                furnishing_status, is_available, image_url)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s)""",
        (
            owner_id,
            title.strip(),
            description.strip(),
            property_type,
            address.strip(),
            city.strip(),
            float(rent_monthly),
            float(security_deposit),
            int(bedrooms),
            int(bathrooms),
            furnishing_status,
            image_url.strip() or DEFAULT_IMAGE_URL,
        ),
    )
    if new_id is None:
        return False, "Failed to save the property listing. Please try again."
    return True, ""


def get_owner_properties(owner_id: int) -> List[Dict[str, Any]]:
    """Fetch all property listings belonging to the specified owner."""
    return fetch_all(
        """SELECT property_id, title, property_type, city, address,
                  rent_monthly, security_deposit, bedrooms, bathrooms,
                  furnishing_status, is_available, image_url, description, created_at
           FROM properties
           WHERE owner_id = %s
           ORDER BY created_at DESC""",
        (owner_id,),
    )


def get_property_by_id(property_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single property record by its ID."""
    return fetch_one(
        """SELECT * FROM properties WHERE property_id = %s""",
        (property_id,),
    )


def update_property(
    property_id: int,
    owner_id: int,
    title: str,
    description: str,
    property_type: str,
    address: str,
    city: str,
    rent_monthly: float,
    security_deposit: float,
    bedrooms: int,
    bathrooms: int,
    furnishing_status: str,
    image_url: str = "",
) -> Tuple[bool, str]:
    """
    Update an existing property listing.
    owner_id is checked to prevent cross-user edits.
    """
    ok, msg = validate_property_form(
        title, city, address, rent_monthly, security_deposit, bedrooms, bathrooms, image_url
    )
    if not ok:
        return False, msg

    if not image_url.strip():
        image_url = DEFAULT_IMAGE_URL

    result = execute_query(
        """UPDATE properties
           SET title=%s, description=%s, property_type=%s, address=%s, city=%s,
               rent_monthly=%s, security_deposit=%s, bedrooms=%s, bathrooms=%s,
               furnishing_status=%s, image_url=%s
           WHERE property_id=%s AND owner_id=%s""",
        (
            title.strip(),
            description.strip(),
            property_type,
            address.strip(),
            city.strip(),
            float(rent_monthly),
            float(security_deposit),
            int(bedrooms),
            int(bathrooms),
            furnishing_status,
            image_url.strip(),
            property_id,
            owner_id,
        ),
    )
    if result is None:
        return False, "Failed to update the property. Please try again."
    return True, ""


def delete_property(property_id: int, owner_id: int) -> Tuple[bool, str]:
    """
    Delete a property listing. Cascades to rental_requests automatically (FK cascade).
    owner_id guard prevents unauthorized deletion.
    """
    result = execute_query(
        "DELETE FROM properties WHERE property_id = %s AND owner_id = %s",
        (property_id, owner_id),
    )
    if result is None:
        return False, "Failed to delete the property. Please try again."
    return True, ""


def toggle_availability(property_id: int, owner_id: int, new_status: bool) -> Tuple[bool, str]:
    """
    Flip the is_available flag for a property.

    Parameters
    ----------
    new_status : True = mark as available, False = mark as unavailable.
    """
    result = execute_query(
        "UPDATE properties SET is_available = %s WHERE property_id = %s AND owner_id = %s",
        (new_status, property_id, owner_id),
    )
    if result is None:
        return False, "Could not update availability. Please try again."
    return True, ""


# ------------------------------------------------------------------
# Request management (Owner side)
# ------------------------------------------------------------------

def get_incoming_requests(owner_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all rental requests for properties owned by owner_id.
    Joins properties and users (tenant) for rich display.
    """
    return fetch_all(
        """SELECT rr.request_id,
                  rr.status,
                  rr.message,
                  rr.proposed_move_in_date,
                  rr.created_at          AS request_date,
                  rr.updated_at,
                  p.property_id,
                  p.title                AS property_title,
                  p.city                 AS property_city,
                  p.rent_monthly,
                  p.is_available,
                  u.user_id              AS tenant_id,
                  u.full_name            AS tenant_name,
                  u.email                AS tenant_email,
                  u.phone                AS tenant_phone
           FROM rental_requests rr
           JOIN properties       p  ON rr.property_id = p.property_id
           JOIN users             u  ON rr.tenant_id   = u.user_id
           WHERE p.owner_id = %s
           ORDER BY rr.created_at DESC""",
        (owner_id,),
    )


def approve_request(request_id: int, owner_id: int) -> Tuple[bool, str]:
    """
    Approve a rental request.
    - Sets request status to 'Approved'.
    - Marks the linked property as unavailable.
    - Rejects all other pending requests for the same property.
    Ownership is verified via a sub-join.
    """
    # Verify the request belongs to this owner and fetch property_id
    row = fetch_one(
        """SELECT rr.request_id, rr.property_id, p.owner_id
           FROM rental_requests rr
           JOIN properties p ON rr.property_id = p.property_id
           WHERE rr.request_id = %s AND p.owner_id = %s AND rr.status = 'Pending'""",
        (request_id, owner_id),
    )
    if row is None:
        return False, "Request not found or already processed."

    property_id = row["property_id"]

    # Approve this request
    r1 = execute_query(
        "UPDATE rental_requests SET status = 'Approved' WHERE request_id = %s",
        (request_id,),
    )
    if r1 is None:
        return False, "Failed to approve the request."

    # Mark property as unavailable
    execute_query(
        "UPDATE properties SET is_available = FALSE WHERE property_id = %s",
        (property_id,),
    )

    # Reject all other pending requests for the same property
    execute_query(
        """UPDATE rental_requests
           SET status = 'Rejected'
           WHERE property_id = %s AND request_id != %s AND status = 'Pending'""",
        (property_id, request_id),
    )

    return True, ""


def reject_request(request_id: int, owner_id: int) -> Tuple[bool, str]:
    """
    Reject a rental request (ownership verified via join).
    """
    row = fetch_one(
        """SELECT rr.request_id
           FROM rental_requests rr
           JOIN properties p ON rr.property_id = p.property_id
           WHERE rr.request_id = %s AND p.owner_id = %s AND rr.status = 'Pending'""",
        (request_id, owner_id),
    )
    if row is None:
        return False, "Request not found or already processed."

    result = execute_query(
        "UPDATE rental_requests SET status = 'Rejected' WHERE request_id = %s",
        (request_id,),
    )
    if result is None:
        return False, "Failed to reject the request."
    return True, ""


# ------------------------------------------------------------------
# Owner dashboard statistics
# ------------------------------------------------------------------

def get_owner_stats(owner_id: int) -> Dict[str, int]:
    """
    Return quick KPI counts for the owner dashboard header.

    Keys: total_listings, available, pending_requests, approved_requests
    """
    row = fetch_one(
        """SELECT
               COUNT(*)                                              AS total_listings,
               SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END)   AS available
           FROM properties
           WHERE owner_id = %s""",
        (owner_id,),
    )
    req_row = fetch_one(
        """SELECT
               SUM(CASE WHEN rr.status = 'Pending'  THEN 1 ELSE 0 END) AS pending_requests,
               SUM(CASE WHEN rr.status = 'Approved' THEN 1 ELSE 0 END) AS approved_requests
           FROM rental_requests rr
           JOIN properties p ON rr.property_id = p.property_id
           WHERE p.owner_id = %s""",
        (owner_id,),
    )
    return {
        "total_listings":   int(row["total_listings"]    or 0) if row else 0,
        "available":        int(row["available"]         or 0) if row else 0,
        "pending_requests": int(req_row["pending_requests"]  or 0) if req_row else 0,
        "approved_requests":int(req_row["approved_requests"] or 0) if req_row else 0,
    }
