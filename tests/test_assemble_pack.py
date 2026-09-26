"""Behaviour of scripts/assemble-pack.py, exercised through its CLI.

The pass criterion for an assembled pack is the existing gate, `check-structure.py --pack`.
Every case works in a throwaway directory; no real vault is read or written.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSEMBLER = REPO_ROOT / "scripts" / "assemble-pack.py"
CHECKER = REPO_ROOT / "scripts" / "check-structure.py"
REFERENCES = REPO_ROOT / "skills" / "smartthink" / "references"

# What the armorer Writes before calling the script: sections 1-4, the section 5 title with an
# empty body, then section 6. Hand-written, not derived from the script.
HEAD = """## 1. 무장 브리핑

브리핑 본문.

## 2. 작업 해석

해석.

## 3. 리서치 합성

리서치.

## 4. 작업 적용 레이어

적용.

## 5. 레퍼런스 원문

"""
TAIL = """## 6. 과거 인사이트와 프로필

프로필 없음 - `/st init` 권장
"""

MANIFEST = {
    "task": "fixture",
    "interpretation": "fixture",
    "cynefin": "Complicated",
    "classification": "fixture",
    "modules": ["core-engines.md", "meta-cognition.md"],
    "budget": None,
    "research": True,
    "profile_version": None,
    "est_tokens": {"pack": 0, "agent": 0},
    "created": "2026-09-27T00:00:00+09:00",
    "harness": "test",
}


class AssemblePackTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.pack_dir = self.root / "vault" / "packs" / "2026-09-27-fixture"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_pack(self, text: str = HEAD + TAIL) -> Path:
        self.pack_dir.mkdir(parents=True, exist_ok=True)
        (self.pack_dir / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
        pack = self.pack_dir / "pack.md"
        pack.write_text(text, encoding="utf-8")
        return pack

    def assemble(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ASSEMBLER), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def check_pack(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), "--pack", str(self.pack_dir)],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_assembled_pack_passes_the_pack_gate(self) -> None:
        self.write_pack()
        result = self.assemble(
            "--pack-dir", str(self.pack_dir), "--modules", "core-engines.md", "meta-cognition.md"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        gate = self.check_pack()
        self.assertIn("pack: 5 passed, 0 failed, 0 skipped", gate.stdout, gate.stdout)

    def test_non_module_names_fail_and_leave_pack_untouched(self) -> None:
        pack = self.write_pack()
        before = pack.read_bytes()
        # A missing file, a reference that is not one of the nine modules, and a path that
        # climbs out of references/ must all be refused.
        for name in ("no-such-module.md", "analysis-method.md", "../SKILL.md"):
            with self.subTest(name=name):
                result = self.assemble("--pack-dir", str(self.pack_dir), "--modules", name)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(name, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(pack.read_bytes(), before)

    def test_section_five_with_content_is_refused(self) -> None:
        # A second run, or a head that already carries section 5 text, must not stack blocks.
        pack = self.write_pack(HEAD + "이미 쓴 원문\n\n" + TAIL)
        before = pack.read_bytes()
        result = self.assemble("--pack-dir", str(self.pack_dir), "--modules", "core-engines.md")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("section 5", result.stderr)
        self.assertEqual(pack.read_bytes(), before)

        self.write_pack()
        self.assertEqual(
            self.assemble("--pack-dir", str(self.pack_dir), "--modules", "core-engines.md").returncode, 0
        )
        once = pack.read_bytes()
        again = self.assemble("--pack-dir", str(self.pack_dir), "--modules", "core-engines.md")
        self.assertNotEqual(again.returncode, 0, again.stdout)
        self.assertEqual(pack.read_bytes(), once)

    def test_paths_outside_a_pack_directory_are_refused(self) -> None:
        # The allow rule approves this command without a prompt, so the script itself only ever
        # rewrites <...>/packs/<pack>/pack.md and never follows a symlink out of it.
        stray = self.root / "elsewhere" / "notes"
        stray.mkdir(parents=True)
        (stray / "pack.md").write_text(HEAD + TAIL, encoding="utf-8")
        before = (stray / "pack.md").read_bytes()
        result = self.assemble("--pack-dir", str(stray), "--modules", "core-engines.md")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("packs", result.stderr)
        self.assertEqual((stray / "pack.md").read_bytes(), before)

        outside = self.root / "outside.md"
        outside.write_text(HEAD + TAIL, encoding="utf-8")
        self.pack_dir.mkdir(parents=True)
        (self.pack_dir / "pack.md").symlink_to(outside)
        linked = self.assemble("--pack-dir", str(self.pack_dir), "--modules", "core-engines.md")
        self.assertNotEqual(linked.returncode, 0, linked.stdout)
        self.assertIn("symlink", linked.stderr)
        self.assertTrue((self.pack_dir / "pack.md").is_symlink())
        self.assertEqual(outside.read_text(encoding="utf-8"), HEAD + TAIL)

    def test_permission_rule_names_this_script_by_absolute_path(self) -> None:
        # Claude Code matches a Bash rule against the command text, and a trailing " *" also
        # matches any arguments. The armorer calls `python3 {SCRIPTS_DIR}/assemble-pack.py ...`
        # with the symlink-resolved absolute path, so the rule must carry exactly that prefix.
        result = self.assemble("--permission-rule")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["permission_rule"], f"Bash(python3 {ASSEMBLER.resolve()} *)")
        self.assertIs(payload["permission_rule_effective"], True)

        # A space in the path splits the command into words, so no prefix rule matches it.
        spaced = self.root / "with space" / "scripts"
        spaced.mkdir(parents=True)
        copy = spaced / "assemble-pack.py"
        copy.write_bytes(ASSEMBLER.read_bytes())
        other = subprocess.run(
            [sys.executable, str(copy), "--permission-rule"], capture_output=True, text=True, check=False
        )
        self.assertEqual(other.returncode, 0, other.stderr)
        self.assertIs(json.loads(other.stdout)["permission_rule_effective"], False)

    def test_pack_keeps_its_file_mode(self) -> None:
        # Found in the T9 run: the rewritten pack.md came back 0600 instead of the mode the
        # Write tool gave it.
        pack = self.write_pack()
        pack.chmod(0o644)
        result = self.assemble("--pack-dir", str(self.pack_dir), "--modules", "core-engines.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(oct(pack.stat().st_mode & 0o777), oct(0o644))


if __name__ == "__main__":
    unittest.main()
