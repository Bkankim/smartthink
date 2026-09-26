"""install.sh / uninstall.sh against leftovers of earlier installs, exercised through the CLI.

Every case runs against a throwaway HOME so the real ~/.claude is never read or written.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL = REPO_ROOT / "install.sh"
LEGACY = REPO_ROOT / "scripts" / "legacy-install.py"
UNINSTALL = REPO_ROOT / "uninstall.sh"

V2_SKILL_MD = "---\nname: smartthink\n---\n# SmartThink v2\nst-thinker를 스폰한다.\n"
V2_THINKER = "---\nname: st-thinker\neffort: max\n---\n# SmartThink 분석 엔진 (STSA)\n"
V2_SEARCHER = "---\nname: st-searcher\n---\n# SmartThink 검색 정찰\n"
V2_ALIAS = 'Alias for /smartthink. Invoke Skill tool: `Skill("smartthink", "$ARGUMENTS")`'

# The runner's own vault, config and XDG locations must never leak into a case.
CONTROLLED = ("SMARTTHINK_VAULT", "CLAUDE_CONFIG_DIR", "XDG_DATA_HOME", "XDG_CONFIG_HOME")


class InstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name).resolve() / "home"
        self.claude = self.home / ".claude"
        (self.claude / "skills").mkdir(parents=True)
        (self.claude / "agents").mkdir()
        (self.claude / "commands").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_script(self, script: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env["HOME"] = str(self.home)
        env.update(extra)
        return subprocess.run(
            ["bash", str(script), *args], env=env, capture_output=True, text=True, check=False
        )

    def plant_copy_install(self) -> None:
        # A v2 install made by copying files instead of the v2 installer's symlinks.
        skill = self.claude / "skills" / "smartthink"
        skill.mkdir()
        (skill / "SKILL.md").write_text(V2_SKILL_MD, encoding="utf-8")
        (self.claude / "agents" / "st-thinker.md").write_text(V2_THINKER, encoding="utf-8")
        (self.claude / "agents" / "st-searcher.md").write_text(V2_SEARCHER, encoding="utf-8")
        (self.claude / "commands" / "st.md").write_text(V2_ALIAS, encoding="utf-8")

    def plant_old_checkout_links(self) -> Path:
        # A v2 symlink install made from another clone that is still on v2.
        old = self.home / "old-clone"
        (old / "skills" / "smartthink").mkdir(parents=True)
        (old / "skills" / "smartthink" / "SKILL.md").write_text(V2_SKILL_MD, encoding="utf-8")
        (old / "agents").mkdir()
        (old / "agents" / "st-thinker.md").write_text(V2_THINKER, encoding="utf-8")
        (old / "commands").mkdir()
        (old / "commands" / "st.md").write_text(V2_ALIAS, encoding="utf-8")
        (self.claude / "skills" / "smartthink").symlink_to(old / "skills" / "smartthink")
        (self.claude / "agents" / "st-thinker.md").symlink_to(old / "agents" / "st-thinker.md")
        (self.claude / "commands" / "st.md").symlink_to(old / "commands" / "st.md")
        return old

    def detect(self) -> str:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            ["python3", str(LEGACY), "detect"], env=env, capture_output=True, text=True, check=True
        )
        return completed.stdout

    def backups(self) -> list[Path]:
        root = self.claude / ".backup"
        return sorted(root.glob("smartthink-legacy-*")) if root.exists() else []

    def assert_linked_to_repo(self) -> None:
        self.assertEqual((self.claude / "skills" / "smartthink").resolve(), REPO_ROOT / "skills" / "smartthink")
        for name in ("st-thinker.md", "st-armorer.md"):
            self.assertEqual((self.claude / "agents" / name).resolve(), REPO_ROOT / "agents" / name)
        self.assertEqual((self.claude / "commands" / "st.md").resolve(), REPO_ROOT / "commands" / "st.md")


class InstallTest(InstallerTestCase):
    def test_copy_install_leftovers_stop_install_without_changes(self) -> None:
        self.plant_copy_install()

        completed = self.run_script(INSTALL)

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("--migrate-legacy", completed.stdout)
        self.assertFalse((self.claude / "skills" / "smartthink").is_symlink())
        self.assertFalse((self.claude / "agents" / "st-armorer.md").exists())
        self.assertEqual((self.claude / "agents" / "st-searcher.md").read_text(encoding="utf-8"), V2_SEARCHER)
        self.assertEqual(self.backups(), [])

    def test_migrate_legacy_moves_leftovers_to_a_backup_then_installs(self) -> None:
        self.plant_copy_install()

        completed = self.run_script(INSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assert_linked_to_repo()
        self.assertFalse((self.claude / "agents" / "st-searcher.md").exists())
        [backup] = self.backups()
        self.assertEqual((backup / "skills" / "smartthink" / "SKILL.md").read_text(encoding="utf-8"), V2_SKILL_MD)
        self.assertEqual((backup / "agents" / "st-thinker.md").read_text(encoding="utf-8"), V2_THINKER)
        self.assertEqual((backup / "agents" / "st-searcher.md").read_text(encoding="utf-8"), V2_SEARCHER)
        self.assertEqual((backup / "commands" / "st.md").read_text(encoding="utf-8"), V2_ALIAS)

    def test_unrelated_agent_file_blocks_before_anything_is_linked(self) -> None:
        # Not a SmartThink leftover, so it is never moved, and it must not cause a partial install.
        own = "---\nname: st-thinker\n---\nsomeone else's agent\n"
        (self.claude / "agents" / "st-thinker.md").write_text(own, encoding="utf-8")

        completed = self.run_script(INSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertFalse((self.claude / "skills" / "smartthink").exists())
        self.assertFalse((self.claude / "commands" / "st.md").exists())
        self.assertEqual((self.claude / "agents" / "st-thinker.md").read_text(encoding="utf-8"), own)

    def test_unmarked_skill_directory_is_not_a_leftover(self) -> None:
        # Someone else's skill that happens to share the name is never moved.
        skill = self.claude / "skills" / "smartthink"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: other\n---\nnot ours\n", encoding="utf-8")

        completed = self.run_script(INSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertTrue((skill / "SKILL.md").is_file())
        self.assertEqual(self.backups(), [])

    def test_searcher_link_into_another_clone_is_moved(self) -> None:
        # A v2 symlink install from a different, still-present clone keeps the removed agent listed.
        other = self.home / "old-clone" / "agents"
        other.mkdir(parents=True)
        (other / "st-searcher.md").write_text(V2_SEARCHER, encoding="utf-8")
        link = self.claude / "agents" / "st-searcher.md"
        link.symlink_to(other / "st-searcher.md")

        completed = self.run_script(INSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse(os.path.lexists(link))
        [backup] = self.backups()
        self.assertTrue((backup / "agents" / "st-searcher.md").is_symlink())
        self.assertTrue((other / "st-searcher.md").is_file())

    def test_v2_symlink_install_upgrades_in_place(self) -> None:
        # The v2 installer symlinked into the clone; after a pull the searcher link dangles.
        (self.claude / "skills" / "smartthink").symlink_to(REPO_ROOT / "skills" / "smartthink")
        (self.claude / "agents" / "st-thinker.md").symlink_to(REPO_ROOT / "agents" / "st-thinker.md")
        (self.claude / "agents" / "st-searcher.md").symlink_to(REPO_ROOT / "agents" / "st-searcher.md")

        completed = self.run_script(INSTALL)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assert_linked_to_repo()
        self.assertFalse(os.path.lexists(self.claude / "agents" / "st-searcher.md"))
        self.assertEqual(self.backups(), [])


    def test_old_checkout_links_are_reported_for_status(self) -> None:
        self.plant_old_checkout_links()

        report = self.detect()

        self.assertIn("skills/smartthink", report)
        self.assertIn("agents/st-thinker.md", report)
        self.assertIn("commands/st.md", report)

    def test_old_checkout_links_are_replaced_without_the_flag(self) -> None:
        old = self.plant_old_checkout_links()

        completed = self.run_script(INSTALL)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assert_linked_to_repo()
        self.assertTrue((old / "skills" / "smartthink" / "SKILL.md").is_file())
        self.assertEqual(self.backups(), [])

    def test_blocked_target_moves_nothing_even_with_the_flag(self) -> None:
        self.plant_copy_install()
        own = "---\nname: st-armorer\n---\nsomeone else's agent\n"
        (self.claude / "agents" / "st-armorer.md").write_text(own, encoding="utf-8")

        completed = self.run_script(INSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertEqual(self.backups(), [])
        self.assertEqual((self.claude / "agents" / "st-searcher.md").read_text(encoding="utf-8"), V2_SEARCHER)

    def test_unwritable_vault_stops_before_any_link(self) -> None:
        blocker = self.home / "not-a-dir"
        blocker.write_text("file, not a directory\n", encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env["HOME"] = str(self.home)
        env["SMARTTHINK_VAULT"] = str(blocker / "vault")

        completed = subprocess.run(["bash", str(INSTALL)], env=env, capture_output=True, text=True, check=False)

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertFalse(os.path.lexists(self.claude / "skills" / "smartthink"))

    def test_install_does_not_create_the_default_vault(self) -> None:
        # /st init picks the vault (step 5); seeding the default first would leave an unused folder.
        completed = self.run_script(INSTALL)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(os.path.lexists(self.claude / "skills" / "smartthink"))
        self.assertFalse((self.home / ".local" / "share" / "smartthink").exists())

    def test_read_only_vault_parent_stops_before_any_link(self) -> None:
        # The writability guard stays: the nearest existing ancestor of the vault must be writable.
        locked = self.home / "locked"
        locked.mkdir()
        locked.chmod(0o555)
        try:
            completed = self.run_script(INSTALL, SMARTTHINK_VAULT=str(locked / "a" / "vault"))
        finally:
            locked.chmod(0o755)

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertFalse(os.path.lexists(self.claude / "skills" / "smartthink"))
        self.assertFalse((locked / "a").exists())

    def test_current_alias_copy_is_not_a_leftover(self) -> None:
        (self.claude / "commands" / "st.md").write_bytes((REPO_ROOT / "commands" / "st.md").read_bytes())

        self.assertEqual(self.detect(), "")


class UninstallTest(InstallerTestCase):
    def test_leftovers_stop_uninstall_without_changes(self) -> None:
        self.plant_copy_install()

        completed = self.run_script(UNINSTALL)

        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("--migrate-legacy", completed.stdout)
        self.assertTrue((self.claude / "agents" / "st-searcher.md").exists())
        self.assertEqual(self.backups(), [])

    def test_migrate_legacy_moves_leftovers_on_uninstall(self) -> None:
        self.plant_copy_install()

        completed = self.run_script(UNINSTALL, "--migrate-legacy")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse((self.claude / "skills" / "smartthink").exists())
        self.assertFalse((self.claude / "agents" / "st-searcher.md").exists())
        [backup] = self.backups()
        self.assertTrue((backup / "commands" / "st.md").is_file())


    def test_old_checkout_links_are_removed_without_the_flag(self) -> None:
        self.plant_old_checkout_links()

        completed = self.run_script(UNINSTALL)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertFalse(os.path.lexists(self.claude / "skills" / "smartthink"))
        self.assertFalse(os.path.lexists(self.claude / "commands" / "st.md"))

    def test_stale_pointer_is_mentioned(self) -> None:
        pointer = self.home / ".config" / "smartthink" / "vault-pointer"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(str(self.home / "notes") + "\n", encoding="utf-8")

        completed = self.run_script(UNINSTALL)

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(str(pointer), completed.stdout)

    def test_pointer_hint_follows_xdg_config_home_like_the_resolver(self) -> None:
        # The resolver strips whitespace around XDG_CONFIG_HOME; the pointer hint must look in the same place.
        config = self.home / "cfg"
        pointer = config / "smartthink" / "vault-pointer"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(str(self.home / "notes") + "\n", encoding="utf-8")

        completed = self.run_script(UNINSTALL, XDG_CONFIG_HOME=f" {config} ")

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(str(pointer), completed.stdout)

    def test_uninstall_removes_links_without_python(self) -> None:
        (self.claude / "skills" / "smartthink").symlink_to(REPO_ROOT / "skills" / "smartthink")
        tools = self.home / "bin"
        tools.mkdir()
        for name in ("rm", "readlink", "dirname", "sed", "cut", "grep", "cat"):
            found = shutil.which(name)
            if found:
                (tools / name).symlink_to(found)
        env = {"HOME": str(self.home), "PATH": str(tools)}

        completed = subprocess.run(
            [shutil.which("bash"), str(UNINSTALL)], env=env, capture_output=True, text=True, check=False
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("python3 not found", completed.stdout)
        self.assertFalse(os.path.lexists(self.claude / "skills" / "smartthink"))


if __name__ == "__main__":
    unittest.main()
