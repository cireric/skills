export const AutoTaskObserver = async ({ project, client, $, directory, worktree }) => {
  const OBSERVABLE_SKILLS = new Set([
    "deep-research",
    "info-collector",
  ])

  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "skill") return

      const skillName = output.args?.name || ""
      if (!OBSERVABLE_SKILLS.has(skillName)) return

      try {
        await client.session.promptAsync({
          path: { id: input.sessionID },
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
    },
  }
}
