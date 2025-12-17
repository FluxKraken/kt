# kt - The Project Scaffolder

`kt` is a powerful, project-oriented scaffolding system designed to help developers create and manage reusable project blueprints. It combines Jinja2 templates, Lua-based recipes, and static assets into a unified workflow.

## Features

- **Project-Oriented**: Organize templates and recipes by project (e.g., `django`, `react`, `library`).
- **Lua Recipes**: Define complex initialization logic using a simple Lua DSL.
- **Interactive Configuration**: Generate configuration files from recipes, edit them, and then apply.
- **Bundling**: Export entire project setups as single `.project` files for easy sharing.
- **Asset Management**: Handle binary assets (images, fonts) alongside text templates.

## Installation

Using `uv`:

```bash
uv sync
uv run kt init
```

## Quick Start

1.  **Create a Project Context**

    ```bash
    kt project add my-stack
    ```

2.  **Add a Recipe**

    ```bash
    kt recipe import ./init.lua --project my-stack --name init
    ```

3.  **Generate Config**

    ```bash
    kt recipe render init --project my-stack --output config.toml
    ```

4.  **Run Scaffolding**
    ```bash
    kt recipe render init --project my-stack --config config.toml
    ```

## Documentation

- [User Guide](docs/user_guide.md): Detailed CLI usage command reference.
- [Recipe API](docs/recipe_api.md): Lua DSL reference for writing recipes.

## License

MIT
