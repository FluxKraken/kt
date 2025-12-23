-- sveltekit.recipe.lua
-- Host provides global `r` (recipe API). Recipes only build a step plan.

-- -----------------------------
-- Project Dependencies
-- -----------------------------
r.declare({
  dependencies = {
    prod = {
      "dotenv",
      "valibot",
      "drizzle-orm",
      "pg",
      "better-auth",
      "@iarna/toml",
      "marked",
      "runed",
      "bits-ui",
      "tailwind-variants",
      "tailwind-merge",
      "css-variants",
    },
    dev = {
      "@types/node",
      "@types/pg",
      "drizzle-kit",
      "tsx",
      "sass-embedded",
      "utopia-core-scss",
    },
  },
})

-- -----------------------------
-- Get Project Configuration
-- -----------------------------
r.config({
  project = {
    _comment = "Project Info",
    title       = { default = "SvelteKit Project", comment = "Project Title" },
    description = { default = "A SvelteKit Project", comment = "Project Description" },
    location    = { default = ".", comment = "Project Location" },
  },
  database = {
    _comment = "Postgres Database Info",
    name     = { default = "svelte" },
    username = { default = "admin" },
    password = { default = "password123" },
  },
  user = {
    name     = { default = "Svelte Admin" },
    username = { default = "admin" },
    email    = { default = "admin@example.com" },
    password = { default = "password123" },
  },
  container = {
    port = {
      external = { default = 3000 },
      internal = { default = 5173 },
    },
    prefix = { default = "svelte" },
  },
})

-- -----------------------------
-- Create .gitignore & README
-- -----------------------------
r.template("sveltekit::readme", {
  output = r.f("$(project.location)/README.md"),
  overwrite = true,
  context = {
    title = r.f("$(project.title)"),
    description = r.f("$(project.description)"),
  },
})

r.template("sveltekit::gitignore", {
  output = r.f("$(project.location)/.gitignore"),
  overwrite = true,
})

-- -----------------------------
-- Assets (copy)
-- -----------------------------
r.assets("sveltekit::logo.png", {
  destination = r.f("$(project.location)/src/lib/assets/logo.png"),
  overwrite = true,
})

-- -----------------------------
-- Create Git Repository (optional)
-- -----------------------------
if r.confirm({ prompt = "Create Git Repository?", default = true, store = "git" }) then
  r.run({ "git", "init" }, { cwd = r.ref("project.location") })
  r.run({ "git", "-C", r.f("$(project.location)"), "add", ".gitignore", "README.md" })
  r.run({ "git", "-C", r.f("$(project.location)"), "commit", "-m", "Initial Commit" })
end

-- -----------------------------
-- Generate SvelteKit Project
-- -----------------------------
r.run({
  "npx", "sv", "create",
  "--template", "minimal",
  "--types", "ts",
  "--add", "sveltekit-adapter=adapter:node",
  "--add", "tailwindcss=plugins:none",
  "--install", "npm",
  r.f("$(project.location)"),
})

if r.ref("git") then
  r.run({ "git", "-C", r.f("$(project.location)"), "add", "." })
  r.run({ "git", "-C", r.f("$(project.location)"), "commit", "-m", "Generate SvelteKit Project" })
end

-- -----------------------------
-- Install Project Dependencies
-- -----------------------------
r.run({ "npm", "--prefix", r.f("$(project.location)"), "install", r.splice("dependencies.prod") })
r.run({ "npm", "--prefix", r.f("$(project.location)"), "install", "--save-dev", r.splice("dependencies.dev") })

if r.ref("git") then
  r.run({ "git", "-C", r.f("$(project.location)"), "add", "." })
  r.run({ "git", "-C", r.f("$(project.location)"), "commit", "-m", "Update Project Dependencies" })
end

-- -----------------------------
-- Configure Project
-- -----------------------------
r.template("sveltekit::svelte.config.js", {
  output = r.f("$(project.location)/svelte.config.js"),
  overwrite = true,
})

r.template("sveltekit::compose", {
  output = r.f("$(project.location)/docker-compose.yml"),
  overwrite = true,
  context = {
    port = {
      external = r.ref("container.port.external"),
      internal = r.ref("container.port.internal"),
    },
    prefix = r.ref("container.prefix"),
    database = {
      name = r.ref("database.name"),
      username = r.ref("database.username"),
      password = r.ref("database.password"),
    },
  },
})

r.template("sveltekit::dockerfile", {
  output = r.f("$(project.location)/Dockerfile"),
  overwrite = true,
})

r.template("sveltekit::env", {
  output = r.f("$(project.location)/.env"),
  overwrite = true,
  context = {
    database = {
      name = r.ref("database.name"),
      username = r.ref("database.username"),
      password = r.ref("database.password"),
    },
    user = {
      name = r.ref("user.name"),
      username = r.ref("user.username"),
      email = r.ref("user.email"),
      password = r.ref("user.password"),
    },
    url = r.ref("base_url"),
  },
})

if r.ref("git") then
  r.run({ "git", "-C", r.f("$(project.location)"), "add", "." })
  r.run({ "git", "-C", r.f("$(project.location)"), "commit", "-m", "Configure Project & Set up docker dev environment" })
end
