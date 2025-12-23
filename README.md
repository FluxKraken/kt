# kt - The Project Scaffolder

`kt` is a project-oriented scaffolding tool that lets you combine Jinja2 templates, Lua recipes, and binary assets into reusable blueprints. It stores everything in a lightweight SQLite database (under your platform’s application data directory) and exposes a Click-based CLI for day-to-day work.

## Why kt?

- **Project-first organization**: Namespaces keep templates, recipes, and assets tidy for each stack (`fastapi`, `react`, `plugin`, etc.).
- **Lua recipe engine**: Recipes mix prompts, templating, filesystem actions, and shell commands with a compact DSL.
- **Interactive or file-driven config**: Generate TOML config skeletons, edit them, and run repeatable scaffolds.
- **One-file bundles**: Share whole stacks as `.project` archives that include metadata, recipes, templates, and assets.
- **Binary-friendly assets**: Ship icons, fonts, and other non-text files alongside templates.
- **Shell commands inside templates**: `{>command<}` tags capture shell output during rendering.

> [!WARNING] > `{>command<}` blocks can execute arbitrary shell commands, so be careful! Only execute templates from sources that you trust, and never run anything without verifying it first!!

## What lives where?

- **Data store**: SQLite database created under your app data directory. OS Appropriate Location, e.g. (~/Library/Application Support/kt) on MacOS.
- **Key resource types**:
  - Templates (Jinja2 extended with `{>command<}` shell command substitution.).
  - Recipes (Lua DSL; config/question/confirm → template render → command execution).
  - Assets (binary or text blobs).
- **Bundles**: `.project` archives containing `project.json`, `templates/`, `recipes/`, and `assets/`.

## Installation

Install with `uv`:

```bash
uv tool install https://github.com/FluxKraken/kt.git
```

After installing, you can invoke the CLI via `kt`.

## Core Workflow (Quick Tour)

1. **Initialize the local database** (creates `kt.db` under your app data dir):

   ```bash
   kt init
   ```

2. **Create a project namespace**:

   ```bash
   kt project add my-stack
   ```

3. **Import a Lua recipe and a template** (assigning them to the project):

   ```bash
   kt recipe import ./init.lua --project my-stack --name init
   kt template import ./service.j2 --project my-stack --name service
   ```

4. **Draft a config from the recipe’s prompts**:

   ```bash
   kt recipe render init --project my-stack --output config.toml
   ```

5. **Fill in `config.toml`** (the file is pre-populated with defaults declared in the recipe).

6. **Execute the scaffold**:

   ```bash
   kt recipe render init --project my-stack --config config.toml
   ```

7. **Bundle and share** everything as a single archive:

   ```bash
   kt project export my-stack --output ./my-stack.project
   ```

## Practical Examples

- **Render a template straight to disk** (prompts for missing values via your editor):

  ```bash
  kt template render service --project my-stack --output ./build/service.py
  ```

- **Generate a config skeleton for a template** (inspect required variables before rendering):

  ```bash
  kt template render service --project my-stack --gen-config ./service.defaults.toml
  ```

- **Copy a binary asset into your project**:

  ```bash
  kt asset add logo --file ./logo.png --project my-stack
  # later
  kt recipe render init --project my-stack --config config.toml
  ```

- **Expand a bundle you received** (without importing into the database):

  ```bash
  kt bundle expand ./starter.project ./unpacked --overwrite
  ```

## Documentation

- [User Guide](docs/user_guide.md): CLI walkthroughs, end-to-end flows, and bundling tips.
- [Recipe API](docs/recipe_api.md): Lua DSL reference with examples for every `r.*` helper.

## License

MIT
