#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "docs" / "source" / "api" / "generated"
SOURCE_DIRS = (
    REPO_ROOT / "pyssp",
    REPO_ROOT / "scripts",
    REPO_ROOT / "spleeter-cli",
)


@dataclass(frozen=True)
class MemberDoc:
    kind: str
    name: str
    signature: str
    lineno: int
    summary: str
    detail: str = ""
    children: tuple["MemberDoc", ...] = ()


@dataclass(frozen=True)
class ModuleDoc:
    rel_path: Path
    title: str
    module_path: str
    summary: str
    docstring: str
    classes: tuple[MemberDoc, ...]
    functions: tuple[MemberDoc, ...]
    constants: tuple[MemberDoc, ...]
    page_path: Path


@dataclass
class DirNode:
    rel_dir: Path
    subdirs: list[Path] = field(default_factory=list)
    modules: list[ModuleDoc] = field(default_factory=list)
    package_module: ModuleDoc | None = None


def _clean_text(value: str) -> str:
    return inspect.cleandoc(value or "").strip()


def _summary_from_docstring(value: str) -> str:
    cleaned = _clean_text(value)
    for line in cleaned.splitlines():
        token = line.strip()
        if token:
            return token
    return ""


def _is_valid_module_path(path: Path) -> bool:
    return all(part.isidentifier() for part in path.parts)


def _module_path_for(rel_path: Path) -> str:
    if rel_path.name == "__init__.py":
        base = rel_path.parent
    else:
        base = rel_path.with_suffix("")
    if not base.parts:
        return ""
    return ".".join(base.parts) if _is_valid_module_path(base) else ""


def _format_annotation(node: ast.AST | None) -> str:
    if node is None:
        return ""
    return ast.unparse(node).strip()


def _format_constant_value(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        rendered = ast.unparse(node).strip()
    except Exception:
        return ""
    if len(rendered) > 80:
        return rendered[:77] + "..."
    return rendered


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    parts: list[str] = []
    positional = list(args.posonlyargs) + list(args.args)
    positional_defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    posonly_cutoff = len(args.posonlyargs)
    for index, argument in enumerate(positional):
        chunk = argument.arg
        annotation = _format_annotation(argument.annotation)
        if annotation:
            chunk += f": {annotation}"
        default_node = positional_defaults[index]
        if default_node is not None:
            chunk += f" = {_format_constant_value(default_node)}"
        parts.append(chunk)
        if index + 1 == posonly_cutoff and posonly_cutoff > 0:
            parts.append("/")
    if args.vararg is not None:
        chunk = f"*{args.vararg.arg}"
        annotation = _format_annotation(args.vararg.annotation)
        if annotation:
            chunk += f": {annotation}"
        parts.append(chunk)
    elif args.kwonlyargs:
        parts.append("*")
    for argument, default_node in zip(args.kwonlyargs, args.kw_defaults):
        chunk = argument.arg
        annotation = _format_annotation(argument.annotation)
        if annotation:
            chunk += f": {annotation}"
        if default_node is not None:
            chunk += f" = {_format_constant_value(default_node)}"
        parts.append(chunk)
    if args.kwarg is not None:
        chunk = f"**{args.kwarg.arg}"
        annotation = _format_annotation(args.kwarg.annotation)
        if annotation:
            chunk += f": {annotation}"
        parts.append(chunk)
    rendered = f"{node.name}(" + ", ".join(parts) + ")"
    returns = _format_annotation(node.returns)
    if returns:
        rendered += f" -> {returns}"
    if isinstance(node, ast.AsyncFunctionDef):
        rendered = "async " + rendered
    return rendered


def _member_kind_for_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    decorators = {_format_annotation(item) for item in node.decorator_list}
    if "property" in decorators:
        return "property"
    if "classmethod" in decorators:
        return "classmethod"
    if "staticmethod" in decorators:
        return "staticmethod"
    return "method" if node.name != "__init__" else "constructor"


def _collect_class_children(node: ast.ClassDef) -> tuple[MemberDoc, ...]:
    children: list[MemberDoc] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(item) or ""
            children.append(
                MemberDoc(
                    kind=_member_kind_for_function(item),
                    name=item.name,
                    signature=_format_signature(item),
                    lineno=int(item.lineno),
                    summary=_summary_from_docstring(docstring),
                    detail=_clean_text(docstring),
                )
            )
    return tuple(sorted(children, key=lambda child: child.lineno))


def _collect_class(node: ast.ClassDef) -> MemberDoc:
    bases = ", ".join(_format_annotation(base) for base in node.bases if _format_annotation(base))
    detail = f"Bases: {bases}" if bases else ""
    docstring = ast.get_docstring(node) or ""
    return MemberDoc(
        kind="class",
        name=node.name,
        signature=node.name,
        lineno=int(node.lineno),
        summary=_summary_from_docstring(docstring),
        detail=detail,
        children=_collect_class_children(node),
    )


def _collect_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> MemberDoc:
    docstring = ast.get_docstring(node) or ""
    return MemberDoc(
        kind="function",
        name=node.name,
        signature=_format_signature(node),
        lineno=int(node.lineno),
        summary=_summary_from_docstring(docstring),
        detail=_clean_text(docstring),
    )


def _collect_constant(node: ast.Assign | ast.AnnAssign) -> Iterable[MemberDoc]:
    targets: list[tuple[str, ast.AST | None]] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append((target.id, node.value))
    elif isinstance(node.target, ast.Name):
        targets.append((node.target.id, node.value))
    for name, value in targets:
        if name.startswith("_") or not name.isupper():
            continue
        detail = _format_constant_value(value)
        yield MemberDoc(
            kind="constant",
            name=name,
            signature=name,
            lineno=int(node.lineno),
            summary="",
            detail=f"Value: {detail}" if detail else "",
        )


def _page_path_for(rel_path: Path) -> Path:
    if rel_path.name == "__init__.py":
        return OUTPUT_ROOT / rel_path.parent / "index.md"
    if len(rel_path.parts) == 1:
        return OUTPUT_ROOT / "root" / f"{rel_path.stem}.md"
    return OUTPUT_ROOT / rel_path.with_suffix(".md")


def _title_for(rel_path: Path) -> str:
    return rel_path.parent.as_posix() + "/" if rel_path.name == "__init__.py" else rel_path.as_posix()


def _parse_module(path: Path) -> ModuleDoc:
    rel_path = path.relative_to(REPO_ROOT)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_docstring = ast.get_docstring(tree) or ""
    classes: list[MemberDoc] = []
    functions: list[MemberDoc] = []
    constants: list[MemberDoc] = []
    for item in tree.body:
        if isinstance(item, ast.ClassDef):
            classes.append(_collect_class(item))
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_collect_function(item))
        elif isinstance(item, (ast.Assign, ast.AnnAssign)):
            constants.extend(_collect_constant(item))
    return ModuleDoc(
        rel_path=rel_path,
        title=_title_for(rel_path),
        module_path=_module_path_for(rel_path),
        summary=_summary_from_docstring(module_docstring),
        docstring=_clean_text(module_docstring),
        classes=tuple(sorted(classes, key=lambda item: item.lineno)),
        functions=tuple(sorted(functions, key=lambda item: item.lineno)),
        constants=tuple(sorted(constants, key=lambda item: item.lineno)),
        page_path=_page_path_for(rel_path),
    )


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    files.extend(sorted(REPO_ROOT.glob("*.py")))
    for source_dir in SOURCE_DIRS:
        if source_dir.exists():
            files.extend(sorted(source_dir.rglob("*.py")))
    return sorted(files)


def _build_tree(modules: list[ModuleDoc]) -> dict[Path, DirNode]:
    nodes: dict[Path, DirNode] = {}

    def ensure_node(rel_dir: Path) -> DirNode:
        node = nodes.get(rel_dir)
        if node is None:
            node = DirNode(rel_dir=rel_dir)
            nodes[rel_dir] = node
        return node

    ensure_node(Path("."))
    for module in modules:
        rel_path = module.rel_path
        rel_dir = Path(".") if len(rel_path.parts) == 1 else rel_path.parent
        node = ensure_node(rel_dir)
        if rel_path.name == "__init__.py":
            node.package_module = module
        else:
            node.modules.append(module)
        for ancestor in [Path(".")] + list(rel_dir.parents)[:-1]:
            ensure_node(ancestor)
        current = rel_dir
        while current != Path("."):
            parent = current.parent
            parent_node = ensure_node(parent)
            if current not in parent_node.subdirs:
                parent_node.subdirs.append(current)
            current = parent

    for node in nodes.values():
        node.subdirs.sort()
        node.modules.sort(key=lambda module: module.rel_path.as_posix())
    return nodes


def _count_modules(nodes: dict[Path, DirNode], rel_dir: Path) -> int:
    node = nodes[rel_dir]
    count = len(node.modules) + (1 if node.package_module else 0)
    for child in node.subdirs:
        count += _count_modules(nodes, child)
    return count


def _count_members(module: ModuleDoc) -> int:
    return len(module.classes) + len(module.functions) + len(module.constants)


def _member_bullets(members: Iterable[MemberDoc], rel_path: Path) -> list[str]:
    lines: list[str] = []
    for member in members:
        summary = f" - {member.summary}" if member.summary else ""
        detail = f" [{member.kind}]" if member.kind else ""
        lines.append(
            f"- `{member.signature}`{detail} ({rel_path.as_posix()}:{member.lineno}){summary}"
        )
        if member.detail and member.kind != "class":
            lines.append(f"  Detail: {member.detail}")
    return lines


def _class_section(module: ModuleDoc) -> list[str]:
    if not module.classes:
        return []
    lines = ["## Classes", ""]
    for class_doc in module.classes:
        lines.append(f"### `{class_doc.name}`")
        lines.append("")
        lines.append(f"- Defined at `{module.rel_path.as_posix()}:{class_doc.lineno}`")
        if class_doc.summary:
            lines.append(f"- Summary: {class_doc.summary}")
        if class_doc.detail:
            lines.append(f"- {class_doc.detail}")
        if class_doc.children:
            public_children = [item for item in class_doc.children if not item.name.startswith("_")]
            private_children = [item for item in class_doc.children if item.name.startswith("_")]
            if public_children:
                lines.append("")
                lines.append("#### Public Members")
                lines.append("")
                lines.extend(_member_bullets(public_children, module.rel_path))
            if private_children:
                lines.append("")
                lines.append("#### Internal Members")
                lines.append("")
                lines.extend(_member_bullets(private_children, module.rel_path))
        lines.append("")
    return lines


def _module_section(title: str, members: tuple[MemberDoc, ...], rel_path: Path) -> list[str]:
    if not members:
        return []
    public_members = [member for member in members if not member.name.startswith("_")]
    private_members = [member for member in members if member.name.startswith("_")]
    lines = [f"## {title}", ""]
    if public_members:
        lines.append("### Public")
        lines.append("")
        lines.extend(_member_bullets(public_members, rel_path))
        lines.append("")
    if private_members:
        lines.append("### Internal")
        lines.append("")
        lines.extend(_member_bullets(private_members, rel_path))
        lines.append("")
    return lines


def _render_module_page(module: ModuleDoc) -> str:
    lines = [f"# `{module.title}`", ""]
    lines.append(f"- Source: `{module.rel_path.as_posix()}`")
    if module.module_path:
        lines.append(f"- Module path: `{module.module_path}`")
    lines.append(f"- API entries: `{_count_members(module)}`")
    if module.summary:
        lines.append(f"- Summary: {module.summary}")
    lines.append("")
    if module.docstring:
        lines.append("## Module Docstring")
        lines.append("")
        lines.append("```text")
        lines.append(module.docstring)
        lines.append("```")
        lines.append("")
    else:
        lines.append("## Module Docstring")
        lines.append("")
        lines.append("No module docstring.")
        lines.append("")
    lines.extend(_module_section("Constants", module.constants, module.rel_path))
    lines.extend(_module_section("Functions", module.functions, module.rel_path))
    lines.extend(_class_section(module))
    return "\n".join(lines).strip() + "\n"


def _render_dir_index(node: DirNode, nodes: dict[Path, DirNode]) -> str:
    title = "Repository Root" if node.rel_dir == Path(".") else f"`{node.rel_dir.as_posix()}/`"
    lines = [f"# {title}", ""]
    lines.append(f"Generated from `{node.rel_dir.as_posix() if node.rel_dir != Path('.') else '.'}`.")
    if node.package_module and node.package_module.summary:
        lines.append("")
        lines.append(f"Package summary: {node.package_module.summary}")
    lines.append("")
    lines.append(
        f"This index covers `{_count_modules(nodes, node.rel_dir)}` Python modules under this path."
    )
    lines.append("")
    lines.append("```{toctree}")
    lines.append(":maxdepth: 1")
    lines.append("")
    entries: list[str] = []
    for child in node.subdirs:
        relative = child.relative_to(node.rel_dir if node.rel_dir != Path(".") else Path("."))
        entries.append((relative / "index").as_posix())
    if node.package_module:
        entries.append("package_api")
    for module in node.modules:
        target = module.page_path.relative_to((OUTPUT_ROOT / node.rel_dir)).with_suffix("")
        entries.append(target.as_posix())
    for entry in entries:
        lines.append(entry)
    lines.append("```")
    lines.append("")
    if node.subdirs:
        lines.append("## Subdirectories")
        lines.append("")
        for child in node.subdirs:
            child_rel = child.relative_to(node.rel_dir if node.rel_dir != Path(".") else Path("."))
            child_node = nodes[child]
            summary = child_node.package_module.summary if child_node.package_module else ""
            suffix = f" - {summary}" if summary else ""
            lines.append(
                f"- [`{child.as_posix()}/`]({child_rel.as_posix()}/index.md): `{_count_modules(nodes, child)}` modules{suffix}"
            )
        lines.append("")
    if node.package_module:
        package_target = "package_api.md"
        suffix = f" - {node.package_module.summary}" if node.package_module.summary else ""
        lines.append("## Package API")
        lines.append("")
        lines.append(
            f"- [`__init__.py`]({package_target}): `{_count_members(node.package_module)}` API entries{suffix}"
        )
        lines.append("")
    if node.modules:
        lines.append("## Modules")
        lines.append("")
        for module in node.modules:
            target = module.page_path.relative_to((OUTPUT_ROOT / node.rel_dir)).as_posix()
            suffix = f" - {module.summary}" if module.summary else ""
            lines.append(
                f"- [`{module.rel_path.name}`]({target}): `{_count_members(module)}` API entries{suffix}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_package_page(module: ModuleDoc) -> str:
    lines = [f"# `{module.rel_path.as_posix()}`", ""]
    lines.append(f"- Source: `{module.rel_path.as_posix()}`")
    if module.module_path:
        lines.append(f"- Module path: `{module.module_path}`")
    lines.append(f"- API entries: `{_count_members(module)}`")
    if module.summary:
        lines.append(f"- Summary: {module.summary}")
    lines.append("")
    if module.docstring:
        lines.append("## Package Docstring")
        lines.append("")
        lines.append("```text")
        lines.append(module.docstring)
        lines.append("```")
        lines.append("")
    else:
        lines.append("## Package Docstring")
        lines.append("")
        lines.append("No package docstring.")
        lines.append("")
    lines.extend(_module_section("Constants", module.constants, module.rel_path))
    lines.extend(_module_section("Functions", module.functions, module.rel_path))
    lines.extend(_class_section(module))
    return "\n".join(lines).strip() + "\n"


def _collect_pages() -> dict[Path, str]:
    modules = [_parse_module(path) for path in _iter_source_files()]
    nodes = _build_tree(modules)
    pages: dict[Path, str] = {}
    for module in modules:
        if module.rel_path.name == "__init__.py":
            pages[module.page_path.parent / "package_api.md"] = _render_package_page(module)
        else:
            pages[module.page_path] = _render_module_page(module)
    for rel_dir, node in nodes.items():
        page_path = OUTPUT_ROOT / rel_dir / "index.md" if rel_dir != Path(".") else OUTPUT_ROOT / "index.md"
        pages[page_path] = _render_dir_index(node, nodes)
    return pages


def _write_pages(pages: dict[Path, str], *, check: bool) -> int:
    existing = {path for path in OUTPUT_ROOT.rglob("*.md")} if OUTPUT_ROOT.exists() else set()
    generated = set(pages)
    changed: list[Path] = []
    missing: list[Path] = []
    for path, content in pages.items():
        if not path.exists():
            missing.append(path)
            continue
        if path.read_text(encoding="utf-8") != content:
            changed.append(path)
    extras = sorted(existing - generated)
    if check:
        if not missing and not changed and not extras:
            print("API docs are up to date.")
            return 0
        if missing:
            print("Missing API docs:")
            for path in missing:
                print(f"  - {path.relative_to(REPO_ROOT).as_posix()}")
        if changed:
            print("Changed API docs:")
            for path in changed:
                print(f"  - {path.relative_to(REPO_ROOT).as_posix()}")
        if extras:
            print("Stale API docs:")
            for path in extras:
                print(f"  - {path.relative_to(REPO_ROOT).as_posix()}")
        return 1
    for path, content in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
    for extra in extras:
        extra.unlink()
    for directory in sorted({path.parent for path in existing | generated}, reverse=True):
        if directory != OUTPUT_ROOT and directory.exists() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"Generated {len(pages)} API documentation pages under {OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix()}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Markdown API docs for repository Python modules.")
    parser.add_argument("--check", action="store_true", help="Fail if generated API docs are out of date.")
    args = parser.parse_args()
    return _write_pages(_collect_pages(), check=bool(args.check))


if __name__ == "__main__":
    raise SystemExit(main())
