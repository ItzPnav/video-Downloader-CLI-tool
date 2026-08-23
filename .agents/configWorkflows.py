from pathlib import Path


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SKILLS_DIR = Path(
    r"C:\pnav\projects\PROMPT THAT WEBSITE\checklist Website\.agents\skills"
)

WORKFLOWS_DIR = SKILLS_DIR.parent / "workflows"


# ---------------------------------------------------------
# Get all skill directories
# ---------------------------------------------------------

skill_names = [
    directory.name
    for directory in SKILLS_DIR.iterdir()
    if directory.is_dir()
]


# ---------------------------------------------------------
# Create workflows directory
# ---------------------------------------------------------

WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Create workflow files
# ---------------------------------------------------------

for skill_name in skill_names:

    workflow_file = WORKFLOWS_DIR / f"{skill_name}.md"

    content = f"""---
description: Explicitly invoke the {skill_name}.md skill.
---

Read and follow all instructions in `.agents/skills/{skill_name}/SKILL.md`.

Treat those instructions as the active skill for this request.

Execute the user's request using that skill.
"""

    workflow_file.write_text(content, encoding="utf-8")


# ---------------------------------------------------------
# Output
# ---------------------------------------------------------

print(f"Found {len(skill_names)} skills:")
for skill in skill_names:
    print(f"  - {skill}")

print()
print(f"Created workflows in:")
print(WORKFLOWS_DIR)

print()
print("Created workflow files:")
for skill in skill_names:
    print(f"  - {skill}.md")
