"""Galería de Arte · Programación Orientada a Objetos (Python + PySide6 + SQLite).

Instalar:  pip install PySide6 PySide6-Fluent-Widgets
Ejecutar:  python galeria_arte_final.py

Dónde está cada concepto de POO:
  Clase abstracta ... Clasificacion
  Herencia ......... Grupo / GrupoFavoritos / Estilo, Dialogo*, PaginaFavoritos, PaginaGrupos/Estilos
  Recursividad ..... Galeria.buscar()
  Persistencia ..... Galeria (SQLite, archivo galery.db)
"""
from main import main

if __name__ == "__main__":
    main()
