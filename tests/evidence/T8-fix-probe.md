# T8-fix 프로브 - Agent 호출이 백그라운드로 뜨는 조건 (#15)

생성: 2026-09-27 (+09:00) | Claude Code 2.1.283, Opus 5.5 | 격리 `CLAUDE_CONFIG_DIR`(settings.json = `{"permissions":{"allow":["Agent","Read"]}}`, 사용자 레벨 agents/skills 없음) | 플러그인·스킬 미사용(하네스 동작만 본다)

## 명령

```
CLAUDE_CONFIG_DIR=<ISOLATED_CONFIG> CLAUDE_CODE_OAUTH_TOKEN="$ANTHROPIC_OAUTH_TOKEN" CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 \
  claude --model opus -p --output-format stream-json --verbose \
  'Call the Agent tool exactly once with these exact input fields: subagent_type "general-purpose", description "probe", run_in_background false, prompt "Reply with the single word PONG and nothing else." Then wait for its result and reply with what it returned. Do nothing else.'
```

## stream-json 발췌 (줄 번호 = jsonl 줄, agentId·임시 경로는 치환, 도구 결과 원문 그대로)

```
[1] init claude_code_version=2.1.283 agent-tool-name=['Task']
[5] tool_use name=Agent input={"subagent_type": "general-purpose", "description": "probe", "prompt": "Reply with the single word PONG and nothing else."}
[8] tool_result: Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.)
agentId: <ID> (internal ID - do not mention to user. Use SendMessage with to: '<ID>', summary: '<5-10 word recap>' to continue this agent.)
The agent is working in the background. You will be notified automatically when it completes. You know nothing about its results until that notification arrives — do not report, assume, or predict them; continue other work or respond to the user in the meantime.
Do not duplicate this agent's work — avoid working with the same files or topics it is using.
output_file: <TMP>
Do NOT Read or tail this file via the shell tool — it is the full subagent JSONL transcript and reading it will overflow your context. If the user asks for progress, say the agent is still running; you'll get a completion notification.
[10] assistant text: PONG
[14] assistant text: I launched the probe agent, but I couldn't make it run in the foreground: the Agent tool has no `run_in_background` field, and the agent started in the background anyway. It's still running and I don't have its reply yet. I'll pass along exactly what it returns when it finishes.
[15] result(stdout candidate): I launched the probe agent, but I couldn't make it run in the foreground: the Agent tool has no `run_in_background` field, and the agent started in the background anyway. It's still running and I don't have its reply yet. I'll pass along exactly what it returns when it finishes.
[16] init claude_code_version=2.1.283 agent-tool-name=['Task']
[17] assistant text: PONG
[18] result(stdout candidate): PONG
```

## 판정

- **H1 채택**: 모델에게 `run_in_background false`를 명시 지시했는데도 [5]의 tool_use 입력에 그 필드가 없다(키: subagent_type, description, prompt). 모델 스스로 [14]에서 "the Agent tool has no `run_in_background` field"라고 보고했다. 결과 [8]은 `Async agent launched successfully ... The agent is working in the background`이다. 이 하네스의 Agent 도구 스키마에는 동기/비동기 선택 파라미터가 없고 모든 서브에이전트가 백그라운드 + 완료 알림으로 돈다. 이 워커 세션(같은 2.1.283)의 Agent 도구 스키마도 `description, isolation, model, prompt, subagent_type`뿐이고 설명에 "Subagents run in the background"가 있다. 선행 증거 `T2-transcript.md:77`, `T11-observation.md:30`도 같은 관찰을 기록했다.
- **H2 기각**: 모델이 인자를 빠뜨리거나 true로 넣은 것이 원인이 아니다. 스키마에 필드가 없으므로 넣을 수 없다. 넣으라고 지시해도 입력에서 빠진다.
- **H3 기각**: 정식 `smartthink:st-armorer`도 백그라운드다. `T9-rerun-transcript.md` 780·1538·2591·2988·3478행의 `smartthink:st-armorer` 호출 5건이 모두 `Async agent launched successfully ... working in the background`를 받았다(786·1544·2597·2994·3484행). general-purpose 폴백만의 문제가 아니다.
- **헤드리스 관찰**: `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`에서 `-p`는 백그라운드 에이전트를 기다린 뒤 완료 알림으로 두 번째 턴을 돌렸다([16]~[18]). result 이벤트가 두 개([15], [18])이고 stdout의 마지막 응답은 알림 뒤 응답([18] `PONG`)이다. 그래서 헤드리스 요약 줄은 알림 뒤 응답에 있어야 한다. 첫 턴 끝의 [14]는 "아직 결과를 모른다"는 고지로, 5a 대기 규칙 2항이 허용하는 1줄 상태 고지에 해당한다(추측 없음).

결론: SKILL.md 5a의 동기 요구는 이 하네스에서 강제할 수 없다. 5a에 "백그라운드 스폰 대기 규칙"을 명시했다(완료 알림 전 6단계 보류, 대기 중 1줄 외 출력·추측 금지, 알림 뒤 반환 규약 확인 후 6단계, 헤드리스는 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`과 알림 뒤 응답의 요약 줄).
