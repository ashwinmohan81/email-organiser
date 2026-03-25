# Mail Organizer

A macOS desktop app that connects to your Gmail, uses AI to categorize your emails, and lets you label, archive, and trash with a single click.

**Features:**
- Multi-account support — organize your inbox and your family's
- Three AI backends: Google Gemini (cloud), Ollama (fully local/private), or rule-based
- Smart categories: Action Required, Important, FYI, Newsletter, Social, Promotions, Spam
- Bulk actions with confirmation — label, archive, and trash in batches
- Beautiful dashboard with email cards, stats, and category tabs
- Native macOS `.app` — double-click to launch

---

## Quick Start

### 1. Set up Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**, search for **Gmail API**, and enable it
4. Go to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth 2.0 Client ID**
6. Choose **Desktop app** as the application type
7. Download the JSON file and save it as `credentials.json` in this folder

> **Important:** On the OAuth consent screen, add yourself (and your wife's email, etc.) as test users if the app is in "Testing" mode.

### 2. Run setup

```bash
cd "/Volumes/T7/Mail Organizer"
bash setup.sh
```

This creates a virtual environment, installs dependencies, and builds the macOS app.

### 3. (Optional) Configure AI backend

Edit the `.env` file:

```bash
# For Gemini (cloud AI) — get a free key at https://aistudio.google.com/apikey
GEMINI_API_KEY=your_key_here

# For Ollama (local AI) — install from https://ollama.com
# Then pull a model: ollama pull llama3.2
OLLAMA_MODEL=llama3.2
```

You can also use **Rules Only** mode which requires no API keys.

### 4. Launch

Double-click **Mail Organizer.app** — it opens in your browser at `localhost:8501`.

Or run manually:

```bash
source .venv/bin/activate
streamlit run mail_organizer/app.py
```

---

## Usage

1. **Add an account** — click "Add Account" in the sidebar. A browser window opens for Gmail authorization.
2. **Select AI engine** — choose Gemini, Ollama, or Rules Only.
3. **Scan Inbox** — click the button. The app fetches your emails and categorizes them.
4. **Review** — browse categorized emails in tabs. Each tab shows email cards with sender, subject, and the AI's reasoning.
5. **Take action** — select emails with checkboxes, then click Label, Archive, or Trash. Destructive actions require confirmation.

---

## AI Backends

| Backend | Data Privacy | Speed | Accuracy | Setup |
|---------|-------------|-------|----------|-------|
| **Gemini** | Email metadata sent to Google API | Fast | Best | Need API key |
| **Ollama** | 100% local, nothing leaves your Mac | Slower | Good | Install Ollama + pull model |
| **Rules** | 100% local, no AI | Instant | Basic | None |

### Ollama setup

```bash
# Install Ollama
brew install ollama

# Pull a model
ollama pull llama3.2

# Start Ollama server (runs in background)
ollama serve
```

---

## Project Structure

```
mail_organizer/
  app.py             — Streamlit UI
  auth.py            — Gmail OAuth2 + multi-account
  gmail_client.py    — Gmail API operations
  categorizer.py     — AI categorization engine
  models.py          — Data models
  config.py          — Labels, categories, settings
resources/
  icon.png           — App icon source
tokens/              — Per-account OAuth tokens (gitignored)
.streamlit/
  config.toml        — Streamlit theme
credentials.json     — Google OAuth credentials (gitignored)
.env                 — API keys (gitignored)
```

---

## Troubleshooting

**"Missing credentials.json"** — You need to download OAuth credentials from Google Cloud Console. See step 1 above.

**OAuth consent screen says "unverified"** — This is normal for personal projects. Click "Advanced" → "Go to Mail Organizer (unsafe)" to proceed. Your data stays between you and Google.

**Gemini returns errors** — Check your API key in `.env`. The free tier has rate limits (15 requests/minute). Switch to Rules Only if you hit limits.

**Ollama is slow** — First run downloads the model. Subsequent runs are faster. Use a smaller model like `llama3.2` instead of larger ones.

**Port 8501 already in use** — The app auto-kills existing Streamlit processes on that port. If issues persist: `lsof -ti:8501 | xargs kill -9`
