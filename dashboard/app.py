
import re
from pathlib import Path

import pandas as pd
import streamlit as st


# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Job Market Intelligence",
    page_icon="📊",
    layout="wide",
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.csv"


# =====================================================
# DATA LOADING AND CLEANING
# =====================================================

def normalize_city(value):
    """Convert common city spelling variations to one name."""
    if pd.isna(value):
        return "Unknown"

    city = str(value)
    city = city.replace("\u200b", "").replace("\ufeff", "")
    city = re.sub(r"\s+", " ", city).strip()

    # Remove parenthetical details, e.g. Ahmedabad (Gujarat)
    city = city.split("(")[0].strip()

    # Normalize punctuation and spelling for comparison
    key = re.sub(r"[^a-z]", "", city.casefold())

    aliases = {
        "ahmedabad": "Ahmedabad",
        "amdavad": "Ahmedabad",
        "ahemdabad": "Ahmedabad",
        "ahmedbad": "Ahmedabad",
        "ahmdabad": "Ahmedabad",
        "ahmedabadgujarat": "Ahmedabad",
        "ahmedabadgujrat": "Ahmedabad",
        "bengaluru": "Bangalore",
        "bangalore": "Bangalore",
        "bombay": "Mumbai",
        "mumbai": "Mumbai",
        "madras": "Chennai",
        "chennai": "Chennai",
        "newdelhi": "Delhi",
        "delhincr": "Delhi",
        "gurugram": "Gurgaon",
        "gurgaon": "Gurgaon",
        "unknown": "Unknown",
        "nan": "Unknown",
        "none": "Unknown",
    }

    return aliases.get(key, city.title()) if city else "Unknown"


@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    data = pd.read_csv(DATA_PATH, low_memory=False)

    required_defaults = {
        "job_title": "",
        "company_name": "",
        "primary_city": "",
        "skills_required": "",
        "experience_raw": "",
        "salary_raw": "",
        "work_mode": "",
        "salary_midpoint_lpa": float("nan"),
        "experience_min_yrs": float("nan"),
        "experience_max_yrs": float("nan"),
    }

    for column, default in required_defaults.items():
        if column not in data.columns:
            data[column] = default

    text_columns = [
        "job_title",
        "company_name",
        "primary_city",
        "skills_required",
        "experience_raw",
        "salary_raw",
        "work_mode",
    ]

    for column in text_columns:
        data[column] = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    data["primary_city"] = data["primary_city"].apply(
        normalize_city
    )

    data["salary_midpoint_lpa"] = pd.to_numeric(
        data["salary_midpoint_lpa"],
        errors="coerce",
    )

    # A zero or negative midpoint is treated as undisclosed.
    data.loc[
        data["salary_midpoint_lpa"] <= 0,
        "salary_midpoint_lpa",
    ] = float("nan")

    for column in [
        "experience_min_yrs",
        "experience_max_yrs",
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    return data


try:
    df = load_data()
except Exception as error:
    st.error(f"Unable to load the dataset: {error}")
    st.stop()


# =====================================================
# HEADER
# =====================================================

st.title("📊 Job Market Intelligence Dashboard")

st.write(
    "Explore technology hiring trends, salary information, "
    "in-demand skills, job locations, and experience requirements."
)

st.caption(f"Dataset records: {len(df):,}")


# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("🔎 Filters")

locations = sorted(
    city
    for city in df["primary_city"].unique()
    if city and city != "Unknown"
)

selected_locations = st.sidebar.multiselect(
    "📍 Location",
    options=locations,
    default=locations,
)

salary_values = df["salary_midpoint_lpa"].dropna()

if not salary_values.empty:
    salary_min = float(salary_values.min())
    salary_max = float(salary_values.max())
else:
    salary_min, salary_max = 0.0, 1.0

if salary_min < salary_max:
    salary_range = st.sidebar.slider(
        "💰 Salary range (LPA)",
        min_value=salary_min,
        max_value=salary_max,
        value=(salary_min, salary_max),
    )
else:
    salary_range = (salary_min, salary_max)
    st.sidebar.caption("No salary range available.")

experience_values = df["experience_max_yrs"].dropna()

if experience_values.empty:
    experience_max = 1
else:
    experience_max = max(
        1,
        min(40, int(experience_values.max())),
    )

experience_range = st.sidebar.slider(
    "💼 Experience (years)",
    min_value=0,
    max_value=experience_max,
    value=(0, experience_max),
)


# =====================================================
# FILTER DATA
# =====================================================

city_mask = df["primary_city"].isin(selected_locations)

# Keep jobs whose salary is not disclosed.
salary_mask = (
    df["salary_midpoint_lpa"].isna()
    | df["salary_midpoint_lpa"].between(
        salary_range[0],
        salary_range[1],
    )
)

experience_mask = (
    df["experience_min_yrs"].fillna(0)
    <= experience_range[1]
) & (
    df["experience_max_yrs"].fillna(experience_max)
    >= experience_range[0]
)

filtered_df = df[
    city_mask & salary_mask & experience_mask
].copy()


# =====================================================
# KEY METRICS
# =====================================================

st.subheader("📌 Job Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Jobs", f"{len(filtered_df):,}")

average_salary = filtered_df["salary_midpoint_lpa"].mean()

col2.metric(
    "Average Disclosed Salary",
    f"{average_salary:.2f} LPA"
    if pd.notna(average_salary)
    else "N/A",
)

col3.metric(
    "Job Titles",
    filtered_df["job_title"].replace("", pd.NA).nunique(),
)

col4.metric(
    "Companies Listed",
    filtered_df["company_name"].replace("", pd.NA).nunique(),
)


# =====================================================
# SALARY BY JOB TITLE
# =====================================================

st.subheader("💰 Average Salary by Job Title")

salary_by_role = (
    filtered_df.dropna(subset=["salary_midpoint_lpa"])
    .groupby("job_title")["salary_midpoint_lpa"]
    .mean()
    .sort_values(ascending=False)
    .head(15)
)

if not salary_by_role.empty:
    st.bar_chart(salary_by_role)
else:
    st.info("No disclosed salaries match the selected filters.")


# =====================================================
# MOST REQUESTED SKILLS
# =====================================================

st.subheader("🔥 Most Requested Skills")

skills = (
    filtered_df["skills_required"]
    .str.split(",")
    .explode()
    .str.strip()
    .str.lower()
)

skills = skills[
    (skills != "")
    & (skills != "not available")
].value_counts().head(15)

if not skills.empty:
    st.bar_chart(skills)
else:
    st.info("No skill information is available.")


# =====================================================
# JOBS BY LOCATION
# =====================================================

st.subheader("📍 Jobs by Location")

location_counts = (
    filtered_df["primary_city"]
    .value_counts()
    .head(15)
)

if not location_counts.empty:
    st.bar_chart(location_counts)
else:
    st.info("No jobs match the selected locations.")


# =====================================================
# SEARCHABLE JOB LISTINGS
# =====================================================

st.subheader("📋 Job Listings")

search_query = st.text_input(
    "🔎 Search by title, company, city, or skill",
    placeholder="e.g. Data Analyst, Python, SQL",
)

search_df = filtered_df.copy()

if search_query.strip():
    query = search_query.strip()

    search_mask = pd.Series(
        False,
        index=search_df.index,
    )

    for column in [
        "job_title",
        "company_name",
        "primary_city",
        "skills_required",
    ]:
        search_mask |= search_df[column].str.contains(
            query,
            case=False,
            regex=False,
            na=False,
        )

    search_df = search_df[search_mask]

display_columns = [
    "job_title",
    "company_name",
    "primary_city",
    "experience_raw",
    "salary_raw",
    "work_mode",
    "skills_required",
]

st.dataframe(
    search_df[display_columns],
    use_container_width=True,
    height=400,
    hide_index=True,
)

st.caption(f"Found {len(search_df):,} matching jobs.")


# =====================================================
# SKILL GAP ANALYZER
# =====================================================

st.subheader("🧠 Skill Gap Analyzer")

roles = sorted(
    role for role in df["job_title"].unique() if role
)

if roles:
    selected_role = st.selectbox(
        "Choose your target job role",
        roles,
    )

    user_skills_input = st.text_input(
        "Enter your current skills, separated by commas",
        placeholder="Python, SQL, Excel, Power BI",
    )

    if user_skills_input.strip():
        user_skills = {
            skill.strip().lower()
            for skill in user_skills_input.split(",")
            if skill.strip()
        }

        role_jobs = df[df["job_title"] == selected_role]

        required_skills = set()

        for job_skills in role_jobs["skills_required"]:
            for skill in job_skills.split(","):
                skill = skill.strip().lower()

                if skill and skill != "not available":
                    required_skills.add(skill)

        matching = required_skills & user_skills
        missing = required_skills - user_skills

        percentage = (
            len(matching) / len(required_skills) * 100
            if required_skills
            else 0
        )

        st.write("### 🎯 Skill Match")
        st.progress(int(percentage))
        st.write(f"**{percentage:.0f}% match**")

        left, right = st.columns(2)

        with left:
            st.write("✅ Skills you have")
            st.write(
                ", ".join(sorted(matching))
                if matching
                else "No matching skills found yet."
            )

        with right:
            st.write("📚 Skills to learn")
            st.write(
                ", ".join(sorted(missing))
                if missing
                else "No missing skills found!"
            )
else:
    st.info("No job titles are available.")


# =====================================================
# FOOTER
# =====================================================

st.divider()
st.caption(
    "Job Market Intelligence | Python • Pandas • Streamlit"
)
