---
description: SmartThink alias. Same as /smartthink:smartthink.
---
Invoke the `smartthink:smartthink` skill with the Skill tool, passing `$ARGUMENTS` through unchanged.

Name resolution: if `smartthink:smartthink` is not found, retry **once** with the bare name
`smartthink`. A plugin install registers the namespaced name; a non-plugin install (install.sh
symlinks the skill into `~/.claude/skills/`) registers only the bare name. If neither resolves,
say the SmartThink skill is not installed and stop. Do not answer the request from general
knowledge under this command.
