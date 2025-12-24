r.config({
    name = { default = "Flux Kraken" },
    age = { default = 30 },
}, { template = "sv::config.toml" })

print("Config generation test complete.")
