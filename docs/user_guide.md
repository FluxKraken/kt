# kt User Guide

`kt` is a project-oriented scaffolding system. It helps you manage and apply templates, recipes, and assets to create new projects or enhance existing ones.

## Concepts

- **Project**: A namespace that groups templates, recipes, and assets (e.g., "sveltekit", "fastapi").
- **Template**: A text file (Jinja2) used to generate code/config files.
- **Recipe**: A Lua script that defines a workflow (prompting, rendering, running commands).
- **Asset**: A static file (image, binary) to be copied.
- **Bundle**: A `.project` archive containing a project and all its resources.

## CLI Core Commands

### Initialization

Initialize the database (run once):

```bash
kt init
```

### Project Management

Projects help organize your resources.

```bash
# List all projects
kt project list

# Add a new project
kt project add [name]

# Delete a project (recursively deletes resources)
kt project delete [name] --recursive

# Import a project bundle
kt project import ./myproject.project --overwrite

# Export a project bundle
kt project export [name] --output ./myproject.project
```

### Resource Management

All resource commands support a `--project [name]` flag to assign them to a specific project.

#### Templates

Jinja2 templates used by recipes.

```bash
kt template list --project [name]
kt template add [name] --project [name] # Opens editor
kt template import [path] --project [name]
kt template render [name] --project [name] --output [path]
# With config
kt template render [name] --project [name] --config config.toml --output [path]
# Generate config skeleton
kt template render [name] --project [name] --gen-config skeleton.toml
```

#### Assets

Static files (logos, binaries).

```bash
kt asset list --project [name]
kt asset add [name] --file [path] --project [name]
```

#### Recipes

Lua scripts that drive the scaffolding process.

```bash
kt recipe list --project [name]
kt recipe add [name] --project [name] # Opens editor
kt recipe import [path] --project [name]
```

## Running Recipes

The core power of `kt` is executing recipes.

### 1. Generate Configuration

First, generate a TOML configuration file based on the queries defined in the recipe.

```bash
kt recipe render [name] --project [project] --output config.toml
```

### 2. Edit Configuration

Open `config.toml` and fill in the required values (e.g., project name, database credentials).

### 3. Execute

Run the recipe using the filled configuration.

```bash
kt recipe render [name] --project [project] --config config.toml
```

If you don't provide a config file, `kt` will attempt to prompt you interactively or use defaults, but the two-step process is recommended for complex setups.
