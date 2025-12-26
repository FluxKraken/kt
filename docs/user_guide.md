# kt User Guide

This guide covers how to install `kt`, organize projects, and use every CLI feature. If you’re brand new to `kt`, start with the tutorial.

## Table of contents

- [Concepts](#concepts)
- [Installation](#installation)
- [Where data lives](#where-data-lives)
- [Beginner tutorial](#beginner-tutorial)
- [Templates](#templates)
- [Assets](#assets)
- [Recipes](#recipes)
- [Bundles and on-disk projects](#bundles-and-on-disk-projects)
- [Command reference](#command-reference)

## Concepts

`kt` manages four core resource types:

- **Project**: A namespace that groups templates, recipes, and assets.
- **Template**: A Jinja2 file stored in the database.
- **Recipe**: A Lua script that can prompt, render templates, copy assets, and run commands.
- **Asset**: A binary or text file stored in the database.

`kt` can also work with **on-disk projects**: a folder containing `project.json`, `templates/`, `recipes/`, and `assets/`.

## Installation

`kt` is distributed as a Python CLI (requires Python 3.14+).

```bash
uv tool install https://github.com/FluxKraken/kt.git
kt --help
```

## Where data lives

`kt` stores its SQLite database in your OS-specific app data directory:

- Path is `click.get_app_dir("kt")/kt.db`
- The directory is created on first run

## Beginner tutorial

This tutorial shows a full flow: create a project, add a template and recipe, generate a config file, and scaffold files.

### 1. Create a project

```bash
kt new --project hello
```

### 2. Create a template

Create a template file on disk:

`app.j2`
```jinja
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"name": "{{ app.name }}", "port": {{ app.port }}}
```

Import it into `kt`:

```bash
kt import --template app --file ./app.j2 --project hello
```

### 3. Create a recipe

`scaffold.lua`
```lua
r.config({
  app = {
    name = { default = "hello-service" },
    port = { default = 8000 }
  }
})

r.mkdir("$(app.name)", { parents = true })

r.template("hello::app", {
  destination = r.f("$(app.name)/main.py"),
  context = {
    app = {
      name = r.ref("app.name"),
      port = r.ref("app.port")
    }
  }
})
```

Import it and set it as the default recipe:

```bash
kt import --recipe scaffold --file ./scaffold.lua --project hello
kt recipe scaffold --project hello --set-default
```

### 4. Generate a config file

```bash
kt r hello --create-config ./config.toml
$EDITOR ./config.toml
```

### 5. Execute the recipe

```bash
kt r hello --config ./config.toml
```

You should now have a `hello-service/main.py` generated from the template.

## Templates

Templates are stored in the database and rendered via Jinja2. You can also run shell commands inside templates using `{>command<}` tags.

Example template:

```jinja
SECRET_KEY = "{>openssl rand -base64 32<}"
PROJECT = "{{ project.name }}"
```

Render a template:

```bash
kt template app --project hello --destination ./output/app.py
```

Generate a config skeleton for template variables:

```bash
kt template app --project hello --create-config ./template.toml
```

## Assets

Assets are binary or text files stored in the database. Recipes can copy assets into generated projects.

Import and copy an asset:

```bash
kt import --asset logo --file ./logo.png --project hello
kt asset logo --project hello --destination ./build/logo.png
```

## Recipes

Recipes are Lua scripts that use the `r` API. They can:

- declare defaults (`r.config`, `r.declare`)
- prompt (`r.question`, `r.confirm`)
- render templates (`r.template`)
- copy assets (`r.asset`)
- run commands (`r.run`, `r.eval`)
- manage files and directories (`r.touch`, `r.mkdir`, `r.delete`)
- call other recipes (`r.recipe`)

See the full [Recipe API](recipe_api.md) for every method and options.

## Bundles and on-disk projects

`kt` supports bundling projects in two ways:

- **Database projects**: Export a database project into a `.project` archive.
- **On-disk projects**: Bundle a folder that contains `project.json`, `templates/`, `recipes/`, and `assets/`.

Initialize a new on-disk project structure:

```bash
kt init ./starter
```

This creates:

```
starter/
  project.json
  templates/
  recipes/
  assets/
  misc/
```

To bundle an on-disk project:

```bash
kt bundle ./starter --destination ./starter.project
```

To import a bundle into the database:

```bash
kt import --bundle ./starter.project
```

## Command reference

### `kt list`

Show a summary of unassigned resources and projects:

```bash
kt list
```

List a specific resource type:

```bash
kt list --type project
kt list --type template --project hello
kt list --type recipe --project hello
kt list --type asset --project hello
```

### `kt project`

Manage projects stored in the database.

```bash
kt project list
kt project add hello
kt project delete hello --recursive
```

Set a default recipe:

```bash
kt project default hello --recipe scaffold
```

Render a project’s default recipe:

```bash
kt project render hello --output ./config.toml
kt project render hello --config ./config.toml
```

Import or export a project:

```bash
kt project import ./starter.project
kt project import ./starter --overwrite
kt project import https://example.com/repo.git --git

kt project export hello --output ./hello.project
```

Unassign resources from a project:

```bash
kt project unassign hello --template app
```

### `kt new`

Create new empty resources in the database:

```bash
kt new --project hello
kt new --template app --project hello
kt new --recipe scaffold --project hello
kt new --asset logo --project hello
```

### `kt import`

Import resources into the database:

```bash
kt import --template app --file ./app.j2 --project hello
kt import --recipe scaffold --file ./scaffold.lua --project hello
kt import --asset logo --file ./logo.png --project hello
```

Import a project from a bundle, directory, or Git repository:

```bash
kt import --bundle ./starter.project
kt import --dir ./starter --overwrite
kt import --git https://example.com/repo.git
```

### `kt edit`

Edit recipes or templates in your `$EDITOR`:

```bash
kt edit --recipe scaffold --project hello
kt edit --template app --project hello
```

### `kt assign` and `kt unassign`

Assign or unassign resources to/from projects:

```bash
kt assign --template app --project hello
kt unassign --recipe scaffold --project hello
```

### `kt delete`

Delete a resource or project:

```bash
kt delete --template app --project hello
kt delete --project hello --recursive
```

### `kt template`

List templates or render one to disk:

```bash
kt template --project hello
kt template app --project hello --destination ./output/app.py
kt template app --project hello --create-config ./template.toml
```

### `kt asset`

List assets or copy one to disk:

```bash
kt asset --project hello
kt asset logo --project hello --destination ./output/logo.png
```

### `kt recipe`

List recipes, execute one, or generate a config file:

```bash
kt recipe --project hello
kt recipe scaffold --project hello --create-config ./config.toml
kt recipe scaffold --project hello --config ./config.toml
```

Set the default recipe for a project:

```bash
kt recipe scaffold --project hello --set-default
```

Generate config files in YAML:

```bash
kt recipe scaffold --project hello --create-config ./config.yaml --format yaml
```

### `kt r`

Execute the default recipe for a project:

```bash
kt r hello --create-config ./config.toml
kt r hello --config ./config.toml
```

If run inside an on-disk project (folder with `project.json`), you can omit the project name:

```bash
kt r --create-config ./config.toml
```

### `kt init`

Initialize an on-disk project structure:

```bash
kt init ./starter
kt init ./starter --set-default scaffold
```

### `kt bundle`

Bundle an on-disk project into a `.project` archive:

```bash
kt bundle ./starter --destination ./starter.project
```

## Safety notes

- `{>command<}` template tags and `r.eval` execute shell commands. Only use trusted templates and recipes.
- Recipe `r.run` executes commands directly and will fail the recipe if the command exits non-zero.
