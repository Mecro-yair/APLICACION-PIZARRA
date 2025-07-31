from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QColorDialog,
    QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QGridLayout, QScrollArea
)
from PyQt5.QtGui import QPainter, QPen, QPainterPath, QColor, QPixmap, QTransform, QFont, QCursor
from PyQt5.QtCore import Qt, QPoint, QRectF
import sys
from PyQt5.QtWidgets import QSizePolicy

class Trazo:
    def __init__(self, path, color, width):
        self.path = path
        self.color = color
        self.width = width

class ImagenColocada:
    def __init__(self, pixmap, pos):
        self.pixmap = pixmap
        self.pos = pos
        self.escala = 1.0
        self.confirmada = False
        self.boton_rect = QRectF()

class Miniatura(QLabel):
    def __init__(self, pixmap, ventana):
        super().__init__()
        self.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setFixedSize(100, 100)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.pixmap_original = pixmap
        self.ventana = ventana
        self.seleccionada = False
        self.actualizar_estilo()

    def mousePressEvent(self, event):
        self.ventana.marcar_miniatura_seleccionada(self)
        self.ventana.pizarra.imagen_a_colocar = self.pixmap_original

    def actualizar_estilo(self):
        if self.seleccionada:
            self.setStyleSheet("border: 3px solid #4CAF50; padding: 2px;")
        else:
            self.setStyleSheet("border: none; padding: 2px;")



class Pizarra(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent; border: none;")
        self.trazos = []
        self.undo_stack = []
        self.redo_stack = []

        self.current_path = QPainterPath()
        self.current_color = QColor(0, 0, 0)
        self.current_width = 3
        self.last_point = None

        self.imagen_a_colocar = None
        self.imagenes_colocadas = []
        self.imagen_seleccionada = None

        self.seleccion_path = QPainterPath()
        self.seleccion_activa = False
        self.seleccion_iniciada = False
        self.modo_arrastre = False
        self.trazos_seleccionados = []
        

    def set_color(self, color):
        self.current_color = color

    def add_trazo(self, path):
        self.trazos.append(Trazo(path, self.current_color, self.current_width))
        self.undo_stack.append(self.trazos[-1])
        self.redo_stack.clear()

    def clear_canvas(self):
        if self.seleccion_activa:
            # Eliminar trazos seleccionados
            self.trazos = [t for t in self.trazos if not t.path.intersects(self.seleccion_path)]

            # Eliminar imágenes que intersectan con la selección
            nuevas_imagenes = []
            for img in self.imagenes_colocadas:
                rect = QRectF(
                    img.pos.x() - img.pixmap.width() * img.escala / 2,
                    img.pos.y() - img.pixmap.height() * img.escala / 2,
                    img.pixmap.width() * img.escala,
                    img.pixmap.height() * img.escala
                )
                if not self.seleccion_path.intersects(rect):
                    nuevas_imagenes.append(img)
            self.imagenes_colocadas = nuevas_imagenes

            self.seleccion_path = QPainterPath()
            self.seleccion_activa = False
        else:
            self.trazos.clear()
            self.imagenes_colocadas.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update()

    def undo(self):
        if self.undo_stack:
            trazo = self.undo_stack.pop()
            self.trazos.remove(trazo)
            self.redo_stack.append(trazo)
            self.update()

    def redo(self):
        if self.redo_stack:
            trazo = self.redo_stack.pop()
            self.trazos.append(trazo)
            self.undo_stack.append(trazo)
            self.update()

    def mousePressEvent(self, event):
        punto = event.pos()

        if event.button() == Qt.RightButton:
            self.seleccion_path = QPainterPath()
            self.seleccion_path.moveTo(punto)
            self.seleccion_iniciada = True
            return

        if event.button() == Qt.LeftButton:
            if self.seleccion_activa and self.seleccion_path.contains(punto):
                self.modo_arrastre = True
                self.offset_seleccion = punto
                self.trazos_seleccionados = [t for t in self.trazos if t.path.intersects(self.seleccion_path)]
                return

            if self.imagen_a_colocar:
                anchura = self.imagen_a_colocar.width()
                altura = self.imagen_a_colocar.height()
                pos_centrada = punto - QPoint(anchura // 2, altura // 2)
                nueva_img = ImagenColocada(self.imagen_a_colocar, pos_centrada)
                self.imagenes_colocadas.append(nueva_img)
                self.imagen_seleccionada = nueva_img
                self.imagen_a_colocar = None
                self.update()
                return

            if self.imagen_seleccionada and not self.imagen_seleccionada.confirmada:
                if self.imagen_seleccionada.boton_rect.contains(punto):
                    self.imagen_seleccionada.confirmada = True
                    self.imagen_seleccionada = None
                    self.update()
                    return

            self.last_point = punto
            self.current_path = QPainterPath()
            self.current_path.moveTo(self.last_point)



    def mouseMoveEvent(self, event):
        punto = event.pos()

        if self.seleccion_iniciada and (event.buttons() & Qt.RightButton):
            self.seleccion_path.lineTo(punto)
            self.update()
            return

        if self.modo_arrastre and (event.buttons() & Qt.LeftButton):
            delta = punto - self.offset_seleccion
            self.offset_seleccion = punto

            transform = QTransform()
            transform.translate(delta.x(), delta.y())
            self.seleccion_path = transform.map(self.seleccion_path)
            for trazo in self.trazos_seleccionados:
                trazo.path = transform.map(trazo.path)
            self.update()
            return

        if self.imagen_seleccionada and not self.imagen_seleccionada.confirmada:
            self.imagen_seleccionada.pos = punto  # simplemente sigue al cursor, ya que el centro es el ancla
            self.update()
        elif (event.buttons() & Qt.LeftButton) and self.last_point:
            current_point = punto
            mid_point = (self.last_point + current_point) / 2
            self.current_path.quadTo(self.last_point, mid_point)
            self.last_point = current_point
            self.update()

    def mouseReleaseEvent(self, event):
        if self.seleccion_iniciada:
            self.seleccion_iniciada = False
            self.seleccion_activa = True
            self.update()
            return

        if self.modo_arrastre:
            self.modo_arrastre = False
            self.trazos_seleccionados = []
            return

        if self.last_point:
            self.add_trazo(self.current_path)
            self.current_path = QPainterPath()
            self.last_point = None
            self.update()

    def wheelEvent(self, event):
        if self.seleccion_activa:
            delta = event.angleDelta().y() / 120
            factor = 1.1 if delta > 0 else 0.9
            centro = self.seleccion_path.boundingRect().center()
            transform = QTransform()
            transform.translate(centro.x(), centro.y())
            transform.scale(factor, factor)
            transform.translate(-centro.x(), -centro.y())
            self.seleccion_path = transform.map(self.seleccion_path)
            self.update()
        elif self.imagen_seleccionada and not self.imagen_seleccionada.confirmada:
            delta = event.angleDelta().y() / 120
            escala = 1.1 if delta > 0 else 0.9
            self.imagen_seleccionada.escala *= escala
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margen = 4
        rect = self.rect().adjusted(margen, margen, -margen, -margen)
        painter.fillRect(rect, Qt.white)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawRect(rect)

        for img in self.imagenes_colocadas:
            transform = QTransform()
            transform.translate(img.pos.x(), img.pos.y())
            transform.scale(img.escala, img.escala)
            painter.setTransform(transform)

            w = img.pixmap.width()
            h = img.pixmap.height()
            painter.drawPixmap(-w // 2, -h // 2, img.pixmap)

            if not img.confirmada:
                painter.resetTransform()
                escala = img.escala
                ancho = img.pixmap.width() * escala
                alto = img.pixmap.height() * escala
                boton_rect = QRectF(img.pos.x() - 60, img.pos.y() + alto / 2 + 10, 120, 25)
                img.boton_rect = boton_rect

                painter.setBrush(QColor("#4CAF50"))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(boton_rect, 6, 6)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Segoe UI", 11, QFont.Medium))
                painter.drawText(boton_rect, Qt.AlignCenter, "Aceptar")


        painter.resetTransform()

        for trazo in self.trazos:
            pen = QPen(trazo.color, trazo.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)  # <- Añade esta línea
            painter.drawPath(trazo.path)

        if not self.current_path.isEmpty():
            pen = QPen(self.current_color, self.current_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)  # <- También aquí
            painter.drawPath(self.current_path)

        if self.seleccion_activa:
            pen = QPen(Qt.blue, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawPath(self.seleccion_path)

    def exportar_como_imagen(self, ruta, formato):
        imagen = QPixmap(self.size())
        self.render(imagen)
        imagen.save(ruta, formato.upper())

class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("logo.png"))
        self.setWindowTitle("PIZARRA THEDEVS")
        self.setStyleSheet("background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #f0f0f0, stop:1 #d0d0d0);")
        self.showFullScreen()

        self.pizarra = Pizarra()
        self.panel_imagenes = QVBoxLayout()

        self.init_ui()

    def init_ui(self):
        contenedor = QWidget()
        main_layout = QHBoxLayout()

        layout_izquierdo = QVBoxLayout()
        layout_izquierdo.setContentsMargins(0, 0, 0, 0)
        layout_izquierdo.setSpacing(0)

        # TÍTULO PRINCIPAL
        titulo = QLabel("🖊️ PIZARRA THEDEVS – ESC para salir")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFixedHeight(50)  # Altura estricta
        titulo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        titulo.setStyleSheet("""
            QLabel {
                font-size: 26px;
                font-weight: bold;
                padding: px;
                margin: 0px;
                color: #222;
                background-color: #e0e0e0;
                border-bottom: 1px solid #aaa;
            }
        """)

        layout_izquierdo.addWidget(titulo)

        botones = QGridLayout()
        colores = [("🟥", Qt.red), ("🟩", Qt.green), ("🟦", Qt.blue), ("⚫", Qt.black)]
        for i, (nombre, color) in enumerate(colores):
            btn = QPushButton(nombre)
            btn.setStyleSheet("color: white; font-size: 24px;")
            btn.clicked.connect(lambda _, c=color: self.pizarra.set_color(c))
            botones.addWidget(btn, 0, i)

        btn_color_personalizado = QPushButton("🎨")
        btn_color_personalizado.setStyleSheet("color: white; font-size: 24px;")
        btn_color_personalizado.clicked.connect(self.seleccionar_color)
        botones.addWidget(btn_color_personalizado, 0, len(colores))

        btn_imagen = QPushButton("🖼️")
        btn_imagen.setStyleSheet("color: white; font-size: 24px;")
        btn_imagen.clicked.connect(self.colocar_imagen)
        botones.addWidget(btn_imagen, 0, len(colores)+1)

        btn_deshacer = QPushButton("↩️")
        btn_deshacer.setStyleSheet("color: black; font-size: 24px;")
        btn_deshacer.clicked.connect(self.pizarra.undo)
        botones.addWidget(btn_deshacer, 0, len(colores)+2)

        btn_rehacer = QPushButton("↪️")
        btn_rehacer.setStyleSheet("color: black; font-size: 24px;")
        btn_rehacer.clicked.connect(self.pizarra.redo)
        botones.addWidget(btn_rehacer, 0, len(colores)+3)

        btn_limpiar = QPushButton("🗑️")
        btn_limpiar.setStyleSheet("color: white; font-size: 24px;")
        btn_limpiar.clicked.connect(self.pizarra.clear_canvas)
        botones.addWidget(btn_limpiar, 0, len(colores)+4)

        btn_exportar_imagen = QPushButton("💾 IMG")
        btn_exportar_imagen.setStyleSheet("color: black; font-size: 20px;")
        btn_exportar_imagen.clicked.connect(self.exportar_imagen)
        botones.addWidget(btn_exportar_imagen, 1, 0)

        layout_izquierdo.addLayout(botones)
        layout_izquierdo.addWidget(self.pizarra)

        panel_scroll = QScrollArea()
        panel_widget = QWidget()
        panel_widget.setLayout(self.panel_imagenes)
        panel_scroll.setWidget(panel_widget)
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setFixedWidth(120)

        main_layout.addLayout(layout_izquierdo)
        main_layout.addWidget(panel_scroll)
        contenedor.setLayout(main_layout)
        self.setCentralWidget(contenedor)

    def seleccionar_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pizarra.set_color(color)

    def exportar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar como imagen", "", "PNG (*.png);;JPG (*.jpg)")
        if ruta:
            formato = "png" if ruta.lower().endswith(".png") else "jpg"
            self.pizarra.exportar_como_imagen(ruta, formato)

    def colocar_imagen(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "", "Imagenes (*.png *.jpg *.bmp)")
        if archivo:
            pixmap = QPixmap(archivo)
            mini = Miniatura(pixmap, self)
            self.panel_imagenes.addWidget(mini)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.showNormal()
        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.pizarra.undo()
            elif event.key() == Qt.Key_Y:
                self.pizarra.redo()

    def marcar_miniatura_seleccionada(self, miniatura_activa):
        for i in range(self.panel_imagenes.count()):
            widget = self.panel_imagenes.itemAt(i).widget()
            if isinstance(widget, Miniatura):
                widget.seleccionada = (widget == miniatura_activa)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = Ventana()
    ventana.show()
    sys.exit(app.exec_())