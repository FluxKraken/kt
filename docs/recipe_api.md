# Recipe API Reference

Recipes in `kt` are Lua scripts that build an execution plan. The `kt` engine provides a global table `r` with methods to declare variables, request input, and execute actions.

## Core Methods

### `r.declare(table)`

Declare default variables in the context.

```lua
r.declare({
  dependencies = {
    prod = {"flask", "requests"}
  },
  base_url = "http://localhost:8000"
})
```

### `r.prompt(table)`

Define variables that need user input. `kt` uses this to generate the config file.

```lua
r.prompt({
  project = {
    name = { default = "My Project" },
    version = { default = "0.1.0" }
  },
  db = {
    _comment = "Database settings",
    port = { default = 5432 }
  }
})
```

### `r.template(name, table)`

Render a Jinja2 template to a file.

- `name`: Template name (use `project::name` if needed).
- `output`: Destination path.
- `context`: Data passed to the template.

```lua
r.template("flask::app", {
  output = r.f("$(project.name)/app.py"),
  context = {
    name = r.ref("project.name"),
    db_port = r.ref("db.port")
  }
})
```

### `r.assets(name, table)`

Copy a static asset.

- `destination`: Target path.

```lua
r.assets("flask::logo", {
  destination = "src/assets/logo.png"
})
```

### `r.command(options, function)`

Define a block of commands to run.

- `check`: (Optional) Name of a boolean context variable. If false, the block is skipped.

```lua
r.command({ check = "use_git" }, function()
  r.run({"git", "init"})
end)
```

### `r.run(args, options)`

Execute a shell command.

- `args`: List of command arguments.
- `options`: Table, e.g., `{ cwd = "path" }`.

```lua
r.run({"npm", "install"}, { cwd = "./my-project" })
```

### `r.gate(table)`

Ask the user for confirmation (boolean).

- `prompt`: Question text.
- `store`: Variable name to store result in.

```lua
r.gate({ prompt = "Initialize Git?", store = "use_git" })
```

## Helper Methods

- **`r.f(string)`**: Format string with `$(var.path)` substitution.
- **`r.ref(path)`**: Get the value of a context variable.
- **`r.splice(path)`**: Get a list value (useful for passing dependencies to `r.run`).

```lua
r.run({"pip", "install", r.splice("dependencies.prod")})
```
