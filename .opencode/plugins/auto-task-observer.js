export const AutoTaskObserver = async ({ project, client, $, directory, worktree }) => {
  return {
    event: async ({ event }) => {
      if (event.type !== "session.created") return

      const sessionID = event.properties.info.id

      try {
        await client.session.promptAsync({
          path: { id: sessionID },
          body: {
            parts: [
              {
                type: "text",
                text: "[system] Load the task-observer skill now and run its Session Start Protocol (init + status check). Do not reply to this message — proceed silently and wait for the user's first input.",
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
