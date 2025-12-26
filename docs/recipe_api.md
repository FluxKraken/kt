# Recipe API Reference

Recipes are Lua scripts executed by `kt`. Each recipe is given a global `r` table that provides helpers for prompts, templates, assets, filesystem actions, and commands.

## Execution modes

Recipes run in one of two modes:

- **GENERATE_CONFIG**: Used when you run `kt recipe ... --create-config`, `kt r ... --create-config`, or `kt project render ... --create-config`. Recipes do not write files or run commands in this mode. Defaults from `r.config` are collected into a config file.
- **EXECUTE**: Used when you pass `--config` or run without `--create-config`. Templates are rendered, assets copied, and commands executed.

## Context and interpolation

- `r.config` and `r.declare` populate the recipe context.
- `r.ref("path.to.value")` reads from the context.
- `r.f("$(path.to.value)/file.txt")` interpolates values into strings using `$(...)` syntax.

## API overview

- `r.declare(table)`
- `r.config(table, options)`
- `r.question(table)`
- `r.confirm(table)`
- `r.template(name, table)`
- `r.asset(name, table)`
- `r.recipe(name)`
- `r.run(args, options)`
- `r.eval(command)`
- `r.touch(path, options)`
- `r.mkdir(path, options)`
- `r.delete(path)`
- `r.f(string)`
- `r.ref(path)`
- `r.splice(path)`

## `r.declare(table)`

Merge values into the recipe context. This is helpful for defaults that should always exist.

```lua
r.declare({
  project = { name = "demo", port = 8080 },
  dependencies = { prod = { "fastapi", "uvicorn" } }
})
```

## `r.config(table, options)`

Define configuration defaults. The structure becomes the generated config file when running in `--create-config` mode.

- Every leaf node is defined by `{ default = <value> }`
- Nested tables group related config

Example:

```lua
r.config({
  project = {
    name = { default = "my-service" },
    port = { default = 8000 }
  },
  features = {
    telemetry = { default = true }
  }
})
```

Optional `options`:

- `template`: a template name or `project::template` to render the config file via Jinja2 instead of default TOML/YAML output.

```lua
r.config({
  project = { name = { default = "example" } }
}, { template = "starter::config" })
```

## `r.question(table)`

Prompt the user for a text value. In `GENERATE_CONFIG` mode it returns the default (or an empty string).

Fields:

- `prompt`: prompt text
- `default`: default value
- `store`: a context key to store the result

```lua
local author = r.question({
  prompt = "Author name",
  default = "Unknown",
  store = "author"
})
```

## `r.confirm(table)`

Prompt for confirmation. In `GENERATE_CONFIG` mode it returns the default.

Fields:

- `prompt`: prompt text
- `default`: boolean (defaults to `false`)
- `store`: a context key to store the result

```lua
if r.confirm({ prompt = "Initialize Git?", default = true, store = "git" }) then
  r.run({ "git", "init" })
end
```

## `r.template(name, table)`

Render a stored template to disk.

- `name`: `template` or `project::template`
- `destination`: output path (required)
- `overwrite`: overwrite existing file (default `false`)
- `context`: template context overrides

```lua
r.template("starter::app", {
  destination = r.f("$(project.name)/app.py"),
  overwrite = true,
  context = { project = { name = r.ref("project.name") } }
})
```

## `r.asset(name, table)`

Copy an asset from the database to disk.

- `name`: `asset` or `project::asset`
- `destination`: output path (required)
- `overwrite`: overwrite existing file (default `false`)

```lua
r.asset("starter::logo", {
  destination = r.f("$(project.name)/public/logo.png"),
  overwrite = true
})
```

## `r.recipe(name)`

Execute another stored recipe by name:

```lua
r.recipe("starter::init")
```

## `r.run(args, options)`

Run a subprocess. Skipped in `GENERATE_CONFIG` mode.

- `args`: list of command arguments
- `options.cwd`: working directory

```lua
r.run({ "python", "-m", "venv", ".venv" })
r.run({ "git", "init" }, { cwd = r.f("$(project.name)") })
```

## `r.eval(command)`

Run a shell command and return its stdout. Useful for computed values.

```lua
local secret = r.eval("openssl rand -base64 32")
r.touch(".env", { content = "SECRET=" .. secret, overwrite = true })
```

## `r.touch(path, options)`

Create a file with optional content.

- `content`: file contents (supports `$(...)` substitutions)
- `overwrite`: overwrite existing file (default `false`)

```lua
r.touch("$(project.name)/README.md", {
  content = "# $(project.name)",
  overwrite = true
})
```

## `r.mkdir(path, options)`

Create a directory.

- `parents`: create intermediate directories (like `mkdir -p`)

```lua
r.mkdir("$(project.name)/src", { parents = true })
```

## `r.delete(path)`

Delete a file or directory recursively.

```lua
r.delete(r.f("$(project.name)/tmp"))
```

## `r.f(string)`

Format strings using `$(path.to.value)` substitution.

```lua
local path = r.f("$(project.name)/main.py")
```

## `r.ref(path)`

Return a context value by dotted path. If missing, returns an empty string.

```lua
local port = r.ref("project.port")
```

## `r.splice(path)`

Return a list from context, suitable for spreading into command arguments.

```lua
r.declare({ dependencies = { prod = { "rich", "toml" } } })
r.run({ "pip", "install", r.splice("dependencies.prod") })
```

## Full example

```lua
r.declare({
  dependencies = { prod = { "fastapi", "uvicorn" } }
})

r.config({
  project = { name = { default = "demo-app" } },
  python = { version = { default = "3.12" } }
})

r.mkdir("$(project.name)", { parents = true })

r.template("demo::app", {
  destination = r.f("$(project.name)/main.py"),
  context = { python_version = r.ref("python.version") }
})

if r.confirm({ prompt = "Create virtualenv?", default = true }) then
  r.run({ "python", "-m", "venv", r.f("$(project.name)/.venv") })
  r.run({ r.f("$(project.name)/.venv/bin/pip"), "install", r.splice("dependencies.prod") })
end
```
