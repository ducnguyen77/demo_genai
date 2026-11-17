
$folders = @(
    "src/demo_genai/llm",
    "src/demo_genai/rag",
    "src/demo_genai/services",
    "src/demo_genai/api",
    "src/demo_genai/config",
    "scripts",
    "tests/unit",
    "tests/integration",
    "tests/evaluation",
    "data/sample",
    "notebooks",
    ".github/workflows"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
}

$packages = @(
    "src/demo_genai",
    "src/demo_genai/llm",
    "src/demo_genai/rag",
    "src/demo_genai/services",
    "src/demo_genai/api",
    "src/demo_genai/config"
)

foreach ($package in $packages) {
    New-Item -ItemType File -Force -Path "$package/__init__.py" | Out-Null
}

New-Item -ItemType File -Force -Path "pyproject.toml", ".env.example" | Out-Null
