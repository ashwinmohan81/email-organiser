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

/* Hide Streamlit chrome but KEEP sidebar toggle visible */
#MainMenu, footer, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* Hide header — sidebar is always visible, no toggle needed */
header[data-testid="stHeader"] {
    display: none !important;
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: #0A0D12 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
    overflow-x: hidden !important;
    transform: none !important;
    transition: none !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 1.2rem 1rem 1rem;
    overflow-x: hidden !important;
}
/* Hide sidebar collapse/expand buttons — sidebar always visible */
button[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] button[kind="header"] {
    display: none !important;
}
section[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px !important;
    padding: 6px 12px !important;
    font-size: 0.78rem !important;
    min-height: 36px !important;
}
section[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    padding: 6px 10px !important;
    border-radius: 8px !important;
    transition: background 0.15s !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,0.04) !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}

/* Sidebar brand */
.sb-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 0 18px; margin-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.sb-brand-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #4A90D9, #67B8F7);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; flex-shrink: 0;
}
.sb-brand-text {
    font-size: 1.05rem; font-weight: 700;
    background: linear-gradient(135deg, #4A90D9, #67B8F7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.3px;
}

/* Sidebar account card */
.sb-account {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; margin: 6px 0 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
}
.sb-account-avatar {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #27AE60, #2ECC71);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.75rem; color: #fff;
    flex-shrink: 0;
}
.sb-account-info {
    flex: 1; min-width: 0;
}
.sb-account-info .name {
    font-size: 0.8rem; font-weight: 600; color: var(--text-primary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sb-account-info .status {
    font-size: 0.68rem; color: var(--success);
    display: flex; align-items: center; gap: 4px;
}
.sb-account-info .status::before {
    content: ''; width: 6px; height: 6px;
    background: var(--success); border-radius: 50%;
    box-shadow: 0 0 6px rgba(39,174,96,0.5);
}

/* Sidebar section labels */
.sb-label {
    font-size: 0.62rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.2px;
    color: var(--text-muted);
    margin: 18px 0 6px 2px;
}
.sb-divider {
    height: 1px; background: rgba(255,255,255,0.05); margin: 16px 0;
}

/* ---- Welcome / empty state ---- */
.hero {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 80px 24px 40px; text-align: center;
}
.hero-icon {
    width: 72px; height: 72px;
    background: linear-gradient(135deg, rgba(74,144,217,0.15), rgba(103,184,247,0.08));
    border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; margin-bottom: 20px;
    border: 1px solid rgba(74,144,217,0.2);
}
.hero h2 {
    font-size: 1.5rem; font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 8px; letter-spacing: -0.3px;
}
.hero p {
    font-size: 0.9rem; color: var(--text-muted);
    max-width: 380px; line-height: 1.6; margin: 0;
}

/* ---- Category card buttons ---- */
div[data-testid="stVerticalBlock"] div[data-testid="stColumns"] .cat-btn-wrap .stButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 20px 16px !important;
    min-height: 120px !important;
    text-align: left !important;
    transition: all 0.2s ease !important;
    color: var(--text-primary) !important;
    white-space: pre-wrap !important;
    line-height: 1.5 !important;
    font-size: 0.8rem !important;
}
div[data-testid="stVerticalBlock"] div[data-testid="stColumns"] .cat-btn-wrap .stButton > button:hover {
    border-color: var(--border-hover) !important;
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-hover) !important;
    background: var(--bg-card-hover) !important;
}

/* ---- Detail header ---- */
.detail-header {
    display: flex; align-items: center; gap: 14px;
    margin-bottom: 18px; padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}
.detail-header .dh-icon { font-size: 1.3rem; }
.detail-header .dh-title {
    font-size: 1.15rem; font-weight: 700; color: var(--text-primary);
}
.detail-header .dh-count {
    font-size: 0.82rem; color: var(--text-muted); font-weight: 500;
}
.detail-header .dh-action-badge {
    margin-left: auto; font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.8px;
    padding: 4px 12px; border-radius: 20px;
}

/* ---- Email list ---- */
.email-list {
    display: flex; flex-direction: column;
    gap: 4px; margin-bottom: 16px;
}
.email-row {
    display: flex; align-items: center; gap: 14px;
    padding: 12px 16px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
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
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.82rem; color: white;
    flex-shrink: 0; opacity: 0.9;
}
.email-body {
    flex: 1; min-width: 0;
    display: flex; flex-direction: column; gap: 1px;
}
.email-from {
    font-weight: 600; font-size: 0.82rem; color: var(--text-primary);
    display: flex; align-items: center; gap: 8px;
}
.email-from .addr {
    font-weight: 400; font-size: 0.72rem; color: var(--text-muted);
}
.email-subj {
    font-size: 0.8rem; color: var(--text-secondary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.email-snip {
    font-size: 0.72rem; color: var(--text-muted);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.email-right {
    flex-shrink: 0; display: flex; flex-direction: column;
    align-items: flex-end; gap: 4px; min-width: 80px;
}
.email-time {
    font-size: 0.7rem; color: var(--text-muted); font-weight: 500;
}
.email-tag {
    font-size: 0.62rem; font-weight: 600;
    padding: 2px 7px; border-radius: 20px;
    background: rgba(74, 144, 217, 0.1);
    color: var(--accent-light);
    white-space: nowrap; max-width: 140px;
    overflow: hidden; text-overflow: ellipsis;
}

/* ---- Confirm banner ---- */
.confirm-banner {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 16px;
    background: var(--danger-bg);
    border: 1px solid rgba(231, 76, 60, 0.2);
    border-radius: var(--radius-sm);
    margin: 10px 0;
}
.confirm-banner .icon { font-size: 1.1rem; }
.confirm-banner .msg {
    flex: 1; font-size: 0.82rem; color: #F1C0B9;
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
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4A90D9, #3A7BC8) !important;
    border: none !important; color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #5A9FE8, #4A8BD8) !important;
}

/* ---- Checkbox ---- */
.stCheckbox { padding: 0 !important; }
.stCheckbox label {
    padding: 0 !important; min-height: 0 !important;
    align-items: center !important; gap: 6px !important;
}
.stCheckbox label span[data-testid="stCheckboxLabel"] {
    font-size: 0.82rem !important; font-weight: 500 !important;
}

/* ---- Form inputs ---- */
.stSelectbox, .stSlider, .stTextInput { margin-bottom: 4px; }
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
if "active_category" not in st.session_state:
    st.session_state.active_category = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    # ── Brand ──
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brand-icon">📬</div>'
        '<div class="sb-brand-text">Mail Organizer</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Account ──
    accounts = st.session_state.accounts

    if accounts:
        if len(accounts) > 1:
            selected = st.selectbox(
                "Account",
                accounts,
                index=(accounts.index(st.session_state.active_account)
                       if st.session_state.active_account in accounts else 0),
                label_visibility="collapsed",
            )
            st.session_state.active_account = selected
        acct = st.session_state.active_account or ""
        initial = acct[0].upper() if acct else "?"
        st.markdown(
            f'<div class="sb-account">'
            f'<div class="sb-account-avatar">{_esc(initial)}</div>'
            f'<div class="sb-account-info">'
            f'<div class="name">{_esc(acct)}</div>'
            f'<div class="status">Connected</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sb-account">'
            '<div class="sb-account-avatar" style="background:#555;">?</div>'
            '<div class="sb-account-info">'
            '<div class="name" style="color:var(--text-muted);">No account</div>'
            '<div class="status" style="color:var(--danger);">Not connected</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

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
    if accounts and st.button("Remove Account", use_container_width=True, icon="🗑️"):
        if st.session_state.active_account:
            remove_account(st.session_state.active_account)
            st.session_state.accounts = list_accounts()
            st.session_state.active_account = (
                st.session_state.accounts[0] if st.session_state.accounts else None
            )
            st.session_state.categorized = []
            st.rerun()

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # ── Scan button (prominent, like Gmail Compose) ──
    sidebar_scan = st.button(
        "Scan Inbox",
        use_container_width=True,
        type="primary",
        disabled=not st.session_state.active_account,
        icon="🔍",
    )

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # ── AI Engine ──
    st.markdown('<div class="sb-label">AI Engine</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # ── Search settings ──
    st.markdown('<div class="sb-label">Search</div>', unsafe_allow_html=True)
    query = st.text_input("Gmail query", value=DEFAULT_QUERY, label_visibility="collapsed",
                          placeholder="is:inbox")
    max_results = st.slider("Emails to fetch", 10, 200, DEFAULT_MAX_RESULTS, step=10)


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

scan_clicked = sidebar_scan

# -- Scan logic --
if scan_clicked and st.session_state.active_account:
    st.session_state.scan_running = True
    st.session_state.active_category = None
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

                progress_placeholder = st.empty()
                _batch_times: list[float] = []
                import time as _time
                _batch_start = [_time.time()]

                def _progress(done, total, msg=""):
                    now = _time.time()
                    if done > 0:
                        _batch_times.append(now - _batch_start[0])
                    _batch_start[0] = now

                    if done < total:
                        avg = sum(_batch_times) / len(_batch_times) if _batch_times else 0
                        remaining = int(avg * (total - done))
                        eta = f" · ~{remaining}s left" if remaining > 0 and _batch_times else ""
                        label = msg or f"Step {done}/{total}"
                        progress_placeholder.progress(
                            max(done / total, 0.01),
                            text=f"{label}{eta}"
                        )
                    else:
                        progress_placeholder.progress(1.0, text="Done!")

                categorized, cat_actions = categorize(
                    emails,
                    backend=backend_key,
                    gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
                    ollama_model=ollama_model,
                    progress_callback=_progress,
                )
                progress_placeholder.empty()
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
            <p>Hit <b>Scan Inbox</b> in the sidebar to fetch
            and categorize your emails.</p>
        </div>
        """, unsafe_allow_html=True)

elif categorized:
    cat_actions = st.session_state.get("cat_actions", {})
    active_cat = st.session_state.get("active_category")

    groups: dict[str, list[CategorizedEmail]] = {}
    for ce in categorized:
        groups.setdefault(ce.category, []).append(ce)

    order_priority = {"keep": 0, "archive": 1, "trash": 2}
    cat_order = sorted(
        groups.keys(),
        key=lambda c: (order_priority.get(cat_actions.get(c, "keep"), 0), c),
    )

    # ── SUMMARY VIEW ── clickable category cards
    if active_cat is None or active_cat not in groups:
        total = len(categorized)
        st.markdown(
            f'<div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:16px;">'
            f'<b>{total}</b> emails organized into <b>{len(cat_order)}</b> categories '
            f'— click a category to view</div>',
            unsafe_allow_html=True,
        )

        action_labels = {"keep": "📌 Keep", "archive": "📦 Archive", "trash": "🗑️ Trash"}

        cols_per_row = 4
        for row_start in range(0, len(cat_order), cols_per_row):
            row_cats = cat_order[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col_idx, cat_name in enumerate(row_cats):
                with cols[col_idx]:
                    cat_idx = cat_order.index(cat_name)
                    color, icon = get_category_style(cat_name, cat_idx)
                    count = len(groups[cat_name])
                    action = cat_actions.get(cat_name, infer_action(cat_name))
                    action_str = action_labels.get(action, "")
                    label = f"{icon}  {count}\n{cat_name}\n{action_str}"

                    st.markdown('<div class="cat-btn-wrap">', unsafe_allow_html=True)
                    if st.button(
                        label,
                        key=f"view_{_cat_key(cat_name)}",
                        use_container_width=True,
                    ):
                        st.session_state.active_category = cat_name
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ── DETAIL VIEW ── emails in the selected category
    else:
        cat_name = active_cat
        cat_emails = groups.get(cat_name, [])
        cat_idx = cat_order.index(cat_name) if cat_name in cat_order else 0
        ck = _cat_key(cat_name)
        color, icon = get_category_style(cat_name, cat_idx)
        action = cat_actions.get(cat_name, infer_action(cat_name))
        label_name = make_label_name(cat_name)
        all_ids = [ce.email.id for ce in cat_emails]
        selected = _get_selected(cat_name)
        action_labels = {"keep": "📌 Keep in inbox", "archive": "📦 Archive", "trash": "🗑️ Trash"}

        # Back button
        if st.button("Back to categories", key="back_btn", icon="⬅️"):
            st.session_state.active_category = None
            st.rerun()

        # Empty state — all emails processed
        if not cat_emails:
            st.markdown(
                '<div style="text-align:center;padding:60px 20px;">'
                '<div style="font-size:2rem;margin-bottom:12px;">✅</div>'
                '<div style="font-size:1rem;font-weight:600;color:var(--text-primary);margin-bottom:4px;">'
                'All done!</div>'
                '<div style="font-size:0.85rem;color:var(--text-muted);">'
                'All emails in this category have been processed.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:

            action_bg = {
                "keep": "rgba(74,144,217,0.12)",
                "archive": "rgba(39,174,96,0.12)",
                "trash": "rgba(231,76,60,0.12)",
            }
            st.markdown(
                f'<div class="detail-header">'
                f'<span class="dh-icon">{icon}</span>'
                f'<span class="dh-title">{_esc(cat_name)}</span>'
                f'<span class="dh-count">{len(cat_emails)} emails</span>'
                f'<span class="dh-action-badge" style="background:{action_bg.get(action, "var(--bg-card)")}; '
                f'color:{color};">{action_labels.get(action, "")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Toolbar
            n_sel = len(selected)
            sel_label = f"Select all ({len(all_ids)})" if n_sel == 0 else f"{n_sel} of {len(all_ids)} selected"
            t1, t2, t3 = st.columns([0.35, 0.20, 0.15])

            with t1:
                st.checkbox(
                    sel_label,
                    key=f"sa_{ck}",
                    value=len(selected) == len(all_ids) and len(all_ids) > 0,
                    on_change=_toggle_select_all,
                    args=(cat_name, all_ids),
                )

            trash_confirm_key = f"_ctr_{ck}"
            trash_ids_key = f"_trash_ids_{ck}"

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
                if st.button("🗑️ Trash", key=f"tr_{ck}",
                             disabled=n_sel == 0, use_container_width=True):
                    st.session_state[trash_confirm_key] = True
                    st.session_state[trash_ids_key] = list(selected)
                    st.rerun()

            # Trash confirmation
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
