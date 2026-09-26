# T9-bash 따옴표 인자 규칙 매칭 프로브 (final-review 20260927-030228 #1)

실행일: 2026-09-27 (+09:00) | Claude Code 2.1.283, `claude --model sonnet --permission-mode default -p` | 격리 `CLAUDE_CONFIG_DIR`, 임시 vault(`<VAULT>`, 팩 디렉터리 이름에 공백 `2026-09-27-q t`).

질문: `Bash(python3 <스크립트 절대경로> *)` 규칙이 팩 디렉터리를 큰따옴표로 감싼 명령에도 매칭되는가.

근거 1(문서): Claude Code 권한 문서 "Bash rules match the whole command text, with `*` standing in for any text"와 "A `*` at the end, with a space before it, also matches the bare command"(https://code.claude.com/docs/en/permissions). 접두어 뒤는 따옴표를 포함한 어떤 텍스트도 ` *`가 받는다. 쪼개지는 것은 `&&`·`;`·`|` 같은 명령 구분자뿐이다.

근거 2(실측): 격리 `settings.json`의 allow는 `assemble-pack.py --permission-rule`이 낸 `permission_rule` 1개(`Bash(python3 <HOME>/workspace/smartthink-st-21-assemble-pack/scripts/assemble-pack.py *)`)와 실제 vault deny 2줄뿐이다. `-p`는 승인을 받을 수 없으므로 규칙에 매칭되지 않는 Bash는 거부된다. 대조군으로 규칙 밖 명령을 함께 실행시켰다. 세션 jsonl에서 추출한 도구 호출(홈·vault 경로 치환):

```
CALL: Bash python3 <HOME>/workspace/smartthink-st-21-assemble-pack/scripts/assemble-pack.py --pack-dir "<VAULT>/packs/2026-09-27-q t" --modules core-engines.md
  RESULT(is_error=False): {"pack": "<VAULT>/packs/2026-09-27-q t/pack.md", "modules": ["core-engines.md"], "bytes": 67318, "est_tokens_pack": 30599}
CALL: Bash python3 <VAULT>/other.py --x
  RESULT(is_error=True): This command requires approval
```

- 따옴표 인자 명령은 프롬프트 없이 실행됐고 공백 경로가 한 인자로 전달됐다(스크립트가 `.../2026-09-27-q t/pack.md`를 조립). 조립된 팩은 `check-structure.py --pack`의 `section 5 verbatim hash integrity` PASS.
- 대조군(규칙 밖 `python3 <VAULT>/other.py`)은 `This command requires approval`로 거부됐다. 즉 허용 설정이 전부 열려 있던 것이 아니라 규칙 매칭으로 실행된 것이다.
- 임시 설정·vault는 추출 뒤 삭제했다.
