---@meta

---@class RecipeAPI
---@field declare fun(table: table) Declare initial variables. Useful for defaults that should exist even before prompting.
---@field config fun(table: table) Define configuration schema and defaults. Used for `kt recipe render --output` to generate TOML.
---@field question fun(table: table): string Ask the user for text input. Returns the user's answer.
---@field confirm fun(table: table): boolean Ask for a yes/no confirmation. Returns true if confirmed.
---@field template fun(name: string, table: table) Render a stored Jinja2 template to a file.
---@field asset fun(name: string, table: table) Copy a binary/text asset.
---@field eval fun(command: string): string Execute a shell command and return the output.
---@field run fun(args: (string|table)[], options?: table) Run a subprocess.
---@field touch fun(path: string, options?: table) Create a file with optional content.
---@field mkdir fun(path: string, options?: table) Create a directory.
---@field delete fun(path: string) Delete a file or directory recursively.
---@field recipe fun(name: string, options?: table) Execute another recipe.
---@field f fun(str: string): string Format using `$(var.path)` substitution from context.
---@field ref fun(path: string): any Read a context value (returns `""` if missing).
---@field splice fun(path: string): table Return a list-like value suitable for spreading into commands.

---@type RecipeAPI
r = {}
