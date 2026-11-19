from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from qfluentwidgets import *
from seccion2_utilidades import aviso, boton_icono

# ======================================================================
# ★ SECCIÓN 3 · VENTANAS (diálogos)
#   HERENCIA: Dialogo (base) -> DialogoObra, DialogoNombre, DialogoDetalle.
#   Uso: if DialogoX(...).exec():  ->  el usuario aceptó.
# ======================================================================
class Dialogo(MessageBoxBase):
    """Base de todas las ventanitas: botones en español y ancho mínimo."""
    def __init__(self, ventana, si="Guardar", ancho=0):
        super().__init__(ventana)
        self.widget.setMinimumWidth(ancho)
        self.yesButton.setText(si)
        self.cancelButton.setText("Cancelar")

    def agregar(self, *widgets):                     # mete widgets o layouts a la ventanita
        for w in widgets:
            self.viewLayout.addLayout(w) if isinstance(w, QLayout) else self.viewLayout.addWidget(w)


class DialogoObra(Dialogo):
    """Formulario para agregar una obra (obra=None) o editar una existente."""
    def __init__(self, galeria, obra, ventana):
        super().__init__(ventana, ancho=460)
        self.galeria, self.obra, self.ruta = galeria, obra, None

        # ★ Recuadro punteado: vacío = borde punteado rosa; con imagen = borde sólido. Clic = elegir imagen.
        self.lbl_imagen = QLabel("🖼  Toca aquí para elegir una imagen")
        self.lbl_imagen.setAlignment(Qt.AlignCenter)
        self.lbl_imagen.setFixedHeight(130)
        self.lbl_imagen.setCursor(Qt.PointingHandCursor)
        self.lbl_imagen.setStyleSheet("QLabel{border:2px dashed #D62976;border-radius:12px;"
                                      "color:#D62976;background:rgba(214,41,118,0.08)}")
        self.lbl_imagen.mousePressEvent = lambda e: self.elegir_imagen()

        btn_imagen = PushButton("Cambiar imagen" if obra else "Elegir imagen", icon=FluentIcon.PHOTO)   # BOTÓN: elegir / cambiar imagen
        btn_imagen.clicked.connect(self.elegir_imagen)
        self.txt_titulo, self.txt_artista = LineEdit(), LineEdit()
        self.txt_titulo.setPlaceholderText("Título de la obra")
        self.txt_artista.setPlaceholderText("Artista")
        self.picker_fecha = CalendarPicker()
        self.picker_fecha.setDate(QDate.currentDate())
        self.picker_fecha.setDateFormat("dd/MM/yyyy")
        fila_fecha = QHBoxLayout()
        for w in (BodyLabel("Fecha de creación"), self.picker_fecha):
            fila_fecha.addWidget(w)
        fila_fecha.insertStretch(1)

        # Grupos: desplegable donde se pueden marcar varios
        self.menu_grupos = CheckableMenu(parent=self, indicatorType=MenuIndicatorType.CHECK)
        self.casillas = []                           # lista de (acción marcable, grupo)
        for g in galeria.grupos:
            accion = Action(g.nombre, self.menu_grupos)
            accion.setCheckable(True)
            accion.toggled.connect(self.actualizar_texto_grupos)
            self.menu_grupos.addAction(accion)
            self.casillas.append((accion, g))
        self.btn_grupos = DropDownPushButton("Grupos")   # BOTÓN desplegable con casillas de grupos
        self.btn_grupos.setMenu(self.menu_grupos)
        if not galeria.grupos:
            self.btn_grupos.setText("Aún no tienes grupos (créalos en «Grupos»)")
            self.btn_grupos.setEnabled(False)

        self.cmb_estilo = ComboBox()
        self.cmb_estilo.addItems(galeria.estilos)
        self.cmb_estilo.setCurrentIndex(-1)
        self.cmb_estilo.setPlaceholderText("Estilo")
        self.txt_descripcion = TextEdit()
        self.txt_descripcion.setPlaceholderText("Descripción (opcional)")
        self.txt_descripcion.setFixedHeight(72)
        self.agregar(SubtitleLabel("Editar obra" if obra else "Agregar obra"), self.lbl_imagen, btn_imagen,
                     self.txt_titulo, self.txt_artista, fila_fecha, self.btn_grupos, self.cmb_estilo,
                     self.txt_descripcion)

        if obra:                                     # al editar, se rellena con los datos de la obra
            self.mostrar_imagen(obra.imagen)
            self.txt_titulo.setText(obra.titulo)
            self.txt_artista.setText(obra.artista)
            self.picker_fecha.setDate(QDate(obra.fecha.year, obra.fecha.month, obra.fecha.day))
            if obra.estilo in galeria.estilos:
                self.cmb_estilo.setCurrentIndex(galeria.estilos.index(obra.estilo))
            self.txt_descripcion.setPlainText(obra.descripcion)
            for casilla, grupo in self.casillas:
                casilla.setChecked(grupo in obra.grupos)

    def actualizar_texto_grupos(self, *_):           # el botón muestra lo que está marcado
        nombres = [g.nombre for accion, g in self.casillas if accion.isChecked()]
        texto = ", ".join(nombres)
        self.btn_grupos.setText((texto if len(texto) <= 35 else f"{len(nombres)} grupos") or "Grupos")

    def mostrar_imagen(self, pixmap):                # con imagen cargada, el borde pasa a sólido
        self.lbl_imagen.setPixmap(pixmap.scaledToHeight(120, Qt.SmoothTransformation))
        self.lbl_imagen.setStyleSheet("QLabel{border:2px solid #D62976;border-radius:12px}")

    def elegir_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Elegir imagen", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if ruta:
            self.ruta = ruta
            self.mostrar_imagen(QPixmap(ruta))

    def validate(self):                              # Qt lo llama al presionar «Guardar»
        if not self.txt_titulo.text().strip() or not (self.ruta or self.obra):
            aviso("Faltan datos", "Elige una imagen y escribe el título", self)
            return False                             # False = la ventana no se cierra
        i = self.cmb_estilo.currentIndex()
        self.datos = dict(
            titulo=self.txt_titulo.text().strip(), artista=self.txt_artista.text().strip() or "Anónimo",
            fecha=self.picker_fecha.date.toPython(), estilo=self.galeria.estilos[i] if i >= 0 else "",
            grupos=[g for casilla, g in self.casillas if casilla.isChecked()],
            descripcion=self.txt_descripcion.toPlainText().strip())
        return True


class DialogoNombre(Dialogo):
    """Cambiar el nombre de un grupo o de un estilo. `aplicar` lanza ValueError si no vale."""
    def __init__(self, nombre, aplicar, ventana):
        super().__init__(ventana)
        self.aplicar = aplicar
        self.txt_nombre = LineEdit()
        self.txt_nombre.setText(nombre)
        self.lbl_error = CaptionLabel()
        self.lbl_error.setStyleSheet("color:#FF3B5C")
        self.agregar(SubtitleLabel("Editar nombre"), self.txt_nombre, self.lbl_error)

    def validate(self):
        try:
            self.aplicar(self.txt_nombre.text())
        except ValueError as error:                  # vacío o repetido: la ventana sigue abierta
            self.lbl_error.setText(str(error))
            return False
        return True


class DialogoDetalle(Dialogo):
    """Ficha de una obra. `accion` dice qué pidió el usuario: None, "editar" o "borrar"."""
    def __init__(self, obra, ventana):
        super().__init__(ventana, si="Cerrar", ancho=460)
        self.accion = None
        self.cancelButton.hide()

        foto = QLabel()
        foto.setAlignment(Qt.AlignCenter)
        foto.setPixmap(obra.imagen.scaled(420, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        corazon = ToggleToolButton(FluentIcon.HEART)             # marcado = es favorita
        corazon.setChecked(obra.favorita)
        corazon.clicked.connect(obra.alternar_favorita)
        arriba = QHBoxLayout()
        for w in (SubtitleLabel(obra.titulo), corazon, boton_icono(FluentIcon.EDIT, lambda: self.pedir("editar")),
                  boton_icono(FluentIcon.DELETE, lambda: self.pedir("borrar"))):
            arriba.addWidget(w)
        arriba.insertStretch(1)
        filas = [("Autor", obra.artista), ("Fecha", obra.fecha.strftime("%d/%m/%Y")),
                 ("Lienzo", obra.lienzo()), ("Tamaño", obra.peso()), ("Estilo", obra.estilo or "—"),
                 ("Grupos", ", ".join(g.nombre for g in obra.grupos) or "—")]
        if obra.descripcion:
            filas.append(("Descripción", obra.descripcion))
        self.agregar(foto, arriba)
        for nombre, valor in filas:
            texto = BodyLabel(f"{nombre}: {valor}")
            texto.setWordWrap(True)
            self.agregar(texto)

    def pedir(self, accion):                         # recuerda qué se pidió y cierra la ventana
        self.accion = accion
        self.accept()
