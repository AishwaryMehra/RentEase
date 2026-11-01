"""
app.py
======
RentEase Rental Portal – Main Streamlit Application Entry Point.

Manages:
  - Global session-state initialisation.
  - Page configuration and theming.
  - Sidebar navigation routing.
  - Per-page rendering dispatched to inline renderers.
  - All Streamlit UI pages for both tenant and owner roles.
"""

import datetime
import streamlit as st

# ------------------------------------------------------------------
# Page config MUST be the very first Streamlit call
# ------------------------------------------------------------------
st.set_page_config(
    page_title="RentEase | Rental Portal",
    layout="wide",
    page_icon="🏠",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Module imports (after set_page_config)
# ------------------------------------------------------------------
from modules.auth import (
    is_logged_in, get_current_role, get_current_user_id,
    get_current_user_name, login_user, register_user,
    get_user_profile, update_user_profile, change_password,
)
from modules.tenant_ops import (
    search_properties, get_available_cities, get_all_cities,
    submit_rental_request, get_tenant_requests,
    cancel_request, get_tenant_stats, has_pending_request,
)
from modules.owner_ops import (
    add_property, get_owner_properties, update_property,
    delete_property, toggle_availability,
    get_incoming_requests, approve_request, reject_request,
    get_owner_stats,
)
from components.navbar import render_navbar
from components.cards import (
    property_card, tenant_request_card,
    owner_property_card, incoming_request_card,
    empty_state, request_status_badge,
)


# ------------------------------------------------------------------
# Global CSS injection
# ------------------------------------------------------------------
def _inject_css() -> None:
    st.markdown(
        """
        <style>
        /* Remove default Streamlit top padding */
        .block-container { padding-top: 1.5rem !important; }

        /* Metric label size */
        [data-testid="stMetricLabel"] { font-size: 0.78rem; }

        /* Button tweaks */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
        }

        /* Sidebar header */
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        /* Tab font */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.95rem;
            font-weight: 600;
        }

        /* Expander border */
        details { border-radius: 8px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Session-state initialisation
# ------------------------------------------------------------------
def _init_session_state() -> None:
    defaults = {
        "logged_in":           False,
        "user_id":             0,
        "user_name":           "",
        "role":                "",
        "email":               "",
        "selected_page":       "Login / Register",
        "booking_property_id": None,
        "editing_property_id": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ====================================================================
# PAGE: LOGIN / REGISTER
# ====================================================================
def page_auth() -> None:
    st.markdown("## 🔐 Welcome to RentEase")
    st.markdown(
        "_A smarter way to find and list rental properties — "
        "supporting UN SDG 11: Sustainable Cities & Communities._"
    )
    st.markdown("")

    login_tab, register_tab = st.tabs(["🔑 Login", "📝 Register"])

    # ---- Login Tab ----
    with login_tab:
        st.markdown("### Sign in to your account")
        with st.form("login_form", clear_on_submit=False):
            email    = st.text_input("📧 Email Address", placeholder="you@example.com")
            password = st.text_input("🔒 Password", type="password", placeholder="Your password")
            submitted = st.form_submit_button("Login →", type="primary", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                ok, msg = login_user(email, password)
                if ok:
                    role = get_current_role()
                    st.session_state["selected_page"] = (
                        "My Listings" if role == "owner" else "Explore Properties"
                    )
                    st.success(f"Welcome back, {get_current_user_name()}! 🎉")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    # ---- Register Tab ----
    with register_tab:
        st.markdown("### Create a new account")
        with st.form("register_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                r_name  = st.text_input("👤 Full Name",   placeholder="Arjun Nair")
                r_email = st.text_input("📧 Email",        placeholder="arjun@example.com")
            with col2:
                r_phone = st.text_input("📞 Phone (10 digits)", placeholder="9876543210")
                r_role  = st.selectbox("🎭 Register as", ["tenant", "owner"],
                                       format_func=lambda x: "🏡 Tenant" if x == "tenant" else "🏢 Owner")
            r_pass  = st.text_input("🔒 Password (min 6 chars)", type="password")
            r_pass2 = st.text_input("🔒 Confirm Password",        type="password")
            reg_btn = st.form_submit_button("Create Account →", type="primary", use_container_width=True)

        if reg_btn:
            if r_pass != r_pass2:
                st.error("❌ Passwords do not match.")
            else:
                ok, msg = register_user(r_name, r_email, r_pass, r_phone, r_role)
                if ok:
                    st.success("✅ Account created! Please log in using the Login tab.")
                else:
                    st.error(f"❌ {msg}")


# ====================================================================
# PAGE: EXPLORE PROPERTIES (Tenant)
# ====================================================================
def page_explore_properties() -> None:
    uid = get_current_user_id()
    st.markdown("## 🔍 Explore Properties")
    st.markdown("Browse available listings across India. Use the filters below to narrow your search.")

    # ---- Filters sidebar panel ----
    with st.expander("🎛️ Search & Filter", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            cities = ["All Cities"] + get_all_cities()
            sel_city = st.selectbox("📍 City", cities)
            sel_city = None if sel_city == "All Cities" else sel_city

            p_types = ["Apartment", "Independent House", "Villa", "Studio", "PG"]
            sel_types = st.multiselect("🏠 Property Type", p_types, default=[])

        with f2:
            furnish_opts = ["Furnished", "Semi-Furnished", "Unfurnished"]
            sel_furnish = st.multiselect("🛋️ Furnishing", furnish_opts, default=[])
            sel_beds = st.slider("🛏️ Min Bedrooms", 1, 10, 1)

        with f3:
            rent_range = st.slider(
                "💰 Monthly Rent (₹)",
                min_value=1_000,
                max_value=500_000,
                value=(5_000, 100_000),
                step=1_000,
                format="₹%d",
            )

        search_btn = st.button("🔍 Search Properties", type="primary")

    # ---- Perform search (auto on load and on button click) ----
    properties = search_properties(
        city=sel_city,
        property_types=sel_types or None,
        min_rent=rent_range[0],
        max_rent=rent_range[1],
        furnishing_statuses=sel_furnish or None,
        min_bedrooms=sel_beds,
        only_available=True,
    )

    st.markdown(f"**{len(properties)} propert{'y' if len(properties)==1 else 'ies'} found**")
    st.markdown("---")

    # ---- Booking modal (inline form) ----
    booking_id = st.session_state.get("booking_property_id")
    if booking_id is not None:
        _render_booking_form(booking_id, uid)
        st.markdown("---")

    if not properties:
        empty_state("🏚️", "No properties match your current filters. Try widening your search.")
        return

    for prop in properties:
        active = has_pending_request(uid, prop["property_id"])
        property_card(
            prop=prop,
            tenant_id=uid,
            on_request_callback=lambda pid: _set_booking_id(pid),
            has_active_request=active,
        )


def _set_booking_id(property_id: int) -> None:
    st.session_state["booking_property_id"] = property_id
    st.rerun()


def _render_booking_form(property_id: int, tenant_id: int) -> None:
    """Inline booking / application form."""
    from modules.tenant_ops import get_property_details
    prop = get_property_details(property_id)
    if not prop:
        st.error("Property not found.")
        st.session_state["booking_property_id"] = None
        return

    st.markdown(f"### 📝 Apply for: **{prop['title']}**")
    with st.form(f"booking_form_{property_id}"):
        move_in = st.date_input(
            "📅 Proposed Move-in Date",
            min_value=datetime.date.today() + datetime.timedelta(days=1),
            value=datetime.date.today() + datetime.timedelta(days=7),
        )
        message = st.text_area(
            "💬 Message to Owner (optional)",
            placeholder="Introduce yourself, mention your occupation, any questions...",
            max_chars=2000,
        )
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("🚀 Submit Application", type="primary")
        cancel = c2.form_submit_button("✖ Cancel")

    if cancel:
        st.session_state["booking_property_id"] = None
        st.rerun()

    if submit:
        ok, msg = submit_rental_request(tenant_id, property_id, message, move_in)
        if ok:
            st.success("✅ Your application has been submitted! The owner will review it shortly.")
            st.session_state["booking_property_id"] = None
            st.rerun()
        else:
            st.error(f"❌ {msg}")


# ====================================================================
# PAGE: MY REQUESTS (Tenant)
# ====================================================================
def page_my_requests() -> None:
    uid = get_current_user_id()
    st.markdown("## 📋 My Rental Applications")

    # KPIs
    stats = get_tenant_stats(uid)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📨 Total Applied",  stats["total_requests"])
    c2.metric("⏳ Pending",        stats["pending"])
    c3.metric("✅ Approved",       stats["approved"])
    c4.metric("❌ Rejected",       stats["rejected"])

    st.markdown("---")

    requests = get_tenant_requests(uid)
    if not requests:
        empty_state("📭", "You haven't submitted any rental applications yet.")
        return

    # Filter by status
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Pending", "Approved", "Rejected", "Cancelled"],
        index=0,
    )
    filtered = requests if status_filter == "All" else [
        r for r in requests if r["status"] == status_filter
    ]

    if not filtered:
        empty_state("🔎", f"No {status_filter.lower()} applications found.")
        return

    for req in filtered:
        tenant_request_card(
            req=req,
            on_cancel_callback=lambda rid: _cancel_request(rid, uid),
        )


def _cancel_request(request_id: int, tenant_id: int) -> None:
    ok, msg = cancel_request(request_id, tenant_id)
    if ok:
        st.success("Application cancelled successfully.")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


# ====================================================================
# PAGE: MY LISTINGS (Owner)
# ====================================================================
def page_my_listings() -> None:
    uid = get_current_user_id()
    st.markdown("## 🏘️ My Property Listings")

    # KPIs
    stats = get_owner_stats(uid)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏠 Total Listings",     stats["total_listings"])
    c2.metric("🟢 Available",          stats["available"])
    c3.metric("⏳ Pending Requests",   stats["pending_requests"])
    c4.metric("✅ Approved Rentals",   stats["approved_requests"])

    st.markdown("---")

    # ---- Inline edit form ----
    editing_id = st.session_state.get("editing_property_id")
    if editing_id is not None:
        _render_edit_property_form(editing_id, uid)
        st.markdown("---")

    properties = get_owner_properties(uid)
    if not properties:
        empty_state("🏗️", "You haven't listed any properties yet. Use 'Add New Property' to get started.")
        return

    for prop in properties:
        owner_property_card(
            prop=prop,
            on_toggle_callback=lambda pid, ns: _toggle_property(pid, uid, ns),
            on_edit_callback=lambda pid: _set_edit_id(pid),
            on_delete_callback=lambda pid: _delete_property(pid, uid),
        )


def _set_edit_id(property_id: int) -> None:
    st.session_state["editing_property_id"] = property_id
    st.rerun()


def _toggle_property(property_id: int, owner_id: int, new_status: bool) -> None:
    ok, msg = toggle_availability(property_id, owner_id, new_status)
    if ok:
        label = "available" if new_status else "unavailable"
        st.success(f"Property marked as {label}.")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


def _delete_property(property_id: int, owner_id: int) -> None:
    ok, msg = delete_property(property_id, owner_id)
    if ok:
        st.success("Property deleted successfully.")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


def _render_edit_property_form(property_id: int, owner_id: int) -> None:
    """Inline property edit form."""
    from modules.owner_ops import get_property_by_id
    prop = get_property_by_id(property_id)
    if not prop:
        st.error("Property not found.")
        st.session_state["editing_property_id"] = None
        return

    st.markdown(f"### ✏️ Editing: {prop['title']}")
    with st.form(f"edit_form_{property_id}"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", value=prop["title"])
            p_type = st.selectbox(
                "Property Type",
                ["Apartment", "Independent House", "Villa", "Studio", "PG"],
                index=["Apartment", "Independent House", "Villa", "Studio", "PG"].index(prop["property_type"]),
            )
            city    = st.text_input("City",    value=prop["city"])
            address = st.text_area("Address", value=prop["address"], height=80)
        with col2:
            rent    = st.number_input("Monthly Rent (₹)", value=float(prop["rent_monthly"]),   min_value=1000.0, step=500.0)
            deposit = st.number_input("Security Deposit (₹)", value=float(prop["security_deposit"]), min_value=0.0, step=1000.0)
            beds    = st.number_input("Bedrooms",  value=int(prop["bedrooms"]),  min_value=1, max_value=20, step=1)
            baths   = st.number_input("Bathrooms", value=int(prop["bathrooms"]), min_value=1, max_value=20, step=1)
        furnish = st.selectbox(
            "Furnishing Status",
            ["Furnished", "Semi-Furnished", "Unfurnished"],
            index=["Furnished", "Semi-Furnished", "Unfurnished"].index(prop["furnishing_status"]),
        )
        desc      = st.text_area("Description", value=prop.get("description", ""), height=100)
        image_url = st.text_input("Image URL", value=prop.get("image_url", ""))

        s_col, c_col = st.columns(2)
        save   = s_col.form_submit_button("💾 Save Changes", type="primary")
        cancel = c_col.form_submit_button("✖ Cancel")

    if cancel:
        st.session_state["editing_property_id"] = None
        st.rerun()

    if save:
        ok, msg = update_property(
            property_id, owner_id,
            title, desc, p_type, address, city,
            rent, deposit, int(beds), int(baths),
            furnish, image_url,
        )
        if ok:
            st.success("✅ Property updated successfully!")
            st.session_state["editing_property_id"] = None
            st.rerun()
        else:
            st.error(f"❌ {msg}")


# ====================================================================
# PAGE: ADD NEW PROPERTY (Owner)
# ====================================================================
def page_add_property() -> None:
    uid = get_current_user_id()
    st.markdown("## ➕ Add a New Property Listing")
    st.markdown("Fill in the details below to list your property on RentEase.")

    with st.form("add_property_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("🏷️ Property Title *",
                                  placeholder="e.g. 2BHK Modern Apartment in Koramangala")
            p_type = st.selectbox("🏠 Property Type *",
                                  ["Apartment", "Independent House", "Villa", "Studio", "PG"])
            city    = st.text_input("📍 City *",    placeholder="Bengaluru")
            address = st.text_area("📬 Full Address *",
                                   placeholder="Street, Area, City – PIN", height=90)

        with col2:
            rent    = st.number_input("💰 Monthly Rent (₹) *",    min_value=1000.0, value=15000.0, step=500.0)
            deposit = st.number_input("🔐 Security Deposit (₹) *", min_value=0.0,    value=30000.0, step=1000.0)
            beds    = st.number_input("🛏️ Bedrooms *",   min_value=1, max_value=20, value=2, step=1)
            baths   = st.number_input("🚿 Bathrooms *",  min_value=1, max_value=20, value=1, step=1)

        furnish = st.selectbox("🛋️ Furnishing Status *",
                               ["Furnished", "Semi-Furnished", "Unfurnished"])
        desc      = st.text_area("📄 Description",
                                 placeholder="Describe the property: amenities, surroundings, rules…",
                                 height=120)
        image_url = st.text_input(
            "🖼️ Image URL (optional)",
            placeholder="https://images.unsplash.com/…",
        )

        submitted = st.form_submit_button("🚀 Publish Listing", type="primary", use_container_width=True)

    if submitted:
        ok, msg = add_property(
            owner_id=uid,
            title=title,
            description=desc,
            property_type=p_type,
            address=address,
            city=city,
            rent_monthly=rent,
            security_deposit=deposit,
            bedrooms=int(beds),
            bathrooms=int(baths),
            furnishing_status=furnish,
            image_url=image_url,
        )
        if ok:
            st.success("🎉 Your property has been listed successfully! Switch to 'My Listings' to manage it.")
            st.balloons()
        else:
            st.error(f"❌ {msg}")


# ====================================================================
# PAGE: INCOMING REQUESTS (Owner)
# ====================================================================
def page_incoming_requests() -> None:
    uid = get_current_user_id()
    st.markdown("## 📬 Incoming Rental Requests")
    st.markdown("Review and respond to tenant applications for your properties.")

    requests = get_incoming_requests(uid)
    if not requests:
        empty_state("📭", "No rental requests received yet. Once tenants apply, they will appear here.")
        return

    # Filter controls
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Pending", "Approved", "Rejected"],
        index=0,
    )
    filtered = requests if status_filter == "All" else [
        r for r in requests if r["status"] == status_filter
    ]

    st.markdown(f"**Showing {len(filtered)} of {len(requests)} request(s)**")
    st.markdown("---")

    if not filtered:
        empty_state("🔎", f"No {status_filter.lower()} requests found.")
        return

    for req in filtered:
        incoming_request_card(
            req=req,
            on_approve_callback=lambda rid: _approve_req(rid, uid),
            on_reject_callback=lambda rid: _reject_req(rid, uid),
        )


def _approve_req(request_id: int, owner_id: int) -> None:
    ok, msg = approve_request(request_id, owner_id)
    if ok:
        st.success("✅ Request approved! The property has been marked as unavailable and other pending requests have been automatically rejected.")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


def _reject_req(request_id: int, owner_id: int) -> None:
    ok, msg = reject_request(request_id, owner_id)
    if ok:
        st.warning("Request rejected.")
        st.rerun()
    else:
        st.error(f"❌ {msg}")


# ====================================================================
# PAGE: PROFILE (Both roles)
# ====================================================================
def page_profile() -> None:
    uid = get_current_user_id()
    st.markdown("## 👤 My Profile")

    user = get_user_profile(uid)
    if not user:
        st.error("Could not load profile. Please log in again.")
        return

    tab_info, tab_pwd = st.tabs(["📋 Profile Information", "🔒 Change Password"])

    with tab_info:
        st.markdown("#### Update your personal details")
        with st.form("profile_form"):
            c1, c2 = st.columns(2)
            new_name  = c1.text_input("👤 Full Name",    value=user["full_name"])
            new_phone = c2.text_input("📞 Phone Number", value=user["phone"])
            st.text_input("📧 Email (cannot be changed)", value=user["email"], disabled=True)
            role_label = "🏢 Owner" if user["role"] == "owner" else "🏡 Tenant"
            st.text_input("🎭 Role", value=role_label, disabled=True)
            joined = str(user.get("created_at", ""))[:10]
            st.text_input("📅 Member Since", value=joined, disabled=True)
            save = st.form_submit_button("💾 Save Changes", type="primary")

        if save:
            ok, msg = update_user_profile(uid, new_name, new_phone)
            if ok:
                st.success("✅ Profile updated successfully!")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    with tab_pwd:
        st.markdown("#### Change your password")
        with st.form("change_pwd_form"):
            old_pwd  = st.text_input("🔒 Current Password", type="password")
            new_pwd  = st.text_input("🆕 New Password (min 6 chars)", type="password")
            new_pwd2 = st.text_input("🔁 Confirm New Password", type="password")
            pwd_btn  = st.form_submit_button("🔐 Update Password", type="primary")

        if pwd_btn:
            if new_pwd != new_pwd2:
                st.error("❌ New passwords do not match.")
            else:
                ok, msg = change_password(uid, old_pwd, new_pwd)
                if ok:
                    st.success("✅ Password changed successfully! Please log in again with your new password.")
                else:
                    st.error(f"❌ {msg}")


# ====================================================================
# MAIN ROUTER
# ====================================================================
def main() -> None:
    _init_session_state()
    _inject_css()

    # Render sidebar navigation and get selected page
    selected_page = render_navbar()

    # Unauthenticated
    if not is_logged_in():
        page_auth()
        return

    role = get_current_role()

    # ---- Tenant routes ----
    if role == "tenant":
        if selected_page == "Explore Properties":
            page_explore_properties()
        elif selected_page == "My Requests":
            page_my_requests()
        elif selected_page == "Profile":
            page_profile()
        else:
            # Fallback
            page_explore_properties()

    # ---- Owner routes ----
    elif role == "owner":
        if selected_page == "My Listings":
            page_my_listings()
        elif selected_page == "Add New Property":
            page_add_property()
        elif selected_page == "Incoming Requests":
            page_incoming_requests()
        elif selected_page == "Profile":
            page_profile()
        else:
            page_my_listings()

    else:
        st.error("Unknown role. Please log out and log in again.")


# ====================================================================
if __name__ == "__main__":
    main()
