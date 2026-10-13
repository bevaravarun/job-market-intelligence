import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Job Market Intelligence",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# LOAD DATASET
# =========================================================

df = pd.read_csv("data/jobs.csv")

# =========================================================
# CLEAN NUMERIC COLUMNS
# =========================================================

df["salary_midpoint_lpa"] = pd.to_numeric(
    df["salary_midpoint_lpa"],
    errors="coerce"
)

# 0 means salary was not disclosed
df.loc[df["salary_midpoint_lpa"] <= 0, "salary_midpoint_lpa"] = pd.NA

df["experience_min_yrs"] = pd.to_numeric(
    df["experience_min_yrs"],
    errors="coerce"
)

df["experience_max_yrs"] = pd.to_numeric(
    df["experience_max_yrs"],
    errors="coerce"
)

# =========================================================
# TITLE
# =========================================================

st.title("📊 Job Market Intelligence Dashboard")

st.write(
    "Explore job demand, salaries, skills, locations and "
    "experience requirements across 23,000+ technology jobs."
)

# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.header("🔎 Filters")

locations = sorted(
    df["primary_city"].dropna().unique()
)

selected_locations = st.sidebar.multiselect(
    "📍 Location",
    locations,
    default=locations
)

salary_min = float(
    df["salary_midpoint_lpa"].min()
)

salary_max = float(
    df["salary_midpoint_lpa"].max()
)

salary_range = st.sidebar.slider(
    "💰 Salary Range (LPA)",
    min_value=salary_min,
    max_value=salary_max,
    value=(salary_min, salary_max)
)

experience_max = int(
    df["experience_max_yrs"].dropna().max()
)

experience_range = st.sidebar.slider(
    "💼 Experience (years)",
    min_value=0,
    max_value=experience_max,
    value=(0, experience_max)
)

# =========================================================
# FILTER DATA
# =========================================================

filtered_df = df[
    (df["primary_city"].isin(selected_locations))
    & (
        df["salary_midpoint_lpa"].between(
            salary_range[0],
            salary_range[1]
        )
    )
    & (
        df["experience_min_yrs"].fillna(0)
        <= experience_range[1]
    )
]

# =========================================================
# KPI CARDS
# =========================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Jobs",
    f"{len(filtered_df):,}"
)

average_salary = filtered_df[
    "salary_midpoint_lpa"
].mean()

col2.metric(
    "Average Salary",
    f"{average_salary:.2f} LPA"
    if pd.notna(average_salary)
    else "N/A"
)

col3.metric(
    "Job Roles",
    filtered_df["job_title"].nunique()
)

col4.metric(
    "Companies",
    filtered_df["company_name"].nunique()
)

# =========================================================
# SALARY BY JOB ROLE
# =========================================================

st.subheader("💰 Average Salary by Job Role")

salary_by_role = (
    filtered_df
    .dropna(subset=["salary_midpoint_lpa"])
    .groupby("job_title")["salary_midpoint_lpa"]
    .mean()
    .sort_values(ascending=False)
    .head(15)
)

st.bar_chart(salary_by_role)

# =========================================================
# MOST DEMANDED SKILLS
# =========================================================

st.subheader("🔥 Most Demanded Skills")

skills = (
    filtered_df["skills_required"]
    .fillna("")
    .str.split(",")
    .explode()
    .str.strip()
)

skills = (
    skills[skills != ""]
    .value_counts()
    .head(15)
)

st.bar_chart(skills)

# =========================================================
# TOP LOCATIONS
# =========================================================

st.subheader("📍 Jobs by Location")

location_counts = (
    filtered_df["primary_city"]
    .value_counts()
    .head(15)
)

st.bar_chart(location_counts)

# =========================================================
# JOB LISTINGS
# =========================================================

st.subheader("📋 Job Listings")

display_columns = [
    "job_title",
    "company_name",
    "primary_city",
    "experience_raw",
    "salary_raw",
    "work_mode",
    "skills_required"
]

st.dataframe(
    filtered_df[display_columns],
    width="stretch",
    height=400
)

# =========================================================
# SKILL GAP ANALYZER
# =========================================================

st.subheader("🧠 Skill Gap Analyzer")

roles = sorted(
    df["job_title"].dropna().unique()
)

selected_role = st.selectbox(
    "Select your target job role",
    roles
)

user_skills_input = st.text_input(
    "Enter your current skills (comma separated)",
    placeholder="Python, SQL, Excel"
)

if user_skills_input:

    user_skills = {
        skill.strip().lower()
        for skill in user_skills_input.split(",")
        if skill.strip()
    }

    role_jobs = df[
        df["job_title"] == selected_role
    ]

    required_skills = set()

    for job_skills in role_jobs["skills_required"].dropna():

        for skill in job_skills.split(","):

            skill = skill.strip().lower()

            if skill:
                required_skills.add(skill)

    matching_skills = (
        required_skills.intersection(user_skills)
    )

    missing_skills = (
        required_skills - user_skills
    )

    if required_skills:
        match_percentage = (
            len(matching_skills)
            / len(required_skills)
        ) * 100
    else:
        match_percentage = 0

    st.subheader("🎯 Skill Match")

    st.progress(
        int(match_percentage)
    )

    st.write(
        f"**{match_percentage:.0f}% match**"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write("✅ Skills you have")

        if matching_skills:
            st.write(
                ", ".join(
                    sorted(matching_skills)
                )
            )
        else:
            st.write("None")

    with col2:

        st.write("📚 Skills to learn")

        if missing_skills:
            st.write(
                ", ".join(
                    sorted(missing_skills)
                )
            )
        else:
            st.write("None")