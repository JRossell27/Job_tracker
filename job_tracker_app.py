import pandas as pd
import os
from datetime import datetime
import streamlit as st
from git import Repo

# =======================
# CONFIG
# =======================
DATA_FILE = "job_data.csv"
SYNC_FILE = "last_synced.txt"
COLUMNS = [
    "Company", "Job Title", "Location", "Salary (Est.)", "Job Posting Link",
    "Application Date", "Application Status", "Follow-Up Date",
    "Resume Optimized?", "Notes"
]

# GitHub repo path (Streamlit Cloud will clone this repo automatically)
REPO_PATH = "."  # current folder since Streamlit runs in the repo root

# =======================
# FUNCTIONS
# =======================
def init_tracker():
    """Create or fix CSV if missing columns"""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.read_csv(DATA_FILE)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
    df.to_csv(DATA_FILE, index=False)

def add_application(company, job_title, location, salary, link, app_date, status, follow_up, resume_opt, notes):
    df = pd.read_csv(DATA_FILE)
    new_row = {
        "Company": company, "Job Title": job_title, "Location": location,
        "Salary (Est.)": salary, "Job Posting Link": link,
        "Application Date": app_date, "Application Status": status,
        "Follow-Up Date": follow_up, "Resume Optimized?": resume_opt, "Notes": notes
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def edit_application(index, updated_row):
    df = pd.read_csv(DATA_FILE)
    for col, val in updated_row.items():
        df.at[index, col] = val
    df.to_csv(DATA_FILE, index=False)

def sync_to_github():
    """Auto-commit and push to GitHub (works on Streamlit Cloud too)"""
    with open(SYNC_FILE, "w") as f:
        f.write(f"Last synced: {datetime.now()}\n")
    repo = Repo(REPO_PATH)
    repo.git.add(DATA_FILE)
    repo.git.add(SYNC_FILE)
    if repo.is_dirty():
        repo.index.commit(f"Job tracker updated {datetime.now()}")
        origin = repo.remote(name="origin")
        origin.push()

def get_stats():
    df = pd.read_csv(DATA_FILE)
    total = len(df)
    interviews = len(df[df["Application Status"].astype(str).str.contains("Interview", na=False)])
    offers = len(df[df["Application Status"].astype(str).str.contains("Offer", na=False)])
    rejected = len(df[df["Application Status"].astype(str).str.contains("Rejected", na=False)])
    optimized = len(df[df["Resume Optimized?"].astype(str).str.contains("Yes", na=False)])
    return {
        "Total Applications": total,
        "Interviews": interviews,
        "Offers": offers,
        "Rejections": rejected,
        "Resume Optimized": optimized,
        "Interview Rate": f"{(interviews / total * 100):.1f}%" if total > 0 else "0%",
        "Offer Rate": f"{(offers / total * 100):.1f}%" if total > 0 else "0%"
    }

def safe_date(value):
    try:
        return pd.to_datetime(value)
    except:
        return datetime.now()

# =======================
# STREAMLIT APP
# =======================
st.set_page_config(page_title="Job Application Tracker", layout="wide")
st.title("📌 Job Application Tracker")

init_tracker()

# --- ADD NEW APPLICATION ---
with st.expander("➕ Add a New Application", expanded=True):
    with st.form("application_form"):
        col1, col2 = st.columns(2)
        company = col1.text_input("Company")
        job_title = col2.text_input("Job Title")
        location = col1.text_input("Location")
        salary = col2.text_input("Salary (Est.)")
        link = st.text_input("Job Posting Link")
        app_date = st.date_input("Application Date")
        status = st.selectbox("Application Status", ["Applied", "Interview", "Offer", "Rejected", "Ghosted"])
        follow_up = st.date_input("Follow-Up Date")
        resume_opt = st.selectbox("Resume Optimized?", ["Yes", "No"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Add Application")
        if submitted:
            add_application(company, job_title, location, salary, link, app_date, status, follow_up, resume_opt, notes)
            sync_to_github()
            st.success("✅ Application added & synced to GitHub!")

# --- STATS ---
st.subheader("📊 Stats")
stats = get_stats()
cols = st.columns(len(stats))
for i, (k, v) in enumerate(stats.items()):
    cols[i].metric(k, v)

# --- VIEW & EDIT APPLICATIONS ---
st.subheader("✏️ Edit Applications")
df = pd.read_csv(DATA_FILE)

if len(df) > 0:
    edited_index = st.selectbox(
        "Select application to edit",
        options=df.index,
        format_func=lambda i: f"{df.at[i, 'Company']} - {df.at[i, 'Job Title']}"
    )
    row = df.iloc[edited_index]

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        company_e = col1.text_input("Company", value=row["Company"])
        job_title_e = col2.text_input("Job Title", value=row["Job Title"])
        location_e = col1.text_input("Location", value=row["Location"])
        salary_e = col2.text_input("Salary (Est.)", value=row["Salary (Est.)"])
        link_e = st.text_input("Job Posting Link", value=row["Job Posting Link"])
        app_date_e = st.date_input("Application Date", value=safe_date(row["Application Date"]))
        status_e = st.selectbox("Application Status", ["Applied", "Interview", "Offer", "Rejected", "Ghosted"],
                                index=["Applied", "Interview", "Offer", "Rejected", "Ghosted"].index(row["Application Status"])
                                if row["Application Status"] in ["Applied", "Interview", "Offer", "Rejected", "Ghosted"] else 0)
        follow_up_e = st.date_input("Follow-Up Date", value=safe_date(row["Follow-Up Date"]))
        resume_opt_e = st.selectbox("Resume Optimized?", ["Yes", "No"], index=0 if row["Resume Optimized?"] == "Yes" else 1)
        notes_e = st.text_area("Notes", value=row["Notes"])
        edited = st.form_submit_button("Save Changes")

        if edited:
            updated_row = {
                "Company": company_e, "Job Title": job_title_e, "Location": location_e,
                "Salary (Est.)": salary_e, "Job Posting Link": link_e,
                "Application Date": app_date_e, "Application Status": status_e,
                "Follow-Up Date": follow_up_e, "Resume Optimized?": resume_opt_e, "Notes": notes_e
            }
            edit_application(edited_index, updated_row)
            sync_to_github()
            st.success("✅ Changes saved & synced to GitHub!")

# --- SHOW TABLE ---
st.subheader("📄 All Applications")
st.dataframe(df)
