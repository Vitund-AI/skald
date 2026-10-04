"""docs/api.md lists every route the board server handles, and nothing it does not.

The routes are read from ``Handler._dispatch`` in src/skald/server.py with ``ast``, so the
inventory cannot drift from the code: each ``if`` that compares the request path
(``parts``/``rest``/``tail``/``sub`` against a literal list, or ``not sub``) is a route, and its
methods come from ``method == ...``/``method in (...)`` in the same test or in the ``if``s
directly inside it. A route written some other way would be missed, so keep to that shape.
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "src" / "skald" / "server.py"
DOC = ROOT / "docs" / "api.md"
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
ANY = "*"
BASES = {"parts": "/", "rest": "/api/", "tail": "/api/projects/<p>/", "sub": "/api/projects/<p>/stories/<id>/"}


def _literal_path(var: str, node: ast.AST):
    if isinstance(node, ast.List) and all(isinstance(e, ast.Constant) for e in node.elts):
        return (BASES[var] + "/".join(e.value for e in node.elts)).rstrip("/") or "/"
    return None


def _paths(test: ast.AST) -> list[str]:
    """Paths a condition matches: ``x == [...]``, ``parts in ([], [...])``, ``not sub``."""
    out = []
    for node in ast.walk(test):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and isinstance(node.operand, ast.Name) \
                and node.operand.id == "sub":
            out.append(BASES["sub"].rstrip("/"))
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id in BASES:
            op, right = node.ops[0], node.comparators[0]
            if isinstance(op, ast.Eq) and (p := _literal_path(node.left.id, right)):
                out.append(p)
            elif isinstance(op, ast.In) and isinstance(right, ast.Tuple):
                out.extend(p for e in right.elts if (p := _literal_path(node.left.id, e)))
    return out


def _methods(test: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(test):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "method":
            right = node.comparators[0]
            values = right.elts if isinstance(right, ast.Tuple) else [right]
            out.update(v.value for v in values if isinstance(v, ast.Constant))
    return out


def server_routes() -> set[tuple[str, str]]:
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    dispatch = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_dispatch")
    routes = set()

    def visit(stmts):
        for node in stmts:
            if isinstance(node, ast.If):
                paths = _paths(node.test)
                if paths:
                    methods = _methods(node.test) or {m for child in node.body if isinstance(child, ast.If)
                                                      for m in _methods(child.test)} or {ANY}
                    routes.update((m, p) for m in methods for p in paths)
                visit(node.body)
                visit(node.orelse)

    visit(dispatch.body)
    return routes


def documented_routes() -> set[tuple[str, str]]:
    """``(METHOD, path)`` from the first cell of every table row; ``\\`PUT\\``` alone reuses the row's last path."""
    out = set()
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        path = None
        for span in re.findall(r"`([^`]+)`", line.split(" | ")[0]):
            bits = span.split()
            if bits[0] not in METHODS:
                continue
            if len(bits) > 1:
                path = re.sub(r"\[.*?\]", "", bits[1]).split("?")[0]
            if path:
                out.add((bits[0], path))
    return out


class TestApiDocs(unittest.TestCase):
    def test_inventory_reads_the_server(self):
        routes = server_routes()
        # A few known routes, so a parser that silently finds nothing cannot pass.
        for route in [("GET", "/api/health"), ("PATCH", "/api/projects/<p>/stories/<id>"),
                      ("POST", "/api/projects/<p>/git/commit"), ("GET", "/")]:
            self.assertIn(route, routes)
        self.assertGreater(len(routes), 30)

    def test_every_server_route_is_documented(self):
        documented = documented_routes()
        documented_paths = {p for _, p in documented}

        def is_documented(method, path):
            # A route that accepts any method needs a row for its path; the rest need their exact method.
            return path in documented_paths if method == ANY else (method, path) in documented

        missing = sorted(f"{m} {p}" for m, p in server_routes() if not is_documented(m, p))
        self.assertEqual(missing, [], "add these routes to docs/api.md")

    def test_every_documented_route_exists(self):
        routes = server_routes()
        stale = sorted(f"{m} {p}" for m, p in documented_routes()
                       if (m, p) not in routes and (ANY, p) not in routes)
        self.assertEqual(stale, [], "docs/api.md lists routes the server does not handle")

    def test_doc_says_the_api_is_internal(self):
        # 0a2011 Q1: documented for reference, internal to the board, outside the 1.x promise.
        head = DOC.read_text(encoding="utf-8")[:1500].lower()
        self.assertIn("internal to the board", head)
        self.assertIn("compatibility promise", head)
