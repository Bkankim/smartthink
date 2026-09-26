# T13-fix 도구 목록 실측 (#16)

실행일: 2026-09-27 00:52~01:00 (+09:00) | codex-cli 0.157.1 | 모델 `anthropic/claude-opus-5-5`(opencodex 프록시 `127.0.0.1:10101` 경유)

## spawn_agent 공급원

`custom_collaboration__spawn_agent` 이름은 Codex 멀티 에이전트 v2 도구(`namespace: "collaboration"`)가 code mode(`tool_mode: "code_mode_only"`) 아래에서 `custom_` 접두어를 달고 노출된 것이다. 켜는 스위치는 기능 플래그가 아니라 **모델 카탈로그 항목의 `multi_agent_version`** 이다.

- `~/.codex/config.toml`의 `model_catalog_json = "<HOME>/.codex/opencodex-catalog.json"`(opencodex가 주입)
- 그 카탈로그의 `anthropic/claude-opus-5-5` 항목: `{'tool_mode': 'code_mode_only', 'multi_agent_version': 'v2', 'shell_type': 'unified_exec'}`
- 카탈로그 22개 모델 전부에 `multi_agent_version`(`v1` 또는 `v2`)이 있다.
- 세션 `turn_context`에도 `"multi_agent_version": "v2"`가 기록된다(#8 run2 armorer 세션).

## 3회 대조 (모두 격리 `CODEX_HOME`, `auth.json`만 심링크, 실제 `~/.codex/` 무수정)

| 회차 | 카탈로그 | `[features]` | 최상위 도구 목록(모델 응답 원문) | 판정 |
|---|---|---|---|---|
| 1 | 원본(`multi_agent_version: v2`) | `multi_agent = false`, `multi_agent_v2 = false` | `custom_exec`, `custom_wait`, `custom_request_user_input`, `custom_request_user_input_async`, `custom_clock__sleep`, `custom_collaboration__followup_task`, `custom_collaboration__interrupt_agent`, `custom_collaboration__list_agents`, `custom_collaboration__send_message`, `custom_collaboration__spawn_agent`, `custom_collaboration__wait_agent`, `web_search` | 플래그를 꺼도 서브에이전트 도구 있음 |
| 2 | 사본에서 `multi_agent_version` 키만 삭제 | 회차 1과 같음 | `custom_exec`, `custom_wait`, `custom_request_user_input`, `custom_request_user_input_async`, `custom_clock__sleep`, `web_search` | 서브에이전트 도구 없음 |
| 3 | 회차 2와 같음 | 블록 없음(기본값, `multi_agent` stable true) | 회차 2와 같은 6개 | 카탈로그 키만으로 결정됨 |

회차 2·3은 `custom_exec` 안의 `ALL_TOOLS`도 출력시켰다. `grep -oE 'custom_collaboration__[a-z_]+'` 0건, 이름에 `spawn`·`agent`가 들어간 것은 `mcp__codex_apps__notion_notion_spawn_session`, `mcp__codex_apps__notion_notion_search_agents`(Notion 앱 커넥터, Codex 서브에이전트 아님)뿐이다. 회차 3의 세션 `turn_context`는 `multi_agent_version: "v1"`로 기록되지만 도구는 노출되지 않았다.

## 격리 CODEX_HOME 구성 (재현 절차)

```sh
WT="<검증 대상 체크아웃 절대경로>"        # 리포 밖 cwd에서 쓰므로 절대경로로 직접 지정한다
: "${WT:?WT 미정의}"                     # 비었으면 여기서 멈춘다
test -f "$WT/skills/smartthink/SKILL.md" || echo "WT 확인 실패 - 아래를 실행하지 말고 WT를 고친다" >&2
CH="$(mktemp -d)"                        # 이후 T13 명령은 이 셸에서 $CH를 그대로 쓴다
ln -s ~/.codex/auth.json "$CH/auth.json"                      # 복사하지 않는다
mkdir -p "$CH/skills" && ln -s "$WT/skills/smartthink" "$CH/skills/smartthink"   # 워크트리 스킬
python3 - "$CH" <<'EOF'
import json, os, sys
c = json.load(open(os.path.expanduser('~/.codex/opencodex-catalog.json')))
c['models'] = [m for m in c['models'] if m.get('slug') == 'anthropic/claude-opus-5-5']
for m in c['models']:
    m.pop('multi_agent_version', None)
json.dump(c, open(sys.argv[1] + '/catalog.json', 'w'))
EOF
cat > "$CH/config.toml" <<EOF
model_catalog_json = "$CH/catalog.json"
openai_base_url = "http://127.0.0.1:10101/v1"
model = "anthropic/claude-opus-5-5"
model_reasoning_effort = "medium"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[features]
multi_agent = false
multi_agent_v2 = false
EOF
```

`--disable multi_agent`·`-c features.multi_agent=false`가 듣지 않았던 이유(#8)는 카탈로그가 모델별로 `multi_agent_version`을 고정하기 때문이다. 카탈로그를 쓰지 않는 기본 OpenAI 모델 설정이라면 기능 플래그만으로 충분할 수 있으나 이 머신에서는 확인하지 않았다.
