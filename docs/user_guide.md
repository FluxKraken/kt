# kt User Guide

`kt` is a project-oriented scaffolding system. It stores templates, recipes, and assets in a lightweight SQLite database and exposes a Click-based CLI to compose them into project skeletons.

## Core Concepts

- **Project** — A namespace that groups templates, recipes, and assets (e.g., `sveltekit`, `fastapi`).
- **Template** — A Jinja2 text template rendered to files. Supports `{>command<}` blocks that execute shell commands at render time.
- **Recipe** — A Lua script that collects input, renders templates, copies assets, and runs commands.
- **Asset** — A binary or text file copied verbatim (images, fonts, binaries).
- **Bundle** — A `.project` tarball that contains a project, its recipes, templates, and assets.

## Installation & Setup

```bash
uv tool install https://github.com/FluxKraken/kt.git
kt --help   # verify installation
```

> **Tip:** All commands accept `--help` for on-demand usage details.

## Project Management

Projects keep resources scoped and organized.

```bash
# List existing projects
kt project list

# Create a project namespace
kt new --project my-stack

# Delete a project (use --recursive to remove its resources)
kt delete --project my-stack --recursive
```

### Importing & Exporting Projects

- **Import from bundle**: `kt import --bundle ./starter.project --overwrite`
- **Import from folder**: `kt import --dir ./starter-folder --overwrite`
- **Export to bundle**: `kt bundle ./ --destination ./my-stack.project`

> Bundles are tar.gz archives. They keep file names and project metadata so you can rehydrate a stack elsewhere.

## Working with Templates

Templates are Jinja2 files. `kt` can pre-compute missing variables and prompt you via your editor.

Common flows:

```bash
# List templates (unscoped or within a project)
kt template --project my-stack

# Add a template (creates a new empty one)
kt new --template service --project my-stack

# Import an existing file as a template
kt import --template ./service.j2 --project my-stack --name service

# Generate a config skeleton for required variables
kt template service --project my-stack --create-config ./service.defaults.toml

# Render to disk (prompts for missing values if needed)
kt template service --project my-stack --destination ./build/service.py
```

Shell command blocks allow dynamic content:

```jinja
SECRET_KEY = "{>openssl rand -base64 32<}"
GIT_REMOTE = "{>git config --get remote.origin.url<}"
```

> **Security warning:** `{>command<}` blocks run with `shell=True`. Only render trusted templates.

## Working with Recipes

Recipes orchestrate prompting, templating, and execution. Each recipe can either **generate config** or **execute** depending on the flags you pass.

```bash
# List or import recipes
kt recipe --project my-stack
kt import --recipe ./init.lua --project my-stack --name init

# Generate a TOML config file from prompts
kt r init --project my-stack --create-config ./config.toml

# Execute using a prepared config
kt r init --project my-stack --config ./config.toml
```

Quick sample recipe (Lua):

```lua
r.prompt({
  project = { name = { default = "my-service" } },
  features = { telemetry = { default = true } }
})

r.template("my-stack::service", {
  output = r.f("$(project.name)/service.py"),
  context = { telemetry = r.ref("features.telemetry") }
})

r.command({ check = "features.telemetry" }, function()
  r.run({ "bash", "-lc", r.f("cd $(project.name) && ./enable-telemetry.sh") })
end)
```

- `r.prompt` writes defaults to the config (or opens your editor in execute mode if values are missing).
- `r.template` renders a template to disk with the provided context.
- `r.command` conditionally runs shell actions (`check` looks up a boolean in the context).

## Working with Assets

Assets keep non-text resources alongside templates.

```bash
# List assets
kt asset --project my-stack

# Add a binary asset
kt import --asset ./logo.png --project my-stack --name logo

# Use assets in recipes
r.assets("my-stack::logo", { destination = r.f("$(project.name)/public/logo.png") })
```

## Bundling & Sharing

Bundles pack everything needed to rehydrate a stack.

```bash
# Initialize a new project structure (optional)
kt init ./starter

# Create a .project archive from a folder
kt bundle ./starter --destination ./starter.project

# Import a received .project archive
kt import --bundle ./starter.project --overwrite
```

## End-to-End Example

1. Create project & import resources:

```bash
kt project add flask-app
kt template import ./app.j2 --project flask-app --name app
kt asset add logo --file ./logo.png --project flask-app
kt recipe import ./scaffold.lua --project flask-app --name scaffold
```

2. Generate config, edit, then execute:

```bash
kt recipe render scaffold --project flask-app --output ./flask-config.toml
${EDITOR:-vi} ./flask-config.toml
kt recipe render scaffold --project flask-app --config ./flask-config.toml
```

3. Share it:

```bash
kt project export flask-app --output ./flask-app.project
```

## Troubleshooting & Tips

- **Editor prompts**: Commands that open your editor respect `$EDITOR` and `$VISUAL`. Set one if you prefer a specific editor.
- **Overwrites**: Most commands default to safety. Pass `--overwrite` to replace existing files or DB entries.
- **Database location**: The SQLite file lives at `click.get_app_dir("kt")/kt.db` (platform-specific app data path).
- **Show help**: `kt <command> --help` prints options and subcommands (e.g., `kt template render --help`).
