# Recipe DSL Grammar & Semantics

This document defines the syntax and execution semantics of the **Recipe DSL**, used to declaratively describe project scaffolding workflows.

---

## 1. File Structure & Execution Model

A project using this system is expected to contain:

```
recipes/    # Recipe files (this DSL)
templates/  # Jinja2 templates
assets/     # Static files copied into generated projects
```

A recipe is executed **top-to-bottom**, block-by-block.

All variables exist in a **single shared scope** unless otherwise stated.

---

## 2. Lexical Elements

### 2.1 Whitespace & Indentation
- Indentation is **semantic**, similar to Python.
- Tabs and spaces must not be mixed.
- Leading whitespace inside `[...]` is ignored.
- Line breaks inside `[...]` are treated as spaces.

### 2.2 Comments
- Lines starting with `#` are comments.
- Inline comments are not supported.

### 2.3 Identifiers & Paths

```
identifier := [A-Za-z_][A-Za-z0-9_]*
path       := identifier ("." identifier)*
```

Examples:
```
project.title
container.port.external
```

---

## 3. Blocks

```
block := block_name [ "(" block_parameters ")" ] ":" newline indented_block
```

Supported blocks:
- `declare`
- `prompt`
- `template`
- `command`
- `assets`

Unknown block names are errors.

All blocks may accept a `check` gate parameter.

---

## 4. Object Statements

```
object_statement := "[" object_target "]" [ "(" parameter_list ")" ] [ ":" ]
```

- The meaning of `object_target` depends on the enclosing block.
- A trailing `:` indicates child objects follow.

---

## 5. Parameter Lists

```
parameter_list := parameter ( "," parameter )*
parameter      := identifier "=" value
```

- Parameters must be comma-separated
- Trailing commas are allowed
- Unknown parameters are errors

---

## 6. Values & Literals

### 6.1 Strings
- Must use double quotes
- Backslash escaping is supported
- Single quotes are allowed inside strings

### 6.2 Numbers
- Integers supported

### 6.3 Lists

```
list := "{" [ value ( "," value )* ] "}"
```

Properties:
- Order preserved
- Duplicates allowed
- Trailing commas allowed
- Multiline allowed

### 6.4 Variable Interpolation

```
$(path)
```

Rules:
- `$()` always refers to recipe variables
- Missing variables cause errors
- `$HOME` style shell variables are passed through untouched

### 6.5 List Expansion

If a list variable is interpolated into a command, it expands into argv entries.

---

## 7. Block Semantics

---

## 7.1 `declare` Block

Assigns variables.

```
declare:
    [path] ( value )
```

Parent objects are auto-created.

---

## 7.2 `prompt` Block

Defines user input collected via an editor-opened TOML file.

Supported parameters:
- `default`
- `comment`

---

## 7.3 `template` Block

Renders Jinja2 templates.

```
template:
    [namespace::template] (
        output = "path",
        overwrite = true,
        context = { ... }
    )
```

Context is a nested object.

---

## 7.4 `command` Block

Executes system commands.

```
command (check = "var"):
    [command words...] (cwd=..., envs=..., env_file=...)
```

### Command Parsing Rules
- Split on spaces
- Double quotes group tokens
- No globbing or piping
- Shell behavior requires `sh -lc`

---

## 7.5 `gate` Statement

Valid only inside `command` blocks.

```
gate (prompt = "Question?", store = "variable")
```

Stores a boolean value.

---

## 7.6 `assets` Block

Copies files or directories from the `assets/` folder into the target project.

```
assets (check = "var"):
    [namespace::asset_path] (
        destination = "path",
        overwrite = true
    )
```

### Parameters
| Parameter | Type | Required | Description |
|---------|------|----------|-------------|
| `destination` | string | yes | Target path |
| `overwrite` | bool | no | Default false |

### Semantics
- Source paths are resolved relative to the `assets/` directory
- Files or directories are copied recursively
- Missing sources cause errors
- Obeys `check` gating rules

---

## 8. Error Handling

- Unknown blocks → error
- Unknown parameters → error
- Missing interpolation variables → error
- Missing gate check variables → error
- Invalid syntax → error

No silent failures are permitted.

---

## 9. Design Guarantees

- Deterministic execution
- Explicit data flow
- No implicit shell behavior
- Human-readable DSL
- Naturally extensible
