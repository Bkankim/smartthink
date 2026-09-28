---
description: SmartThink alias. Same as /smartthink:smartthink.
---
Invoke the SmartThink skill with the Skill tool, passing `$ARGUMENTS` through unchanged.

Name resolution: call the exact name the available skills list shows for SmartThink, before any
guess. If both are listed, call `smartthink:smartthink`: the bare name may be a stale user-level copy.
If only the bare `smartthink` is listed, call `smartthink`; call `smartthink:smartthink` only when
that name itself is listed. Read the skill list, not slash commands or agent names: a
`smartthink:st` command or `smartthink:st-armorer` agent can be registered while
`smartthink:smartthink` is not, because a same-named user-level skill shadows the plugin one.
Guessing the prefixed name costs a non-plugin install one failed call on every `/st`.

Only when no list is visible: if `smartthink:smartthink` is not found, retry **once** with the bare name
`smartthink`. A plugin install registers the namespaced name; a non-plugin install (install.sh
symlinks the skill into `~/.claude/skills/`) registers only the bare name. If neither resolves,
say the SmartThink skill is not installed and stop. Do not answer the request from general
knowledge under this command.
