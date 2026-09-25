"""
Seed de usuario: crea/actualiza un usuario desde variables de entorno.

Uso:
  SEED_USERNAME=admin SEED_PASSWORD=... python seed_user.py
  (o pasando usuario y contraseña como argumentos: python seed_user.py <user> <pass>)

La contraseña nunca se imprime ni se loguea.
"""

import os
import sys

from auth import upsert_user


def main():
    username = os.getenv("SEED_USERNAME")
    password = os.getenv("SEED_PASSWORD")
    if len(sys.argv) >= 3:
        username, password = sys.argv[1], sys.argv[2]
    if not username or not password:
        print("Faltan credenciales: definí SEED_USERNAME y SEED_PASSWORD, "
              "o pasá <usuario> <contraseña> como argumentos.")
        sys.exit(1)
    upsert_user(username, password)
    print(f"Usuario '{username}' creado/actualizado.")


if __name__ == "__main__":
    main()
