from PySide6.QtCore import *
from PySide6.QtWidgets import *
from qfluentwidgets import *
from seccion1_modelo import ANCHO_IMG, Estilo, Obra
from seccion2_utilidades import AreaScroll, aviso, boton_icono, vaciar
from seccion3_dialogos import DialogoDetalle, DialogoNombre, DialogoObra

# ======================================================================
# ★ SECCIÓN 4 · INTERFAZ (páginas del menú lateral)
#   PaginaGaleria, PaginaFavoritos, PaginaGrupos, PaginaEstilos.
# ======================================================================
class TarjetaObra(CardWidget):
    """Foto + título + artista de una obra."""
    def __init__(self, obra):
        super().__init__()
        self.setFixedWidth(ANCHO_IMG + 24)
        foto = QLabel()
        foto.setPixmap(obra.miniatura)
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(12, 12, 12, 12)
        disposicion.setSpacing(4)
        for w in (foto, BodyLabel(obra.titulo), CaptionLabel(f"{obra.artista} · {obra.fecha.year}")):
            disposicion.addWidget(w)


class PaginaGaleria(QWidget):
    """Buscador + filtros por grupo + obras en tarjetas."""
    MENSAJE_VACIO = "Aún no hay obras. Presiona «Agregar obra» para empezar."

    def __init__(self, galeria, nombre="paginaGaleria"):
        super().__init__()
        self.setObjectName(nombre)                   # FluentWindow pide un nombre único
        self.galeria, self.grupo_activo = galeria, None          # None = todas las obras
        self.txt_buscar = SearchLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por nombre, artista, estilo o grupo...")
        self.txt_buscar.textChanged.connect(self.actualizar)
        self.btn_agregar = PrimaryPushButton("Agregar obra", icon=FluentIcon.ADD)   # BOTÓN principal: agregar obra
        self.btn_agregar.clicked.connect(lambda: self.abrir_formulario())
        busqueda = QHBoxLayout()
        busqueda.addWidget(self.txt_buscar, 1)
        busqueda.addWidget(self.btn_agregar)
        self.zona_filtros = QWidget()
        self.filtros = QHBoxLayout(self.zona_filtros)
        self.filtros.setContentsMargins(0, 0, 0, 0)

        self.lbl_vacio = CaptionLabel()
        self.lbl_vacio.setAlignment(Qt.AlignCenter)

        self.scroll = AreaScroll()
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(28, 22, 28, 0)
        disposicion.setSpacing(12)
        disposicion.addLayout(busqueda)
        disposicion.addWidget(self.zona_filtros)
        disposicion.addWidget(self.lbl_vacio, 1)
        disposicion.addWidget(self.scroll, 1)
        self.actualizar()

    def showEvent(self, evento):                     # al entrar a la página se pone al día
        super().showEvent(evento)
        self.actualizar()

    def obras_a_mostrar(self):
        return self.galeria.buscar(self.txt_buscar.text(), self.grupo_activo)

    def reconstruir_filtros(self):
        vaciar(self.filtros)
        if self.grupo_activo not in self.galeria.grupos:
            self.grupo_activo = None
        for grupo in [None] + self.galeria.grupos:
            boton = PillPushButton(grupo.nombre if grupo else "Todas")   # BOTÓN tipo píldora: filtro por grupo
            boton.setChecked(grupo is self.grupo_activo)
            boton.clicked.connect(lambda _=False, g=grupo: self.elegir_grupo(g))
            self.filtros.addWidget(boton)
        self.filtros.addStretch(1)
        self.zona_filtros.setVisible(bool(self.galeria.grupos))

    def elegir_grupo(self, grupo):
        self.grupo_activo = grupo
        self.actualizar()

    def actualizar(self, *_):
        self.reconstruir_filtros()
        obras = self.obras_a_mostrar()
        zona = QWidget()                             # contenedor nuevo con las tarjetas
        zona.setStyleSheet("background:transparent")
        flujo = FlowLayout(zona, needAni=False)
        flujo.setContentsMargins(4, 4, 4, 20)
        flujo.setHorizontalSpacing(16)
        flujo.setVerticalSpacing(16)
        for obra in obras:
            tarjeta = TarjetaObra(obra)
            tarjeta.clicked.connect(lambda o=obra: self.abrir_detalle(o))
            flujo.addWidget(tarjeta)
        self.scroll.setWidget(zona)
        self.scroll.setVisible(bool(obras))
        self.lbl_vacio.setVisible(not obras)
        self.lbl_vacio.setText("Sin resultados para esta búsqueda."
                               if (self.txt_buscar.text() or self.grupo_activo) else self.MENSAJE_VACIO)

    def abrir_detalle(self, obra):
        dialogo = DialogoDetalle(obra, self.window())
        dialogo.exec()
        self.galeria._sql("UPDATE obra SET favorita=? WHERE id=?", (int(obra.favorita), obra.id))
        if dialogo.accion == "borrar":
            self.confirmar_borrado(obra)
        elif dialogo.accion == "editar":
            self.abrir_formulario(obra)
        self.actualizar()

    def confirmar_borrado(self, obra):
        pregunta = MessageBox("Eliminar obra", f"¿Seguro que quieres eliminar «{obra.titulo}»? "
                              "Esta acción no se puede deshacer.", self.window())
        pregunta.yesButton.setText("Eliminar")
        pregunta.cancelButton.setText("Cancelar")
        if pregunta.exec():
            self.galeria.eliminar_obra(obra)

    def abrir_formulario(self, obra=None):
        dialogo = DialogoObra(self.galeria, obra, self.window())
        if not dialogo.exec():
            return
        if obra is None:                             # agregar: se crea un objeto Obra nuevo
            self.galeria.agregar_obra(Obra(imagen=dialogo.ruta, **dialogo.datos))
        else:                                        # editar: el objeto existente se actualiza
            obra.actualizar(**dialogo.datos)
            if dialogo.ruta:
                obra.poner_imagen(dialogo.ruta)
            self.galeria.guardar_obra(obra)
        self.actualizar()


# ======================================================================
# ★ HERENCIA: PaginaFavoritos hereda de PaginaGaleria
#   Reutiliza toda la pantalla y solo cambia qué obras muestra (polimorfismo).
# ======================================================================
class PaginaFavoritos(PaginaGaleria):
    """La misma pantalla de la galería (herencia), pero solo con las obras favoritas."""
    MENSAJE_VACIO = "Aún no tienes favoritas. Toca el corazón en una obra para guardarla aquí."

    def __init__(self, galeria):
        super().__init__(galeria, "paginaFavoritos")
        self.btn_agregar.hide()

    def obras_a_mostrar(self):
        return self.galeria.buscar(self.txt_buscar.text(), self.galeria.favoritos)

    def reconstruir_filtros(self):
        self.zona_filtros.hide()


# ======================================================================
# ★ CLASE BASE: PaginaCatalogo (Grupos y Estilos)
#   Define el comportamiento común; las hijas rellenan los métodos que cambian.
# ======================================================================
class PaginaCatalogo(QWidget):
    """Base de «Grupos» y «Estilos»: cuadro para crear + lista con botones de editar y borrar.
    Cada hija define: elementos(), nombre(), cantidad(), crear_elemento(), renombrar(), eliminar()."""
    def __init__(self, nombre_objeto, galeria, titulo, pista):
        super().__init__()
        self.setObjectName(nombre_objeto)
        self.galeria = galeria
        self.txt_nombre = LineEdit()
        self.txt_nombre.setPlaceholderText(pista)
        self.txt_nombre.returnPressed.connect(self.crear)
        btn_crear = PrimaryPushButton("Crear", icon=FluentIcon.ADD)   # BOTÓN: crear grupo / estilo
        btn_crear.clicked.connect(self.crear)
        fila_crear = QHBoxLayout()
        fila_crear.addWidget(self.txt_nombre, 1)
        fila_crear.addWidget(btn_crear)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(10)
        self.lista.setContentsMargins(0, 0, 0, 20)
        self.lista.setAlignment(Qt.AlignTop)
        contenido = QWidget()
        contenido.setStyleSheet("background:transparent")
        contenido.setLayout(self.lista)
        self.scroll = AreaScroll()
        self.scroll.setWidget(contenido)
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(40, 36, 40, 0)
        disposicion.setSpacing(14)
        disposicion.addWidget(SubtitleLabel(titulo))
        disposicion.addLayout(fila_crear)
        disposicion.addWidget(self.scroll, 1)

    def showEvent(self, evento):
        super().showEvent(evento)
        self.actualizar()

    def editable(self, elemento): return True        # por defecto todo se puede editar y borrar

    def actualizar(self):
        vaciar(self.lista)
        for elemento in self.elementos():
            n = self.cantidad(elemento)
            tarjeta = CardWidget()
            tarjeta.setFixedHeight(56)
            fila = QHBoxLayout(tarjeta)
            fila.addWidget(BodyLabel(self.nombre(elemento)))
            fila.addWidget(CaptionLabel(f"{n} obra" + ("" if n == 1 else "s")))
            fila.addStretch(1)
            if self.editable(elemento):
                fila.addWidget(boton_icono(FluentIcon.EDIT, lambda _=False, e=elemento: self.abrir_editor(e)))
                fila.addWidget(boton_icono(FluentIcon.DELETE, lambda _=False, e=elemento: self.borrar(e)))
            self.lista.addWidget(tarjeta)

    def crear(self):
        try:
            self.crear_elemento(self.txt_nombre.text())
        except ValueError as error:                  # nombre vacío o repetido
            return aviso("No se pudo crear", str(error), self.window())
        self.txt_nombre.clear()
        self.actualizar()

    def abrir_editor(self, elemento):
        DialogoNombre(self.nombre(elemento), lambda nuevo: self.renombrar(elemento, nuevo), self.window()).exec()
        self.actualizar()

    def borrar(self, elemento):
        self.eliminar(elemento)
        self.actualizar()


class PaginaGrupos(PaginaCatalogo):
    def __init__(self, galeria):
        super().__init__("paginaGrupos", galeria, "Grupos", "Nombre del nuevo grupo")
    def elementos(self): return self.galeria.todos_los_grupos()
    def nombre(self, grupo): return grupo.nombre
    def cantidad(self, grupo): return len(self.galeria.buscar("", grupo))
    def editable(self, grupo): return grupo.es_propio()          # Favoritos no se edita ni se borra
    def crear_elemento(self, nombre): self.galeria.crear_grupo(nombre)
    def renombrar(self, grupo, nombre): self.galeria.renombrar_grupo(grupo, nombre)
    def eliminar(self, grupo): self.galeria.eliminar_grupo(grupo)


class PaginaEstilos(PaginaCatalogo):
    def __init__(self, galeria):
        super().__init__("paginaEstilos", galeria, "Estilos", "Nombre del nuevo estilo")
    def elementos(self): return self.galeria.estilos
    def nombre(self, estilo): return estilo                      # cada estilo ya es un texto
    def cantidad(self, estilo): return len(self.galeria.buscar("", Estilo(estilo)))
    def crear_elemento(self, nombre): self.galeria.crear_estilo(nombre)
    def renombrar(self, estilo, nombre): self.galeria.renombrar_estilo(estilo, nombre)
    def eliminar(self, estilo): self.galeria.eliminar_estilo(estilo)
