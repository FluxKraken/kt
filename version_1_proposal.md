# Path to Version 1 - Proposed Changes - Command Line Interface

In order to get this project ready for version 1, there needs to be a few changes.

The first step is to standardize the command line interface.

## kt command

>*When run with no arguments, it should list all available commands.*

Regarding database initialization, instead of an explicit `init` command to initialize the database, this should be done automatically whenever the command is run and the database is missing.  The init command will be used to initialize a new project instead.

### r [project_name] [options] [arguments]

>*Executes the default recipe for the specified project.*

#### Options

- --create-config [config_path]

>*Creates a new config file at the specified path.*

- --config [config_path]

>*Uses the specified config file.*

#### Examples

`kt r svelte --create-config flux.toml`

- Creates a config file for the default recipe of the svelte project.

`kt r svelte --config flux.toml`

- Uses the config file to render the default recipe of the svelte project.

`kt r add-types`

- Renders the default recipe of the add-types project.  The default recipe of this project does not use a config file.

### import [type] [identifier]

>*Imports a project from the [type] using the [identifier].*

#### Importing a Project

- --git [git_url]
- --bundle [bundle_path]
- --dir [dir_path]
- --url [url_to_bundle]

#### Importing other types

>*For these import types, the project name is optional, the name and file path are required.*

- --recipe [recipe_name] --file [recipe_path] --project [project_name]
- --template [template_name] --file [template_path] --project [project_name]
- --asset [asset_name] --file [asset_path] --project [project_name]

### init [path]

>*Initializes a new project at the specified path.*

### bundle [path] --destination [destination_path]

>*Bundles the project at the specified path.*

The *.project file will be output to the destination path.

Example: `kt bundle . --destination ../svelte.project`

### new --[type] [name] --project [project_name]

>*Creates a new object of the specified type with the specified name, optionally assignes to the named project.*

- --project [project_name]
- --recipe [recipe_name] --project [project_name]
- --template [template_name] --project [project_name]
- --asset [asset_name] --project [project_name]

### recipe [recipe_name] --project [project_name] --[options] [arguments]

>*Executes the specified recipe.*

If the project name is specified, the recipe will be executed from that project.  Otherwise it will be from the unassigned recipe list.

#### Options

- --create-config [config_path]

>*Creates a new config file at the specified path.*

- --config [config_path]

>*Runs the recipe with the specified config file.*

### template [template_name] --destination [destination_path] --project [project_name] --[options] [arguments] --overwrite

>*Render's the specified template.*

If the project name is specified, the template will be rendered from that project.  Otherwise it will be from the unassigned template list.

If the overwrite flag is specified, the destination file will be overwritten if it already exists.

#### Options

- --create-config [config_path]

>*Creates a new config file at the specified path.*

- --config [config_path]

>*Renders the template with the specified config file.*

### asset [asset_name] --destination [destination_path] --project [project_name] --overwrite

>*Copies the specified asset to the destination path.*

If the project name is specified, the asset will be copied from that project.  Otherwise it will be from the unassigned asset list.

If the overwrite flag is specified, the destination file will be overwritten if it already exists.

### assign --[type] [name] --project [project_name]

>*Assigns the specified object to the specified project.*

### unassign --[type] [name] --project [project_name]

>*Unassigns the specified object from the specified project.*

### delete --[type] [name] --project [project_name] --recursive

>*Deletes the specified object from the specified project.*

#### types

- --asset [asset_name] --project [project_name]
- --template [template_name] --project [project_name]
- --recipe [recipe_name] --project [project_name]
- --project [project_name] --recursive

In the case of type --project, the specified project will be deleted, and all objects assigned to the project will be unassigned.  In the case of name conflicts, the user will be prompted to provide new names for each conflicting object.

If the recursive flag is specified, the project will be deleted recursively, and all objects assigned to the project will be deleted as well.
