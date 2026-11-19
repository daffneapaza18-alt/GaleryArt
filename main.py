import sys
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme, setThemeColor
from seccion1_modelo import Galeria
from seccion5_ventana import VentanaPrincipal

# ======================================================================
# ★ ARRANQUE: tema oscuro por defecto y color principal (rosa #D62976)
# ======================================================================
def main():
    aplicacion = QApplication(sys.argv)
    setTheme(Theme.DARK)
    setThemeColor("#D62976")
    ventana = VentanaPrincipal(Galeria())
    ventana.show()
    sys.exit(aplicacion.exec())


if __name__ == "__main__":
    main()
