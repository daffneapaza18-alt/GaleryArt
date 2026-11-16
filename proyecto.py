import sys
import random

from PIL import Image, ImageDraw
import qtawesome as qta

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea
)
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition, SearchLineEdit,
    PushButton, BodyLabel, CaptionLabel, InfoBar, InfoBarPosition,
    setTheme, Theme
)

ANCHO_TARJETA = 220
COLUMNAS = 4


# ---------- Utilidades de imagen (Pillow -> Qt) ----------
def crear_imagen_demo(ancho, alto):
    """Genera una imagen de prueba con degradado (Pillow)."""
    c1 = tuple(random.randint(40, 255) for _ in range(3))
    c2 = tuple(random.randint(40, 255) for _ in range(3))
    img = Image.new("RGB", (ancho, alto))
    dibujo = ImageDraw.Draw(img)
    for y in range(alto):
        t = y / alto
        color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        dibujo.line([(0, y), (ancho, y)], fill=color)
    return img


def pil_a_pixmap(img):
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def redondear(pix, radio=16):
    """Devuelve el pixmap con esquinas redondeadas."""
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


# ---------- Clases (POO) ----------
class Obra:
    def __init__(self, titulo, artista, categoria, alto):
        self.titulo = titulo
        self.artista = artista
        self.categoria = categoria
        self.alto = alto
        self.pixmap = redondear(pil_a_pixmap(crear_imagen_demo(ANCHO_TARJETA, alto)))


class TarjetaObra(QWidget):
    """Una tarjeta: imagen redondeada + título + artista."""
    clic = Signal(object)

    def __init__(self, obra):
        super().__init__()
        self.obra = obra
        self.setFixedWidth(ANCHO_TARJETA)
        self.setCursor(Qt.PointingHandCursor)

        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 8)
        capa.setSpacing(4)

        from PySide6.QtWidgets import QLabel
        imagen = QLabel()
        imagen.setPixmap(obra.pixmap)
        capa.addWidget(imagen)
        capa.addWidget(BodyLabel(obra.titulo))
        capa.addWidget(CaptionLabel(f"{obra.artista} · {obra.categoria}"))

    def mousePressEvent(self, evento):
        self.clic.emit(self.obra)


class CuadriculaMosaico(QScrollArea):
    """Cuadrícula tipo Pinterest: cada tarjeta va en la columna más corta."""

    def __init__(self, al_hacer_clic):
        super().__init__()
        self.al_hacer_clic = al_hacer_clic
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea{border:none;background:transparent}")

        self.contenido = QWidget()
        self.contenido.setStyleSheet("background:transparent")
        self.setWidget(self.contenido)

        self.fila = QHBoxLayout(self.contenido)
        self.fila.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.fila.setSpacing(16)

    def mostrar(self, obras):
        # Limpiar lo anterior
        while self.fila.count():
            item = self.fila.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        columnas, alturas = [], [0] * COLUMNAS
        for _ in range(COLUMNAS):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignTop)
            col.setSpacing(8)
            contenedor = QWidget()
            contenedor.setLayout(col)
            self.fila.addWidget(contenedor)
            columnas.append(col)

        for obra in obras:
            i = alturas.index(min(alturas))  # columna más corta
            tarjeta = TarjetaObra(obra)
            tarjeta.clic.connect(self.al_hacer_clic)
            columnas[i].addWidget(tarjeta)
            alturas[i] += obra.alto + 50


class PaginaGaleria(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("paginaGaleria")  # obligatorio en FluentWindow

        titulos = ["Luna", "Mar", "Bosque", "Retrato", "Atardecer", "Ciudad",
                   "Flores", "Abstracto", "Montaña", "Gato", "Noche", "Desierto"]
        artistas = ["Ana", "Luis", "Marta", "Pablo"]
        categorias = ["Pintura", "Escultura", "Fotografía"]
        self.obras = [
            Obra(random.choice(titulos), random.choice(artistas),
                 random.choice(categorias), random.randint(180, 340))
            for _ in range(20)
        ]

        capa = QVBoxLayout(self)
        capa.setContentsMargins(24, 24, 24, 0)

        barra = QHBoxLayout()
        self.buscador = SearchLineEdit()
        self.buscador.setPlaceholderText("Buscar por nombre, artista o categoría...")
        self.buscador.setFixedHeight(40)
        self.buscador.textChanged.connect(self.filtrar)

        boton = PushButton("Agregar obra")
        boton.setIcon(qta.icon("fa5s.plus", color="white"))
        boton.clicked.connect(self.agregar)

        barra.addWidget(self.buscador, 1)
        barra.addWidget(boton)
        capa.addLayout(barra)

        self.cuadricula = CuadriculaMosaico(self.abrir_obra)
        capa.addWidget(self.cuadricula)
        self.cuadricula.mostrar(self.obras)

    def filtrar(self, texto):
        t = texto.lower()
        resultado = [o for o in self.obras
                     if t in o.titulo.lower() or t in o.artista.lower()
                     or t in o.categoria.lower()]
        self.cuadricula.mostrar(resultado)

    def abrir_obra(self, obra):
        InfoBar.info(
            title=obra.titulo,
            content=f"{obra.artista} · {obra.categoria}",
            parent=self.window(),
            position=InfoBarPosition.TOP_RIGHT,
            duration=2500,
        )

    def agregar(self):
        InfoBar.success(
            title="Listo",
            content="Aquí abrirías tu ventana de agregar obra",
            parent=self.window(),
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
        )


class PaginaSimple(QWidget):
    def __init__(self, nombre, texto):
        super().__init__()
        self.setObjectName(nombre)
        capa = QVBoxLayout(self)
        capa.setAlignment(Qt.AlignCenter)
        capa.addWidget(BodyLabel(texto))


class VentanaPrincipal(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Galería de Arte")
        self.resize(1100, 700)

        self.pagina_galeria = PaginaGaleria()
        self.pagina_grupos = PaginaSimple("paginaGrupos", "Aquí van tus grupos / colecciones")
        self.pagina_config = PaginaSimple("paginaConfig", "Configuración")

        self.addSubInterface(self.pagina_galeria, FluentIcon.PHOTO, "Galería")
        self.addSubInterface(self.pagina_grupos, FluentIcon.FOLDER, "Grupos")
        self.addSubInterface(self.pagina_config, FluentIcon.SETTING, "Ajustes",
                             NavigationItemPosition.BOTTOM)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)  # cambia a Theme.LIGHT para modo claro
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())