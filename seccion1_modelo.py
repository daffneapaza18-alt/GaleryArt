from PySide6.QtCore import *
from PySide6.QtGui import *
import os, sqlite3, sys
from abc import ABC, abstractmethod
from datetime import date

# ======================================================================
# ★ SECCIÓN 1 · MODELO (POO) Y BASE DE DATOS
#   Clases del dominio: Clasificacion, Grupo, Estilo, GrupoFavoritos, Obra, Galeria.
#   La base de datos SQLite (galery.db) guarda todo: persistencia en archivo.
# ======================================================================
# --- Constantes y esquema SQL (4 tablas: estilo, grupo, obra, obra_grupo) ---
ESTILOS_INICIALES = "Cartoon,Realismo,Abstracto,Anime,Manga,Cómic,Semirealismo,Chibi,Surrealismo,Pixel art".split(",")
ANCHO_IMG = 220
RUTA_DB = os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__)), "galery.db")
ESQUEMA = """
CREATE TABLE IF NOT EXISTS estilo (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(nombre)) > 0));
CREATE TABLE IF NOT EXISTS grupo (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(nombre)) > 0));
CREATE TABLE IF NOT EXISTS obra (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL CHECK (length(trim(titulo)) > 0), artista TEXT NOT NULL DEFAULT 'Anónimo',
    fecha TEXT NOT NULL, imagen BLOB NOT NULL, ancho INTEGER NOT NULL, alto INTEGER NOT NULL, peso_bytes INTEGER NOT NULL DEFAULT 0, descripcion TEXT NOT NULL DEFAULT '',
    favorita INTEGER NOT NULL DEFAULT 0 CHECK (favorita IN (0, 1)), estilo_id INTEGER REFERENCES estilo(id) ON DELETE SET NULL ON UPDATE CASCADE);
CREATE TABLE IF NOT EXISTS obra_grupo (obra_id INTEGER NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    grupo_id INTEGER NOT NULL REFERENCES grupo(id) ON DELETE CASCADE, PRIMARY KEY (obra_id, grupo_id));
"""


# ======================================================================
# ★ CLASE ABSTRACTA: Clasificacion
#   No se puede instanciar. Obliga a las hijas a definir contiene() y es_propio().
# ======================================================================
class Clasificacion(ABC):
    """CLASE ABSTRACTA: una forma de clasificar obras. No se puede instanciar; obliga a las hijas a definir estos métodos."""
    def __init__(self, nombre, id=None):
        self.nombre, self.id = nombre, id
    @abstractmethod
    def contiene(self, obra): ...                    # ¿la obra pertenece a esta clasificación?
    @abstractmethod
    def es_propio(self): ...                         # ¿el usuario puede editarla y borrarla?


# ======================================================================
# ★ HERENCIA
#   Clasificacion  ->  Grupo  ->  GrupoFavoritos
#   Clasificacion  ->  Estilo
#   Cada hija redefine contiene() a su manera (polimorfismo).
# ======================================================================
class Grupo(Clasificacion):
    """Un grupo que crea el usuario (nombre + id de la base de datos)."""
    def contiene(self, obra): return self in obra.grupos
    def es_propio(self): return True                 # los grupos propios se editan y se borran


class Estilo(Clasificacion):                         # permite contar/buscar obras por estilo con la misma lógica
    def contiene(self, obra): return obra.estilo == self.nombre
    def es_propio(self): return True


class GrupoFavoritos(Grupo):                         # HERENCIA: es un Grupo con reglas propias
    def __init__(self): super().__init__("Favoritos")
    def contiene(self, obra): return obra.favorita   # aquí "estar en el grupo" = tener corazón
    def es_propio(self): return False


# ======================================================================
# ★ CLASE Obra: cada obra guardada es un OBJETO
#   Atributos: título, artista, fecha, imagen, estilo, grupos, favorita.
# ======================================================================
class Obra:
    """Una obra de arte. Cada obra guardada es un OBJETO de esta clase."""
    def __init__(self, titulo, artista, fecha, imagen, estilo="", grupos=(),
                 descripcion="", favorita=False, id=None):
        self.titulo, self.artista, self.fecha, self.estilo = titulo, artista, fecha, estilo
        self.grupos, self.descripcion, self.favorita, self.id = list(grupos), descripcion, favorita, id
        self.poner_imagen(imagen)

    def poner_imagen(self, origen):                  # origen: ruta de un archivo o bytes de la BD
        if isinstance(origen, str):
            origen = open(origen, "rb").read()
        self.bytes = origen                          # esto es lo que se guarda en la BD
        self.imagen = QPixmap()
        self.imagen.loadFromData(origen)
        self.miniatura = self.imagen.scaledToWidth(ANCHO_IMG, Qt.SmoothTransformation)

    def actualizar(self, **datos):                   # editar: cambia los atributos que le pases
        self.__dict__.update(datos)

    def alternar_favorita(self): self.favorita = not self.favorita
    def lienzo(self): return f"{self.imagen.width()} × {self.imagen.height()} px"
    def peso(self): return f"{max(1, round(len(self.bytes) / 1024))} KB"

    def coincide_con(self, texto):                   # para el buscador
        campos = [self.titulo, self.artista, self.fecha.year, self.estilo] + [g.nombre for g in self.grupos]
        return any(texto.lower() in str(c).lower() for c in campos)


# ======================================================================
# ★ CLASE Galeria: lista de obras en memoria + persistencia SQLite
#   self.obras / self.grupos / self.estilos son las estructuras dinámicas (listas).
# ======================================================================
class Galeria:
    """Guarda obras, grupos y estilos (en galery.db) y aplica las reglas."""
    def __init__(self, ruta_db=RUTA_DB):
        self.db = sqlite3.connect(ruta_db)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(ESQUEMA)
        if not self.db.execute("SELECT 1 FROM estilo").fetchone():       # primera vez
            for estilo in ESTILOS_INICIALES:
                self._sql("INSERT INTO estilo(nombre) VALUES (?)", (estilo,))
        self.favoritos = GrupoFavoritos()
        self.grupos = [Grupo(n, i) for i, n in self.db.execute("SELECT id, nombre FROM grupo")]
        self.estilos = [e for (e,) in self.db.execute("SELECT nombre FROM estilo ORDER BY id")]
        self.obras = [self._leer_obra(*fila) for fila in self.db.execute(
            "SELECT o.id, o.titulo, o.artista, o.fecha, o.imagen, o.descripcion, o.favorita, e.nombre "
            "FROM obra o LEFT JOIN estilo e ON e.id = o.estilo_id ORDER BY o.id DESC")]

    def _sql(self, consulta, datos=()):              # ejecuta y guarda (commit) en la BD
        with self.db:
            return self.db.execute(consulta, datos)

    def _leer_obra(self, id, titulo, artista, fecha, imagen, descripcion, favorita, estilo):
        ids = [g for (g,) in self.db.execute("SELECT grupo_id FROM obra_grupo WHERE obra_id=?", (id,))]
        return Obra(titulo, artista, date.fromisoformat(fecha), imagen, estilo or "",
                    [g for g in self.grupos if g.id in ids], descripcion, bool(favorita), id)

    def todos_los_grupos(self): return [self.favoritos] + self.grupos

    def _validar(self, nombre, existentes, actual=""):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("Escribe un nombre.")
        if nombre.lower() in [e.lower() for e in existentes if e.lower() != actual.lower()]:
            raise ValueError(f"Ya existe «{nombre}».")
        return nombre

    def guardar_obra(self, obra):                    # REPLACE: inserta si es nueva, actualiza si existe
        obra.id = self._sql(
            "INSERT OR REPLACE INTO obra(id, titulo, artista, fecha, imagen, ancho, alto, peso_bytes, "
            "descripcion, favorita, estilo_id) VALUES (?,?,?,?,?,?,?,?,?,?,"
            "(SELECT id FROM estilo WHERE nombre=?))",
            (obra.id, obra.titulo, obra.artista, obra.fecha.isoformat(), obra.bytes, obra.imagen.width(),
             obra.imagen.height(), len(obra.bytes), obra.descripcion, int(obra.favorita), obra.estilo)).lastrowid
        for grupo in obra.grupos:
            self._sql("INSERT INTO obra_grupo VALUES (?,?)", (obra.id, grupo.id))

    def agregar_obra(self, obra):
        self.guardar_obra(obra)
        self.obras.insert(0, obra)                   # la nueva aparece primero

    def eliminar_obra(self, obra):                   # obra_grupo se limpia en cascada
        self._sql("DELETE FROM obra WHERE id=?", (obra.id,))
        self.obras.remove(obra)

    def crear_grupo(self, nombre):
        nombre = self._validar(nombre, [g.nombre for g in self.todos_los_grupos()])
        self.grupos.append(Grupo(nombre, self._sql("INSERT INTO grupo(nombre) VALUES (?)", (nombre,)).lastrowid))

    def renombrar_grupo(self, grupo, nombre):
        grupo.nombre = self._validar(nombre, [g.nombre for g in self.todos_los_grupos()], grupo.nombre)
        self._sql("UPDATE grupo SET nombre=? WHERE id=?", (grupo.nombre, grupo.id))

    def eliminar_grupo(self, grupo):                 # las obras no se borran, solo salen del grupo
        self._sql("DELETE FROM grupo WHERE id=?", (grupo.id,))
        self.grupos.remove(grupo)
        for obra in self.obras:
            if grupo in obra.grupos:
                obra.grupos.remove(grupo)

    def crear_estilo(self, nombre):
        nombre = self._validar(nombre, self.estilos)
        self._sql("INSERT INTO estilo(nombre) VALUES (?)", (nombre,))
        self.estilos.append(nombre)

    def renombrar_estilo(self, viejo, nombre):
        nuevo = self._validar(nombre, self.estilos, viejo)
        self._sql("UPDATE estilo SET nombre=? WHERE nombre=?", (nuevo, viejo))
        self.estilos[self.estilos.index(viejo)] = nuevo
        for obra in self.obras:
            if obra.estilo == viejo:
                obra.estilo = nuevo

    def eliminar_estilo(self, nombre):               # las obras no se borran, quedan sin estilo
        self._sql("DELETE FROM estilo WHERE nombre=?", (nombre,))
        self.estilos.remove(nombre)
        for obra in self.obras:
            if obra.estilo == nombre:
                obra.estilo = ""

    # ======================================================================
    # ★ FUNCIÓN RECURSIVA: buscar()
    #   Divide la lista por la mitad hasta 0 o 1 obra (caso base) y une los resultados.
    #   Sirve para la barra de búsqueda, los filtros de grupo y el conteo por estilo/grupo.
    # ======================================================================
    def buscar(self, texto="", grupo=None, obras=None):      # RECURSIVA: parte la lista por la mitad
        obras = self.obras if obras is None else obras
        if not obras: return []                              # caso base 1: lista vacía
        if len(obras) == 1:                                  # caso base 2: una sola obra
            o = obras[0]
            return [o] if (grupo is None or grupo.contiene(o)) and o.coincide_con(texto) else []
        m = len(obras) // 2                                  # caso recursivo: mitad izquierda + mitad derecha
        return self.buscar(texto, grupo, obras[:m]) + self.buscar(texto, grupo, obras[m:])
