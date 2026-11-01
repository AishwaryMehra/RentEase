"""
cards.py
========
Reusable Streamlit UI components for RentEase Rental Portal.

Exports:
  - property_card(prop, ...)        : Full property listing card for tenants.
  - owner_property_card(prop, ...)  : Owner's property card with management controls.
  - request_status_badge(status)    : Coloured inline status badge.
  - tenant_request_card(req, ...)   : Tenant's application summary card.
  - incoming_request_card(req, ...) : Owner's view of incoming tenant request.
  - empty_state(icon, message)      : Friendly empty-state placeholder.
"""

import datetime
import streamlit as st


# ------------------------------------------------------------------
# Colour / style constants
# ------------------------------------------------------------------
STATUS_COLOURS = {
    "Pending":   "#FFA500",   # amber
    "Approved":  "#28a745",   # green
    "Rejected":  "#dc3545",   # red
    "Cancelled": "#6c757d",   # grey
}

STATUS_ICONS = {
    "Pending":   "⏳",
    "Approved":  "✅",
    "Rejected":  "❌",
    "Cancelled": "🚫",
}

FURNISHING_ICONS = {
    "Furnished":       "🛋️",
    "Semi-Furnished":  "🪑",
    "Unfurnished":     "🏠",
}

TYPE_ICONS = {
    "Apartment":        "🏢",
    "Independent House":"🏡",
    "Villa":            "🏰",
    "Studio":           "🏙️",
    "PG":               "🛏️",
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _format_inr(amount) -> str:
    """Format a number as Indian Rupees with comma separation."""
    try:
        val = float(amount)
        if val >= 100_000:
            return f"₹{val/100_000:.2f}L"
        return f"₹{val:,.0f}"
    except (TypeError, ValueError):
        return str(amount)


def request_status_badge(status: str) -> str:
    """
    Return an HTML span styled as a coloured badge for the given status.
    Safe to use inside st.markdown(..., unsafe_allow_html=True).
    """
    colour = STATUS_COLOURS.get(status, "#999")
    icon   = STATUS_ICONS.get(status, "")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 10px;'
        f'border-radius:12px;font-size:0.8rem;font-weight:600;">'
        f'{icon} {status}</span>'
    )


def empty_state(icon: str = "🔍", message: str = "Nothing found.") -> None:
    """Render a centred empty-state message with an icon."""
    st.markdown(
        f"""
        <div style="text-align:center;padding:3rem 1rem;color:#888;">
            <div style="font-size:3rem;">{icon}</div>
            <p style="font-size:1rem;margin-top:0.5rem;">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _divider() -> None:
    st.markdown("<hr style='margin:0.5rem 0;border-color:#eee;'>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Tenant-facing property card
# ------------------------------------------------------------------

def property_card(
    prop: dict,
    tenant_id: int,
    on_request_callback,        # callable(property_id) -> opens booking form
    has_active_request: bool = False,
) -> None:
    """
    Render a full property card for tenant browse view.

    Parameters
    ----------
    prop                : Property dict from tenant_ops.search_properties().
    tenant_id           : Currently logged-in tenant's ID.
    on_request_callback : Function called when the tenant clicks "Apply Now".
    has_active_request  : Whether the tenant already applied for this property.
    """
    prop_id   = prop.get("property_id")
    title     = prop.get("title", "Untitled")
    city      = prop.get("city", "")
    p_type    = prop.get("property_type", "")
    furnish   = prop.get("furnishing_status", "")
    rent      = prop.get("rent_monthly", 0)
    deposit   = prop.get("security_deposit", 0)
    bedrooms  = prop.get("bedrooms", 0)
    bathrooms = prop.get("bathrooms", 0)
    image_url = prop.get("image_url") or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800"
    desc      = prop.get("description", "")
    owner_name= prop.get("owner_name", "Owner")
    avail     = prop.get("is_available", True)

    type_icon    = TYPE_ICONS.get(p_type, "🏠")
    furnish_icon = FURNISHING_ICONS.get(furnish, "")

    with st.container():
        # Card wrapper
        st.markdown(
            f"""
            <div style="border:1px solid #e0e0e0;border-radius:12px;
                        overflow:hidden;margin-bottom:1rem;
                        box-shadow:0 2px 8px rgba(0,0,0,0.07);">
            """,
            unsafe_allow_html=True,
        )

        img_col, info_col = st.columns([1, 2])

        with img_col:
            st.image(image_url, use_container_width=True)

        with info_col:
            # Header row
            avail_badge = (
                '<span style="background:#28a745;color:#fff;font-size:0.7rem;'
                'padding:2px 8px;border-radius:10px;margin-left:8px;">Available</span>'
                if avail else
                '<span style="background:#dc3545;color:#fff;font-size:0.7rem;'
                'padding:2px 8px;border-radius:10px;margin-left:8px;">Unavailable</span>'
            )
            st.markdown(
                f"<h4 style='margin-bottom:2px;'>{type_icon} {title} {avail_badge}</h4>"
                f"<p style='color:#666;margin:0;'>📍 {city}</p>",
                unsafe_allow_html=True,
            )
            st.markdown("")

            # Specs row
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🛏 Beds",   bedrooms)
            c2.metric("🚿 Baths",  bathrooms)
            c3.metric("Rent/mo",   _format_inr(rent))
            c4.metric("Deposit",   _format_inr(deposit))

            # Tags
            st.markdown(
                f'<span style="background:#f0f4ff;color:#3366cc;padding:3px 10px;'
                f'border-radius:10px;font-size:0.8rem;margin-right:6px;">'
                f'{p_type}</span>'
                f'<span style="background:#fff3e0;color:#e65100;padding:3px 10px;'
                f'border-radius:10px;font-size:0.8rem;">'
                f'{furnish_icon} {furnish}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("")

            # Description expander
            with st.expander("📄 View Description & Owner Details"):
                st.write(desc or "No description provided.")
                _divider()
                st.markdown(f"**🏠 Listed by:** {owner_name}")
                addr = prop.get("address", "")
                if addr:
                    st.markdown(f"**📬 Address:** {addr}")

            # Action button
            if has_active_request:
                st.info("✅ You have already applied for this property.", icon="ℹ️")
            elif not avail:
                st.warning("This property is currently not available.", icon="⚠️")
            else:
                if st.button("🏷️ Apply Now", key=f"apply_{prop_id}", type="primary"):
                    on_request_callback(prop_id)

        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Tenant's own request card
# ------------------------------------------------------------------

def tenant_request_card(
    req: dict,
    on_cancel_callback,         # callable(request_id)
) -> None:
    """
    Render a single rental-request card for the tenant's "My Requests" page.
    """
    req_id   = req.get("request_id")
    status   = req.get("status", "Pending")
    title    = req.get("property_title", "Unknown Property")
    city     = req.get("property_city", "")
    rent     = req.get("rent_monthly", 0)
    p_type   = req.get("property_type", "")
    msg      = req.get("message", "")
    move_in  = req.get("proposed_move_in_date", "")
    req_date = req.get("request_date", "")
    owner    = req.get("owner_name", "")
    o_phone  = req.get("owner_phone", "")
    o_email  = req.get("owner_email", "")
    img_url  = req.get("image_url") or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800"

    colour = STATUS_COLOURS.get(status, "#999")
    icon   = STATUS_ICONS.get(status, "")

    with st.container():
        st.markdown(
            f'<div style="border:1px solid {colour}44;border-left:5px solid {colour};'
            f'border-radius:10px;padding:0;margin-bottom:1rem;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.06);">',
            unsafe_allow_html=True,
        )

        c_img, c_info = st.columns([1, 3])
        with c_img:
            st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(
                f"<h4 style='margin-bottom:2px;'>{TYPE_ICONS.get(p_type,'🏠')} {title}</h4>"
                f"<p style='color:#666;margin:0;'>📍 {city} &nbsp;|&nbsp; Rent: {_format_inr(rent)}/mo</p>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**Status:** {request_status_badge(status)}",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Move-in date:** {move_in}  &nbsp;|&nbsp;  **Applied on:** {str(req_date)[:10]}")

            with st.expander("📋 View Application Details"):
                st.markdown(f"**Your message:** {msg or '_No message_'}")
                _divider()
                st.markdown(f"**Owner:** {owner}  |  📞 {o_phone}  |  ✉️ {o_email}")

            if status == "Pending":
                if st.button("🚫 Cancel Application", key=f"cancel_{req_id}", type="secondary"):
                    on_cancel_callback(req_id)

        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Owner's property management card
# ------------------------------------------------------------------

def owner_property_card(
    prop: dict,
    on_toggle_callback,         # callable(property_id, new_status)
    on_edit_callback,           # callable(property_id)
    on_delete_callback,         # callable(property_id)
) -> None:
    """
    Render an owner's property card with management controls.
    """
    prop_id   = prop.get("property_id")
    title     = prop.get("title", "Untitled")
    p_type    = prop.get("property_type", "")
    city      = prop.get("city", "")
    rent      = prop.get("rent_monthly", 0)
    deposit   = prop.get("security_deposit", 0)
    bedrooms  = prop.get("bedrooms", 0)
    bathrooms = prop.get("bathrooms", 0)
    furnish   = prop.get("furnishing_status", "")
    is_avail  = prop.get("is_available", True)
    image_url = prop.get("image_url") or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800"
    desc      = prop.get("description", "")

    border_colour = "#28a745" if is_avail else "#dc3545"

    with st.container():
        st.markdown(
            f'<div style="border:1px solid {border_colour}44;'
            f'border-left:5px solid {border_colour};border-radius:10px;'
            f'padding:0;margin-bottom:1rem;box-shadow:0 1px 4px rgba(0,0,0,0.06);">',
            unsafe_allow_html=True,
        )

        c_img, c_info = st.columns([1, 2])
        with c_img:
            st.image(image_url, use_container_width=True)

        with c_info:
            avail_label = "🟢 Available" if is_avail else "🔴 Unavailable"
            st.markdown(
                f"<h4 style='margin-bottom:2px;'>"
                f"{TYPE_ICONS.get(p_type,'🏠')} {title}</h4>"
                f"<p style='color:#666;margin:0;'>📍 {city} &nbsp;|&nbsp; {avail_label}</p>",
                unsafe_allow_html=True,
            )
            st.markdown("")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🛏 Beds",   bedrooms)
            m2.metric("🚿 Baths",  bathrooms)
            m3.metric("Rent/mo",   _format_inr(rent))
            m4.metric("Deposit",   _format_inr(deposit))

            st.markdown(
                f'<span style="background:#f0f4ff;color:#3366cc;padding:3px 10px;'
                f'border-radius:10px;font-size:0.8rem;margin-right:6px;">{p_type}</span>'
                f'<span style="background:#fff3e0;color:#e65100;padding:3px 10px;'
                f'border-radius:10px;font-size:0.8rem;">'
                f'{FURNISHING_ICONS.get(furnish,"")} {furnish}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("")

            with st.expander("📄 Description"):
                st.write(desc or "No description provided.")

            # Control buttons
            b1, b2, b3 = st.columns(3)
            toggle_label = "Mark Unavailable" if is_avail else "Mark Available"
            toggle_icon  = "🔴" if is_avail else "🟢"
            if b1.button(f"{toggle_icon} {toggle_label}", key=f"toggle_{prop_id}"):
                on_toggle_callback(prop_id, not is_avail)

            if b2.button("✏️ Edit", key=f"edit_{prop_id}"):
                on_edit_callback(prop_id)

            if b3.button("🗑️ Delete", key=f"delete_{prop_id}", type="secondary"):
                on_delete_callback(prop_id)

        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# Owner's incoming request card
# ------------------------------------------------------------------

def incoming_request_card(
    req: dict,
    on_approve_callback,        # callable(request_id)
    on_reject_callback,         # callable(request_id)
) -> None:
    """
    Render an incoming rental-request card for the owner's request manager.
    """
    req_id     = req.get("request_id")
    status     = req.get("status", "Pending")
    prop_title = req.get("property_title", "")
    prop_city  = req.get("property_city", "")
    rent       = req.get("rent_monthly", 0)
    t_name     = req.get("tenant_name", "")
    t_email    = req.get("tenant_email", "")
    t_phone    = req.get("tenant_phone", "")
    msg        = req.get("message", "")
    move_in    = req.get("proposed_move_in_date", "")
    req_date   = req.get("request_date", "")

    colour = STATUS_COLOURS.get(status, "#999")

    with st.container():
        st.markdown(
            f'<div style="border:1px solid {colour}55;border-left:5px solid {colour};'
            f'border-radius:10px;padding:1rem;margin-bottom:1rem;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.06);">',
            unsafe_allow_html=True,
        )

        hcol1, hcol2 = st.columns([3, 1])
        with hcol1:
            st.markdown(
                f"<h4 style='margin:0;'>🏠 {prop_title}</h4>"
                f"<p style='color:#666;margin:0;'>📍 {prop_city} &nbsp;|&nbsp; Rent: {_format_inr(rent)}/mo</p>",
                unsafe_allow_html=True,
            )
        with hcol2:
            st.markdown(
                f"**{request_status_badge(status)}**",
                unsafe_allow_html=True,
            )

        st.markdown("")

        d1, d2, d3 = st.columns(3)
        d1.markdown(f"**👤 Tenant**\n{t_name}")
        d2.markdown(f"**📞 Phone**\n{t_phone}")
        d3.markdown(f"**📅 Move-in**\n{move_in}")

        with st.expander("💬 Tenant's Message"):
            st.write(msg or "_No message provided_")
            st.caption(f"✉️ {t_email}  |  Applied: {str(req_date)[:10]}")

        if status == "Pending":
            a_col, r_col, _ = st.columns([1, 1, 2])
            if a_col.button("✅ Approve", key=f"approve_{req_id}", type="primary"):
                on_approve_callback(req_id)
            if r_col.button("❌ Reject",  key=f"reject_{req_id}", type="secondary"):
                on_reject_callback(req_id)

        st.markdown("</div>", unsafe_allow_html=True)
