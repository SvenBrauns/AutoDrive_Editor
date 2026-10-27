import importlib.util

from autodrive_editor.paths import PROJECT_ROOT


def load_packaging_script(name: str):
    """Loaded from its path: "packaging" is also the name of an installed library."""

    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "packaging" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
