import pandas as pd
import os
from datetime import datetime
import streamlit as st
from git import Repo, Actor
import matplotlib.pyplot as plt

# =======================
# CONFIG
# =======================
DATA_FILE = "job_data.csv"
SYNC_FILE = "last_synced.txt"
COLUMNS = [
    "Company", "Job Title", "Location", "Salary (Est.)", "Job Posting Link",
    "Application Date", "Application Status", "Interview Stage",
    "Follow-Up Date", "Follow-Up Sent?", "Resume Optimized?",
    "Job Source", "Contact Name", "Notes"
]

# =======================
# FUNCTIONS
# =======================
def init_tracker():
    """Create or fix CSV if missing columns"""
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=COLUMNS)
    else:
        try:
            df = pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=COLUMNS)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
    df.to_csv(DATA_FILE, index=False)

def add_application(company, job_title, location, salary, link, app_date, status,
                    interview_stage, follow_up, follow_up_sent, resume_opt, job_source, contact_name, notes):
    df = pd.read_csv(DATA_FILE)
    new_row = {
        "Company": company, "Job Title": job_title, "Location": location,
        "Salary (Est.)": salary, "Job Posting Link": link,
        "Application Date": app_date, "Application Status": status,
        "Interview Stage": interview_stage, "Follow-Up Date": follow_up,
        "Follow-Up Sent?": follow_up_sent, "Resume Optimized?": resume_opt,
        "Job Source": job_source, "Contact Name": contact_name, "Notes": notes
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)

def edit_application(index, updated_row):
    df = pd.read_csv(DATA_FILE)
    for col, val in updated_row.items():
        df.at[index, col] = val
    df.to_csv(DATA_FILE, index=False)

def sync_to_github():
    """Commit & push changes to GitHub using token-based auth"""
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME")
    repo_name = os.getenv("GITHUB_REPO")

    if not token or not username or not repo_name:
        st.warning("⚠️ GitHub sync disabled – missing secrets.")
        return

    with open(SYNC_FILE, "w") as f:
        f.write(f"Last synced: {datetime.now()}\n")

    repo = Repo(".")
    repo.git.add(DATA_FILE)
    repo.git.add(SYNC_FILE)

    if repo.is_dirty():
        author = Actor(username, f"{username}@users.noreply.github.com")
        repo.index.commit(f"Job tracker updated {datetime.now()}", author=author)
        origin = repo.remote(name="origin")
        origin.set_url(f"https://{username}:{token}@github.com/{username}/{repo_name}.git")
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
    if "reset_form" not in st.session_state:
        st.session_state.reset_form = False

    def reset_form():
        st.session_state.reset_form = True
        init_tracker()
        st.rerun()

    with st.form("application_form", clear_on_submit=st.session_state.reset_form):
        col1, col2 = st.columns(2)
        company = col1.text_input("Company")
        job_title = col2.text_input("Job Title")
        location = col1.text_input("Location")
        salary = col2.text_input("Salary (Est.)")
        link = st.text_input("Job Posting Link")
        app_date = st.date_input("Application Date")
        status = st.selectbox("Application Status", ["Applied", "Interview", "Offer", "Rejected", "Ghosted"])
        interview_stage = st.selectbox("Interview Stage", ["N/A", "Screening", "Technical", "Final", "Offer Pending"])
        follow_up = st.date_input("Follow-Up Date")
        clear_follow_up = st.checkbox("Clear Follow-Up Date")
        follow_up = "" if clear_follow_up else follow_up
        follow_up_sent = st.selectbox("Follow-Up Sent?", ["Yes", "No"])
        resume_opt = st.selectbox("Resume Optimized?", ["Yes", "No"])
        job_source = st.text_input("Job Source (LinkedIn, Referral, etc.)")
        contact_name = st.text_input("Contact Name (if any)")
        notes = st.text_area("Notes")

        col3, col4 = st.columns(2)
        submitted = col3.form_submit_button("Add Application")
        reset = col4.form_submit_button("Reset Form", on_click=reset_form)

        if submitted:
            add_application(company, job_title, location, salary, link, app_date, status,
                            interview_stage, follow_up, follow_up_sent, resume_opt, job_source, contact_name, notes)
            sync_to_github()
            st.success("✅ Application added & synced to GitHub!")
            st.session_state.reset_form = True
            st.rerun()

# --- STATS ---
st.subheader("📊 Stats")
stats = get_stats()
cols = st.columns(len(stats))
for i, (k, v) in enumerate(stats.items()):
    cols[i].metric(k, v)

# --- VIEW & EDIT APPLICATIONS ---
with st.expander("✏️ Edit or Delete Applications", expanded=False):
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
            status_e = st.selectbox(
                "Application Status",
                ["Applied", "Interview", "Offer", "Rejected", "Ghosted"],
                index=["Applied", "Interview", "Offer", "Rejected", "Ghosted"].index(row["Application Status"])
                if row["Application Status"] in ["Applied", "Interview", "Offer", "Rejected", "Ghosted"] else 0
            )
            interview_stage_e = st.selectbox(
                "Interview Stage",
                ["N/A", "Screening", "Technical", "Final", "Offer Pending"],
                index=["N/A", "Screening", "Technical", "Final", "Offer Pending"].index(row["Interview Stage"])
                if row["Interview Stage"] in ["N/A", "Screening", "Technical", "Final", "Offer Pending"] else 0
            )
            clear_follow_up_edit = st.checkbox("Clear Follow-Up Date (Edit)")
            follow_up_e = "" if clear_follow_up_edit else st.date_input(
                "Follow-Up Date", value=safe_date(row["Follow-Up Date"]) if row["Follow-Up Date"] != "" else datetime.now()
            )
            follow_up_sent_e = st.selectbox("Follow-Up Sent?", ["Yes", "No"], index=0 if row["Follow-Up Sent?"] == "Yes" else 1)
            resume_opt_e = st.selectbox("Resume Optimized?", ["Yes", "No"], index=0 if row["Resume Optimized?"] == "Yes" else 1)
            job_source_e = st.text_input("Job Source", value=row["Job Source"])
            contact_name_e = st.text_input("Contact Name", value=row["Contact Name"])
            notes_e = st.text_area("Notes", value=row["Notes"])

            col3, col4 = st.columns(2)
            edited = col3.form_submit_button("💾 Save Changes")
            delete = col4.form_submit_button("🗑️ Delete Entry")

            if edited:
                updated_row = {
                    "Company": company_e, "Job Title": job_title_e, "Location": location_e,
                    "Salary (Est.)": salary_e, "Job Posting Link": link_e,
                    "Application Date": app_date_e, "Application Status": status_e,
                    "Interview Stage": interview_stage_e, "Follow-Up Date": follow_up_e,
                    "Follow-Up Sent?": follow_up_sent_e, "Resume Optimized?": resume_opt_e,
                    "Job Source": job_source_e, "Contact Name": contact_name_e, "Notes": notes_e
                }
                edit_application(edited_index, updated_row)
                sync_to_github()
                st.success("✅ Changes saved & synced to GitHub!")

            if delete:
                df.drop(index=edited_index, inplace=True)
                df.to_csv(DATA_FILE, index=False)
                sync_to_github()
                st.warning("🗑️ Entry deleted & synced to GitHub!")
                st.rerun()

# --- SEARCH, FILTERS, AND CHARTS ---
st.subheader("🔍 Search, Filters & Charts")

df = pd.read_csv(DATA_FILE)

if len(df) > 0:
    search = st.text_input("Search by Company or Job Title")
    status_filter = st.multiselect("Filter by Application Status", df["Application Status"].unique())
    follow_up_filter = st.multiselect("Filter by Follow-Up Sent?", df["Follow-Up Sent?"].unique())
    resume_filter = st.multiselect("Filter by Resume Optimized?", df["Resume Optimized?"].unique())

    filtered_df = df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["Company"].str.contains(search, case=False, na=False) |
            filtered_df["Job Title"].str.contains(search, case=False, na=False)
        ]
    if status_filter:
        filtered_df = filtered_df[filtered_df["Application Status"].isin(status_filter)]
    if follow_up_filter:
        filtered_df = filtered_df[filtered_df["Follow-Up Sent?"].isin(follow_up_filter)]
    if resume_filter:
        filtered_df = filtered_df[filtered_df["Resume Optimized?"].isin(resume_filter)]

    st.write("### Filtered Results")
    st.dataframe(filtered_df)

    # --- Charts ---
    st.write("### 📊 Applications Over Time")
    filtered_df["Application Date"] = pd.to_datetime(filtered_df["Application Date"], errors="coerce")
    apps_over_time = filtered_df.groupby(filtered_df["Application Date"].dt.date).size()

    if not apps_over_time.empty:
        plt.figure(figsize=(6, 3))
        plt.plot(apps_over_time.index, apps_over_time.values, marker="o")
        plt.xticks(rotation=45)
        plt.title("Applications Over Time")
        plt.xlabel("Date")
        plt.ylabel("Applications")
        st.pyplot(plt)

    st.write("### 📊 Status Breakdown")
    status_counts = filtered_df["Application Status"].value_counts()
    if not status_counts.empty:
        plt.figure(figsize=(5, 3))
        plt.bar(status_counts.index, status_counts.values)
        plt.title("Status Breakdown")
        plt.xlabel("Status")
        plt.ylabel("Count")
        st.pyplot(plt)
