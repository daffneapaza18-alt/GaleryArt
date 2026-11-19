from PySide6.QtGui import *
from qfluentwidgets import *
from seccion4_paginas import PaginaEstilos, PaginaFavoritos, PaginaGrupos, PaginaGaleria

# ======================================================================
# ★ SECCIÓN 5 · VENTANA PRINCIPAL Y COLORES
#   FluentWindow hereda de Qt. El fondo degradado y el color del tema se definen aquí.
#   El botón «Cambiar tema» (abajo del menú) alterna entre modo oscuro y claro.
# ======================================================================
class VentanaPrincipal(FluentWindow):
    def __init__(self, galeria):
        super().__init__()
        self.setWindowTitle("Galería de Arte")
        self.resize(1200, 760)
        self.setMicaEffectEnabled(False)             # usamos nuestro propio fondo
        self.navigationInterface.setExpandWidth(200)
        for pagina, icono, texto in ((PaginaGaleria(galeria), FluentIcon.PHOTO, "Galería"),
                                     (PaginaFavoritos(galeria), FluentIcon.HEART, "Favoritos"),
                                     (PaginaGrupos(galeria), FluentIcon.FOLDER, "Grupos"),
                                     (PaginaEstilos(galeria), FluentIcon.PALETTE, "Estilos")):
            self.addSubInterface(pagina, icono, texto, isTransparent=True)
        # BOTÓN de tema: abajo del menú lateral, no se queda "seleccionado"
        self.navigationInterface.addItem("tema", FluentIcon.BRIGHTNESS, "Cambiar tema", self.alternar_tema,
                                         selectable=False, position=NavigationItemPosition.BOTTOM)
        self.navigationInterface.setCollapsible(False)           # el menú lateral se queda fijo

    def alternar_tema(self):                         # oscuro <-> claro
        setTheme(Theme.LIGHT if isDarkTheme() else Theme.DARK)
        self.update()

    # COLORES: fondo con degradado (3 colores) que cambia según el tema
    def paintEvent(self, evento):
        colores = ("#191236", "#271443", "#15254D") if isDarkTheme() else ("#D1BFF3", "#ECBED5", "#C1D1F3")
        degradado = QLinearGradient(0, 0, self.width(), self.height())
        for posicion, color in zip((0, 0.5, 1), colores):
            degradado.setColorAt(posicion, QColor(color))
        QPainter(self).fillRect(self.rect(), degradado)
