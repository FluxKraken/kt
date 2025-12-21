# Recipe API Reference

Recipes in `kt` are Lua scripts. The engine exposes a single global table `r` with helpers for collecting input, rendering templates, copying assets, and running commands.

> **Execution modes:** `kt recipe render ... --output` runs in **GENERATE_CONFIG** mode (defaults only, no side effects). Supplying `--config` switches to **EXECUTE** mode (runs commands, writes files).

## Quick Cheat Sheet

- `r.declare` — Seed context with defaults.
- `r.prompt` — Collect user input (or emit defaults when generating config).
- `r.template` — Render a Jinja2 template to disk.
- `r.assets` — Copy a stored asset to disk.
- `r.command` — Group shell actions (optional `check` gate).
- `r.run` — Execute a command (`cmd`, `args`, `cwd`).
- `r.gate` — Ask for confirmation and store/use the answer.
- `r.touch` — Create a file with optional content.
- `r.mkdir` — Create directories (optionally with parents).
- `r.delete` — Delete a file or directory recursively.
- `r.f` / `r.ref` / `r.splice` — Formatting and lookups.

## Core Methods (with examples)

### `r.declare(table)`

Declare initial variables. Useful for defaults that should exist even before prompting.

```lua
r.declare({
  service = { name = "my-api", port = 8080 },
  dependencies = { prod = { "flask", "requests" } }
})
```

### `r.prompt(table)`

Ask for values (or emit them to the generated config file).

- `default`: Value written to the config file.
- `_comment`: A description that appears above the key in the generated TOML.

```lua
r.prompt({
  project = {
    name = { default = "My Project" },
    version = { default = "0.1.0" }
  },
  db = {
    _comment = "Database settings",
    host = { default = "localhost" },
    port = { default = 5432 }
  }
})
```

In EXECUTE mode, missing values trigger an editor prompt (respects `$EDITOR`/`$VISUAL`).

### `r.template(name, table)`

Render a stored Jinja2 template to a file.

Parameters:

- `output` (required): Target path.
- `overwrite` (bool): Replace existing file (default: `false`).
- `context` (table): Values available to the template.

```lua
r.template("flask::app", {
  output = r.f("$(project.name)/app.py"),
  overwrite = true,
  context = {
    name = r.ref("project.name"),
    db_port = r.ref("db.port")
  }
})
```

### `r.assets(name, table)`

Copy a binary/text asset.

- `destination` (required): Where to write the file.
- `overwrite` (bool): Replace if present.

```lua
r.assets("flask::logo", {
  destination = r.f("$(project.name)/public/logo.png"),
  overwrite = true
})
```

### `r.command(options, function)`

Group one or more `r.run` calls. If `check` is provided and resolves to falsy, the block is skipped.

```lua
r.command({ check = "use_git" }, function()
  r.run({ "git", "init" })
  r.run({ "git", "add", "." })
end)
```

### `r.run(args, options)`

Run a subprocess.

- `args`: Array of command tokens (Lua table, numeric keys).
- `options`: Optional table. Currently supports `cwd`.

```lua
r.run({ "npm", "install" }, { cwd = r.f("$(project.name)") })
```

### `r.gate(table)`

Prompt for a boolean (returns the answer). In CONFIG mode it uses the default without prompting.

Fields:

- `prompt`: Question text.
- `default`: Default boolean (optional, defaults to `true`).
- `store`: Context key to persist the answer.

```lua
if r.gate({ prompt = "Initialize Git?", store = "use_git", default = true }) then
  r.run({ "git", "init" })
end
```

### `r.touch(path, options)`

Create a file with optional content.

- `content`: String (supports `$(...)` substitutions via `r.f` inside the value).
- `overwrite`: Replace if present.

```lua
r.touch("$(project.name)/README.md", {
  content = "# $(project.name)",
  overwrite = true
})
```

### `r.mkdir(path, options)`

Create a directory.

- `parents`: Create intermediate directories (like `mkdir -p`).

```lua
r.mkdir("$(project.name)/src", { parents = true })
```

### `r.delete(path)`

Delete a file or directory recursively. Path interpolation requires explicit `r.f()`.

- `path`: String path to delete.

```lua
-- Delete a single file
r.delete("temp_file.txt")

-- Delete a directory recursively (using variable)
r.delete(r.f("$(project.name)/temp_dir"))
```

## Helper Methods

- **`r.f(string)`** — Format using `$(var.path)` substitution from context.
  ```lua
  local path = r.f("$(project.name)/Dockerfile")
  ```
- **`r.ref(path)`** — Read a context value (returns `""` if missing).
  ```lua
  local port = r.ref("service.port")
  ```
- **`r.splice(path)`** — Return a list-like value suitable for spreading into commands.
  ```lua
  r.run({ "pip", "install", r.splice("dependencies.prod") })
  ```

## Putting It Together (mini recipe)

```lua
r.declare({
  dependencies = { prod = { "click", "rich" } }
})

r.prompt({
  project = { name = { default = "demo-app" } },
  python = { version = { default = "3.12" } }
})

r.mkdir("$(project.name)", { parents = true })
r.template("demo::app", {
  output = r.f("$(project.name)/app.py"),
  context = { python_version = r.ref("python.version") }
})

r.command({}, function()
  r.run({ "python", "-m", "venv", r.f("$(project.name)/.venv") })
  r.run({ r.f("$(project.name)/.venv/bin/pip"), "install", r.splice("dependencies.prod") })
end)
```

Generate a config:

```bash
kt recipe render scaffold --project demo --output ./config.toml
```

Execute with filled config:

```bash
kt recipe render scaffold --project demo --config ./config.toml
```
