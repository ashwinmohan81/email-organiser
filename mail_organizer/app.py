from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import streamlit as st
from dotenv import load_dotenv

from mail_organizer.auth import add_account, get_gmail_service, list_accounts, remove_account
from mail_organizer.categorizer import categorize
from mail_organizer.config import CATEGORY_CONFIG, DEFAULT_MAX_RESULTS, DEFAULT_QUERY
from mail_organizer.gmail_client import (
    apply_label_and_archive,
    apply_label_keep_inbox,
    archive_emails,
    fetch_emails,
    trash_emails,
)
from mail_organizer.models import Category, CategorizedEmail

load_dotenv()

st.set_page_config(
    page_title="Mail Organizer",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --accent: #4A90D9;
    --danger: #E74C3C;
    --success: #27AE60;
    --warning: #F39C12;
    --bg-card: #1A1F2E;
    --bg-card-hover: #222839;
    --border: #2A3042;
    --text-muted: #8892A4;
    --radius: 12px;
}

html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}

/* App title */
.app-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}
.app-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    margin: 0;
    background: linear-gradient(135deg, #4A90D9, #67B8F7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Metric cards */
.metric-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 20px;
}
.metric-card {
    flex: 1;
    min-width: 120px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    text-align: center;
    transition: transform 0.15s, box-shadow 0.15s;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.metric-count {
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

/* Email card */
.email-card {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 8px;
    transition: background 0.15s, border-color 0.15s;
}
.email-card:hover {
    background: var(--bg-card-hover);
    border-color: #3A4062;
}
.email-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    color: white;
    flex-shrink: 0;
}
.email-content {
    flex: 1;
    min-width: 0;
}
.email-sender {
    font-weight: 600;
    font-size: 0.9rem;
    color: #E8ECF1;
    margin-bottom: 2px;
}
.email-sender-addr {
    font-weight: 400;
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-left: 6px;
}
.email-subject {
    font-size: 0.85rem;
    color: #C8CED8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 4px;
}
.email-snippet {
    font-size: 0.78rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.email-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    flex-shrink: 0;
}
.email-date {
    font-size: 0.75rem;
    color: var(--text-muted);
    white-space: nowrap;
}
.email-reason {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 20px;
    background: rgba(74, 144, 217, 0.15);
    color: #7AB4E8;
    white-space: nowrap;
}

/* Category badge */
.cat-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Action bar */
.action-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 16px;
}
.action-count {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-left: auto;
}

/* Welcome state */
.welcome-container {
    text-align: center;
    padding: 80px 20px;
}
.welcome-icon {
    font-size: 4rem;
    margin-bottom: 16px;
}
.welcome-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #E8ECF1;
    margin-bottom: 8px;
}
.welcome-sub {
    font-size: 1rem;
    color: var(--text-muted);
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.6;
}

/* Sidebar refinements */
section[data-testid="stSidebar"] {
    background: #0D1117 !important;
}
section[data-testid="stSidebar"] .stRadio > label {
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
}

/* Divider */
.sidebar-divider {
    border-top: 1px solid var(--border);
    margin: 16px 0;
}

/* Connection dot */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-connected { background: var(--success); }
.status-disconnected { background: var(--danger); }

/* Confirmation box */
.confirm-box {
    background: rgba(231, 76, 60, 0.1);
    border: 1px solid rgba(231, 76, 60, 0.3);
    border-radius: var(--radius);
    padding: 16px;
    margin: 12px 0;
}
.confirm-box p {
    margin: 0;
    color: #F1C0B9;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
AVATAR_COLORS = [
    "#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#9B59B6",
    "#1ABC9C", "#E67E22", "#2980B9", "#C0392B", "#16A085",
]


def _avatar_color(email_addr: str) -> str:
    return AVATAR_COLORS[hash(email_addr) % len(AVATAR_COLORS)]


def _relative_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = now - dt
        secs = diff.total_seconds()
        if secs < 60:
            return "Just now"
        if secs < 3600:
            m = int(secs / 60)
            return f"{m}m ago"
        if secs < 86400:
            h = int(secs / 3600)
            return f"{h}h ago"
        if secs < 172800:
            return "Yesterday"
        if secs < 604800:
            d = int(secs / 86400)
            return f"{d}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return date_str[:16] if date_str else ""


def _render_email_card(ce: CategorizedEmail) -> str:
    e = ce.email
    color = _avatar_color(e.sender_email)
    cat_cfg = CATEGORY_CONFIG.get(ce.category)
    reason_html = ""
    if ce.reason:
        reason_html = f'<span class="email-reason">{ce.reason}</span>'

    addr_display = ""
    if e.sender != e.sender_email:
        addr_display = f'<span class="email-sender-addr">{e.sender_email}</span>'

    return f"""
    <div class="email-card">
        <div class="email-avatar" style="background:{color};">{e.sender_initial}</div>
        <div class="email-content">
            <div class="email-sender">{e.sender_display}{addr_display}</div>
            <div class="email-subject">{e.subject}</div>
            <div class="email-snippet">{e.snippet[:120]}</div>
        </div>
        <div class="email-meta">
            <span class="email-date">{_relative_date(e.date)}</span>
            {reason_html}
        </div>
    </div>
    """


def _render_metrics(categorized: list[CategorizedEmail]) -> str:
    counts: dict[Category, int] = {}
    for ce in categorized:
        counts[ce.category] = counts.get(ce.category, 0) + 1

    cards_html = ""
    for cat in Category:
        if cat == Category.UNCATEGORIZED and cat not in counts:
            continue
        count = counts.get(cat, 0)
        cfg = CATEGORY_CONFIG[cat]
        cards_html += f"""
        <div class="metric-card">
            <div class="metric-count" style="color:{cfg.color};">{count}</div>
            <div class="metric-label">{cfg.icon} {cat.value}</div>
        </div>
        """

    return f'<div class="metric-row">{cards_html}</div>'


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "categorized" not in st.session_state:
    st.session_state.categorized = []
if "accounts" not in st.session_state:
    st.session_state.accounts = list_accounts()
if "active_account" not in st.session_state:
    st.session_state.active_account = (
        st.session_state.accounts[0] if st.session_state.accounts else None
    )
if "scan_running" not in st.session_state:
    st.session_state.scan_running = False


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="app-header"><span style="font-size:1.8rem;">📬</span>'
        '<h1>Mail Organizer</h1></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- Account section --
    st.markdown("**ACCOUNT**")
    accounts = st.session_state.accounts

    if accounts:
        selected = st.selectbox(
            "Gmail Account",
            accounts,
            index=accounts.index(st.session_state.active_account)
            if st.session_state.active_account in accounts
            else 0,
            label_visibility="collapsed",
        )
        st.session_state.active_account = selected
        st.markdown(
            f'<span class="status-dot status-connected"></span> Connected as **{selected}**',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-dot status-disconnected"></span> No accounts connected',
            unsafe_allow_html=True,
        )

    col_add, col_rm = st.columns(2)
    with col_add:
        if st.button("➕ Add Account", use_container_width=True):
            try:
                email = add_account()
                if email:
                    st.session_state.accounts = list_accounts()
                    st.session_state.active_account = email
                    st.rerun()
            except FileNotFoundError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Auth failed: {exc}")
    with col_rm:
        if accounts and st.button("🗑️ Remove", use_container_width=True):
            if st.session_state.active_account:
                remove_account(st.session_state.active_account)
                st.session_state.accounts = list_accounts()
                st.session_state.active_account = (
                    st.session_state.accounts[0] if st.session_state.accounts else None
                )
                st.session_state.categorized = []
                st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- AI Engine section --
    st.markdown("**AI ENGINE**")
    backend = st.radio(
        "Categorization backend",
        ["Gemini (Cloud)", "Ollama (Local)", "Rules Only"],
        index=2,
        label_visibility="collapsed",
    )
    backend_key = "gemini" if "Gemini" in backend else ("ollama" if "Ollama" in backend else "rules")

    ollama_model = "llama3.2"
    if backend_key == "ollama":
        ollama_model = st.text_input("Ollama model", value="llama3.2")

    if backend_key == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            st.warning("Set GEMINI_API_KEY in .env")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- Search section --
    st.markdown("**SEARCH**")
    query = st.text_input("Gmail query", value=DEFAULT_QUERY)
    max_results = st.slider("Max emails", 10, 200, DEFAULT_MAX_RESULTS, step=10)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- Scan button --
    scan_clicked = st.button(
        "🔍  Scan Inbox",
        use_container_width=True,
        type="primary",
        disabled=not st.session_state.active_account,
    )


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
if scan_clicked and st.session_state.active_account:
    st.session_state.scan_running = True
    try:
        service = get_gmail_service(st.session_state.active_account)

        with st.status("Scanning your inbox...", expanded=True) as status:
            st.write("📥 Fetching emails from Gmail...")
            emails = fetch_emails(service, max_results=max_results, query=query)
            st.write(f"✅ Fetched **{len(emails)}** emails")

            if emails:
                engine_label = {"gemini": "Gemini", "ollama": "Ollama", "rules": "rules engine"}
                st.write(f"🧠 Categorizing with **{engine_label[backend_key]}**...")
                categorized = categorize(
                    emails,
                    backend=backend_key,
                    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
                    ollama_model=ollama_model,
                )
                st.session_state.categorized = categorized
                st.write(f"✅ Categorized **{len(categorized)}** emails")
                status.update(label="Scan complete!", state="complete")
            else:
                st.session_state.categorized = []
                status.update(label="No emails found", state="complete")

    except Exception as exc:
        st.error(f"Error: {exc}")
    finally:
        st.session_state.scan_running = False


# -- Display results --
categorized = st.session_state.categorized

if not categorized and not st.session_state.scan_running:
    if not st.session_state.accounts:
        st.markdown(
            """
            <div class="welcome-container">
                <div class="welcome-icon">📬</div>
                <div class="welcome-title">Welcome to Mail Organizer</div>
                <div class="welcome-sub">
                    Connect your Gmail account to get started.
                    Click <b>Add Account</b> in the sidebar.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="welcome-container">
                <div class="welcome-icon">🔍</div>
                <div class="welcome-title">Ready to organize</div>
                <div class="welcome-sub">
                    Click <b>Scan Inbox</b> in the sidebar to fetch and
                    categorize your emails.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif categorized:
    # Metrics
    st.markdown(_render_metrics(categorized), unsafe_allow_html=True)

    # Group by category
    groups: dict[Category, list[CategorizedEmail]] = {}
    for ce in categorized:
        groups.setdefault(ce.category, []).append(ce)

    # Build tabs for categories that have emails
    active_cats = [c for c in Category if c in groups]
    if not active_cats:
        st.info("No emails to display.")
    else:
        tab_labels = [
            f"{CATEGORY_CONFIG[c].icon} {c.value} ({len(groups[c])})"
            for c in active_cats
        ]
        tabs = st.tabs(tab_labels)

        for tab, cat in zip(tabs, active_cats):
            with tab:
                cat_emails = groups[cat]
                cfg = CATEGORY_CONFIG[cat]

                # Selection
                select_key = f"select_all_{cat.name}"
                select_all = st.checkbox(
                    "Select all", key=select_key, value=False
                )

                selected_ids = []
                for i, ce in enumerate(cat_emails):
                    col_check, col_card = st.columns([0.04, 0.96])
                    with col_check:
                        checked = st.checkbox(
                            "sel",
                            key=f"chk_{cat.name}_{i}",
                            value=select_all,
                            label_visibility="collapsed",
                        )
                        if checked:
                            selected_ids.append(ce.email.id)
                    with col_card:
                        st.markdown(
                            _render_email_card(ce), unsafe_allow_html=True
                        )

                # Action bar
                st.markdown("---")
                n_sel = len(selected_ids)
                sel_label = f"**{n_sel}** selected" if n_sel else "None selected"
                st.caption(sel_label)

                act_cols = st.columns(4)

                if cfg.label_name and not cfg.archive:
                    with act_cols[0]:
                        if st.button(
                            f"🏷️ Label as {cfg.label_name}",
                            key=f"label_{cat.name}",
                            disabled=n_sel == 0,
                            use_container_width=True,
                        ):
                            service = get_gmail_service(st.session_state.active_account)
                            apply_label_keep_inbox(service, selected_ids, cfg.label_name)
                            st.toast(f"Labeled {n_sel} emails as {cfg.label_name}", icon="🏷️")

                if cfg.label_name and cfg.archive:
                    with act_cols[0]:
                        if st.button(
                            f"📦 Label & Archive",
                            key=f"labarch_{cat.name}",
                            disabled=n_sel == 0,
                            use_container_width=True,
                        ):
                            service = get_gmail_service(st.session_state.active_account)
                            apply_label_and_archive(service, selected_ids, cfg.label_name)
                            st.toast(f"Labeled & archived {n_sel} emails", icon="📦")

                if not cfg.label_name and not cfg.trash:
                    with act_cols[0]:
                        if st.button(
                            "📦 Archive",
                            key=f"arch_{cat.name}",
                            disabled=n_sel == 0,
                            use_container_width=True,
                        ):
                            service = get_gmail_service(st.session_state.active_account)
                            archive_emails(service, selected_ids)
                            st.toast(f"Archived {n_sel} emails", icon="📦")

                with act_cols[1]:
                    trash_key = f"trash_{cat.name}"
                    confirm_key = f"confirm_trash_{cat.name}"

                    if st.button(
                        "🗑️ Trash",
                        key=trash_key,
                        disabled=n_sel == 0,
                        type="secondary",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = True

                    if st.session_state.get(confirm_key, False):
                        st.markdown(
                            f"""<div class="confirm-box">
                            <p>⚠️ Move <b>{n_sel}</b> emails to trash?
                            They can be recovered from Gmail Trash within 30 days.</p>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(
                                "Yes, trash them",
                                key=f"yes_trash_{cat.name}",
                                type="primary",
                                use_container_width=True,
                            ):
                                service = get_gmail_service(st.session_state.active_account)
                                trash_emails(service, selected_ids)
                                st.session_state[confirm_key] = False
                                st.toast(f"Trashed {n_sel} emails", icon="🗑️")
                        with c2:
                            if st.button(
                                "Cancel",
                                key=f"cancel_trash_{cat.name}",
                                use_container_width=True,
                            ):
                                st.session_state[confirm_key] = False
                                st.rerun()
