import pytest
from pathlib import Path


class TestBundledSkills:
    def test_cron_skill_exists(self):
        skill_path = Path("companio/skills/cron/SKILL.md")
        assert skill_path.exists()

    def test_memory_skill_exists(self):
        skill_path = Path("companio/skills/memory/SKILL.md")
        assert skill_path.exists()

    def test_skill_creator_exists(self):
        skill_path = Path("companio/skills/skill-creator/SKILL.md")
        assert skill_path.exists()

    def test_no_nanobot_in_skills(self):
        skills_dir = Path("companio/skills")
        for md_file in skills_dir.rglob("*.md"):
            content = md_file.read_text()
            # Allow "nanobot" only if it's referring to the original project
            # But check for incorrect references like "~/.nanobot" or "from nanobot"
            assert "~/.nanobot" not in content, f"Found ~/.nanobot in {md_file}"
            assert "from nanobot" not in content, f"Found 'from nanobot' in {md_file}"
