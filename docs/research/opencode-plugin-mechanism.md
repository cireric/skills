# OpenCode Plugin Mechanism Research

## Question

Can JS scripts placed in a project's `.opencode/plugins/` directory work as opencode plugins?

## Answer

**Yes — fully supported.** `.opencode/plugins/` is the official, documented project-level plugin directory. OpenCode automatically discovers and loads `.js` and `.ts` files from this directory at startup. No additional registration is required for local file-based plugins.

## Evidence

| Claim | Source | What was found |
|-------|--------|----------------|
| `.opencode/plugins/` is the project-level plugin directory | [opencode.ai/docs/plugins/](https://opencode.ai/docs/plugins/) — "From local files" section | "Place JavaScript or TypeScript files in the plugin directory. `.opencode/plugins/` - Project-level plugins" |
| Files are auto-loaded at startup | Same source | "Files in these directories are automatically loaded at startup." |
| Both `.js` and `.ts` are supported | Same source | "Place **JavaScript or TypeScript** files in the plugin directory." |
| Load order is documented | Same source — "Load order" section | 4-step order: global config → project config → global plugin dir → project plugin dir |
| V2 API also supports `.opencode/plugins/` | [opencode.ai/v2/docs/build/plugins](https://opencode.ai/v2/docs/build/plugins) — "Local discovery" section | "OpenCode automatically scans this directory in every discovered OpenCode config directory: `.opencode/plugins/`" |
| V2 local discovery details | Same source | "Direct `.ts` and `.js` children are loaded. An immediate child directory is also loaded as a package when OpenCode can resolve a string `exports`, `module`, or `main` entrypoint, or an `index.ts` or `index.js` file." |
| Plugin type definition in source | [deepwiki.com/anomalyco/opencode/2.9-plugin-system](https://deepwiki.com/anomalyco/opencode/2.9-plugin-system) | "Plugins are JavaScript/TypeScript modules that export functions conforming to the `Plugin` type [packages/plugin/src/index.ts:74]" |
| Source code: plugin loading from `.opencode/plugins/` | [github.com/anomalyco/opencode — packages/opencode/src/plugin/index.ts:152](https://github.com/anomalyco/opencode/blob/7ad68f81/packages/opencode/src/plugin/index.ts#L152) | Local plugins scanned from `.opencode/plugins/` or project directory |
| Source code: PluginLoader implementation | [github.com/anomalyco/opencode — packages/opencode/src/plugin/loader.ts](https://github.com/anomalyco/opencode/blob/7ad68f81/packages/opencode/src/plugin/loader.ts) | Handles fetching npm packages and evaluating local files |
| Config docs confirm plugin directory convention | [opencode.ai/docs/config/](https://opencode.ai/docs/config/) — "Precedence order" note | "The `.opencode` and `~/.config/opencode` directories use **plural names** for subdirectories: `agents/`, `commands/`, `modes/`, `plugins/`, `skills/`, `tools/`, and `themes/`." |
| Config: `plugin` array for npm packages | Same source — "Plugins" section | `"plugin": ["opencode-helicone-session", "@my-org/custom-plugin"]` in `opencode.json` |

## Plugin Mechanism Overview

OpenCode has a **two-generation plugin system**:

### V1 Plugin API (current stable)

A plugin is an **async function** that receives a `PluginInput` context and returns a `Hooks` object:

```js
export const MyPlugin = async ({ project, client, $, directory, worktree }) => {
  return {
    // Hook implementations
  }
}
```

**PluginInput fields:**
- `project` — current project information
- `directory` — current working directory
- `worktree` — git worktree path
- `client` — opencode SDK client
- `$` — Bun's shell API for executing commands

**Hooks interface (V1):**

| Hook | Purpose |
|------|---------|
| `event` | Subscribe to system events |
| `config` | Inject configuration |
| `tool` | Register custom tools (keyed object) |
| `auth` | Custom authentication for providers |
| `chat.message` | Intercept chat messages |
| `chat.params` | Modify LLM parameters (temperature, etc.) |
| `chat.headers` | Inject custom HTTP headers |
| `permission.ask` | Custom permission logic |
| `command.execute.before` | Pre-command hook |
| `tool.execute.before` | Modify tool args / block execution |
| `tool.execute.after` | Process tool results |
| `shell.env` | Inject environment variables |
| `experimental.session.compacting` | Customize compaction context |

### V2 Plugin API (beta)

Uses `Plugin.define` with a unique `id` and `setup` function:

```ts
import { Plugin } from "@opencode-ai/plugin"

export default Plugin.define({
  id: "acme.reviewer",
  setup: async (ctx) => {
    // Register transforms, hooks, tools
  },
})
```

V2 adds **transform hooks** (modify agents, models, commands, integrations, skills, tools) and **runtime hooks** (intercept live operations). The context object (`ctx`) provides a rich client API. V2 also supports an Effect-based API via `@opencode-ai/plugin/effect`.

## Supported Locations

| Location | Scope | Auto-discovered | Notes |
|----------|-------|-----------------|-------|
| `.opencode/plugins/` | Project | Yes | `.js` and `.ts` files auto-loaded; child dirs loaded as packages if they have entrypoint |
| `~/.config/opencode/plugins/` | Global | Yes | Same auto-discovery as project-level |
| `opencode.json` → `"plugin"` array | Config | N/A (explicit) | npm package names or local paths (e.g., `"./plugins/local.ts"`) |
| `OPENCODE_CONFIG_DIR`/plugins/ | Custom | Yes | When `OPENCODE_CONFIG_DIR` env var is set |

**Load order (V1):**
1. Global config (`~/.config/opencode/opencode.json`)
2. Project config (`opencode.json`)
3. Global plugin directory (`~/.config/opencode/plugins/`)
4. Project plugin directory (`.opencode/plugins/`)

**V2 note:** A `plugins/` directory beside a project-root `opencode.json` is **not** auto-discovered. It must be under `.opencode/`, or added explicitly via a relative config entry.

## Supported Formats

| Format | Supported | Notes |
|--------|-----------|-------|
| `.js` (JavaScript) | Yes | Plain JS modules |
| `.ts` (TypeScript) | Yes | Native TS support via Bun runtime — no build step needed |
| `.mjs` / `.mts` | Likely | Bun supports these; not explicitly documented for plugins |
| Child directory as package | Yes (V2) | If the dir has `exports`, `module`, `main`, `index.ts`, or `index.js` |
| npm package | Yes | Via `"plugin"` array in config |

TypeScript plugins can import types from `@opencode-ai/plugin`:

```ts
import type { Plugin } from "@opencode-ai/plugin"
```

## Configuration

### Local plugins (auto-discovered)

No configuration needed. Drop `.js` or `.ts` files in `.opencode/plugins/` and they are loaded at startup.

### npm plugins (config-based)

Add to `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-helicone-session", "@my-org/custom-plugin"]
}
```

### V2 config-based plugins

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    "opencode-acme-plugin@1.2.0",
    "./plugins/local.ts",
    {
      "package": "./plugins/reviewer.ts",
      "options": { "agent": "reviewer", "strict": true }
    }
  ]
}
```

V2 supports disable directives: `"-"` prefix disables by plugin `id`:

```json
{
  "plugins": ["-acme.reviewer", "-opencode.provider.*", "opencode.provider.openai"]
}
```

### Dependencies

Local plugins needing npm packages must have a `package.json` in the config directory (e.g., `.opencode/package.json`). OpenCode runs `bun install` at startup.

```json
// .opencode/package.json
{
  "dependencies": {
    "shescape": "^2.1.0"
  }
}
```

**V2 note:** For V2 local files, OpenCode does **not** install their dependencies automatically. Install deps in a `package.json` visible from the plugin file:

```bash
cd .opencode
bun add @opencode-ai/plugin@next
```

## Limitations / Gotchas

1. **V2 API is beta** — Entrypoints, hooks, draft shapes, and configuration may change before stable release. ([source](https://opencode.ai/v2/docs/build/plugins))

2. **`plugins/` beside `opencode.json` is not auto-discovered (V2)** — It must be under `.opencode/`, or referenced explicitly in config. ([source](https://opencode.ai/v2/docs/build/plugins) — "Local discovery" section)

3. **Duplicate handling** — npm packages with the same name+version are loaded once. A local plugin and an npm plugin with similar names are loaded separately. ([source](https://opencode.ai/docs/plugins/))

4. **V1 uses singular `"plugin"` key, V2 uses plural `"plugins"` key** in `opencode.json`. The V1 key is `"plugin": [...]`, the V2 key is `"plugins": [...]`.

5. **Plugin tool name collisions** — If a plugin tool uses the same name as a built-in tool, the plugin tool takes precedence. Use unique names unless intentionally overriding. ([source](https://opencode.ai/docs/custom-tools/))

6. **Hook failures are fatal** — A runtime hook failure fails the operation it intercepts. Keep hooks fast and handle expected errors inside the callback. ([source](https://opencode.ai/v2/docs/build/plugins))

7. **V2 local deps not auto-installed** — For V2 local plugin files, OpenCode does not install their dependencies. You must install them yourself. ([source](https://opencode.ai/v2/docs/build/plugins) — "Installation and dependencies")

8. **Hot reload** — Config and discovered plugin files under watched config directories are reloaded when they change. But changing an npm package version or local dependency requires a restart. ([source](https://opencode.ai/v2/docs/build/plugins))

9. **Bun runtime required** — Plugins run on Bun (not Node.js). The `$` shell API and module resolution are Bun-specific. npm plugins are installed via `bun install`. ([source](https://opencode.ai/docs/plugins/))

10. **Backwards-compatible singular dir names** — `.opencode/plugin/` (singular) is also supported for backwards compatibility, but plural `plugins/` is the convention. ([source](https://opencode.ai/docs/config/))

## Summary

Placing JS (or TS) scripts under `.opencode/plugins/` is the **official, first-class, documented way** to create project-level opencode plugins. Files are auto-discovered and loaded at startup with no additional configuration. The plugin system is mature (V1 stable, V2 beta) and supports hooks for events, tools, chat parameters, authentication, permissions, shell environment, and more.
