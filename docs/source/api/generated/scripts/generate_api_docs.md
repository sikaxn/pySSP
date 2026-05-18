# `scripts/generate_api_docs.py`

- Source: `scripts/generate_api_docs.py`
- Module path: `scripts.generate_api_docs`
- API entries: `34`

## Module Docstring

No module docstring.

## Constants

### Public

- `REPO_ROOT` [constant] (scripts/generate_api_docs.py:12)
  Detail: Value: Path(__file__).resolve().parents[1]
- `OUTPUT_ROOT` [constant] (scripts/generate_api_docs.py:13)
  Detail: Value: REPO_ROOT / 'docs' / 'source' / 'api' / 'generated'
- `SOURCE_DIRS` [constant] (scripts/generate_api_docs.py:14)
  Detail: Value: (REPO_ROOT / 'pyssp', REPO_ROOT / 'scripts', REPO_ROOT / 'spleeter-cli')

## Functions

### Public

- `main() -> int` [function] (scripts/generate_api_docs.py:553)

### Internal

- `_clean_text(value: str) -> str` [function] (scripts/generate_api_docs.py:53)
- `_summary_from_docstring(value: str) -> str` [function] (scripts/generate_api_docs.py:57)
- `_is_valid_module_path(path: Path) -> bool` [function] (scripts/generate_api_docs.py:66)
- `_module_path_for(rel_path: Path) -> str` [function] (scripts/generate_api_docs.py:70)
- `_format_annotation(node: ast.AST | None) -> str` [function] (scripts/generate_api_docs.py:80)
- `_format_constant_value(node: ast.AST | None) -> str` [function] (scripts/generate_api_docs.py:86)
- `_format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str` [function] (scripts/generate_api_docs.py:98)
- `_member_kind_for_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str` [function] (scripts/generate_api_docs.py:146)
- `_collect_class_children(node: ast.ClassDef) -> tuple[MemberDoc, ...]` [function] (scripts/generate_api_docs.py:157)
- `_collect_class(node: ast.ClassDef) -> MemberDoc` [function] (scripts/generate_api_docs.py:175)
- `_collect_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> MemberDoc` [function] (scripts/generate_api_docs.py:190)
- `_collect_constant(node: ast.Assign | ast.AnnAssign) -> Iterable[MemberDoc]` [function] (scripts/generate_api_docs.py:202)
- `_page_path_for(rel_path: Path) -> Path` [function] (scripts/generate_api_docs.py:224)
- `_title_for(rel_path: Path) -> str` [function] (scripts/generate_api_docs.py:232)
- `_parse_module(path: Path) -> ModuleDoc` [function] (scripts/generate_api_docs.py:236)
- `_iter_source_files() -> list[Path]` [function] (scripts/generate_api_docs.py:263)
- `_build_tree(modules: list[ModuleDoc]) -> dict[Path, DirNode]` [function] (scripts/generate_api_docs.py:272)
- `_count_modules(nodes: dict[Path, DirNode], rel_dir: Path) -> int` [function] (scripts/generate_api_docs.py:307)
- `_count_members(module: ModuleDoc) -> int` [function] (scripts/generate_api_docs.py:315)
- `_member_bullets(members: Iterable[MemberDoc], rel_path: Path) -> list[str]` [function] (scripts/generate_api_docs.py:319)
- `_class_section(module: ModuleDoc) -> list[str]` [function] (scripts/generate_api_docs.py:332)
- `_module_section(title: str, members: tuple[MemberDoc, ...], rel_path: Path) -> list[str]` [function] (scripts/generate_api_docs.py:361)
- `_render_module_page(module: ModuleDoc) -> str` [function] (scripts/generate_api_docs.py:380)
- `_render_dir_index(node: DirNode, nodes: dict[Path, DirNode]) -> str` [function] (scripts/generate_api_docs.py:407)
- `_render_package_page(module: ModuleDoc) -> str` [function] (scripts/generate_api_docs.py:469)
- `_collect_pages() -> dict[Path, str]` [function] (scripts/generate_api_docs.py:496)
- `_write_pages(pages: dict[Path, str], *, check: bool) -> int` [function] (scripts/generate_api_docs.py:511)

## Classes

### `MemberDoc`

- Defined at `scripts/generate_api_docs.py:22`

### `ModuleDoc`

- Defined at `scripts/generate_api_docs.py:33`

### `DirNode`

- Defined at `scripts/generate_api_docs.py:46`
