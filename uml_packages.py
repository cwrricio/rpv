#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AutoDiag: Gera PlantUML real a partir do que EXISTE no disco.
- packages.puml: diagrama de pacotes (pastas reais, recursivo).
- components.puml: componentes por pasta raiz + arestas por imports (Py/JS/TS).

Uso rápido:
  python autodiag.py
Opções:
  --root .            # pasta do projeto
  --max-depth 3       # profundidade do diagrama de pacotes
  --min-files 1       # só cria pacote se tiver pelo menos N arquivos dentro
  --ignore ".git,node_modules,dist,build,.venv,venv,__pycache__"
  --outfile-packages packages.puml
  --outfile-components components.puml
"""

import argparse
import os
import re
from pathlib import Path
from collections import defaultdict

# ----------- Helpers -----------
DEF_IGNORES = {
    ".git","node_modules","dist","build",".venv","venv","__pycache__",
    ".idea",".vscode",".pytest_cache",".mypy_cache",".ruff_cache",
    ".next",".nuxt",".cache",".parcel-cache","coverage",".DS_Store"
}

JS_TS_EXT = {".js",".jsx",".ts",".tsx",".mjs",".cjs"}
PY_EXT    = {".py"}

IMPORT_RE_JS = re.compile(
    r"""(?x)
    ^\s*import\s+[^'"]*\s+from\s+['"]([^'"]+)['"]\s*;?|
    ^\s*import\s+['"]([^'"]+)['"]\s*;?|
    ^\s*const\s+.*=\s*require\(\s*['"]([^'"]+)['"]\s*\)|
    ^\s*require\(\s*['"]([^'"]+)['"]\s*\)
    """, re.MULTILINE
)

IMPORT_RE_PY = re.compile(
    r"""(?x)
    ^\s*import\s+([a-zA-Z0-9_\.]+)|
    ^\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+
    """, re.MULTILINE
)

def is_hidden(p: Path) -> bool:
    return any(part.startswith(".") and part not in {".", ".."} for part in p.parts)

def norm_ref(s: str) -> str:
    """Normaliza ref de pacote para PlantUML id."""
    return re.sub(r"[^A-Za-z0-9_]", "_", s)

def rel_to_root(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)

def is_inside_any(p: Path, names: set) -> bool:
    return any(part in names for part in p.parts)

# ----------- Escaneio do filesystem -----------
def walk_tree(root: Path, ignores: set):
    files = []
    dirs  = []
    for dirpath, dirnames, filenames in os.walk(root):
        # filtra dirs ignorados in-place (evita descer neles)
        dirnames[:] = [d for d in dirnames if d not in ignores]
        # ignora pastas ocultas profundas
        dirnames[:] = [d for d in dirnames if not d.startswith(".") or d in {"."}]
        p = Path(dirpath)
        dirs.append(p)
        for f in filenames:
            if f.startswith("."): 
                continue
            files.append(p / f)
    return dirs, files

# ----------- Diagrama de Pacotes -----------
def build_packages_puml(root: Path, dirs, files, max_depth: int, min_files: int, ignores: set) -> str:
    # conta arquivos por pasta (apenas os que estão dentro da pasta)
    file_count = defaultdict(int)
    for f in files:
        parent = f.parent
        while True:
            if parent == root.parent:
                break
            file_count[parent] += 1
            if parent == root:
                break
            parent = parent.parent

    # gera estrutura hierárquica até max_depth
    root_id = norm_ref(root.name or "root")
    lines = [
        "@startuml",
        f"title Pacotes do Sistema — raiz: {root.name}",
        "skinparam packageStyle rectangle"
    ]

    # montar árvore por níveis
    # só cria pacote se: não ignorado, dentro da profundidade, e atende min_files
    def add_package(path: Path, depth: int):
        if depth > max_depth:
            return
        if path != root and (path.name in ignores or is_hidden(path)):
            return
        if file_count.get(path, 0) < (min_files if path != root else 0):
            return

        children = sorted([d for d in path.iterdir() if d.is_dir()
                           and d.name not in ignores
                           and not is_hidden(d)], key=lambda x: x.name.lower())

        if path == root:
            # raiz: abre direto
            for c in children:
                add_package(c, depth+1)
            return

        pkg_title = rel_to_root(path, root)
        pkg_id = norm_ref(pkg_title)
        lines.append(f'package "{pkg_title}" as {pkg_id} {{')

        for c in children:
            if file_count.get(c, 0) >= min_files and depth+1 <= max_depth:
                # cria subpacote como container; conteúdo dos filhos virá quando add_package(c, ...)
                lines.append(f'  package "{rel_to_root(c, root)}" as {norm_ref(rel_to_root(c, root))}')
        lines.append("}")

        for c in children:
            add_package(c, depth+1)

    # entrada
    add_package(root, 0)

    lines.append("@enduml")
    return "\n".join(lines)

# ----------- Diagrama de Componentes (por pasta-raiz) -----------
def top_level_groups(root: Path, dirs, ignores: set):
    """Agrupa componentes pelo primeiro nível de pasta dentro da raiz."""
    groups = set()
    for d in root.iterdir():
        if d.is_dir() and d.name not in ignores and not is_hidden(d):
            groups.add(d.name)
    # se não houver subpastas, usa a própria raiz como 1 grupo
    if not groups:
        groups = {root.name}
    return sorted(groups)

def path_to_toplevel(p: Path, root: Path):
    rel = rel_to_root(p, root)
    if rel == ".":
        return root.name
    first = rel.split(os.sep, 1)[0]
    return first or root.name

def parse_imports(file_path: Path, root: Path):
    """Extrai imports de um arquivo para mapeá-los a toplevel groups."""
    ext = file_path.suffix.lower()
    content = ""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    refs = set()

    if ext in JS_TS_EXT:
        for m in IMPORT_RE_JS.finditer(content):
            mod = next((g for g in m.groups() if g), None)
            if not mod: 
                continue
            # resolve apenas imports relativos -> mapeia ao grupo destino
            if mod.startswith("."):
                target = (file_path.parent / mod).resolve()
                # tente achar um arquivo real (index.[tj]s[x], ou mesmo pasta)
                candidates = []
                # path como pasta?
                candidates.append(target)
                # como arquivo?
                for suff in ["", ".js",".jsx",".ts",".tsx",".mjs",".cjs",".py"]:
                    candidates.append(Path(str(target) + suff))
                # index padrão
                for idx in ["index.js","index.ts","index.jsx","index.tsx"]:
                    candidates.append(target / idx)
                existing = next((c for c in candidates if c.exists()), None)
                if existing:
                    refs.add(path_to_toplevel(existing, root))
            else:
                # import de pacote externo -> ignoramos (não mapeia para componente local)
                pass

    elif ext in PY_EXT:
        for m in IMPORT_RE_PY.finditer(content):
            mod = m.group(1) or m.group(2)
            if not mod:
                continue
            # tenta resolver import relativo ao projeto: procura pelo primeiro segmento no topo
            top_seg = mod.split(".")[0]
            # se existe uma pasta/arquivo com esse nome no topo, contamos
            candidate_dir = root / top_seg
            candidate_file = root / (top_seg + ".py")
            if candidate_dir.exists() or candidate_file.exists():
                refs.add(top_seg)

    return list(refs)

def build_components_puml(root: Path, files, ignores: set) -> str:
    groups = top_level_groups(root, [], ignores)
    if groups == [root.name]:
        # projeto "flat": um único componente
        nodes = [root.name]
    else:
        nodes = groups

    # nó de cada grupo + arestas por import entre grupos
    edges = defaultdict(set)

    for f in files:
        # só considera arquivos de código
        if f.suffix.lower() not in JS_TS_EXT | PY_EXT:
            continue
        src_group = path_to_toplevel(f, root)
        if src_group not in nodes:
            continue
        targets = parse_imports(f, root)
        for tgt in targets:
            if tgt in nodes and tgt != src_group:
                edges[src_group].add(tgt)

    # heurísticas para “nomes amigáveis” de certos grupos
    pretty_name = {
        "src": "Frontend (SPA)",
        "frontend": "Frontend",
        "web": "Frontend",
        "app": "App (web/mobile)",
        "api": "BFF/API",
        "server": "Servidor",
        "backend": "Backend",
        "functions": "Funções Serverless",
        "cmd": "CLI/Jobs",
        "scripts": "Scripts",
        "infra": "Infra/DevOps",
        "db": "Camada de Dados",
        "data": "Dados",
        "shared": "Shared/Lib",
        "lib": "Biblioteca Compartilhada",
    }

    def label_of(n: str) -> str:
        return f'{pretty_name.get(n.lower(), n)}\\n({n})' if n.lower() in pretty_name else n

    lines = [
        "@startuml",
        f"title Componentes por pasta-raiz — raiz: {root.name}",
        "skinparam componentStyle rectangle"
    ]

    # desenha componentes
    for n in nodes:
        nid = norm_ref(n)
        lines.append(f'component "{label_of(n)}" as {nid}')

    # desenha arestas
    for src, tgts in edges.items():
        sid = norm_ref(src)
        for tgt in sorted(tgts):
            tid = norm_ref(tgt)
            lines.append(f"{sid} --> {tid}")

    # dica visual: agrupar alguns conhecidos em contêineres
    known_web = [n for n in nodes if n.lower() in {"src","frontend","web","app"}]
    known_api = [n for n in nodes if n.lower() in {"api","backend","server","functions"}]
    if known_web:
        box = " ".join(norm_ref(n) for n in known_web)
        lines.append(f"rectangle \"Camada Web\" {{ {box} }}")
    if known_api:
        box = " ".join(norm_ref(n) for n in known_api)
        lines.append(f"rectangle \"Camada de Serviços\" {{ {box} }}")

    lines.append("@enduml")
    return "\n".join(lines)

# ----------- Main -----------
def main():
    ap = argparse.ArgumentParser(description="Gera PlantUML real a partir do filesystem.")
    ap.add_argument("--root", default=".", help="Raiz do projeto")
    ap.add_argument("--max-depth", type=int, default=3, help="Profundidade para o diagrama de pacotes")
    ap.add_argument("--min-files", type=int, default=1, help="Mínimo de arquivos para criar um pacote")
    ap.add_argument("--ignore", default=",".join(sorted(DEF_IGNORES)),
                    help="Lista de pastas ignoradas, separadas por vírgula")
    ap.add_argument("--outfile-packages", default="packages.puml", help="Saída do diagrama de pacotes")
    ap.add_argument("--outfile-components", default="components.puml", help="Saída do diagrama de componentes")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    ignores = set(s.strip() for s in args.ignore.split(",") if s.strip())

    dirs, files = walk_tree(root, ignores)

    pkg_puml = build_packages_puml(root, dirs, files, args.max_depth, args.min_files, ignores)
    (root / args.outfile_packages).write_text(pkg_puml, encoding="utf-8")

    comp_puml = build_components_puml(root, files, ignores)
    (root / args.outfile_components).write_text(comp_puml, encoding="utf-8")

    print("OK!")
    print(f"- {args.outfile_packages}")
    print(f"- {args.outfile_components}")

if __name__ == "__main__":
    main()
