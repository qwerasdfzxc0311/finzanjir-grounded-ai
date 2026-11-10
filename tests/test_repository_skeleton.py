from pathlib import Path


def test_repository_skeleton_contains_required_layers():
    required_paths = [
        "frontend",
        "backend",
        "shared",
        "data",
        "synthetic_data",
        "tests",
        "docs",
        "config",
        "contracts",
        "pyproject.toml",
    ]

    missing = [path for path in required_paths if not Path(path).exists()]
    assert not missing, f"Missing repository skeleton paths: {missing}"


def test_repository_skeleton_has_contract_and_documentation_entrypoints():
    required_files = [
        "contracts/architecture_v1.json",
        "docs/README.md",
        "config/README.md",
        "shared/README.md",
        "synthetic_data/README.md",
        "frontend/README.md",
        "backend/README.md",
    ]

    missing = [path for path in required_files if not Path(path).is_file()]
    assert not missing, f"Missing repository skeleton files: {missing}"
