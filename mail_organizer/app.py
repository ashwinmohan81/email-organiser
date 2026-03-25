from __future__ import annotations

import html as html_lib
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from dotenv import load_dotenv

from mail_organizer.auth import add_account, get_gmail_service, list_accounts, remove_account
from mail_organizer.categorizer import categorize
from mail_organizer.config import (
    DEFAULT_MAX_RESULTS, DEFAULT_QUERY,
    get_category_style, infer_action, make_label_name,
)
from mail_organizer.gmail_client import (
    apply_label_and_archive,
    apply_label_keep_inbox,
    archive_emails,
    fetch_emails,
    trash_emails,
)
from mail_organizer.models import CategorizedEmail

load_dotenv()

st.set_page_config(
    page_title="Mail Organizer",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

AVATAR_COLORS = [
    "#E74C3C", "#3498DB", "#27AE60", "#F39C12", "#9B59B6",
    "#1ABC9C", "#E67E22", "#2980B9", "#C0392B", "#16A085",
]

# ---------------------------------------------------------------------------
# CSS — the entire visual layer
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --accent: #4A90D9;
    --accent-light: #67B8F7;
    --accent-bg: rgba(74, 144, 217, 0.08);
    --danger: #E74C3C;
    --danger-bg: rgba(231, 76, 60, 0.08);
    --success: #27AE60;
    --success-bg: rgba(39, 174, 96, 0.08);
    --warning: #F39C12;
    --bg-page: #0E1117;
    --bg-card: rgba(255, 255, 255, 0.03);
    --bg-card-hover: rgba(255, 255, 255, 0.06);
    --bg-card-selected: rgba(74, 144, 217, 0.08);
    --border: rgba(255, 255, 255, 0.06);
    --border-hover: rgba(255, 255, 255, 0.12);
    --border-selected: rgba(74, 144, 217, 0.3);
    --text-primary: #F0F2F5;
    --text-secondary: #B0B8C4;
    --text-muted: #6B7585;
    --radius: 16px;
    --radius-sm: 10px;
    --radius-xs: 6px;
    --shadow: 0 1px 3px rgba(0,0,0,0.2);
    --shadow-hover: 0 4px 16px rgba(0,0,0,0.3);
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="st-"],
.stMarkdown, .stMarkdown p, .stMarkdown span,
button, input, select, textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                 'Segoe UI', Roboto, sans-serif !important;
}

/* ---- Hide Streamlit chrome ---- */
#MainMenu, header, footer, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: #0B0E14 !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1.5rem;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}
.sidebar-brand-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #4A90D9, #67B8F7);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.sidebar-brand-text {
    font-size: 1.15rem;
    font-weight: 700;
    background: linear-gradient(135deg, #4A90D9, #67B8F7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.3px;
}

.sidebar-section-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: var(--text-muted);
    margin: 20px 0 8px 0;
}

.sidebar-divider {
    height: 1px;
    background: var(--border);
    margin: 20px 0;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    color: var(--text-secondary);
    padding: 6px 10px;
    background: var(--bg-card);
    border-radius: 8px;
    border: 1px solid var(--border);
    margin-top: 4px;
}
.status-badge .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.status-badge .dot.on  { background: var(--success); box-shadow: 0 0 6px rgba(39,174,96,0.5); }
.status-badge .dot.off { background: var(--danger); }

/* ---- Welcome / empty state ---- */
.hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 100px 24px 60px;
    text-align: center;
}
.hero-icon {
    width: 80px; height: 80px;
    background: linear-gradient(135deg, rgba(74,144,217,0.15), rgba(103,184,247,0.08));
    border-radius: 24px;
    display: flex; align-items: center; justify-content: center;
    font-size: 36px;
    margin-bottom: 24px;
    border: 1px solid rgba(74,144,217,0.2);
}
.hero h2 {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 8px;
    letter-spacing: -0.3px;
}
.hero p {
    font-size: 0.95rem;
    color: var(--text-muted);
    max-width: 380px;
    line-height: 1.65;
    margin: 0;
}

/* ---- Metrics row ---- */
.metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin-bottom: 28px;
}
.metric {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 18px 16px;
    text-align: center;
    transition: all 0.2s ease;
}
.metric:hover {
    border-color: var(--border-hover);
    transform: translateY(-1px);
    box-shadow: var(--shadow-hover);
}
.metric-num {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
}
.metric-name {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    margin-top: 6px;
}

/* ---- Tab styling ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    padding: 4px;
    border: 1px solid var(--border);
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-xs);
    padding: 8px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    background: transparent;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: rgba(74, 144, 217, 0.15) !important;
    color: var(--accent-light) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ---- Email list ---- */
.email-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 20px;
}

.email-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 18px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    cursor: default;
    transition: all 0.15s ease;
}
.email-row:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-hover);
}
.email-row.selected {
    background: var(--bg-card-selected);
    border-color: var(--border-selected);
}

.email-avatar {
    width: 38px; height: 38px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.85rem;
    color: white;
    flex-shrink: 0;
    opacity: 0.9;
}

.email-body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.email-from {
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}
.email-from .addr {
    font-weight: 400;
    font-size: 0.75rem;
    color: var(--text-muted);
}
.email-subj {
    font-size: 0.82rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.email-snip {
    font-size: 0.75rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.email-right {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    min-width: 90px;
}
.email-time {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-weight: 500;
}
.email-tag {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    background: rgba(74, 144, 217, 0.1);
    color: var(--accent-light);
    white-space: nowrap;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ---- Action toolbar ---- */
.toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
}
.toolbar-count {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-secondary);
}
.toolbar-sep {
    width: 1px;
    height: 20px;
    background: var(--border);
}

/* ---- Confirm banner ---- */
.confirm-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    background: var(--danger-bg);
    border: 1px solid rgba(231, 76, 60, 0.2);
    border-radius: var(--radius-sm);
    margin: 12px 0;
}
.confirm-banner .icon { font-size: 1.2rem; }
.confirm-banner .msg {
    flex: 1;
    font-size: 0.85rem;
    color: #F1C0B9;
}

/* ---- Button overrides ---- */
.stButton > button {
    border-radius: var(--radius-xs) !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: -0.2px !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: var(--shadow-hover) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4A90D9, #3A7BC8) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #5A9FE8, #4A8BD8) !important;
}

/* ---- Checkbox style overrides ---- */
.stCheckbox {
    padding: 0 !important;
}
.stCheckbox label {
    padding: 0 !important;
    min-height: 0 !important;
    align-items: center !important;
    gap: 6px !important;
}
.stCheckbox label span[data-testid="stCheckboxLabel"] {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* ---- Selectbox / slider / input overrides ---- */
.stSelectbox, .stSlider, .stTextInput {
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _avatar_color(email_addr: str) -> str:
    return AVATAR_COLORS[hash(email_addr) % len(AVATAR_COLORS)]


def _relative_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        secs = (now - dt).total_seconds()
        if secs < 60:
            return "now"
        if secs < 3600:
            return f"{int(secs / 60)}m"
        if secs < 86400:
            return f"{int(secs / 3600)}h"
        if secs < 172800:
            return "1d"
        if secs < 604800:
            return f"{int(secs / 86400)}d"
        return dt.strftime("%b %d")
    except Exception:
        return date_str[:10] if date_str else ""


def _esc(text: str) -> str:
    return html_lib.escape(text) if text else ""


def _render_email_list(emails: list[CategorizedEmail], selected_set: set[str]) -> str:
    rows = []
    for ce in emails:
        e = ce.email
        color = _avatar_color(e.sender_email)
        sel_class = " selected" if e.id in selected_set else ""
        addr_html = ""
        if e.sender and e.sender != e.sender_email:
            addr_html = f'<span class="addr">{_esc(e.sender_email)}</span>'

        tag_html = ""
        if ce.reason:
            tag_html = f'<div class="email-tag">{_esc(ce.reason)}</div>'

        rows.append(f"""
        <div class="email-row{sel_class}">
            <div class="email-avatar" style="background:{color};">{_esc(e.sender_initial)}</div>
            <div class="email-body">
                <div class="email-from">{_esc(e.sender_display)}{addr_html}</div>
                <div class="email-subj">{_esc(e.subject)}</div>
                <div class="email-snip">{_esc(e.snippet[:140])}</div>
            </div>
            <div class="email-right">
                <div class="email-time">{_relative_date(e.date)}</div>
                {tag_html}
            </div>
        </div>""")

    return f'<div class="email-list">{"".join(rows)}</div>'


def _render_metrics(categorized: list[CategorizedEmail], cat_order: list[str]) -> str:
    counts: dict[str, int] = {}
    for ce in categorized:
        counts[ce.category] = counts.get(ce.category, 0) + 1

    cards = []
    for i, cat in enumerate(cat_order):
        n = counts.get(cat, 0)
        color, icon = get_category_style(cat, i)
        cards.append(f"""
        <div class="metric">
            <div class="metric-num" style="color:{color};">{n}</div>
            <div class="metric-name">{icon} {_esc(cat)}</div>
        </div>""")

    return f'<div class="metrics">{"".join(cards)}</div>'


# ---------------------------------------------------------------------------
# Selection helpers — proper session_state management
# ---------------------------------------------------------------------------
def _cat_key(cat_name: str) -> str:
    return cat_name.replace(" ", "_").replace("&", "and").replace("/", "_")


def _sel_key(cat_name: str) -> str:
    return f"_sel_{_cat_key(cat_name)}"


def _get_selected(cat_name: str) -> set[str]:
    return st.session_state.get(_sel_key(cat_name), set())


def _set_selected(cat_name: str, ids: set[str]) -> None:
    st.session_state[_sel_key(cat_name)] = ids


def _toggle_select_all(cat_name: str, all_ids: list[str]) -> None:
    key = f"sa_{_cat_key(cat_name)}"
    if st.session_state.get(key, False):
        _set_selected(cat_name, set(all_ids))
    else:
        _set_selected(cat_name, set())


def _toggle_single(cat_name: str, email_id: str) -> None:
    key = f"chk_{_cat_key(cat_name)}_{email_id}"
    current = _get_selected(cat_name)
    if st.session_state.get(key, False):
        current.add(email_id)
    else:
        current.discard(email_id)
    _set_selected(cat_name, current)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "categorized" not in st.session_state:
    st.session_state.categorized = []
if "cat_actions" not in st.session_state:
    st.session_state.cat_actions = {}
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
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-icon">📬</div>
        <div class="sidebar-brand-text">Mail Organizer</div>
    </div>
    """, unsafe_allow_html=True)

    # -- Account --
    st.markdown('<div class="sidebar-section-label">Account</div>', unsafe_allow_html=True)
    accounts = st.session_state.accounts

    if accounts:
        selected = st.selectbox(
            "Gmail Account",
            accounts,
            index=(accounts.index(st.session_state.active_account)
                   if st.session_state.active_account in accounts else 0),
            label_visibility="collapsed",
        )
        st.session_state.active_account = selected
        st.markdown(
            f'<div class="status-badge"><span class="dot on"></span>{selected}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-badge"><span class="dot off"></span>No accounts</div>',
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Add Account", use_container_width=True, icon="➕"):
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
    with c2:
        if accounts and st.button("Remove", use_container_width=True, icon="🗑️"):
            if st.session_state.active_account:
                remove_account(st.session_state.active_account)
                st.session_state.accounts = list_accounts()
                st.session_state.active_account = (
                    st.session_state.accounts[0] if st.session_state.accounts else None
                )
                st.session_state.categorized = []
                st.rerun()

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- AI Engine --
    st.markdown('<div class="sidebar-section-label">AI Engine</div>', unsafe_allow_html=True)
    backend = st.radio(
        "Backend",
        ["✨ Gemini (Cloud)", "🔒 Ollama (Local)", "⚡ Rules Only"],
        index=2,
        label_visibility="collapsed",
    )
    backend_key = "gemini" if "Gemini" in backend else ("ollama" if "Ollama" in backend else "rules")

    ollama_model = "mistral"
    if backend_key == "ollama":
        ollama_model = st.text_input("Ollama model", value="mistral")
    if backend_key == "gemini" and not os.getenv("GEMINI_API_KEY", ""):
        st.warning("Set GEMINI_API_KEY in .env", icon="⚠️")

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # -- Search --
    st.markdown('<div class="sidebar-section-label">Search</div>', unsafe_allow_html=True)
    query = st.text_input("Gmail search query", value=DEFAULT_QUERY, label_visibility="collapsed",
                          placeholder="is:inbox")
    max_results = st.slider("Emails to fetch", 10, 200, DEFAULT_MAX_RESULTS, step=10)

    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    scan_clicked = st.button(
        "Scan Inbox",
        use_container_width=True,
        type="primary",
        disabled=not st.session_state.active_account,
        icon="🔍",
    )


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

# -- Scan logic --
if scan_clicked and st.session_state.active_account:
    st.session_state.scan_running = True
    # Clear old selections
    for key in list(st.session_state.keys()):
        if key.startswith("_sel_") or key.startswith("sa_") or key.startswith("chk_"):
            del st.session_state[key]

    try:
        service = get_gmail_service(st.session_state.active_account)

        with st.status("Scanning your inbox...", expanded=True) as status:
            st.write("Fetching emails from Gmail...")
            emails = fetch_emails(service, max_results=max_results, query=query)
            st.write(f"Found **{len(emails)}** emails")

            if emails:
                engine_name = {"gemini": "Gemini", "ollama": "Ollama", "rules": "rules engine"}
                st.write(f"Categorizing with **{engine_name[backend_key]}**...")
                categorized, cat_actions = categorize(
                    emails,
                    backend=backend_key,
                    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
                    ollama_model=ollama_model,
                )
                st.session_state.categorized = categorized
                st.session_state.cat_actions = cat_actions
                n_cats = len(cat_actions)
                st.write(f"Organized **{len(categorized)}** emails into **{n_cats}** categories")
                status.update(label=f"Done — {len(categorized)} emails, {n_cats} categories", state="complete")
            else:
                st.session_state.categorized = []
                st.session_state.cat_actions = {}
                status.update(label="No emails matched your query", state="complete")
    except Exception as exc:
        st.error(f"Error: {exc}")
    finally:
        st.session_state.scan_running = False


# -- Display --
categorized = st.session_state.categorized

if not categorized and not st.session_state.scan_running:
    if not st.session_state.accounts:
        st.markdown("""
        <div class="hero">
            <div class="hero-icon">📬</div>
            <h2>Welcome to Mail Organizer</h2>
            <p>Connect your Gmail account to get started.<br>
            Click <b>Add Account</b> in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="hero">
            <div class="hero-icon">🔍</div>
            <h2>Ready to organize</h2>
            <p>Click <b>Scan Inbox</b> in the sidebar to fetch
            and categorize your emails.</p>
        </div>
        """, unsafe_allow_html=True)

elif categorized:
    cat_actions = st.session_state.get("cat_actions", {})

    # Build ordered category list (keep > archive > trash)
    groups: dict[str, list[CategorizedEmail]] = {}
    for ce in categorized:
        groups.setdefault(ce.category, []).append(ce)

    order_priority = {"keep": 0, "archive": 1, "trash": 2}
    cat_order = sorted(
        groups.keys(),
        key=lambda c: (order_priority.get(cat_actions.get(c, "keep"), 0), c),
    )

    st.markdown(_render_metrics(categorized, cat_order), unsafe_allow_html=True)

    if not cat_order:
        st.info("No emails to display.")
    else:
        tab_labels = []
        for i, c in enumerate(cat_order):
            _, icon = get_category_style(c, i)
            tab_labels.append(f"{icon} {c} ({len(groups[c])})")
        tabs = st.tabs(tab_labels)

        for tab_idx, (tab, cat_name) in enumerate(zip(tabs, cat_order)):
            with tab:
                cat_emails = groups[cat_name]
                ck = _cat_key(cat_name)
                action = cat_actions.get(cat_name, infer_action(cat_name))
                label_name = make_label_name(cat_name)
                all_ids = [ce.email.id for ce in cat_emails]
                selected = _get_selected(cat_name)

                # Toolbar
                t1, t2, t3, t4, t5 = st.columns([0.18, 0.20, 0.14, 0.14, 0.34])

                with t1:
                    st.checkbox(
                        f"Select all ({len(all_ids)})",
                        key=f"sa_{ck}",
                        value=len(selected) == len(all_ids) and len(all_ids) > 0,
                        on_change=_toggle_select_all,
                        args=(cat_name, all_ids),
                    )

                n_sel = len(selected)

                with t2:
                    if action in ("trash", "archive"):
                        if st.button("📦 Label & Archive", key=f"la_{ck}",
                                     disabled=n_sel == 0, use_container_width=True):
                            svc = get_gmail_service(st.session_state.active_account)
                            apply_label_and_archive(svc, list(selected), label_name)
                            done_set = set(selected)
                            st.session_state.categorized = [
                                ce for ce in st.session_state.categorized
                                if ce.email.id not in done_set
                            ]
                            _set_selected(cat_name, set())
                            st.toast(f"Labeled & archived {n_sel} emails", icon="📦")
                            st.rerun()
                    else:
                        if st.button("🏷️ Label", key=f"lbl_{ck}",
                                     disabled=n_sel == 0, use_container_width=True):
                            svc = get_gmail_service(st.session_state.active_account)
                            apply_label_keep_inbox(svc, list(selected), label_name)
                            _set_selected(cat_name, set())
                            st.toast(f"Labeled {n_sel} emails as {label_name}", icon="🏷️")
                            st.rerun()

                with t3:
                    trash_confirm_key = f"_ctr_{ck}"
                    trash_ids_key = f"_trash_ids_{ck}"
                    if st.button("🗑️ Trash", key=f"tr_{ck}",
                                 disabled=n_sel == 0, use_container_width=True):
                        st.session_state[trash_confirm_key] = True
                        st.session_state[trash_ids_key] = list(selected)
                        st.rerun()

                with t5:
                    action_label = {"keep": "📌 Keep in inbox", "archive": "📦 Archive", "trash": "🗑️ Trash"}
                    color, _ = get_category_style(cat_name, tab_idx)
                    parts = []
                    if n_sel > 0:
                        parts.append(f'<span style="color:var(--accent-light);font-weight:600;">'
                                     f'{n_sel}/{len(all_ids)} selected</span>')
                    parts.append(f'<span style="color:{color};font-weight:500;">'
                                 f'{action_label.get(action, "")}</span>')
                    st.markdown(
                        f'<div style="text-align:right;padding-top:6px;font-size:0.82rem;">'
                        f'{" · ".join(parts)}</div>',
                        unsafe_allow_html=True,
                    )

                # Trash confirmation
                trash_confirm_key = f"_ctr_{ck}"
                trash_ids_key = f"_trash_ids_{ck}"
                if st.session_state.get(trash_confirm_key, False):
                    pending_ids = st.session_state.get(trash_ids_key, [])
                    n_pending = len(pending_ids)
                    st.markdown(
                        f'<div class="confirm-banner">'
                        f'<span class="icon">⚠️</span>'
                        f'<span class="msg">Move <b>{n_pending}</b> email{"s" if n_pending != 1 else ""} '
                        f'to trash? Recoverable from Gmail Trash for 30 days.</span>'
                        f'</div>', unsafe_allow_html=True,
                    )
                    cc1, cc2, _ = st.columns([0.15, 0.15, 0.7])
                    with cc1:
                        if st.button("Yes, trash", key=f"yt_{ck}", type="primary",
                                     use_container_width=True):
                            if pending_ids:
                                svc = get_gmail_service(st.session_state.active_account)
                                trash_emails(svc, pending_ids)
                                st.toast(f"Trashed {n_pending} emails", icon="🗑️")
                                # Remove trashed emails from results
                                trashed_set = set(pending_ids)
                                st.session_state.categorized = [
                                    ce for ce in st.session_state.categorized
                                    if ce.email.id not in trashed_set
                                ]
                            st.session_state[trash_confirm_key] = False
                            st.session_state.pop(trash_ids_key, None)
                            _set_selected(cat_name, set())
                            st.rerun()
                    with cc2:
                        if st.button("Cancel", key=f"ct_{ck}", use_container_width=True):
                            st.session_state[trash_confirm_key] = False
                            st.session_state.pop(trash_ids_key, None)
                            st.rerun()

                # Email list with checkboxes
                for ce in cat_emails:
                    eid = ce.email.id
                    chk_key = f"chk_{ck}_{eid}"

                    if chk_key not in st.session_state:
                        st.session_state[chk_key] = eid in selected
                    if eid in selected and not st.session_state.get(chk_key, False):
                        st.session_state[chk_key] = True
                    elif eid not in selected and st.session_state.get(chk_key, False):
                        st.session_state[chk_key] = False

                    col_chk, col_card = st.columns([0.03, 0.97], gap="small")
                    with col_chk:
                        st.checkbox(
                            " ",
                            key=chk_key,
                            label_visibility="collapsed",
                            on_change=_toggle_single,
                            args=(cat_name, eid),
                        )
                    with col_card:
                        current_sel = _get_selected(cat_name)
                        st.markdown(
                            _render_email_list([ce], current_sel),
                            unsafe_allow_html=True,
                        )
