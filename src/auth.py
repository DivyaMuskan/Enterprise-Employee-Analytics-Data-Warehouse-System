"""Streamlit authentication and role permissions."""

import hashlib
import hmac
import secrets
from collections.abc import Mapping

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


PASSWORD_HASH_ITERATIONS = 600_000
ROLE_PERMISSIONS = {
    "hr": frozenset({"read", "write"}),
    "manager": frozenset({"read"}),
    "employee": frozenset({"read"}),
}


def hash_password(password: str) -> str:
    """Create a salted PBKDF2 hash suitable for storing in Streamlit secrets."""
    if not password:
        raise ValueError("Password must not be empty.")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), PASSWORD_HASH_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a PBKDF2 password hash stored in Streamlit secrets."""
    try:
        algorithm, iterations_text, salt, expected_digest = encoded_hash.split("$", 3)
        iterations = int(iterations_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Password hash must use the configured PBKDF2 format.") from exc

    if (
        algorithm != "pbkdf2_sha256"
        or iterations < 100_000
        or iterations > 2_000_000
        or not salt
        or len(expected_digest) != 64
    ):
        raise ValueError("Password hash must use the configured PBKDF2 format.")

    try:
        bytes.fromhex(salt)
        bytes.fromhex(expected_digest)
    except ValueError as exc:
        raise ValueError("Password hash contains invalid hexadecimal data.") from exc

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), iterations
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def has_permission(role: str, permission: str) -> bool:
    """Return whether a configured role grants the requested permission."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def verify_user_login(account: Mapping[str, str], password: str, selected_role: str) -> bool:
    """Verify credentials and ensure the selected role matches the configured account."""
    role = account.get("role")
    if role not in ROLE_PERMISSIONS:
        raise ValueError("Account has an invalid configured role.")
    return role == selected_role and verify_password(password, account.get("password_hash"))


def _configured_users() -> Mapping:
    try:
        users = st.secrets["users"]
    except (KeyError, StreamlitSecretNotFoundError):
        return {}

    if not isinstance(users, Mapping):
        raise ValueError("The [users] Streamlit secrets section must contain user tables.")
    return users


def _render_login_page(users: Mapping, configured_usernames: dict) -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            [data-testid="stHeader"] {
                background: transparent;
            }
            .block-container {
                max-width: 1180px;
                padding-top: 2rem;
                padding-bottom: 3rem;
            }
            .login-hero {
                display: flex;
                min-height: 510px;
                flex-direction: column;
                justify-content: space-between;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 24px;
                background:
                    radial-gradient(circle at 85% 12%, rgba(96, 165, 250, 0.42), transparent 30%),
                    linear-gradient(145deg, #102347 0%, #173d79 55%, #2563eb 100%);
                box-shadow: 0 24px 60px rgba(23, 43, 77, 0.2);
                padding: 2.2rem;
                color: #fff;
            }
            .login-brand {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                color: #fff;
                font-size: 0.9rem;
                font-weight: 700;
                letter-spacing: 0.015em;
            }
            .login-mark {
                display: grid;
                width: 42px;
                height: 42px;
                place-items: center;
                border: 1px solid rgba(255, 255, 255, 0.35);
                border-radius: 13px;
                background: rgba(255, 255, 255, 0.14);
                color: #fff;
                font-size: 0.95rem;
                font-weight: 800;
            }
            .login-hero-copy {
                margin: 3.5rem 0;
            }
            .login-eyebrow {
                color: #bfdbfe;
                font-size: 0.72rem;
                font-weight: 750;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }
            .login-hero-copy h2 {
                margin: 0.8rem 0;
                color: #fff;
                font-size: clamp(2rem, 3.2vw, 2.8rem);
                font-weight: 750;
                letter-spacing: -0.05em;
                line-height: 1.08;
            }
            .login-hero-copy p {
                max-width: 340px;
                color: #dbeafe;
                font-size: 0.98rem;
                line-height: 1.7;
            }
            .login-role-list {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
            }
            .login-role-list span {
                border: 1px solid rgba(255, 255, 255, 0.24);
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.1);
                color: #eff6ff;
                font-size: 0.72rem;
                font-weight: 650;
                padding: 0.42rem 0.68rem;
            }
            .login-heading {
                margin: 0.25rem 0 0.35rem;
                color: #172b4d;
                font-size: 2rem;
                font-weight: 750;
                letter-spacing: -0.045em;
            }
            .login-description {
                margin: 0 0 1.4rem;
                color: #62748b;
                font-size: 0.92rem;
                line-height: 1.6;
            }
            [data-testid="stForm"] {
                border: 1px solid #e3eaf3;
                border-radius: 18px;
                background: #fff;
                box-shadow: 0 18px 45px rgba(23, 43, 77, 0.08);
                padding: 1.3rem 1.3rem 0.8rem;
            }
            [data-testid="stForm"] label {
                color: #334155;
                font-size: 0.84rem;
                font-weight: 650;
            }
            [data-testid="stForm"] input,
            [data-testid="stForm"] [data-baseweb="select"] > div {
                min-height: 2.8rem;
                border-radius: 9px;
            }
            [data-testid="stForm"] .stFormSubmitButton > button {
                width: 100%;
                min-height: 2.8rem;
                border-radius: 9px;
                font-weight: 700;
            }
            .login-footnote {
                margin-top: 1rem;
                color: #7b8ba1;
                font-size: 0.78rem;
                text-align: center;
            }
            @media (max-width: 760px) {
                .block-container {
                    padding: 1.1rem 1rem 2rem;
                }
                .login-hero {
                    min-height: 340px;
                    padding: 1.5rem;
                }
                .login-hero-copy {
                    margin: 2rem 0;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    hero_column, form_column = st.columns([1, 1.05], gap="large")
    with hero_column:
        st.markdown(
            """
            <section class="login-hero">
                <div class="login-brand">
                    <span class="login-mark">EA</span>
                    <span>Enterprise Analytics</span>
                </div>
                <div class="login-hero-copy">
                    <div class="login-eyebrow">Workforce intelligence</div>
                    <h2>Better insight<br>starts with people.</h2>
                    <p>A secure workspace for employee operations and workforce analytics.</p>
                </div>
                <div class="login-role-list">
                    <span>HR · Read &amp; write</span>
                    <span>Manager · Read</span>
                    <span>Employee · Read</span>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with form_column:
        st.markdown('<div class="login-heading">Welcome back</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-description">Sign in to continue to your secure workspace.</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            selected_role = st.selectbox(
                "Role",
                options=list(ROLE_PERMISSIONS),
                format_func=str.title
            )
            entered_username = st.text_input("Username")
            entered_password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")

        if submitted:
            if not users:
                st.error(
                    "No login accounts are configured. Add [users.<username>] entries "
                    "with a role and password_hash to .streamlit/secrets.toml."
                )
            else:
                canonical_username = configured_usernames.get(entered_username.strip().casefold())
                account = users.get(canonical_username) if canonical_username is not None else None
                if account is None:
                    st.error("Invalid username or password.")
                else:
                    try:
                        credentials_match = verify_user_login(
                            account, entered_password, selected_role
                        )
                    except ValueError as exc:
                        st.error(f"Authentication configuration error: {exc}")
                        st.stop()

                    if credentials_match:
                        st.session_state["auth_username"] = canonical_username
                        st.rerun()
                    else:
                        st.error("Invalid username, password, or selected role.")
        elif not users:
            st.info("Login accounts need to be configured by an administrator before sign-in.")

        st.markdown(
            '<div class="login-footnote">Role-based access · Protected employee data</div>',
            unsafe_allow_html=True,
        )


def require_authentication() -> dict:
    """Render the login form when needed and return the authenticated user."""
    users = _configured_users()
    configured_usernames = {str(username).casefold(): username for username in users}
    username = st.session_state.get("auth_username")

    if username not in users:
        username = configured_usernames.get(str(username).casefold()) if username else None
        if username is None:
            st.session_state.pop("auth_username", None)
            _render_login_page(users, configured_usernames)
            st.stop()

    account = users[username]
    role = account.get("role")
    if role not in ROLE_PERMISSIONS:
        st.error(f"Account '{username}' has an invalid configured role.")
        st.stop()

    st.sidebar.caption(f"Signed in as **{username}** · {role.title()}")
    if st.sidebar.button("Log out"):
        st.session_state.pop("auth_username", None)
        st.rerun()

    return {"username": username, "role": role}
