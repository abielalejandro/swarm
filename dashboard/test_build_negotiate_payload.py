"""Check mínimo de build_negotiate_payload: omitir opcionales vacíos. Correr: python3 test_build_negotiate_payload.py"""
import ast

# Extraer solo la función del módulo (app.py ejecuta UI de Streamlit a nivel top).
src = open("app.py", encoding="utf-8").read()
tree = ast.parse(src)
fn = next(n for n in tree.body
          if isinstance(n, ast.FunctionDef) and n.name == "build_negotiate_payload")
ns = {}
exec(compile(ast.Module([fn], []), "app.py", "exec"), ns)
build = ns["build_negotiate_payload"]

# Solo goal -> sin opcionales (y trim)
assert build("  Decidir tech  ") == {"goal": "Decidir tech"}, "goal solo / trim"
# Todos los campos
full = build("Cloud", deadline="2026-09-15", budget=200000, max_rounds=7, agents=["Finance", "DevOps"])
assert full == {"goal": "Cloud", "deadline": "2026-09-15", "budget": 200000.0,
                "max_rounds": 7, "agents": ["Finance", "DevOps"]}, full
# Vacíos/ceros se omiten
assert build("X", deadline="  ", budget=0, max_rounds=0, agents=[]) == {"goal": "X"}, "opcionales vacíos"
print("OK: build_negotiate_payload")
