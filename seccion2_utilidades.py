from PySide6.QtCore import *
from PySide6.QtWidgets import *
from qfluentwidgets import *

# ======================================================================
# ★ SECCIÓN 2 · PIEZAS REUTILIZABLES (avisos, BOTONES, scroll)
# ======================================================================
def aviso(titulo, texto, padre):
    InfoBar.warning(titulo, texto, parent=padre, position=InfoBarPosition.TOP_RIGHT, duration=2500)


# BOTONES: crea un botón con ícono (editar / borrar) y le conecta su acción
def boton_icono(icono, accion):                      # botones de editar / borrar
    boton = TransparentToolButton(icono)
    boton.clicked.connect(accion)
    return boton


def vaciar(layout):                                  # quita todo lo que tenga un layout
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget:
            widget.deleteLater()


class AreaScroll(QScrollArea):                       # zona con barra para subir y bajar
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("QScrollArea{background:transparent;border:none}")
        self.viewport().setStyleSheet("background:transparent")
