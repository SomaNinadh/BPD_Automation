# BPD Generator

A Streamlit + python-docx app for generating Business Process Documents
in a fixed corporate format. Build documents block-by-block in the UI,
save server-backed drafts, and export a polished `.docx`.

## Features

- Block-based authoring for Heading, Subheading, Normal Heading, Paragraph, Image, and Table blocks
- Auto-numbered headings with uppercase conversion for Heading and Subheading
- Live Word Table of Contents field
- Branded header and footer with document metadata
- Table paste/import support from Excel or Word
- Hosted draft saving with Supabase Auth and Postgres
- Fixed header logos configured from code

## Project layout

```text
Soma/
|-- app.py
|-- requirements.txt
|-- README.md
|-- supabase/
|   `-- schema.sql
`-- src/
    |-- document/
    |   |-- blocks.py
    |   |-- builder.py
    |   |-- header_footer.py
    |   |-- styles.py
    |   `-- toc.py
    |-- services/
    |   |-- auth_service.py
    |   |-- draft_service.py
    |   `-- supabase_service.py
    `-- ui/
        |-- components.py
        `-- state.py
```

## Run locally

Requires Python 3.9+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Supabase setup

1. Create a free Supabase project.
2. In the Supabase SQL editor, run the SQL in `supabase/schema.sql`.
3. Enable Email provider with password login in Supabase Auth.
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

For Streamlit Community Cloud, put the same values in the deployed app's secrets.

## Using the app

1. Sign up or log in.
2. Create or load a draft from the sidebar.
3. Add blocks and edit the document content.
4. Save the draft whenever you want to keep progress.
5. Generate and download the `.docx` when ready.

## Fixed header logos

Set both logo image paths in `src/document/header_footer.py`:

```python
CLIENT_LOGO_PATH = r"C:\path\to\client_logo.png"
OUR_LOGO_PATH = r"C:\path\to\our_logo.png"
```

The app no longer asks for a client logo in the UI.

## Notes

- Drafts are stored as JSON snapshots of the editor state, not as `.docx` files.
- The app stays public at the URL level, but document editing is gated behind app login.
- The current draft model allows all signed-in users to view and edit all drafts.
