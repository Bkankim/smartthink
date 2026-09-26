"""Behaviour of scripts/resolve-vault.py, exercised through its CLI.

Every case runs against a throwaway HOME, with the XDG variables cleared unless a case sets them,
so the real vault, pointer and config are never read or written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOLVER = REPO_ROOT / "scripts" / "resolve-vault.py"
TEMPLATES = REPO_ROOT / "skills" / "smartthink" / ".data"
# Variables the runner's own environment must never leak into a case.
CONTROLLED = ("SMARTTHINK_VAULT", "CLAUDE_CONFIG_DIR", "XDG_DATA_HOME", "XDG_CONFIG_HOME")


class ResolveVaultTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.default_vault = self.home / ".local" / "share" / "smartthink"
        self.old_vault = self.home / ".claude" / "smartthink-vault"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def make_env(self, vault_env: str | None = None, **extra: str) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env["HOME"] = str(self.home)
        if vault_env is not None:
            env["SMARTTHINK_VAULT"] = vault_env
        env.update(extra)
        return env

    def run_resolver_raw(self, *args: str, vault_env: str | None = None, **extra: str) -> subprocess.CompletedProcess[str]:
        env = self.make_env(vault_env, **extra)
        return subprocess.run(
            [sys.executable, str(RESOLVER), *args],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def run_resolver(self, *args: str, vault_env: str | None = None, **extra: str) -> dict:
        completed = self.run_resolver_raw(*args, vault_env=vault_env, **extra)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def write_pointer(self, target: str, config_home: Path | None = None) -> None:
        pointer = (config_home or self.home / ".config") / "smartthink" / "vault-pointer"
        pointer.parent.mkdir(parents=True)
        pointer.write_text(target + "\n", encoding="utf-8")

    def test_empty_env_vault_is_used_not_skipped(self) -> None:
        empty = self.root / "empty-vault"
        empty.mkdir()
        # A seeded default vault is the tempting fallback the old prose rule allowed.
        self.default_vault.mkdir(parents=True)
        (self.default_vault / "evolution-state.md").write_text("real insights\n", encoding="utf-8")

        result = self.run_resolver(vault_env=str(empty))

        self.assertEqual(result, {"path": str(empty), "source": "env"})

    def test_missing_env_vault_is_created_by_ensure(self) -> None:
        missing = self.root / "not-yet" / "vault"

        result = self.run_resolver("--ensure", vault_env=str(missing))

        self.assertEqual(result, {"path": str(missing), "source": "env"})
        self.assertTrue((missing / "packs").is_dir())
        self.assertFalse(self.default_vault.exists())

    def test_pointer_is_used_when_env_is_unset(self) -> None:
        notes = self.root / "notes" / "smartthink"
        self.write_pointer(str(notes))

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(notes), "source": "pointer"})

    def test_old_pointer_under_home_claude_is_ignored(self) -> None:
        # No compatibility with the pre-#20 layout: neither the old default nor its pointer is read.
        self.old_vault.mkdir(parents=True)
        (self.old_vault / "vault-pointer").write_text(str(self.root / "notes") + "\n", encoding="utf-8")

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_env_wins_over_pointer(self) -> None:
        self.write_pointer(str(self.root / "notes" / "smartthink"))
        explicit = self.root / "explicit"

        result = self.run_resolver(vault_env=str(explicit))

        self.assertEqual(result, {"path": str(explicit), "source": "env"})

    def test_blank_env_counts_as_unset(self) -> None:
        result = self.run_resolver(vault_env="   ")

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_relative_env_vault_is_used_with_a_warning(self) -> None:
        completed = self.run_resolver_raw(vault_env="rel-vault")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"path": str(self.root / "rel-vault"), "source": "env"})
        self.assertIn("relative", completed.stderr)

    def test_blank_env_warns_that_it_is_ignored(self) -> None:
        completed = self.run_resolver_raw(vault_env="   ")

        self.assertIn("blank", completed.stderr)

    def test_default_when_nothing_is_set(self) -> None:
        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_default_follows_xdg_data_home(self) -> None:
        data_home = self.root / "xdg-data"

        result = self.run_resolver(XDG_DATA_HOME=str(data_home))

        self.assertEqual(result, {"path": str(data_home / "smartthink"), "source": "default"})

    def test_pointer_follows_xdg_config_home(self) -> None:
        config_home = self.root / "xdg-config"
        notes = self.root / "notes" / "smartthink"
        self.write_pointer(str(notes), config_home=config_home)

        result = self.run_resolver(XDG_CONFIG_HOME=str(config_home))

        self.assertEqual(result, {"path": str(notes), "source": "pointer"})

    def test_relative_xdg_values_are_ignored(self) -> None:
        # The XDG spec says relative values are invalid and must be ignored.
        result = self.run_resolver(XDG_DATA_HOME="rel-data", XDG_CONFIG_HOME="rel-config")

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_relative_pointer_is_ignored(self) -> None:
        self.write_pointer("notes/smartthink")

        result = self.run_resolver()

        self.assertEqual(result, {"path": str(self.default_vault), "source": "default"})

    def test_ensure_never_overwrites_existing_state(self) -> None:
        vault = self.root / "vault"
        vault.mkdir()
        (vault / "evolution-state.md").write_text("kept\n", encoding="utf-8")

        self.run_resolver("--ensure", vault_env=str(vault))

        self.assertEqual((vault / "evolution-state.md").read_text(encoding="utf-8"), "kept\n")
        self.assertTrue((vault / "packs").is_dir())

    def test_ensure_seeds_evolution_state_but_not_profile(self) -> None:
        # A missing profile.md is the signal that makes the skill suggest `/st init`.
        vault = self.root / "vault"

        self.run_resolver("--ensure", vault_env=str(vault))

        self.assertEqual(
            (vault / "evolution-state.md").read_bytes(),
            (TEMPLATES / "evolution-state.md").read_bytes(),
        )
        self.assertFalse((vault / "profile.md").exists())

    def run_rule(self, vault_env: str | None = None, config_dir: str | None = None) -> dict:
        # CLAUDE_CONFIG_DIR is controlled explicitly so the runner's own value never leaks in.
        env = self.make_env(vault_env)
        if config_dir is not None:
            env["CLAUDE_CONFIG_DIR"] = config_dir
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), "--permission-rule"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def run_rule_env(self, **extra: str) -> dict:
        completed = self.run_resolver_raw("--permission-rule", **extra)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_rule_for_default_vault_is_home_relative(self) -> None:
        result = self.run_rule()

        self.assertEqual(result["source"], "default")
        self.assertEqual(result["permission_rule"], "Edit(~/.local/share/smartthink/**)")
        self.assertTrue(result["permission_rule_effective"])

    def test_rule_follows_the_xdg_default(self) -> None:
        data_home = self.root / "xdg-data"

        result = self.run_rule_env(XDG_DATA_HOME=str(data_home))

        self.assertEqual(result["permission_rule"], f"Edit(/{data_home}/smartthink/**)")
        self.assertTrue(result["permission_rule_effective"])

    def test_rule_for_vault_under_home_uses_tilde(self) -> None:
        result = self.run_rule(vault_env=str(self.home / "notes" / "smartthink"))

        self.assertEqual(result["permission_rule"], "Edit(~/notes/smartthink/**)")

    def test_rule_for_vault_outside_home_uses_double_slash(self) -> None:
        # A single leading / is relative to the settings file and never matches (issue #14).
        outside = self.root / "outside-vault"

        result = self.run_rule(vault_env=str(outside))

        self.assertEqual(result["permission_rule"], f"Edit(/{outside}/**)")
        self.assertTrue(result["permission_rule"].startswith("Edit(//"))

    def test_settings_path_defaults_to_home_claude(self) -> None:
        result = self.run_rule()

        self.assertEqual(result["settings_path"], str(self.home / ".claude" / "settings.json"))

    def test_settings_path_follows_claude_config_dir(self) -> None:
        config = self.root / "isolated-config"

        result = self.run_rule(config_dir=str(config))

        self.assertEqual(result["settings_path"], str(config / "settings.json"))

    def test_blank_claude_config_dir_counts_as_unset(self) -> None:
        result = self.run_rule(config_dir="  ")

        self.assertEqual(result["settings_path"], str(self.home / ".claude" / "settings.json"))

    def test_rule_under_home_claude_is_not_effective(self) -> None:
        # Writes under ~/.claude prompt as sensitive files no matter what the allow rules say.
        self.assertFalse(self.run_rule(vault_env=str(self.old_vault))["permission_rule_effective"])
        self.assertFalse(self.run_rule(vault_env=str(self.home / ".claude" / "other"))["permission_rule_effective"])

    def test_rule_outside_home_claude_is_effective(self) -> None:
        self.assertTrue(self.run_rule(vault_env=str(self.home / "notes" / "smartthink"))["permission_rule_effective"])
        self.assertTrue(self.run_rule(vault_env=str(self.root / "outside"))["permission_rule_effective"])

    def test_symlink_into_home_claude_is_not_effective(self) -> None:
        # The rule string keeps the user's spelling; only the effectiveness check resolves links.
        self.old_vault.mkdir(parents=True)
        link = self.home / "vault-link"
        link.symlink_to(self.old_vault)

        result = self.run_rule(vault_env=str(link))

        self.assertFalse(result["permission_rule_effective"])
        self.assertEqual(result["permission_rule"], "Edit(~/vault-link/**)")

    def test_config_dir_does_not_change_effectiveness(self) -> None:
        # The sensitive-path check follows HOME, so a vault inside CLAUDE_CONFIG_DIR is fine.
        config = self.root / "isolated-config"

        result = self.run_rule(vault_env=str(config / "vault"), config_dir=str(config))

        self.assertTrue(result["permission_rule_effective"])

    def test_rule_syntax_characters_make_the_rule_ineffective(self) -> None:
        # Issue #23: [ ] * ? { } ( ) are glob or rule syntax and are not escaped, so the rule may
        # not match the vault. Refuse to call it effective and say why.
        for name in ("Obsidian [main]", "notes*", "what?", "a{b}", "x (copy)"):
            with self.subTest(name=name):
                result = self.run_rule(vault_env=str(self.home / name / "smartthink"))

                self.assertFalse(result["permission_rule_effective"])
                self.assertEqual(result["permission_rule_reason"], "special-characters")

    def test_effective_rule_has_no_reason(self) -> None:
        result = self.run_rule(vault_env=str(self.home / "notes" / "smartthink"))

        self.assertTrue(result["permission_rule_effective"])
        self.assertIsNone(result["permission_rule_reason"])

    def test_relative_claude_config_dir_leaves_settings_path_empty(self) -> None:
        # Issue #23: a relative CLAUDE_CONFIG_DIR depends on the session's own cwd, which the
        # resolver cannot know, so it names no settings file and warns instead of guessing.
        completed = self.run_resolver_raw("--permission-rule", CLAUDE_CONFIG_DIR="rel-config")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIsNone(json.loads(completed.stdout)["settings_path"])
        self.assertIn("CLAUDE_CONFIG_DIR", completed.stderr)

    def test_rule_under_protected_folders_is_not_effective(self) -> None:
        # Headless probes (#20, Claude Code 2.1.283) denied Writes as "a sensitive file" under any
        # .claude, .git, .vscode or .idea folder despite a matching Edit(//abs/**) allow rule,
        # inside or outside a repo and whatever the cwd. A hidden folder like .notes was fine.
        for parts in (("repo", ".claude", "vault"), ("repo", ".git", "vault"), ("w", ".vscode", "v"), ("w", ".idea", "v")):
            with self.subTest(parts=parts):
                result = self.run_rule(vault_env=str(self.root.joinpath("outside", *parts)))

                self.assertFalse(result["permission_rule_effective"])
                self.assertEqual(result["permission_rule_reason"], "protected-folder")
        self.assertTrue(self.run_rule(vault_env=str(self.root / "outside" / ".notes" / "v"))["permission_rule_effective"])

    def test_rule_fields_are_opt_in(self) -> None:
        result = self.run_resolver()

        self.assertEqual(set(result), {"path", "source"})


class CandidatesTest(unittest.TestCase):
    """--candidates lists existing note stores for `st init` to offer; it never picks one."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def scan(self, *args: str) -> dict:
        env = {key: value for key, value in os.environ.items() if key not in CONTROLLED}
        env["HOME"] = str(self.home)
        completed = subprocess.run(
            [sys.executable, str(RESOLVER), "--candidates", *args],
            env=env,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_empty_home_offers_only_the_new_default(self) -> None:
        result = self.scan()

        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["create_new"], {"path": str(self.home / ".local" / "share" / "smartthink")})

    def by_path(self, result: dict) -> dict[str, dict]:
        return {candidate["path"]: candidate for candidate in result["candidates"]}

    def make_store(self, relative: str, marker: str | None = None, files: int = 1) -> Path:
        store = self.home / relative
        store.mkdir(parents=True)
        if marker == "dendron.yml":
            (store / marker).write_text("version: 5\n", encoding="utf-8")
        elif marker:
            (store / marker).mkdir()
        for index in range(files):
            (store / f"note-{index}.md").write_text("x\n", encoding="utf-8")
        return store

    def test_marker_files_make_candidates(self) -> None:
        stores = {
            "marker:.obsidian": self.make_store("Documents/Brain", ".obsidian"),
            "marker:.logseq": self.make_store("Sync/graph", ".logseq"),
            "marker:dendron.yml": self.make_store("dendron-ws", "dendron.yml"),
            "marker:.foam": self.make_store("a/b/foam-kb", ".foam"),
        }

        found = self.by_path(self.scan())

        self.assertEqual(set(found), {str(store) for store in stores.values()})
        for signal, store in stores.items():
            self.assertEqual(found[str(store)]["signals"], [signal])
            self.assertEqual(found[str(store)]["suggested_vault"], str(store / "smartthink"))

    def test_folder_names_are_a_signal(self) -> None:
        named = {
            "name:vault": self.make_store("Work/Vault"),
            "name:notes": self.make_store("my_notes"),
            "name:second-brain": self.make_store("Documents/Second Brain"),
        }
        self.make_store("projects/app")

        found = self.by_path(self.scan())

        self.assertEqual(set(found), {str(store) for store in named.values()})
        for signal, store in named.items():
            self.assertEqual(found[str(store)]["signals"], [signal])

    def write_registry(self, location: str, *paths: str) -> None:
        registry = self.home / location
        registry.parent.mkdir(parents=True, exist_ok=True)
        vaults = {f"id{index}": {"path": path, "ts": 1700000000000} for index, path in enumerate(paths)}
        registry.write_text(json.dumps({"vaults": vaults}), encoding="utf-8")

    def test_obsidian_registries_are_a_signal_and_merge_with_markers(self) -> None:
        brain = self.make_store("Documents/Brain", ".obsidian")
        deep = self.make_store("deep/a/b/c/Kb")  # beyond the walk depth, found only via the registry
        self.write_registry("Library/Application Support/obsidian/obsidian.json", str(brain) + "/")
        self.write_registry(".config/obsidian/obsidian.json", str(deep), str(self.home / "gone"))

        found = self.by_path(self.scan())

        self.assertEqual(set(found), {str(brain), str(deep)})
        self.assertEqual(found[str(brain)]["signals"], ["registry:obsidian", "marker:.obsidian"])
        self.assertEqual(found[str(deep)]["signals"], ["registry:obsidian"])

    def test_excluded_places_are_never_candidates(self) -> None:
        kept = self.make_store("a/b/notes")  # depth 3 is the deepest level scanned
        self.make_store("a/b/c/notes")  # depth 4
        self.make_store("Library/Mobile Documents/Vault", ".obsidian")
        self.make_store("app/node_modules/notes")
        self.make_store("repo/.git/notes")
        self.make_store(".Trash/old-vault", ".obsidian")
        self.make_store(".claude/smartthink-vault")
        protected = self.make_store(".claude/notes", ".obsidian")
        repo_protected = self.make_store("repo/.claude/vault", ".obsidian")
        self.write_registry(".config/obsidian/obsidian.json", str(protected), str(repo_protected))

        found = self.by_path(self.scan())

        self.assertEqual(set(found), {str(kept)})

    def age(self, store: Path, timestamp: int) -> None:
        for path in store.rglob("*"):
            if path.is_file():
                os.utime(path, (timestamp, timestamp))

    def test_candidate_fields_and_warnings(self) -> None:
        fresh = self.make_store("Documents/Brain", ".obsidian", files=10)
        stale = self.make_store("old-notes", files=10)
        self.age(stale, 1768478400)  # 2026-01-15T12:00:00Z, over 180 days before any run of this suite
        empty = self.make_store("Obsidian Vault", ".obsidian", files=1)
        repo = self.home / "code" / "site"
        (repo / ".git").mkdir(parents=True)
        in_repo = self.make_store("code/site/notes", files=10)
        workspace = self.make_store("workspace", ".obsidian", files=10)
        for index in range(4):
            (workspace / f"repo-{index}" / ".git").mkdir(parents=True)

        found = self.by_path(self.scan())

        today = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(
            found[str(fresh)],
            {
                "path": str(fresh),
                "signals": ["marker:.obsidian"],
                "last_modified": today,
                "file_count": 10,
                "git_repo": False,
                "warnings": [],
                "suggested_vault": str(fresh / "smartthink"),
            },
        )
        self.assertEqual(found[str(stale)]["last_modified"], "2026-01-15")
        self.assertEqual(found[str(stale)]["warnings"], ["stale"])
        self.assertEqual(found[str(empty)]["warnings"], ["nearly-empty"])
        self.assertTrue(found[str(in_repo)]["git_repo"])
        self.assertEqual(found[str(in_repo)]["warnings"], [])
        self.assertEqual(found[str(workspace)]["warnings"], ["workspace-root"])

    def test_real_case_registry_points_at_the_wrong_places(self) -> None:
        # Observed on a real machine: Obsidian's registry lists an unused starter vault and a work
        # folder holding 30 repos, while the real note store has only a name signal.
        starter = self.make_store("Documents/Obsidian Vault", ".obsidian", files=1)
        workspace = self.make_store("workspace", ".obsidian", files=2)
        for index in range(30):
            (workspace / f"repo-{index:02d}" / ".git").mkdir(parents=True)
        real = self.make_store("workspace/notes", files=40)
        (real / ".git").mkdir()
        self.write_registry("Library/Application Support/obsidian/obsidian.json", str(starter), str(workspace))

        result = self.scan()
        found = self.by_path(result)

        self.assertEqual(set(found), {str(starter), str(workspace), str(real)})
        self.assertIn("nearly-empty", found[str(starter)]["warnings"])
        self.assertIn("workspace-root", found[str(workspace)]["warnings"])
        self.assertEqual(found[str(real)]["signals"], ["name:notes"])
        self.assertEqual(found[str(real)]["warnings"], [])
        self.assertTrue(found[str(real)]["git_repo"])

    def test_scan_reports_its_bounds_and_stops_at_the_time_limit(self) -> None:
        self.make_store("notes")

        unbounded = self.scan()
        stopped = self.scan("--time-limit", "0")

        # Nothing in the output marks a candidate as chosen: the user picks.
        self.assertEqual(set(unbounded), {"candidates", "create_new", "scan"})
        self.assertEqual(unbounded["scan"], {"root": str(self.home), "max_depth": 3, "timed_out": False})
        self.assertTrue(stopped["scan"]["timed_out"])

    def test_time_limit_also_bounds_describing_candidates(self) -> None:
        # The registry is read before the walk, so its entries reach describe() even when the walk
        # stops at once. Counting a big tree must stop at the limit too and say the facts are partial.
        big = self.home / "Big Vault"
        for folder in range(30):
            (big / f"d{folder}").mkdir(parents=True)
            for index in range(100):
                (big / f"d{folder}" / f"n{index}.md").write_text("x\n", encoding="utf-8")
        self.write_registry(".config/obsidian/obsidian.json", str(big))

        stopped = self.scan("--time-limit", "0")
        full = self.by_path(self.scan())

        self.assertTrue(stopped["scan"]["timed_out"])
        [candidate] = stopped["candidates"]
        self.assertEqual(candidate["path"], str(big))
        self.assertLess(candidate["file_count"], 3000)
        self.assertEqual(candidate["warnings"], ["partial"])
        self.assertEqual(full[str(big)]["file_count"], 3000)
        self.assertNotIn("partial", full[str(big)]["warnings"])


if __name__ == "__main__":
    unittest.main()
