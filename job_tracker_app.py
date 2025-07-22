import pandas as pd
import os
import hashlib
from datetime import datetime
import streamlit as st
from git import Repo

# =======================
# CONFIG
# =======================
USER_PASSWORD_FILE = "user_passwords.csv"
SYNC_FILE = "last_synced.txt"
COLUMNS = [
    "Company", "Job Title", "Location", "Salary (Est.)", "Job Posting Link",
    "Application Date", "Application Status", "Interview Stage",
    "Follow-Up Date", "Follow-Up Sent?", "Resume Optimized?",
    "Job Source", "Contact Name", "Notes"
]

# =======================
# PASSWORD FUNCTIONS
# =======================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_user_passwords():
    if not os.path.exists(USER_PASSWORD_FILE):
        return pd.DataFrame(columns=["User", "PasswordHash"])
    return pd.read_csv(USER_PASSWORD_FILE)

def save_user_password(user, password):
    df = load_user_passwords()
    if user in df["User"].values:
        df.loc[df["User"] == user, "PasswordHash"] = hash_password(password)
    else:
        df = pd.concat([df, pd.DataFrame([{"User": user, "PasswordHash": hash_password(password)}])], ignore_index=True)
    df.to_csv(USER_PASSWORD_FILE, index=False)

def verify_password(user, password):
    df = load_user_passwords()
    if user not in df["User"].values:
        return None
    stored_hash = df.loc[df["User"] == user, "PasswordHash"].values[0]
    return stored_hash == hash_password(password)

# =======================
# JOB TRACKER FUNCTIONS
# =======================
def init_tracker(user_file):
    """Creates a blank CSV for new users, ensures correct columns"""
    if not os.path.exists(user_file):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(user_file, index=False)
    else:
        try:
            df = pd.read_csv(user_file)
        except pd.errors.EmptyDataError:
            df = pd.DataFrame(columns=COLUMNS)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df.to_csv(user_file, index=False)

def add_application(user_file, company, job_title, location, salary, link, app_date, status,
                    interview_stage, follow_up, follow_up_sent, resume_opt, job_source, contact_name, notes):
    df = pd.read_csv(user_file)
    new_row = {
        "Company": company, "Job Title": job_title, "Location": location,
        "Salary (Est.)": salary, "Job Posting Link": link,
        "Application Date": app_date, "Application Status": status,
        "Interview Stage": interview_stage, "Follow-Up Date": follow_up,
        "Follow-Up Sent?": follow_up_sent, "Resume Optimized?": resume_opt,
        "Job Source": job_source, "Contact Name": contact_name, "Notes": notes
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(user_file, index=False)

def edit_application(user_file, index, updated_row):
    df = pd.read_csv(user_file)
    for col, val in updated_row.items():
        df.at[index, col] = val
    df.to_csv(user_file, index=False)

def sync_to_github():
    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME")
    repo_name = os.getenv("GITHUB_REPO")

    if not token or not username or not repo_name:
        st.warning("⚠️ GitHub sync disabled – missing secrets.")
        return

    with open(SYNC_FILE, "w") as f:
        f.write(f"Last synced: {datetime.now()}\n")

    repo = Repo(".")
    repo.git.add(A=True)
    repo.git.add(SYNC_FILE)

    if repo.is_dirty():
        repo.index.commit(f"Job tracker updated {datetime.now()}")
        origin = repo.remote(name="origin")
        origin.set_url(f"https://{username}:{token}@github.com/{username}/{repo_name}.git")
        origin.push()

def get_stats(user_file):
    df = pd.read_csv(user_file)
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
        if pd.isna(value) or value == "" or str(value).lower() == "nan":
            return datetime.now()
        return pd.to_datetime(value)
    except:
        return datetime.now()

# =======================
# STREAMLIT APP
# =======================
st.set_page_config(page_title="Multi-User Job Tracker", layout="wide")
st.title("📌 Multi-User Job Application Tracker")

# --- USER LOGIN / REGISTRATION ---
st.subheader("👤 Login or Create Account")

user_name = st.text_input("Enter Your Name").strip()
user_pass = st.text_input("Enter Your Password", type="password")

if not user_name or not user_pass:
    st.stop()

existing = user_name in load_user_passwords()["User"].values

if existing:
    if not verify_password(user_name, user_pass):
        st.error("❌ Incorrect password. Try again.")
        st.stop()
else:
    st.info("🆕 New user detected! Creating your account now...")
    save_user_password(user_name, user_pass)

# Setup user CSV
user_file = f"job_data_{user_name}.csv"
init_tracker(user_file)

st.success(f"✅ Logged in as {user_name}")

# --- ADD NEW APPLICATION ---
with st.expander("➕ Add a New Application", expanded=True):
    if "reset_form" not in st.session_state:
        st.session_state.reset_form = False

    def reset_form():
        st.session_state.reset_form = True
        init_tracker(user_file)
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
            add_application(user_file, company, job_title, location, salary, link, app_date, status,
                            interview_stage, follow_up, follow_up_sent, resume_opt, job_source, contact_name, notes)
            sync_to_github()
            st.success(f"✅ Application added for {user_name}!")
            st.session_state.reset_form = True
            st.rerun()

# --- STATS ---
st.subheader(f"📊 Stats for {user_name}")
stats = get_stats(user_file)
cols = st.columns(len(stats))
for i, (k, v) in enumerate(stats.items()):
    cols[i].metric(k, v)

# --- VIEW & EDIT APPLICATIONS ---
with st.expander(f"✏️ Edit or Delete Applications ({user_name})", expanded=False):
    df_edit = pd.read_csv(user_file)
    if len(df_edit) > 0:
        edited_index = st.selectbox(
            "Select application to edit",
            options=df_edit.index,
            format_func=lambda i: f"{df_edit.at[i, 'Company']} - {df_edit.at[i, 'Job Title']}"
        )
        row = df_edit.iloc[edited_index]

        with st.form("edit_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            company_e = col1.text_input("Company", value=row["Company"])
            job_title_e = col2.text_input("Job Title", value=row["Job Title"])
            location_e = col1.text_input("Location", value=row["Location"])
            salary_e = col2.text_input("Salary (Est.)", value=row["Salary (Est.)"])
            link_e = st.text_input("Job Posting Link", value=row["Job Posting Link"])
            app_date_e = st.date_input("Application Date", value=safe_date(row["Application Date"]))
            status_e = st.selectbox("Application Status",
                                    ["Applied", "Interview", "Offer", "Rejected", "Ghosted"],
                                    index=["Applied", "Interview", "Offer", "Rejected", "Ghosted"].index(row["Application Status"])
                                    if row["Application Status"] in ["Applied", "Interview", "Offer", "Rejected", "Ghosted"] else 0)
            interview_stage_e = st.selectbox("Interview Stage",
                                             ["N/A", "Screening", "Technical", "Final", "Offer Pending"],
                                             index=["N/A", "Screening", "Technical", "Final", "Offer Pending"].index(row["Interview Stage"])
                                             if row["Interview Stage"] in ["N/A", "Screening", "Technical", "Final", "Offer Pending"] else 0)
            clear_follow_up_edit = st.checkbox("Clear Follow-Up Date (Edit)")
            follow_up_e = "" if clear_follow_up_edit else st.date_input("Follow-Up Date", value=safe_date(row["Follow-Up Date"]))
            follow_up_sent_e = st.selectbox("Follow-Up Sent?", ["Yes", "No"],
                                            index=0 if row["Follow-Up Sent?"] == "Yes" else 1)
            resume_opt_e = st.selectbox("Resume Optimized?", ["Yes", "No"],
                                        index=0 if row["Resume Optimized?"] == "Yes" else 1)
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
                edit_application(user_file, edited_index, updated_row)
                sync_to_github()
                st.success(f"✅ Changes saved for {user_name}!")

            if delete:
                df_edit.drop(index=edited_index, inplace=True)
                df_edit.to_csv(user_file, index=False)
                sync_to_github()
                st.warning(f"🗑️ Entry deleted for {user_name}!")
                st.rerun()

# --- SEARCH, FILTERS & CHARTS ---
st.subheader(f"🔍 Search, Filters & Charts ({user_name})")
df_view = pd.read_csv(user_file)
if len(df_view) > 0:
    search = st.text_input("Search by Company or Job Title")
    status_filter = st.multiselect("Filter by Application Status", df_view["Application Status"].unique())
    follow_up_filter = st.multiselect("Filter by Follow-Up Sent?", df_view["Follow-Up Sent?"].unique())
    resume_filter = st.multiselect("Filter by Resume Optimized?", df_view["Resume Optimized?"].unique())

    filtered_df = df_view.copy()
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

    st.write("### 📊 Applications Over Time")
    filtered_df["Application Date"] = pd.to_datetime(filtered_df["Application Date"], errors="coerce")
    apps_over_time = filtered_df.groupby(filtered_df["Application Date"].dt.date).size()
    if not apps_over_time.empty:
        st.line_chart(apps_over_time)

    st.write("### 📊 Status Breakdown")
    status_counts = filtered_df["Application Status"].value_counts()
    if not status_counts.empty:
        st.bar_chart(status_counts)
