"""docs/api.md lists every route the board server handles, and nothing it does not.

The routes are read from ``Handler._dispatch`` in src/skald/server.py with ``ast``, so the
inventory cannot drift from the code: each ``if`` that compares the request path
(``parts``/``rest``/``tail``/``sub`` against a literal list, or ``not sub``) is a route, and its
methods come from ``method == ...``/``method in (...)`` in the same test or in the ``if``s
directly inside it. A route written some other way would be missed, so keep to that shape.

The page has two planes. Every route belongs to exactly one: the data plane (stable for 1.x)
or the board backend (internal). ``STABLE`` pins the data plane: a route may join it in a
minor release (add it here), but none may leave it before 2.0.
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
DATA_PLANE, BOARD = "## Data plane", "## Board backend"
# The 1.x data plane. Adding a route is a deliberate promotion; removing one breaks the promise.
STABLE = {
    ("GET", "/api/health"),
    ("GET", "/api/projects"),
    ("GET", "/api/ready"),
    ("GET", "/api/projects/<p>/version"),
    ("GET", "/api/projects/<p>/events"),
    ("POST", "/api/projects/<p>/stories"),
    ("GET", "/api/projects/<p>/stories/<id>"),
    ("PATCH", "/api/projects/<p>/stories/<id>"),
    ("DELETE", "/api/projects/<p>/stories/<id>"),
    ("PUT", "/api/projects/<p>/stories/<id>/body"),
    ("POST", "/api/projects/<p>/stories/<id>/notes"),
    ("POST", "/api/projects/<p>/stories/<id>/claim"),
}


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


def documented_sections() -> dict[str, set[tuple[str, str]]]:
    """``(METHOD, path)`` from the first cell of every table row, grouped by the ``##`` section.

    A span holding only a method (``PUT``) reuses the row's last path. A bracketed query (``[?force=1]``) is an optional
    parameter of the route; an unbracketed one (``?ref=REF``) documents a variant of a route listed
    elsewhere, so it counts toward coverage but not toward which plane the route is in.
    """
    sections: dict[str, set[tuple[str, str]]] = {"": set(), "variants": set()}
    current = ""
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line.split(" (")[0]
            sections.setdefault(current, set())
            continue
        if not line.startswith("| `"):
            continue
        path, variant = None, False
        for span in re.findall(r"`([^`]+)`", line.split(" | ")[0]):
            bits = span.split()
            if bits[0] not in METHODS:
                continue
            if len(bits) > 1:
                bare = re.sub(r"\[.*?\]", "", bits[1])
                path, variant = bare.split("?")[0], "?" in bare
            if path:
                sections["variants" if variant else current].add((bits[0], path))
    return sections


def documented_routes() -> set[tuple[str, str]]:
    return set().union(*documented_sections().values())


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

    def test_every_route_is_in_exactly_one_plane(self):
        sections = documented_sections()
        data, board = sections.get(DATA_PLANE, set()), sections.get(BOARD, set())
        self.assertTrue(data and board, "docs/api.md needs a data-plane section and a board-backend section")
        stray = sorted(f"{m} {p}" for m, p in sections[""])
        self.assertEqual(stray, [], "routes listed outside the two planes")
        both = sorted(f"{m} {p}" for m, p in data & board)
        self.assertEqual(both, [], "routes listed in both planes")

    def test_data_plane_is_pinned(self):
        data = documented_sections().get(DATA_PLANE, set())
        left = sorted(f"{m} {p}" for m, p in STABLE - data)
        self.assertEqual(left, [], "a stable route cannot leave the data plane before 2.0")
        joined = sorted(f"{m} {p}" for m, p in data - STABLE)
        self.assertEqual(joined, [], "promoting a route to the data plane is deliberate: add it to STABLE")
        self.assertTrue(STABLE <= server_routes(), "a stable route no longer exists in the server")

    def test_doc_states_both_planes(self):
        head = DOC.read_text(encoding="utf-8")[:1500].lower()
        self.assertIn("stable for 1.x", head)
        self.assertIn("internal to the board", head)
