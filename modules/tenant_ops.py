"""
tenant_ops.py
=============
Tenant-facing database operations for RentEase Rental Portal.

Covers:
  - Property discovery : Multi-criteria search with dynamic filters.
  - Request lifecycle  : Submit, view, and cancel rental applications.
  - Statistics         : Quick KPI counts for the tenant dashboard.
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple

from database.db_connection import execute_query, fetch_all, fetch_one


# ------------------------------------------------------------------
# Property discovery / search
# ------------------------------------------------------------------

def get_available_cities() -> List[str]:
    """
    Return a sorted list of distinct cities that have at least one
    available property listing.
    """
    rows = fetch_all(
        """SELECT DISTINCT city
           FROM properties
           WHERE is_available = TRUE
           ORDER BY city ASC"""
    )
    return [r["city"] for r in rows]


def get_all_cities() -> List[str]:
    """Return a sorted list of ALL distinct cities in the properties table."""
    rows = fetch_all("SELECT DISTINCT city FROM properties ORDER BY city ASC")
    return [r["city"] for r in rows]


def search_properties(
    city: Optional[str] = None,
    property_types: Optional[List[str]] = None,
    min_rent: float = 0,
    max_rent: float = 10_000_000,
    furnishing_statuses: Optional[List[str]] = None,
    min_bedrooms: int = 1,
    max_bedrooms: int = 20,
    only_available: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search for properties using optional multi-criteria filters.

    All parameters are optional. When a parameter is None or an empty list,
    the corresponding filter is skipped (match-all).

    Returns
    -------
    List of property dicts ordered by rent (ascending).
    """
    conditions = ["1 = 1"]
    params: List[Any] = []

    if only_available:
        conditions.append("p.is_available = TRUE")

    if city and city.strip():
        conditions.append("p.city = %s")
        params.append(city.strip())

    if property_types:
        placeholders = ", ".join(["%s"] * len(property_types))
        conditions.append(f"p.property_type IN ({placeholders})")
        params.extend(property_types)

    if furnishing_statuses:
        placeholders = ", ".join(["%s"] * len(furnishing_statuses))
        conditions.append(f"p.furnishing_status IN ({placeholders})")
        params.extend(furnishing_statuses)

    conditions.append("p.rent_monthly BETWEEN %s AND %s")
    params.extend([float(min_rent), float(max_rent)])

    conditions.append("p.bedrooms BETWEEN %s AND %s")
    params.extend([int(min_bedrooms), int(max_bedrooms)])

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT p.property_id,
               p.owner_id,
               p.title,
               p.description,
               p.property_type,
               p.address,
               p.city,
               p.rent_monthly,
               p.security_deposit,
               p.bedrooms,
               p.bathrooms,
               p.furnishing_status,
               p.is_available,
               p.image_url,
               p.created_at,
               u.full_name  AS owner_name,
               u.phone      AS owner_phone,
               u.email      AS owner_email
        FROM properties p
        JOIN users       u ON p.owner_id = u.user_id
        WHERE {where_clause}
        ORDER BY p.rent_monthly ASC
    """
    return fetch_all(sql, tuple(params))


def get_property_details(property_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch full details of a single property (joins owner info).
    """
    return fetch_one(
        """SELECT p.*,
                  u.full_name AS owner_name,
                  u.phone     AS owner_phone,
                  u.email     AS owner_email
           FROM properties p
           JOIN users       u ON p.owner_id = u.user_id
           WHERE p.property_id = %s""",
        (property_id,),
    )


# ------------------------------------------------------------------
# Rental request lifecycle
# ------------------------------------------------------------------

def has_pending_request(tenant_id: int, property_id: int) -> bool:
    """
    Return True if the tenant already has a Pending or Approved request
    for this property (prevents duplicate applications).
    """
    row = fetch_one(
        """SELECT request_id
           FROM rental_requests
           WHERE tenant_id = %s AND property_id = %s AND status IN ('Pending', 'Approved')""",
        (tenant_id, property_id),
    )
    return row is not None


def submit_rental_request(
    tenant_id: int,
    property_id: int,
    message: str,
    move_in_date: datetime.date,
) -> Tuple[bool, str]:
    """
    Submit a new rental application.

    Guards against:
    - Requesting an unavailable property.
    - Duplicate pending/approved requests.
    - Move-in date in the past.

    Returns (True, "") on success, (False, error_message) on failure.
    """
    # Check the property is still available
    prop = fetch_one(
        "SELECT is_available FROM properties WHERE property_id = %s",
        (property_id,),
    )
    if prop is None:
        return False, "Property not found."
    if not prop["is_available"]:
        return False, "This property is no longer available for rent."

    # Guard: move-in date must be today or in the future
    if move_in_date < datetime.date.today():
        return False, "Proposed move-in date cannot be in the past."

    # Guard: no duplicate active request
    if has_pending_request(tenant_id, property_id):
        return False, "You already have an active application for this property."

    result = execute_query(
        """INSERT INTO rental_requests
               (property_id, tenant_id, message, proposed_move_in_date, status)
           VALUES (%s, %s, %s, %s, 'Pending')""",
        (property_id, tenant_id, message.strip(), move_in_date),
    )
    if result is None:
        return False, "Failed to submit your request. Please try again."
    return True, ""


def get_tenant_requests(tenant_id: int) -> List[Dict[str, Any]]:
    """
    Fetch all rental requests submitted by this tenant.
    Joins property and owner info for full display.
    """
    return fetch_all(
        """SELECT rr.request_id,
                  rr.status,
                  rr.message,
                  rr.proposed_move_in_date,
                  rr.created_at         AS request_date,
                  rr.updated_at,
                  p.property_id,
                  p.title               AS property_title,
                  p.city                AS property_city,
                  p.address             AS property_address,
                  p.rent_monthly,
                  p.property_type,
                  p.image_url,
                  u.full_name           AS owner_name,
                  u.email               AS owner_email,
                  u.phone               AS owner_phone
           FROM rental_requests rr
           JOIN properties       p  ON rr.property_id = p.property_id
           JOIN users             u  ON p.owner_id     = u.user_id
           WHERE rr.tenant_id = %s
           ORDER BY rr.created_at DESC""",
        (tenant_id,),
    )


def cancel_request(request_id: int, tenant_id: int) -> Tuple[bool, str]:
    """
    Cancel a Pending rental request.
    Only the owning tenant can cancel, and only Pending requests.

    Returns (True, "") on success, (False, error_message) on failure.
    """
    row = fetch_one(
        """SELECT request_id FROM rental_requests
           WHERE request_id = %s AND tenant_id = %s AND status = 'Pending'""",
        (request_id, tenant_id),
    )
    if row is None:
        return False, "Request not found or cannot be cancelled at this stage."

    result = execute_query(
        "UPDATE rental_requests SET status = 'Cancelled' WHERE request_id = %s",
        (request_id,),
    )
    if result is None:
        return False, "Failed to cancel the request. Please try again."
    return True, ""


# ------------------------------------------------------------------
# Tenant dashboard statistics
# ------------------------------------------------------------------

def get_tenant_stats(tenant_id: int) -> Dict[str, int]:
    """
    Return quick KPI counts for the tenant dashboard header.

    Keys: total_requests, pending, approved, rejected
    """
    row = fetch_one(
        """SELECT
               COUNT(*)                                                  AS total_requests,
               SUM(CASE WHEN status = 'Pending'   THEN 1 ELSE 0 END)   AS pending,
               SUM(CASE WHEN status = 'Approved'  THEN 1 ELSE 0 END)   AS approved,
               SUM(CASE WHEN status = 'Rejected'  THEN 1 ELSE 0 END)   AS rejected
           FROM rental_requests
           WHERE tenant_id = %s""",
        (tenant_id,),
    )
    if row is None:
        return {"total_requests": 0, "pending": 0, "approved": 0, "rejected": 0}
    return {
        "total_requests": int(row["total_requests"] or 0),
        "pending":        int(row["pending"]        or 0),
        "approved":       int(row["approved"]       or 0),
        "rejected":       int(row["rejected"]       or 0),
    }
