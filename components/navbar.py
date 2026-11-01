"""
navbar.py
=========
Sidebar navigation router for RentEase Rental Portal.

Dynamically adapts the navigation menu to the current user's login state
and role. Returns the selected page name as a string so app.py can route
to the correct renderer.
"""

import streamlit as st
from modules.auth import (
    is_logged_in,
    get_current_role,
    get_current_user_name,
    logout,
)
from database.db_connection import test_connection


# ------------------------------------------------------------------
# Page definitions per role
# ------------------------------------------------------------------

TENANT_PAGES = [
    ("🔍", "Explore Properties"),
    ("📋", "My Requests"),
    ("👤", "Profile"),
]

OWNER_PAGES = [
    ("🏘️",  "My Listings"),
    ("➕",  "Add New Property"),
    ("📬",  "Incoming Requests"),
    ("👤",  "Profile"),
]

AUTH_PAGES = [
    ("🔐", "Login / Register"),
]


# ------------------------------------------------------------------
# Sidebar renderer
# ------------------------------------------------------------------

def render_navbar() -> str:
    """
    Render the sidebar navigation and return the selected page name.

    The sidebar contains:
    - Branding header with SDG 11 tagline.
    - User greeting (when logged in).
    - Role-appropriate navigation buttons.
    - DB connection status indicator.
    - Logout button (when logged in).
    """
    with st.sidebar:
        # ----- Branding -----
        st.markdown(
            """
            <div style='text-align:center;padding:10px 0 5px;'>
                <span style='font-size:2.5rem;'>🏠</span>
                <h2 style='margin:4px 0 0;font-weight:700;color:#1a3c5e;'>RentEase</h2>
                <p style='font-size:0.72rem;color:#888;margin:0;'>
                    🌍 UN SDG 11 – Sustainable Cities
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # ----- User greeting -----
        if is_logged_in():
            role = get_current_role()
            name = get_current_user_name()
            role_label = "🏢 Owner" if role == "owner" else "🏡 Tenant"
            st.markdown(
                f"<div style='background:#f0f7ff;padding:10px 12px;border-radius:8px;"
                f"margin-bottom:12px;'>"
                f"<b>👋 {name}</b><br>"
                f"<small style='color:#555;'>{role_label}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ----- Page selection -----
        if not is_logged_in():
            pages = AUTH_PAGES
        elif get_current_role() == "owner":
            pages = OWNER_PAGES
        else:
            pages = TENANT_PAGES

        # Initialize selected_page in session state
        if "selected_page" not in st.session_state:
            st.session_state["selected_page"] = pages[0][1]

        # Render nav buttons
        selected = st.session_state.get("selected_page", pages[0][1])

        for icon, label in pages:
            is_active = selected == label
            btn_style = (
                "background:#1a3c5e;color:#fff;border-radius:8px;"
                "padding:0.4rem 0.8rem;margin-bottom:4px;width:100%;"
                "border:none;cursor:pointer;text-align:left;font-weight:600;"
            ) if is_active else (
                "background:transparent;color:#1a3c5e;border-radius:8px;"
                "padding:0.4rem 0.8rem;margin-bottom:4px;width:100%;"
                "border:none;cursor:pointer;text-align:left;"
            )
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state["selected_page"] = label
                # Clear any edit state when navigating away
                for key in ["editing_property_id", "booking_property_id"]:
                    st.session_state.pop(key, None)
                st.rerun()

        st.markdown("---")

        # ----- Logout -----
        if is_logged_in():
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                logout()
                st.session_state["selected_page"] = "Login / Register"
                st.rerun()

        # ----- DB status indicator -----
        st.markdown("")
        db_ok = test_connection()
        if db_ok:
            st.markdown(
                "<div style='text-align:center;font-size:0.72rem;color:#28a745;'>"
                "🟢 Database Connected</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='text-align:center;font-size:0.72rem;color:#dc3545;'>"
                "🔴 Database Offline</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<div style='text-align:center;font-size:0.68rem;color:#aaa;margin-top:20px;'>"
            "© 2026 RentEase Portal<br>Built with ❤️ & Streamlit"
            "</div>",
            unsafe_allow_html=True,
        )

    # Return the current selection (may have been changed by a button click above)
    return st.session_state.get("selected_page", pages[0][1])
