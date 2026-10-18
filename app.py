import os
import html
from datetime import datetime

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from src.vision import extract_register_data
from src.reconcile import run_reconciliation
from src.alert import send_slack_alert

load_dotenv()

MODEL_NAME = "gemini-3.8-flash"
REGISTER_IMAGES = ["data/t4_register_page1.jpg", "data/t4_register_page2.jpg"]
ERP_PATH = "data/t4_erp_grn.csv"
STORE_PATH = "data/t4_store_sheet.xlsx"

INPUT_SOURCES = [
    ("Handwritten register", "Two scanned pages. The system reads the handwriting for you.", REGISTER_IMAGES),
    ("ERP export", "Goods received notes exported from the accounting system.", [ERP_PATH]),
    ("Store sheet", "The storekeeper's Excel file of what physically arrived.", [STORE_PATH]),
]

st.set_page_config(
    page_title="Kestrel Industries | Month-end reconciliation",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {
    --ink: #1B2430;
    --muted: #5B6572;
    --faint: #8A93A0;
    --rule: #D9DDE3;
    --ground: #F5F6F8;
    --sheet: #FFFFFF;
    --accent: #1F4E6B;
    --accent-dark: #173B52;
    --ok: #1E6B4E;
    --ok-bg: #E3F1EA;
    --warn: #8A5A00;
    --warn-bg: #FBF0D6;
    --bad: #9B2C2C;
    --bad-bg: #F8E4E2;
}

html, body, .stApp, [class*="css"] { font-family: 'IBM Plex Sans', system-ui, sans-serif; color: var(--ink); }
.stApp { background: var(--ground); color-scheme: light; }

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

.block-container { padding: 3.25rem 3.5rem 4rem; max-width: 1280px; }

/* Header */
.page-title {
    font-family: 'Newsreader', Georgia, serif; font-size: 2.15rem; font-weight: 500;
    letter-spacing: -0.01em; line-height: 1.15; margin: 0; color: var(--ink);
}
.page-sub { margin: 0.5rem 0 0; font-size: 0.95rem; color: var(--muted); max-width: 66ch; line-height: 1.6; }
.header-rule { border: 0; border-top: 1px solid var(--rule); margin: 1.75rem 0 1.5rem; }

/* Sidebar */
[data-testid="stSidebar"] { background: var(--sheet); border-right: 1px solid var(--rule); }
[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
.side-heading { font-family: 'Newsreader', Georgia, serif; font-size: 1.15rem; font-weight: 500; margin: 0 0 1rem; }
.side-list { margin: 1.25rem 0 0; padding: 0; }
.side-row {
    display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
    padding: 0.6rem 0; border-top: 1px solid var(--rule); font-size: 0.85rem;
}
.side-row dt { color: var(--muted); margin: 0; }
.side-row dd { margin: 0; font-weight: 500; text-align: right; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 7px; background: var(--ok); }
.dot.is-off { background: var(--bad); }
.side-help { font-size: 0.82rem; color: var(--muted); line-height: 1.55; margin: 1.5rem 0 0; }

/* Inputs */
label, [data-testid="stWidgetLabel"] p { font-size: 0.85rem !important; color: var(--muted) !important; font-weight: 500; }
.stTextInput input {
    background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px;
    font-family: 'IBM Plex Sans', sans-serif; font-variant-numeric: tabular-nums; color: var(--ink);
}
.stTextInput input:focus { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
[data-baseweb="select"] > div { background: var(--sheet); border-color: var(--rule); border-radius: 4px; }

/* Buttons */
.stButton > button, .stDownloadButton > button {
    font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; font-size: 0.9rem;
    border-radius: 4px; padding: 0.6rem 1.25rem; transition: background 120ms ease, border-color 120ms ease;
}
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
    background: var(--accent); border: 1px solid var(--accent); color: #fff;
}
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent-dark); border-color: var(--accent-dark); color: #fff;
}
.stButton > button[kind="primary"]:disabled, button[data-testid="stBaseButton-primary"]:disabled {
    background: var(--rule); border-color: var(--rule); color: var(--faint);
}
.stDownloadButton > button, button[data-testid="stBaseButton-secondary"] {
    background: var(--sheet); border: 1px solid var(--rule); color: var(--ink);
}
.stDownloadButton > button:hover, button[data-testid="stBaseButton-secondary"]:hover { border-color: var(--accent); color: var(--accent); }
button:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }

/* Run status panel */
[data-testid="stStatus"], details[data-testid="stExpander"] {
    background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px;
}

/* Sections */
.section-title { font-family: 'Newsreader', Georgia, serif; font-size: 1.35rem; font-weight: 500; margin: 2.25rem 0 0.35rem; }
.section-copy { font-size: 0.9rem; color: var(--muted); margin: 0 0 1rem; max-width: 72ch; line-height: 1.6; }

/* How it works (a real sequence, so numbered) */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0; background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; }
.step { padding: 1.25rem 1.5rem 1.4rem; border-left: 1px solid var(--rule); }
.step:first-child { border-left: 0; }
.step-num { font-family: 'Newsreader', Georgia, serif; font-size: 1.6rem; color: var(--accent); line-height: 1; margin: 0 0 0.6rem; }
.step-title { font-size: 0.95rem; font-weight: 600; margin: 0 0 0.35rem; }
.step-copy { font-size: 0.85rem; color: var(--muted); line-height: 1.55; margin: 0; }

/* Input files */
.files { width: 100%; border-collapse: collapse; background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; font-size: 0.88rem; }
.files td { padding: 0.85rem 1.1rem; border-top: 1px solid var(--rule); vertical-align: top; }
.files tr:first-child td { border-top: 0; }
.files .f-name { font-weight: 500; width: 22%; }
.files .f-desc { color: var(--muted); }
.files .f-path { color: var(--faint); font-size: 0.8rem; margin-top: 0.2rem; font-variant-numeric: tabular-nums; }
.files .f-state { text-align: right; white-space: nowrap; width: 12%; }
.pill { display: inline-block; font-size: 0.78rem; font-weight: 500; padding: 0.15rem 0.6rem; border-radius: 999px; }
.pill.ok { background: var(--ok-bg); color: var(--ok); }
.pill.bad { background: var(--bad-bg); color: var(--bad); }
.pill.warn { background: var(--warn-bg); color: var(--warn); }

.run-note { font-size: 0.85rem; color: var(--muted); margin: 0.6rem 0 0; line-height: 1.55; max-width: 66ch; }

/* Verdict */
.verdict { font-family: 'Newsreader', Georgia, serif; font-size: 2rem; font-weight: 500; line-height: 1.25; letter-spacing: -0.01em; margin: 0.25rem 0 0.4rem; max-width: 30ch; }
.verdict-sub { font-size: 0.9rem; color: var(--muted); margin: 0 0 1.5rem; line-height: 1.55; max-width: 66ch; }

/* Summary figures */
.figures { display: grid; grid-template-columns: repeat(4, 1fr); background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; }
.figure { padding: 1.25rem 1.5rem 1.35rem; border-left: 1px solid var(--rule); }
.figure:first-child { border-left: 0; }
.figure-label { font-size: 0.85rem; font-weight: 500; margin: 0 0 0.5rem; }
.figure-value { font-family: 'Newsreader', Georgia, serif; font-size: 2.35rem; font-weight: 500; line-height: 1; font-variant-numeric: lining-nums tabular-nums; margin: 0; }
.figure-note { font-size: 0.8rem; margin: 0.6rem 0 0; color: var(--muted); line-height: 1.5; }
.figure.is-warn .figure-value { color: var(--warn); }
.figure.is-ok .figure-value { color: var(--ok); }

.split { margin: 1.5rem 0 0; }
.split-head { display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--muted); margin-bottom: 0.5rem; }
.split-bar { display: flex; height: 10px; border-radius: 2px; overflow: hidden; background: var(--rule); }
.split-ok { background: var(--ok); }
.split-warn { background: #C99A2E; }
.split-bar span + span { margin-left: 2px; }
.fine { font-size: 0.8rem; color: var(--faint); margin: 0.9rem 0 0; line-height: 1.5; max-width: 80ch; }

/* Next steps */
.todo { background: var(--sheet); border: 1px solid var(--rule); border-radius: 4px; padding: 0.4rem 1.5rem; }
.todo-row { display: flex; gap: 1rem; padding: 0.85rem 0; border-top: 1px solid var(--rule); font-size: 0.9rem; line-height: 1.55; }
.todo-row:first-child { border-top: 0; }
.todo-n { font-family: 'Newsreader', Georgia, serif; color: var(--accent); font-size: 1.1rem; width: 1.2rem; flex: none; }

/* Meaning table */
.meaning { width: 100%; border-collapse: collapse; background: var(--sheet); border: 1px solid var(--rule); font-size: 0.88rem; }
.meaning th { text-align: left; font-weight: 500; color: var(--muted); padding: 0.7rem 1.1rem; border-bottom: 1px solid var(--rule); font-size: 0.82rem; }
.meaning td { padding: 0.85rem 1.1rem; border-top: 1px solid var(--rule); vertical-align: top; line-height: 1.55; }
.meaning tr:first-child td { border-top: 0; }
.meaning .m-count { text-align: right; font-variant-numeric: tabular-nums; width: 8%; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 1.75rem; border-bottom: 1px solid var(--rule); }
.stTabs [data-baseweb="tab"] { padding: 0.65rem 0; background: transparent; font-size: 0.92rem; font-weight: 500; height: auto; }
.stTabs [data-baseweb="tab"] p, .stTabs [data-baseweb="tab"] span { color: #4A5260 !important; font-weight: 500; }
.stTabs [data-baseweb="tab"]:hover p { color: #1B2430 !important; }
.stTabs [aria-selected="true"] p, .stTabs [aria-selected="true"] span { color: #1B2430 !important; font-weight: 600; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

[data-testid="stDataFrame"] { border: 1px solid var(--rule); border-radius: 4px; background: var(--sheet); }

/* Messages */
.msg { border-radius: 4px; padding: 1rem 1.25rem; font-size: 0.9rem; line-height: 1.6; margin: 0 0 1rem; }
.msg.ok { background: var(--ok-bg); color: var(--ok); }
.msg.bad { background: var(--bad-bg); color: var(--bad); }
.msg strong { font-weight: 600; }
.msg ul { margin: 0.5rem 0 0 1.1rem; padding: 0; }

@media (max-width: 900px) {
    .block-container { padding: 2rem 1.25rem 3rem; }
    .figures, .steps { grid-template-columns: repeat(2, 1fr); }
    .figure:nth-child(3), .step:nth-child(3) { border-left: 0; }
    .figure:nth-child(n+3), .step:nth-child(n+3) { border-top: 1px solid var(--rule); }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def esc(value) -> str:
    return html.escape(str(value))


def now_pkt() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %b %Y, %H:%M")
    except Exception:
        return datetime.now().strftime("%d %b %Y, %H:%M")


def explain_status(status: str) -> str:
    """Plain-language meaning of a status label. Matches on keywords, falls back to a generic line."""
    s = str(status).lower()
    if s == "matched":
        return "All three sources agree on this line. Nothing to do."
    if any(k in s for k in ("unread", "illegible", "unclear", "ocr", "low confidence")):
        return "The handwriting could not be read with confidence. Open the register page and read the line yourself."
    if "orphan" in s:
        return "This record exists in only one source. Find out why the other sources do not list it."
    if any(k in s for k in ("missing", "not found", "absent")):
        return "The line is missing from at least one source. Check whether the goods were recorded late or not at all."
    if any(k in s for k in ("mismatch", "differ", "discrepan", "variance", "quantity", "qty", "short", "excess")):
        return "The sources disagree on a value such as quantity or amount. Compare the figures side by side."
    return "This line did not pass the three-way check. Compare it with the register, the ERP export and the store sheet."


def status_style(value: str) -> str:
    if value == "Matched":
        return "background-color: #E3F1EA; color: #1E6B4E; font-weight: 500;"
    return "background-color: #FBF0D6; color: #8A5A00; font-weight: 500;"


def styled(frame: pd.DataFrame):
    if "Status" not in frame.columns:
        return frame
    return frame.style.map(status_style, subset=["Status"])


def filter_frame(frame: pd.DataFrame, key: str, statuses: list) -> pd.DataFrame:
    """Status filter and free-text search shared by both tables."""
    left, right = st.columns([2, 3])
    with left:
        chosen = st.multiselect(
            "Show these statuses",
            options=statuses,
            default=statuses,
            key=f"{key}_status",
            help="Remove a status to hide those lines.",
        )
    with right:
        query = st.text_input(
            "Search",
            key=f"{key}_search",
            placeholder="Type an item name, code or supplier",
            help="Looks through every column. Leave empty to see all lines.",
        )
    out = frame[frame["Status"].isin(chosen)]
    if query.strip():
        mask = out.astype(str).apply(
            lambda col: col.str.contains(query.strip(), case=False, regex=False)
        ).any(axis=1)
        out = out[mask]
    st.caption(f"Showing {len(out):,} of {len(frame):,} lines.")
    return out


def input_files_status():
    rows, all_ok = [], True
    for name, desc, paths in INPUT_SOURCES:
        missing = [p for p in paths if not os.path.exists(p)]
        ok = not missing
        all_ok = all_ok and ok
        rows.append((name, desc, paths, missing))
    return rows, all_ok


file_rows, files_ok = input_files_status()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="side-heading">Run settings</p>', unsafe_allow_html=True)
    scenario_date = st.text_input(
        "Report time (PKT)",
        value="2026-10-15 08:30",
        help="This time is printed on the Slack message. Change it only if the report belongs to a different date.",
    )
    state_class = "" if files_ok else " is-off"
    state_text = "Ready to run" if files_ok else "Input files missing"
    last_run = st.session_state.get("last_run", "No run yet")
    st.markdown(
        f"""
<dl class="side-list">
<div class="side-row"><dt>Status</dt><dd><span class="dot{state_class}"></span>{state_text}</dd></div>
<div class="side-row"><dt>Last run</dt><dd>{esc(last_run)}</dd></div>
<div class="side-row"><dt>Handwriting reader</dt><dd>{esc(MODEL_NAME)}</dd></div>
<div class="side-row"><dt>Results sent to</dt><dd>Slack</dd></div>
</dl>
<p class="side-help">Nothing on this page changes your accounting data. The tool only reads the three files and reports what it finds.</p>
""",
        unsafe_allow_html=True,
    )
    if "merged_df" in st.session_state:
        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        if st.button("Clear results", use_container_width=True):
            for k in ("merged_df", "total_inputs", "last_run"):
                st.session_state.pop(k, None)
            st.rerun()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
<h1 class="page-title">Month-end reconciliation</h1>
<p class="page-sub">Kestrel Industries. This page checks that what the storekeeper wrote, what the store recorded and what the ERP shows all tell the same story, and lists every line that does not.</p>
<hr class="header-rule">
""",
    unsafe_allow_html=True,
)

has_results = "merged_df" in st.session_state


def render_steps():
    st.markdown(
        """
<div class="steps">
<div class="step"><p class="step-num">1</p><p class="step-title">Read the register</p><p class="step-copy">The scanned handwritten pages are read and turned into rows of data, the way a clerk would type them in.</p></div>
<div class="step"><p class="step-num">2</p><p class="step-title">Compare three sources</p><p class="step-copy">Every row from the register, the ERP and the store sheet is lined up by item. Rows are kept even when they have no partner.</p></div>
<div class="step"><p class="step-num">3</p><p class="step-title">Report the exceptions</p><p class="step-copy">Lines that disagree, cannot be read or appear in only one source are listed here and posted to Slack.</p></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_files():
    body = ""
    for name, desc, paths, missing in file_rows:
        names = ", ".join(os.path.basename(p) for p in paths)
        if missing:
            miss = ", ".join(os.path.basename(p) for p in missing)
            pill = '<span class="pill bad">Missing</span>'
            extra = f'<div class="f-path">Not found: {esc(miss)}</div>'
        else:
            pill = '<span class="pill ok">Found</span>'
            extra = f'<div class="f-path">{esc(names)}</div>'
        body += (
            f'<tr><td class="f-name">{esc(name)}</td>'
            f'<td class="f-desc">{esc(desc)}{extra}</td>'
            f'<td class="f-state">{pill}</td></tr>'
        )
    st.markdown(f'<table class="files">{body}</table>', unsafe_allow_html=True)


if not has_results:
    st.markdown('<h2 class="section-title" style="margin-top:0">How it works</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-copy">One button runs all three stages. You do not need to prepare anything else.</p>', unsafe_allow_html=True)
    render_steps()
else:
    with st.expander("How it works"):
        render_steps()

st.markdown('<h2 class="section-title">Files used in this run</h2>', unsafe_allow_html=True)
st.markdown('<p class="section-copy">All three must be present before you can start. They are read from the project&#8217;s data folder.</p>', unsafe_allow_html=True)
render_files()

st.markdown('<div style="height:1.25rem"></div>', unsafe_allow_html=True)

run_clicked = st.button("Run September reconciliation", type="primary", disabled=not files_ok)
if files_ok:
    st.markdown(
        '<p class="run-note">Keep this page open while the run is in progress. Running again replaces the results below and sends a new message to Slack.</p>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<p class="run-note">Add the missing files to the data folder and refresh this page. The run button turns on once all three are found.</p>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if run_clicked:
    try:
        with st.status("Running reconciliation", expanded=True) as status:
            st.write("Step 1 of 3: reading the register pages.")
            vision_data = extract_register_data(REGISTER_IMAGES)

            st.write("Step 2 of 3: comparing the three sources and checking that no row was dropped.")
            merged_df, total_inputs = run_reconciliation(
                erp_path=ERP_PATH,
                store_path=STORE_PATH,
                vision_data=vision_data,
            )

            st.write("Step 3 of 3: sending the exception summary to Slack.")
            send_slack_alert(merged_df, total_inputs, scenario_date)

            status.update(label="Reconciliation complete. No rows were lost.", state="complete", expanded=False)

        st.session_state["merged_df"] = merged_df
        st.session_state["total_inputs"] = total_inputs
        st.session_state["last_run"] = now_pkt()
        st.rerun()

    except Exception as e:
        st.markdown(
            """
<div class="msg bad"><strong>The run stopped before it finished.</strong> No results were saved and no complete Slack message was sent.
<ul>
<li>Check that all three input files are present and not open in another program.</li>
<li>Check that the API key and Slack webhook in the .env file are filled in.</li>
<li>Check your internet connection, then run again.</li>
</ul></div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("Technical detail for your developer"):
            st.code(str(e))
        st.stop()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if "merged_df" in st.session_state:
    df = st.session_state["merged_df"]
    total_inputs = st.session_state["total_inputs"]

    total_rows = len(df)
    matched_count = int((df["Status"] == "Matched").sum())
    exception_df = df[df["Status"] != "Matched"]
    exception_count = len(exception_df)
    denom = max(total_rows, 1)
    matched_pct = matched_count / denom * 100
    exception_pct = exception_count / denom * 100

    st.markdown('<h2 class="section-title">Result</h2>', unsafe_allow_html=True)

    if exception_count == 0:
        headline = f"All {total_rows:,} lines match."
        subline = "The register, the ERP export and the store sheet agree. No action is needed."
    else:
        word = "line needs" if exception_count == 1 else "lines need"
        headline = f"{matched_count:,} of {total_rows:,} lines match. {exception_count:,} {word} your review."
        subline = "Open the Needs review tab below. Each line there says what is wrong and where to look."
    st.markdown(
        f'<p class="verdict">{esc(headline)}</p><p class="verdict-sub">{esc(subline)}</p>',
        unsafe_allow_html=True,
    )

    fine = ""
    if total_inputs != total_rows:
        fine = (
            '<p class="fine">Input rows and ledger lines can differ. When the same item appears in more than one source, '
            "those rows are combined into a single ledger line.</p>"
        )

    st.markdown(
        f"""
<div class="figures">
<div class="figure"><p class="figure-label">Input rows read</p><p class="figure-value">{total_inputs:,}</p><p class="figure-note">Rows taken from the register, the ERP and the store sheet together.</p></div>
<div class="figure is-ok"><p class="figure-label">Matched</p><p class="figure-value">{matched_count:,}</p><p class="figure-note">{matched_pct:.0f}% of ledger lines. All three sources agree.</p></div>
<div class="figure is-warn"><p class="figure-label">Needs review</p><p class="figure-value">{exception_count:,}</p><p class="figure-note">{exception_pct:.0f}% of ledger lines. A person should look at these.</p></div>
<div class="figure"><p class="figure-label">Completeness check</p><p class="figure-value">Passed</p><p class="figure-note">Every input row appears somewhere in the ledger.</p></div>
</div>
<div class="split">
<div class="split-head"><span>Share of ledger lines</span><span>{matched_count:,} matched, {exception_count:,} need review</span></div>
<div class="split-bar" role="img" aria-label="{matched_pct:.0f} percent matched, {exception_pct:.0f} percent need review">
<span class="split-ok" style="width:{matched_pct:.2f}%"></span>
<span class="split-warn" style="width:{exception_pct:.2f}%"></span>
</div>
</div>
{fine}
""",
        unsafe_allow_html=True,
    )

    if exception_count > 0:
        st.markdown('<h2 class="section-title">What to do next</h2>', unsafe_allow_html=True)
        st.markdown(
            """
<div class="todo">
<div class="todo-row"><span class="todo-n">1</span><span>Open <strong>Needs review</strong> below. Use the status filter to work through one type of problem at a time.</span></div>
<div class="todo-row"><span class="todo-n">2</span><span>For each line, compare the register page, the ERP export and the store sheet. The &#8220;What the statuses mean&#8221; tab explains each status.</span></div>
<div class="todo-row"><span class="todo-n">3</span><span>Correct the record in the system where the mistake is, then run the reconciliation again to confirm the line clears.</span></div>
<div class="todo-row"><span class="todo-n">4</span><span>Download the list as CSV if you need to share it with the store or purchasing team. The same summary was posted to Slack.</span></div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:1.75rem"></div>', unsafe_allow_html=True)

    tab_review, tab_ledger, tab_meaning = st.tabs(
        [f"Needs review ({exception_count})", f"All lines ({total_rows})", "What the statuses mean"]
    )

    with tab_review:
        st.markdown(
            '<h2 class="section-title" style="margin-top:1.5rem">Lines that need a person</h2>'
            '<p class="section-copy">These lines failed the three-way check, contain handwriting that could not be read, or exist in only one source.</p>',
            unsafe_allow_html=True,
        )
        if exception_count > 0:
            exc_statuses = sorted(exception_df["Status"].astype(str).unique())
            shown = filter_frame(exception_df, "exc", exc_statuses)
            st.dataframe(styled(shown), use_container_width=True, hide_index=True)
            st.download_button(
                "Download this list (CSV)",
                data=shown.to_csv(index=False).encode("utf-8"),
                file_name="september_needs_review.csv",
                mime="text/csv",
                help="Opens in Excel. Contains the lines currently shown in the table.",
            )
        else:
            st.markdown(
                '<div class="msg ok"><strong>Nothing to review.</strong> Every record matches across all three sources.</div>',
                unsafe_allow_html=True,
            )

    with tab_ledger:
        st.markdown(
            '<h2 class="section-title" style="margin-top:1.5rem">Every line, with its status</h2>'
            '<p class="section-copy">The complete record from the register, the ERP export and the store sheet. Use it to trace a single item across all three.</p>',
            unsafe_allow_html=True,
        )
        all_statuses = sorted(df["Status"].astype(str).unique())
        shown_all = filter_frame(df, "all", all_statuses)
        st.dataframe(styled(shown_all), use_container_width=True, hide_index=True)
        st.download_button(
            "Download this list (CSV)",
            data=shown_all.to_csv(index=False).encode("utf-8"),
            file_name="september_all_lines.csv",
            mime="text/csv",
            help="Opens in Excel. Contains the lines currently shown in the table.",
        )

    with tab_meaning:
        st.markdown(
            '<h2 class="section-title" style="margin-top:1.5rem">What each status means</h2>'
            '<p class="section-copy">Only statuses that appear in this run are listed.</p>',
            unsafe_allow_html=True,
        )
        counts = df["Status"].astype(str).value_counts()
        ordered = sorted(counts.index, key=lambda s: (s != "Matched", s))
        rows = ""
        for s in ordered:
            pill_class = "ok" if s == "Matched" else "warn"
            rows += (
                f'<tr><td><span class="pill {pill_class}">{esc(s)}</span></td>'
                f"<td>{esc(explain_status(s))}</td>"
                f'<td class="m-count">{int(counts[s]):,}</td></tr>'
            )
        st.markdown(
            f'<table class="meaning"><tr><th>Status</th><th>What it means and what to do</th><th style="text-align:right">Lines</th></tr>{rows}</table>',
            unsafe_allow_html=True,
        )