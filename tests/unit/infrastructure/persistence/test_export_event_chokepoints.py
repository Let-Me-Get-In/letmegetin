"""Unit: every PlaceModel writer in infrastructure/persistence also journals its write.

The scan is structural, over the source (AST), with no import and no database: a future
write path that forgets ``_append_export_event`` fails here before it can reach production
(D-08, T-14-01).
"""

from __future__ import annotations

import ast
from pathlib import Path

from letmegetin.infrastructure.persistence import __path__ as persistence_path

_PACKAGE = Path(next(iter(persistence_path)))
_APPEND_CALLS = {"_append_export_event", "_append_export_events"}
_MODEL_LOOKUPS = {"get", "scalar", "scalars"}

_Function = ast.FunctionDef | ast.AsyncFunctionDef


def _contains_place_model(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Name) and child.id == "PlaceModel" for child in ast.walk(node))


def _place_bindings(function: _Function) -> set[str]:
    """Local names bound to a PlaceModel instance (constructor, get, or a select)."""
    names: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        if isinstance(value, ast.Await):
            value = value.value
        if not isinstance(value, ast.Call):
            continue
        is_constructor = isinstance(value.func, ast.Name) and value.func.id == "PlaceModel"
        is_lookup = (
            isinstance(value.func, ast.Attribute)
            and value.func.attr in _MODEL_LOOKUPS
            and any(_contains_place_model(arg) for arg in value.args)
        )
        if is_constructor or is_lookup:
            names.add(target.id)
    return names


def _writes_place(function: _Function, bindings: set[str]) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add" and node.args:
                argument = node.args[0]
                if isinstance(argument, ast.Call) and _contains_place_model(argument):
                    return True
                if isinstance(argument, ast.Name) and argument.id in bindings:
                    return True
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in {"insert", "update", "delete"}
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "PlaceModel"
            ):
                return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in bindings
                ):
                    return True
    return False


def _calls_append(function: _Function) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _APPEND_CALLS
        for node in ast.walk(function)
    )


def scan(source: str) -> tuple[set[str], set[str]]:
    """``(writers, appenders)`` as ``Class.method`` names across every class of a module."""
    writers: set[str] = set()
    appenders: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = f"{node.name}.{member.name}"
            if _writes_place(member, _place_bindings(member)):
                writers.add(name)
            if _calls_append(member):
                appenders.add(name)
    return writers, appenders


def _package_scan() -> tuple[set[str], set[str]]:
    writers: set[str] = set()
    appenders: set[str] = set()
    for path in sorted(_PACKAGE.glob("*.py")):
        module_writers, module_appenders = scan(path.read_text(encoding="utf-8"))
        writers |= module_writers
        appenders |= module_appenders
    return writers, appenders


def test_every_place_writer_appends_a_journal_event() -> None:
    writers, appenders = _package_scan()

    assert {"SqlAlchemyPlaceRepository.add", "SqlAlchemyPlaceRepository.update"} <= writers
    assert writers <= appenders, (
        f"PlaceModel writers without a journal append: {writers - appenders}"
    )


def test_a_new_writer_method_without_an_append_is_reported() -> None:
    source = """
class SqlAlchemyPlaceRepository:
    async def touch(self, place_id):
        await self._session.execute(
            update(PlaceModel).where(PlaceModel.id == place_id).values(operating_status="open")
        )
"""

    writers, appenders = scan(source)

    assert writers == {"SqlAlchemyPlaceRepository.touch"}
    assert not writers <= appenders


def test_a_loaded_model_mutation_without_an_append_is_reported() -> None:
    source = """
class SqlAlchemyPlaceRepository:
    async def touch(self, place_id):
        model = await self._session.get(PlaceModel, place_id)
        model.category_id = 1
"""

    writers, appenders = scan(source)

    assert writers == {"SqlAlchemyPlaceRepository.touch"}
    assert not writers <= appenders
