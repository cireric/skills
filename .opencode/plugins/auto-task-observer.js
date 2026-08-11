export const AutoTaskObserver = async ({ project, client, $, directory, worktree }) => {
  const OBSERVABLE_SKILLS = new Set([
    "intent-research",
    "video-download",
  ])
  const SKILL_MARKERS = {
    "intent-research": ["# Intent-Research Skill", "Invoke via /intent-research only"],
    "video-download": ["# Video Download 视频下载"],
  }
  const triggered = new Set()

  const inject = async (sessionID, name) => {
    const key = `${sessionID}:${name}`
    if (triggered.has(key)) return
    triggered.add(key)
    try {
      await client.session.promptAsync({
        path: { id: sessionID },
        body: {
          parts: [
            {
              type: "text",
              text: "[system] A skill with observation value was loaded. Load task-observer skill now and run its Session Start Protocol. Do not reply — proceed silently.",
              synthetic: true,
            },
          ],
          noReply: true,
        },
      })
    } catch (err) {
      console.error("[auto-task-observer] failed to inject skill-load prompt:", err)
    }
  }

  const matchSkill = (text) => {
    for (const [name, markers] of Object.entries(SKILL_MARKERS)) {
      if (!OBSERVABLE_SKILLS.has(name)) continue
      if (markers.some((m) => text?.includes(m))) return name
    }
    return null
  }

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "skill") return

      const skillName = output.args?.name || ""
      if (!OBSERVABLE_SKILLS.has(skillName)) return

      await inject(input.sessionID, skillName)
    },
    event: async ({ event }) => {
      if (event.type !== "message.part.updated") return
      const part = event.properties?.part
      if (part?.type !== "text") return
      const name = matchSkill(part.text)
      if (name) await inject(part.sessionID, name)
    },
  }
}
