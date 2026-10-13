import pandas as pd
import matplotlib.pyplot as plt

# Load dataset
df = pd.read_csv("data/jobs.csv")

# Most demanded skills
skills = (
    df["skills"]
    .str.split(",")
    .explode()
    .str.strip()
    .value_counts()
)

print("\nMost demanded skills:")
print(skills)

# Average salary by job role
salary_by_role = (
    df.groupby("job_title")["salary_lpa"]
    .mean()
    .sort_values(ascending=False)
)

print("\nAverage salary by job role:")
print(salary_by_role)

# Average salary associated with each skill
skill_salary = {}

for _, row in df.iterrows():
    job_skills = [skill.strip() for skill in row["skills"].split(",")]

    for skill in job_skills:
        if skill not in skill_salary:
            skill_salary[skill] = []

        skill_salary[skill].append(row["salary_lpa"])

skill_salary_avg = (
    pd.Series(skill_salary)
    .apply(lambda salaries: sum(salaries) / len(salaries))
    .sort_values(ascending=False)
)

print("\nAverage salary associated with each skill:")
print(skill_salary_avg)

# Most demanded skills chart
top_skills = skills.head(10).sort_values()

plt.figure(figsize=(10, 6))
top_skills.plot(kind="barh")

plt.title("Top 10 Most Demanded Skills")
plt.xlabel("Number of Job Postings")
plt.ylabel("Skill")
plt.tight_layout()

plt.savefig("dashboard/top_skills.png")
plt.show()