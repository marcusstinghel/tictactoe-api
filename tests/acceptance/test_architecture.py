"""Static checks of the Clean Architecture rules (criteria AC-10 to AC-17).

Layers (inner -> outer): app.domain -> app.application -> app.infra / app.interface.
``app.container`` is the single composition root and may import every layer.
"""
import ast
import importlib
import inspect
import pkgutil

import pytest

from .support import ROOT

APP = ROOT / "app"


def _modules(package_dir):
    for path in sorted(package_dir.rglob("*.py")):
        rel = path.relative_to(ROOT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        yield ".".join(parts), path


def _imports(path, module_name):
    """Absolute names imported by a module (relative imports resolved)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    is_pkg = path.name == "__init__.py"
    package = module_name if is_pkg else module_name.rpartition(".")[0]
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            names.add(target)
            names.update(f"{target}.{alias.name}" for alias in node.names)
    return names


def _violations(layer_dir, forbidden_prefixes):
    found = []
    for module_name, path in _modules(layer_dir):
        for name in _imports(path, module_name):
            for prefix in forbidden_prefixes:
                if name == prefix or name.startswith(prefix + "."):
                    found.append(f"{path.relative_to(ROOT)} imports {name}")
    return sorted(set(found))


FRAMEWORKS = ["flask", "werkzeug", "sqlalchemy", "torch", "numpy", "dotenv"]


def test_domain_depends_on_nothing_outer():
    forbidden = ["app.application", "app.infra", "app.interface", "app.container", *FRAMEWORKS]
    assert _violations(APP / "domain", forbidden) == []


def test_application_depends_only_on_domain():
    forbidden = ["app.infra", "app.interface", "app.container", *FRAMEWORKS]
    assert _violations(APP / "application", forbidden) == []


def test_interface_does_not_import_infra():
    """Controllers/routes get use cases injected; only app.container wires infra."""
    assert _violations(APP / "interface", ["app.infra", "sqlalchemy", "torch", "dotenv"]) == []


def test_infra_does_not_import_interface():
    assert _violations(APP / "infra", ["app.interface", "app.container", "flask"]) == []


@pytest.mark.parametrize(
    "framework,allowed_dir",
    [("torch", "infra/ai"), ("sqlalchemy", "infra/db"), ("flask", "interface")],
)
def test_frameworks_are_confined_to_their_adapter(framework, allowed_dir):
    allowed = APP / allowed_dir
    offenders = []
    for module_name, path in _modules(APP):
        if allowed in path.parents:
            continue
        if any(n == framework or n.startswith(framework + ".") for n in _imports(path, module_name)):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_adapters_do_not_read_configuration_themselves():
    """Repositories and AI adapters receive engine/session and model path via constructor."""
    offenders = []
    for sub in ("infra/ai", "infra/db/repositories"):
        for module_name, path in _modules(APP / sub):
            imports = _imports(path, module_name)
            source = path.read_text(encoding="utf-8")
            if any(n.startswith("app.infra.settings") for n in imports) or "getenv" in source or "os.environ" in source:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_storage_detail_does_not_leak_into_ports():
    """The ML ports must not know about .pth files (path is an adapter detail)."""
    offenders = []
    for layer in ("domain", "application"):
        for _, path in _modules(APP / layer):
            if "pth" in path.read_text(encoding="utf-8").lower():
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def _abstract_ports():
    ports = []
    for layer in ("app.domain", "app.application"):
        package = importlib.import_module(layer)
        for info in pkgutil.walk_packages(package.__path__, layer + "."):
            module = importlib.import_module(info.name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module.__name__ and getattr(obj, "__abstractmethods__", None):
                    ports.append(obj)
    return ports


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


def _params(cls, name):
    """Parameter names of a method, without self/cls, looking through classmethod/staticmethod."""
    attr = inspect.getattr_static(cls, name)
    if isinstance(attr, staticmethod):
        return list(inspect.signature(attr.__func__).parameters)
    func = attr.__func__ if isinstance(attr, classmethod) else attr
    return list(inspect.signature(func).parameters)[1:]


def test_adapters_honour_port_signatures():
    package = importlib.import_module("app.infra")
    for info in pkgutil.walk_packages(package.__path__, "app.infra."):
        importlib.import_module(info.name)

    ports = _abstract_ports()
    assert ports, "expected abstract ports (repository/ML interfaces) in domain or application"
    mismatches = []
    implemented = 0
    for port in ports:
        for adapter in _all_subclasses(port):
            if not adapter.__module__.startswith("app.infra"):
                continue
            implemented += 1
            assert not getattr(adapter, "__abstractmethods__", None), f"{adapter} is still abstract"
            for name in port.__abstractmethods__:
                expected = _params(port, name)
                actual = _params(adapter, name)
                if expected != actual:
                    mismatches.append(f"{adapter.__name__}.{name}: port {expected} != adapter {actual}")
    assert implemented >= 4, "expected game/player repositories and the two ML adapters"
    assert mismatches == []


def test_adapters_are_instance_based_not_classmethod_singletons():
    """Class-level mutable state (cls.session, cls.__model) is not thread-safe."""
    offenders = []
    for sub in ("infra/ai", "infra/db/repositories"):
        for _, path in _modules(APP / sub):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setattr":
                    if node.args and isinstance(node.args[0], ast.Name) and node.args[0].id == "cls":
                        offenders.append(f"{path.relative_to(ROOT)}: setattr(cls, ...)")
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "cls":
                            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} cls.{target.attr} = ...")
    assert offenders == []


def test_domain_rules_raise_domain_errors():
    from app.domain import exceptions

    base = exceptions.DomainError
    subclasses = [obj for _, obj in inspect.getmembers(exceptions, inspect.isclass)
                  if issubclass(obj, base) and obj is not base]
    assert len(subclasses) >= 4


def test_no_swallowing_broad_excepts_in_app():
    """No ``except Exception``/bare except that does not re-raise (errors map in one place)."""
    offenders = []
    for _, path in _modules(APP):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"})
            reraises = any(isinstance(n, ast.Raise) for stmt in node.body for n in ast.walk(stmt))
            if broad and not reraises:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_composition_root_exists():
    container = importlib.import_module("app.container")
    assert hasattr(container, "build_container")
