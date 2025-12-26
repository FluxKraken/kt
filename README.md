# kt

`kt` is a project-oriented scaffolding tool that stores templates, recipes, and assets in a local SQLite database. It renders Jinja2 templates, runs Lua-based recipes, and bundles projects into shareable `.project` archives.

## What it can do

- **Projects as namespaces**: Keep templates, recipes, and assets organized by project.
- **Lua recipes**: Orchestrate prompts, file generation, asset copying, and shell commands.
- **Jinja2 templating with shell tags**: `{>command<}` tags run shell commands at render time.
- **Config generation**: Produce TOML/YAML config files from recipe defaults.
- **Bundles**: Export/import complete project bundles as `.project` archives.
- **On-disk projects**: Initialize and bundle projects from a folder structure.

## Getting started

### Install

`kt` is distributed as a Python CLI (requires Python 3.14+).

```bash
uv tool install https://github.com/FluxKraken/kt.git
```

### Quick example

Create a project, import a template and recipe, generate a config file, then run the recipe:

```bash
kt new --project hello

kt import --template app --file ./app.j2 --project hello
kt import --recipe scaffold --file ./scaffold.lua --project hello

kt recipe scaffold --project hello --set-default

kt r hello --create-config ./config.toml
$EDITOR ./config.toml
kt r hello --config ./config.toml
```

### Basic template and recipe

`app.j2`
```jinja
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"name": "{{ app.name }}"}
```

`scaffold.lua`
```lua
r.config({
  app = { name = { default = "hello-service" } }
})

r.mkdir("$(app.name)", { parents = true })
r.template("hello::app", {
  destination = r.f("$(app.name)/main.py"),
  context = { app = { name = r.ref("app.name") } }
})
```

## Documentation

- [User Guide](docs/user_guide.md)
- [Recipe API](docs/recipe_api.md)

## License

MIT
