import sys
import random

from PIL import Image, ImageDraw, ImageFilter
import qtawesome as qta

from PySide6.QtCore import (
    Qt, Signal, QVariantAnimation, QEasingCurve, QAbstractAnimation, QEvent, QRectF
)
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QPainterPath, QLinearGradient, QRadialGradient,
    QColor, QPen
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QFileDialog, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition, NavigationDisplayMode, SearchLineEdit,
    PushButton, PrimaryPushButton, PillPushButton, LineEdit, ComboBox, TextEdit,
    BodyLabel, CaptionLabel, SubtitleLabel, TransparentToolButton, SwitchButton,
    InfoBar, InfoBarPosition, setTheme, Theme, setThemeColor, isDarkTheme, qconfig
)

# ---------------------------------------------------------------
#  COLORES  (paleta estilo Instagram: oscuro por defecto + claro)
# ---------------------------------------------------------------
COLOR_ACENTO = "#D62976"
FONDO_PASTEL = [(0.00, "#FFE3C8"),   # durazno
                (0.35, "#FFD1E3"),   # rosa
                (0.70, "#E3D4FF"),   # lila
                (1.00, "#D4E6FF")]   # celeste
FONDO_OSCURO = [(0.00, "#150F2E"),   # violeta muy oscuro
                (0.50, "#24123F"),   # ciruela
                (1.00, "#0F1B3A")]   # azul noche
# Resplandores de color sobre el fondo oscuro: (x, y, color, opacidad 0-255)
BRILLOS_OSCURO = [(0.88, 0.02, "#D62976", 85),   # rosa arriba a la derecha
                  (0.05, 0.98, "#4F5BD5", 95),   # azul abajo a la izquierda
                  (0.95, 0.97, "#FA7E1E", 38)]   # naranja suave abajo a la derecha
PARES_DEMO = [("#FEDA75", "#FA7E1E"), ("#FA7E1E", "#D62976"),
              ("#D62976", "#962FBF"), ("#962FBF", "#4F5BD5"),
              ("#4F5BD5", "#6EC6FF"), ("#FF9A9E", "#FAD0C4"),
              ("#A18CD1", "#FBC2EB"), ("#84FAB0", "#8FD3F4")]

ANCHO_IMG = 220
MARGEN_TARJETA = 8
ANCHO_TARJETA = ANCHO_IMG + MARGEN_TARJETA * 2
ESPACIO = 16


def dibujar_fondo(pintor, rect):
    """Fondo de toda la ventana: degradado + resplandores (oscuro) o pastel (claro)."""
    w, h = rect.width(), rect.height()
    g = QLinearGradient(0, 0, w, h)
    for pos, color in (FONDO_OSCURO if isDarkTheme() else FONDO_PASTEL):
        g.setColorAt(pos, QColor(color))
    pintor.fillRect(rect, g)

    if isDarkTheme():
        radio = max(w, h) * 0.55
        for fx, fy, color, alfa in BRILLOS_OSCURO:
            rg = QRadialGradient(w * fx, h * fy, radio)
            c = QColor(color)
            c.setAlpha(alfa)
            rg.setColorAt(0, c)
            c.setAlpha(0)
            rg.setColorAt(1, c)
            pintor.fillRect(rect, rg)


# ---------------------------------------------------------------
#  UTILIDADES DE IMAGEN (Pillow <-> Qt)
# ---------------------------------------------------------------
def hex_a_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def crear_imagen_demo(ancho, alto):
    """Imagen de prueba con degradado diagonal de colores vivos."""
    c1, c2 = random.choice(PARES_DEMO)
    c1, c2 = hex_a_rgb(c1), hex_a_rgb(c2)
    img = Image.new("RGB", (ancho, alto))
    d = ImageDraw.Draw(img)
    for y in range(alto):
        t = y / alto
        d.line([(0, y), (ancho, y)],
               fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    # un círculo translúcido para que parezca "obra"
    capa = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    ImageDraw.Draw(capa).ellipse(
        [ancho * 0.2, alto * 0.25, ancho * 0.8, alto * 0.25 + ancho * 0.6],
        fill=(255, 255, 255, 70))
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def pil_a_pixmap(img):
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def pixmap_a_pil(pix):
    qimg = pix.toImage().convertToFormat(QImage.Format_RGBA8888)
    datos = bytes(qimg.constBits())
    return Image.frombuffer("RGBA", (qimg.width(), qimg.height()), datos,
                            "raw", "RGBA", qimg.bytesPerLine(), 1)


def redondear(pix, radio=16):
    salida = QPixmap(pix.size())
    salida.fill(Qt.transparent)
    p = QPainter(salida)
    p.setRenderHint(QPainter.Antialiasing)
    ruta = QPainterPath()
    ruta.addRoundedRect(0, 0, pix.width(), pix.height(), radio, radio)
    p.setClipPath(ruta)
    p.drawPixmap(0, 0, pix)
    p.end()
    return salida


# ---------------------------------------------------------------
#  CLASE DE DATOS
# ---------------------------------------------------------------
class Obra:
    def __init__(self, titulo, artista, categoria, estilo="", descripcion="", ruta=None):
        self.titulo = titulo
        self.artista = artista
        self.categoria = categoria
        self.estilo = estilo
        self.descripcion = descripcion or "Sin descripción."
        self.likes = random.randint(3, 120)
        self.me_gusta = False

        if ruta:
            img = Image.open(ruta).convert("RGB")
            img.thumbnail((1600, 1600))
        else:
            img = crear_imagen_demo(440, random.randint(360, 680))
        self.original = img

        self.alto = int(img.height * ANCHO_IMG / img.width)
        mini = img.resize((ANCHO_IMG, self.alto), Image.LANCZOS)
        self.miniatura = redondear(pil_a_pixmap(mini), 14)

    def pixmap_grande(self, ancho, alto_max):
        img = self.original
        alto = int(img.height * ancho / img.width)
        pix = pil_a_pixmap(img.resize((ancho, alto), Image.LANCZOS))
        if alto > alto_max:  # recorta al centro si es muy alta
            pix = pix.copy(0, (alto - alto_max) // 2, ancho, alto_max)
        return redondear(pix, 18)


# ---------------------------------------------------------------
#  TARJETA DE CRISTAL
# ---------------------------------------------------------------
class TarjetaObra(QWidget):
    clic = Signal(object)

    def __init__(self, obra):
        super().__init__()
        self.obra = obra
        self.hover = False
        self.setFixedWidth(ANCHO_TARJETA)
        self.setCursor(Qt.PointingHandCursor)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(MARGEN_TARJETA, MARGEN_TARJETA, MARGEN_TARJETA, 12)
        capa.setSpacing(4)

        imagen = QLabel()
        imagen.setPixmap(obra.miniatura)
        imagen.setFixedSize(obra.miniatura.size())
        capa.addWidget(imagen)
        capa.addWidget(BodyLabel(obra.titulo))
        capa.addWidget(CaptionLabel(f"{obra.artista} · {obra.categoria}"))

        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(26)
        sombra.setOffset(0, 8)
        sombra.setColor(QColor(0, 0, 0, 120) if isDarkTheme() else QColor(150, 47, 120, 55))
        self.setGraphicsEffect(sombra)

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if isDarkTheme():   # cristal oscuro: blanco muy tenue + borde de luz
            p.setPen(QPen(QColor(255, 255, 255, 70 if self.hover else 38), 1))
            p.setBrush(QColor(255, 255, 255, 34 if self.hover else 17))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 230), 1))
            p.setBrush(QColor(255, 255, 255, 225 if self.hover else 150))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 18, 18)

    def mousePressEvent(self, e):
        self.clic.emit(self.obra)


# ---------------------------------------------------------------
#  MOSAICO ESTILO PINTEREST (columnas se ajustan al ancho)
# ---------------------------------------------------------------
class CuadriculaMosaico(QScrollArea):
    def __init__(self, al_hacer_clic):
        super().__init__()
        self.al_hacer_clic = al_hacer_clic
        self.obras_actuales = []
        self.n_columnas = 0

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("QScrollArea{background:transparent;border:none}")
        self.viewport().setStyleSheet("background:transparent")

        self.contenido = QWidget()
        self.contenido.setStyleSheet("background:transparent")
        self.setWidget(self.contenido)

        self.fila = QHBoxLayout(self.contenido)
        self.fila.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.fila.setContentsMargins(10, 10, 10, 20)
        self.fila.setSpacing(ESPACIO)

    def _columnas_que_caben(self):
        ancho = self.viewport().width() - 20
        return max(1, (ancho + ESPACIO) // (ANCHO_TARJETA + ESPACIO))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.obras_actuales and self._columnas_que_caben() != self.n_columnas:
            self.mostrar(self.obras_actuales)

    def mostrar(self, obras):
        self.obras_actuales = obras
        while self.fila.count():
            item = self.fila.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.n_columnas = self._columnas_que_caben()
        usadas = min(self.n_columnas, max(1, len(obras)))  # sin columnas vacías
        columnas, alturas = [], [0] * usadas
        for _ in range(usadas):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignTop)
            col.setSpacing(ESPACIO)
            col.setContentsMargins(0, 0, 0, 0)
            cont = QWidget()
            cont.setLayout(col)
            self.fila.addWidget(cont)
            columnas.append(col)

        for obra in obras:
            i = alturas.index(min(alturas))
            tarjeta = TarjetaObra(obra)
            tarjeta.clic.connect(self.al_hacer_clic)
            columnas[i].addWidget(tarjeta)
            alturas[i] += obra.alto + 70


# ---------------------------------------------------------------
#  VENTANAS EMERGENTES: fondo borroso + panel de cristal + animación
# ---------------------------------------------------------------
class PanelCristal(QFrame):
    """Panel blanco translúcido con esquinas muy redondeadas."""
    cerrar = Signal()

    def __init__(self, ancho):
        super().__init__()
        self.setFixedWidth(ancho)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        if isDarkTheme():
            g.setColorAt(0, QColor(40, 30, 68, 236))
            g.setColorAt(1, QColor(24, 17, 44, 240))
            p.setPen(QPen(QColor(255, 255, 255, 60), 1.2))
        else:
            g.setColorAt(0, QColor(255, 255, 255, 240))
            g.setColorAt(1, QColor(255, 244, 250, 225))
            p.setPen(QPen(QColor(255, 255, 255, 255), 1.5))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 26, 26)


class VeloBorroso(QWidget):
    """Capa que cubre la ventana, desenfoca lo de atrás y muestra el panel."""

    def __init__(self, ventana, panel):
        super().__init__(ventana)
        self.ventana = ventana
        self.panel = panel
        self.progreso = 0.0
        self.efecto = None
        self.setFocusPolicy(Qt.StrongFocus)

        self.fondo = self._crear_fondo_borroso()
        self.setGeometry(ventana.rect())
        panel.setParent(self)
        ventana.installEventFilter(self)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(280)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._aplicar)
        self.anim.finished.connect(self._terminada)

    def _crear_fondo_borroso(self):
        img = pixmap_a_pil(self.ventana.grab())
        chica = img.resize((max(1, img.width // 2), max(1, img.height // 2)))
        borrosa = chica.filter(ImageFilter.GaussianBlur(7)).convert("RGBA")
        color_tinte = (12, 7, 28, 125) if isDarkTheme() else (255, 236, 246, 95)
        tinte = Image.new("RGBA", borrosa.size, color_tinte)
        return pil_a_pixmap(Image.alpha_composite(borrosa, tinte))

    # --- animación ---
    def abrir(self):
        self.panel.adjustSize()
        alto = max(self.panel.sizeHint().height(),
                   self.panel.layout().totalHeightForWidth(self.panel.width()))
        self.panel.resize(self.panel.width(), alto)

        self.efecto = QGraphicsOpacityEffect(self.panel)
        self.efecto.setOpacity(0)
        self.panel.setGraphicsEffect(self.efecto)

        self.show()
        self.raise_()
        self.panel.show()
        self.setFocus()
        self._colocar()
        self.anim.setDirection(QAbstractAnimation.Forward)
        self.anim.start()

    def cerrar(self):
        if self.anim.state() == QAbstractAnimation.Running and \
                self.anim.direction() == QAbstractAnimation.Backward:
            return
        if self.efecto is None:
            self.efecto = QGraphicsOpacityEffect(self.panel)
            self.efecto.setOpacity(1)
            self.panel.setGraphicsEffect(self.efecto)
        self.anim.setDirection(QAbstractAnimation.Backward)
        self.anim.start()

    def _aplicar(self, v):
        self.progreso = float(v)
        if self.efecto:
            self.efecto.setOpacity(self.progreso)
        self._colocar()
        self.update()

    def _terminada(self):
        if self.anim.direction() == QAbstractAnimation.Backward:
            self.ventana.removeEventFilter(self)
            self.hide()
            self.deleteLater()
        else:
            self.panel.setGraphicsEffect(None)  # panel nítido al terminar
            self.efecto = None

    def _colocar(self):
        x = (self.width() - self.panel.width()) // 2
        y = (self.height() - self.panel.height()) // 2 + int((1 - self.progreso) * 36)
        self.panel.move(x, y)

    # --- eventos ---
    def eventFilter(self, obj, ev):
        if obj is self.ventana and ev.type() == QEvent.Resize:
            self.setGeometry(self.ventana.rect())
            self._colocar()
        return super().eventFilter(obj, ev)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self.progreso)
        p.drawPixmap(self.rect(), self.fondo)
        # sombra suave del panel
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0) if isDarkTheme() else QColor(120, 30, 100))
        r = self.panel.geometry()
        for i in range(9):
            p.setOpacity(self.progreso * (0.05 if isDarkTheme() else 0.03))
            p.drawRoundedRect(r.adjusted(-i * 3, -i * 3 + 10, i * 3, i * 3 + 10),
                              26 + i * 3, 26 + i * 3)

    def mousePressEvent(self, e):
        if not self.panel.geometry().contains(e.position().toPoint()):
            self.cerrar()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cerrar()


def abrir_panel(ventana, panel):
    velo = VeloBorroso(ventana, panel)
    panel.cerrar.connect(velo.cerrar)
    velo.abrir()


# ---------------------------------------------------------------
#  PANEL: AGREGAR OBRA
# ---------------------------------------------------------------
class PanelAgregarObra(PanelCristal):
    guardada = Signal(object)

    def __init__(self):
        super().__init__(440)
        self.ruta = None

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 24, 28, 24)
        capa.setSpacing(10)

        capa.addWidget(SubtitleLabel("Agregar obra"))

        self.vista = QLabel("Aún no eliges una imagen")
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setFixedHeight(140)
        if isDarkTheme():
            acento, fondo = "#FF6FAE", "rgba(255,255,255,14)"
        else:
            acento, fondo = COLOR_ACENTO, "rgba(255,255,255,120)"
        self.vista.setStyleSheet(
            f"QLabel{{border:2px dashed {acento};border-radius:16px;"
            f"color:{acento};background:{fondo}}}")
        capa.addWidget(self.vista)

        btn_img = PushButton("Elegir imagen")
        btn_img.setIcon(FluentIcon.PHOTO)
        btn_img.clicked.connect(self.elegir_imagen)
        capa.addWidget(btn_img)

        self.txt_titulo = LineEdit()
        self.txt_titulo.setPlaceholderText("Título de la obra")
        self.txt_artista = LineEdit()
        self.txt_artista.setPlaceholderText("Artista")
        capa.addWidget(self.txt_titulo)
        capa.addWidget(self.txt_artista)

        combos = QHBoxLayout()
        self.cmb_categoria = ComboBox()
        self.cmb_categoria.addItems(["Pintura", "Escultura", "Fotografía"])
        self.cmb_estilo = ComboBox()
        self.cmb_estilo.addItems(["Impresionismo", "Cubismo", "Surrealismo", "Abstracto"])
        combos.addWidget(self.cmb_categoria)
        combos.addWidget(self.cmb_estilo)
        capa.addLayout(combos)

        self.txt_desc = TextEdit()
        self.txt_desc.setPlaceholderText("Descripción")
        self.txt_desc.setFixedHeight(72)
        capa.addWidget(self.txt_desc)

        botones = QHBoxLayout()
        cancelar = PushButton("Cancelar")
        cancelar.clicked.connect(self.cerrar.emit)
        guardar = PrimaryPushButton("Guardar")
        guardar.clicked.connect(self.guardar)
        botones.addStretch(1)
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        capa.addLayout(botones)

    def elegir_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Elegir imagen", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if ruta:
            self.ruta = ruta
            pix = QPixmap(ruta).scaled(self.vista.width() - 8, self.vista.height() - 8,
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.vista.setPixmap(pix)

    def guardar(self):
        if not self.txt_titulo.text().strip() or not self.ruta:
            InfoBar.warning("Faltan datos", "Elige una imagen y escribe el título",
                            parent=self.window(), position=InfoBarPosition.TOP_RIGHT,
                            duration=2500)
            return
        obra = Obra(self.txt_titulo.text().strip(),
                    self.txt_artista.text().strip() or "Anónimo",
                    self.cmb_categoria.text(), self.cmb_estilo.text(),
                    self.txt_desc.toPlainText().strip(), self.ruta)
        self.guardada.emit(obra)
        self.cerrar.emit()


# ---------------------------------------------------------------
#  PANEL: DETALLE DE OBRA (como abrir un post)
# ---------------------------------------------------------------
class PanelDetalle(PanelCristal):
    def __init__(self, obra):
        super().__init__(420)
        self.obra = obra

        capa = QVBoxLayout(self)
        capa.setContentsMargins(24, 18, 24, 22)
        capa.setSpacing(8)

        arriba = QHBoxLayout()
        arriba.addWidget(SubtitleLabel(obra.titulo))
        arriba.addStretch(1)
        x = TransparentToolButton(FluentIcon.CLOSE)
        x.clicked.connect(self.cerrar.emit)
        arriba.addWidget(x)
        capa.addLayout(arriba)

        imagen = QLabel()
        imagen.setPixmap(obra.pixmap_grande(372, 360))
        imagen.setAlignment(Qt.AlignCenter)
        capa.addWidget(imagen)

        sub = f"{obra.artista} · {obra.categoria}" + (f" · {obra.estilo}" if obra.estilo else "")
        capa.addWidget(CaptionLabel(sub))
        desc = BodyLabel(obra.descripcion)
        desc.setWordWrap(True)
        capa.addWidget(desc)

        fila = QHBoxLayout()
        self.btn_like = TransparentToolButton()
        self.btn_like.clicked.connect(self.alternar_like)
        self.lbl_likes = BodyLabel()
        fila.addWidget(self.btn_like)
        fila.addWidget(self.lbl_likes)
        fila.addStretch(1)
        cerrar = PrimaryPushButton("Cerrar")
        cerrar.clicked.connect(self.cerrar.emit)
        fila.addWidget(cerrar)
        capa.addLayout(fila)
        self._refrescar_like()

    def alternar_like(self):
        self.obra.me_gusta = not self.obra.me_gusta
        self.obra.likes += 1 if self.obra.me_gusta else -1
        self._refrescar_like()

    def _refrescar_like(self):
        if self.obra.me_gusta:
            self.btn_like.setIcon(qta.icon("fa5s.heart", color=COLOR_ACENTO))
        else:
            self.btn_like.setIcon(qta.icon("fa5.heart",
                                           color="#DDDDDD" if isDarkTheme() else "#555555"))
        self.lbl_likes.setText(f"{self.obra.likes} me gusta")


# ---------------------------------------------------------------
#  PÁGINAS
# ---------------------------------------------------------------
class PaginaConFondo(QWidget):
    """Página transparente: el fondo lo dibuja la ventana principal."""


class PaginaGaleria(PaginaConFondo):
    def __init__(self):
        super().__init__()
        self.setObjectName("paginaGaleria")
        self.categoria_activa = "Todas"

        titulos = ["Luna", "Mar", "Bosque", "Retrato", "Atardecer", "Ciudad",
                   "Flores", "Abstracto", "Montaña", "Gato", "Noche", "Desierto"]
        artistas = ["Ana", "Luis", "Marta", "Pablo"]
        categorias = ["Pintura", "Escultura", "Fotografía"]
        estilos = ["Impresionismo", "Cubismo", "Surrealismo", "Abstracto"]
        self.obras = [
            Obra(random.choice(titulos), random.choice(artistas),
                 random.choice(categorias), random.choice(estilos))
            for _ in range(14)
        ]

        capa = QVBoxLayout(self)
        capa.setContentsMargins(28, 22, 28, 0)
        capa.setSpacing(12)

        barra = QHBoxLayout()
        self.buscador = SearchLineEdit()
        self.buscador.setPlaceholderText("Buscar por nombre, artista, estilo o categoría...")
        self.buscador.setFixedHeight(42)
        self.buscador.textChanged.connect(self.filtrar)
        boton = PrimaryPushButton("Agregar obra")
        boton.setIcon(qta.icon("fa5s.plus", color="white"))
        boton.setFixedHeight(42)
        boton.clicked.connect(self.agregar)
        barra.addWidget(self.buscador, 1)
        barra.addWidget(boton)
        capa.addLayout(barra)

        # Píldoras de categoría (como las historias de Instagram)
        pildoras = QHBoxLayout()
        self.pildoras = {}
        for nombre in ["Todas"] + categorias:
            b = PillPushButton(nombre)
            b.clicked.connect(lambda _=False, n=nombre: self.elegir_categoria(n))
            self.pildoras[nombre] = b
            pildoras.addWidget(b)
        pildoras.addStretch(1)
        self.pildoras["Todas"].setChecked(True)
        capa.addLayout(pildoras)

        self.cuadricula = CuadriculaMosaico(self.abrir_obra)
        capa.addWidget(self.cuadricula)
        self.cuadricula.mostrar(self.obras)

    def elegir_categoria(self, nombre):
        self.categoria_activa = nombre
        for n, b in self.pildoras.items():
            b.setChecked(n == nombre)
        self.filtrar()

    def filtrar(self, *_):
        t = self.buscador.text().lower()
        res = [o for o in self.obras
               if (self.categoria_activa in ("Todas", o.categoria))
               and (t in o.titulo.lower() or t in o.artista.lower()
                    or t in o.categoria.lower() or t in o.estilo.lower())]
        self.cuadricula.mostrar(res)

    def abrir_obra(self, obra):
        abrir_panel(self.window(), PanelDetalle(obra))

    def agregar(self):
        panel = PanelAgregarObra()
        panel.guardada.connect(self.nueva_obra)
        abrir_panel(self.window(), panel)

    def nueva_obra(self, obra):
        self.obras.insert(0, obra)
        self.filtrar()
        InfoBar.success("Listo", "Obra guardada correctamente",
                        parent=self.window(), position=InfoBarPosition.TOP_RIGHT,
                        duration=2000)


class PaginaSimple(PaginaConFondo):
    def __init__(self, nombre, texto):
        super().__init__()
        self.setObjectName(nombre)
        capa = QVBoxLayout(self)
        capa.setAlignment(Qt.AlignCenter)
        capa.addWidget(SubtitleLabel(texto), alignment=Qt.AlignCenter)


# ---------------------------------------------------------------
#  VENTANA PRINCIPAL
# ---------------------------------------------------------------
class PaginaAjustes(PaginaConFondo):
    def __init__(self, ventana):
        super().__init__()
        self.setObjectName("paginaConfig")
        capa = QVBoxLayout(self)
        capa.setContentsMargins(40, 36, 40, 0)
        capa.setAlignment(Qt.AlignTop)
        capa.addWidget(SubtitleLabel("Ajustes"))

        fila = QHBoxLayout()
        fila.addWidget(BodyLabel("Tema de la aplicación"))
        fila.addStretch(1)
        self.interruptor = SwitchButton()
        self.interruptor.setOnText("Oscuro")
        self.interruptor.setOffText("Claro")
        self.interruptor.setChecked(isDarkTheme())
        self.interruptor.checkedChanged.connect(ventana.cambiar_tema)
        fila.addWidget(self.interruptor)
        capa.addSpacing(14)
        capa.addLayout(fila)


# Cristal translúcido para la barra lateral (el rectángulo del menú de 3 rayitas).
# Se agrega sobre los estilos de Fluent; los valores alpha son la "transparencia".
CRISTAL_OSCURO = """/*cristal*/
NavigationPanel[menu=false] {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-left: none;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
}
NavigationPanel[menu=true] {
    background-color: rgba(22, 14, 42, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-left: none;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
}
"""
CRISTAL_CLARO = """/*cristal*/
NavigationPanel[menu=false] {
    background-color: rgba(255, 255, 255, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.75);
    border-left: none;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
}
NavigationPanel[menu=true] {
    background-color: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-left: none;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
}
"""


class VentanaPrincipal(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Galería de Arte")
        self.resize(1200, 760)
        try:
            self.setMicaEffectEnabled(False)
        except Exception:
            pass

        self.pagina_galeria = PaginaGaleria()
        self.pagina_grupos = PaginaSimple("paginaGrupos", "Aquí van tus grupos / colecciones")
        self.pagina_config = PaginaAjustes(self)

        # isTransparent=True quita la línea/borde y el fondo gris de Fluent
        self.addSubInterface(self.pagina_galeria, FluentIcon.PHOTO, "Galería",
                             isTransparent=True)
        self.addSubInterface(self.pagina_grupos, FluentIcon.FOLDER, "Grupos",
                             isTransparent=True)
        self.addSubInterface(self.pagina_config, FluentIcon.SETTING, "Ajustes",
                             NavigationItemPosition.BOTTOM, isTransparent=True)

        # Fondo borroso para el menú cuando se abre flotando sobre las obras
        self.fondo_menu = QLabel(self.navigationInterface.panel)
        self.fondo_menu.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.fondo_menu.hide()
        self.navigationInterface.displayModeChanged.connect(self._modo_menu_cambiado)

        self._aplicar_cristal()
        qconfig.themeChangedFinished.connect(self._aplicar_cristal)

    def _modo_menu_cambiado(self, modo):
        if modo == NavigationDisplayMode.MENU:
            self._desenfocar_menu()
        else:
            self.fondo_menu.hide()

    def _desenfocar_menu(self):
        """Captura lo que hay detrás del menú, lo desenfoca y lo usa de fondo."""
        panel = self.navigationInterface.panel
        ancho, alto = panel.expandWidth, max(panel.height(), 100)

        panel.hide()
        self.titleBar.hide()
        captura = self.grab()
        panel.show()
        self.titleBar.show()

        img = pixmap_a_pil(captura)
        f = captura.devicePixelRatio()
        img = img.crop((0, 0, int(ancho * f), int(alto * f))).resize((ancho, alto))
        chica = img.resize((max(1, ancho // 2), max(1, alto // 2)))
        borrosa = chica.filter(ImageFilter.GaussianBlur(9)).resize((ancho, alto), Image.BICUBIC)
        tinte = (14, 9, 32, 150) if isDarkTheme() else (255, 255, 255, 165)
        borrosa = Image.alpha_composite(borrosa.convert("RGBA"),
                                        Image.new("RGBA", (ancho, alto), tinte))

        # Esquinas redondeadas a la derecha + línea de luz en el borde
        salida = QPixmap(ancho, alto)
        salida.fill(Qt.transparent)
        p = QPainter(salida)
        p.setRenderHint(QPainter.Antialiasing)
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(-30, 0, ancho + 30 - 0.5, alto - 0.5), 20, 20)
        p.setClipPath(ruta)
        p.drawPixmap(0, 0, pil_a_pixmap(borrosa))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 60 if isDarkTheme() else 200), 1))
        p.drawPath(ruta)
        p.end()

        self.fondo_menu.setPixmap(salida)
        self.fondo_menu.setGeometry(0, 0, ancho, alto)
        self.fondo_menu.show()
        self.fondo_menu.lower()   # detrás de los iconos y textos del menú

    def paintEvent(self, e):
        # El fondo (degradado + resplandores) se dibuja aquí, detrás de todo,
        # así la barra lateral y la barra de arriba se ven translúcidas.
        p = QPainter(self)
        dibujar_fondo(p, self.rect())

    def _aplicar_cristal(self):
        panel = self.navigationInterface.panel
        base = panel.styleSheet().split("/*cristal*/")[0]
        panel.setStyleSheet(base + (CRISTAL_OSCURO if isDarkTheme() else CRISTAL_CLARO))
        self.update()

    def cambiar_tema(self, oscuro):
        setTheme(Theme.DARK if oscuro else Theme.LIGHT)
        self._aplicar_cristal()
        self.pagina_galeria.filtrar()   # reconstruye tarjetas con los colores del tema


if __name__ == "__main__":
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)   # Theme.LIGHT para arrancar en claro
    setThemeColor(COLOR_ACENTO)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())