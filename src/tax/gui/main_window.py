import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QCheckBox, QTextEdit, QProgressBar, 
                             QFileDialog, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

# Import core modules
from core.parser import parse_bitpanda_csv, get_available_years
from core.calculator import calculate_taxes
# We will import generator later

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, csv_path, year, fifo_path, output_path):
        super().__init__()
        self.csv_path = csv_path
        self.year = year
        self.fifo_path = fifo_path
        self.output_path = output_path

    def run(self):
        try:
            self.log.emit("Iniciando procesamiento...")
            self.progress.emit(10)
            
            self.log.emit(f"Calculando impuestos para el año {self.year}...")
            # Here we call the calculator
            metadata, results, fifo = calculate_taxes(self.csv_path, self.year, self.fifo_path)
            self.progress.emit(50)
            
            self.log.emit("Generando informe PDF...")
            from pdf.generator import generate_pdf
            generate_pdf(self.output_path, metadata, results, self.year)
            self.progress.emit(80)
            
            # Save FIFO state
            fifo_out_path = f"fifo_state_{self.year}.json"
            fifo.save_state(fifo_out_path)
            self.log.emit(f"Estado FIFO guardado en: {fifo_out_path}")
            
            self.progress.emit(100)
            self.log.emit("¡Proceso completado con éxito!")
            self.finished.emit(True, self.output_path)
            
        except Exception as e:
            self.log.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BitpandaTax — Informe Fiscal España")
        
        # Set the application logo
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bitpanda_tax_logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon("bitpanda_tax_logo.png"))
            
        self.resize(700, 500)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Archivo CSV
        group_csv = QGroupBox("Archivo CSV")
        layout_csv = QHBoxLayout()
        self.txt_csv = QLineEdit()
        self.txt_csv.setReadOnly(True)
        btn_csv = QPushButton("Seleccionar CSV...")
        btn_csv.clicked.connect(self.select_csv)
        layout_csv.addWidget(self.txt_csv)
        layout_csv.addWidget(btn_csv)
        group_csv.setLayout(layout_csv)
        layout.addWidget(group_csv)
        
        # Configuración
        group_conf = QGroupBox("Configuración")
        layout_conf = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Año fiscal:"))
        self.cb_year = QComboBox()
        self.cb_year.currentTextChanged.connect(self.update_output_path)
        row1.addWidget(self.cb_year)
        layout_conf.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Cargar FIFO previo (opcional):"))
        self.txt_fifo = QLineEdit()
        btn_fifo = QPushButton("Seleccionar...")
        btn_fifo.clicked.connect(self.select_fifo)
        row2.addWidget(self.txt_fifo)
        row2.addWidget(btn_fifo)
        layout_conf.addLayout(row2)
        
        self.chk_warn = QCheckBox("Advertir si no hay FIFO previo")
        self.chk_warn.setChecked(True)
        layout_conf.addWidget(self.chk_warn)
        
        group_conf.setLayout(layout_conf)
        layout.addWidget(group_conf)
        
        # Salida
        group_out = QGroupBox("Salida")
        layout_out = QHBoxLayout()
        layout_out.addWidget(QLabel("Ruta PDF:"))
        self.txt_out = QLineEdit()
        layout_out.addWidget(self.txt_out)
        group_out.setLayout(layout_out)
        layout.addWidget(group_out)
        
        # Botones de acción
        layout_btn = QHBoxLayout()
        self.btn_gen = QPushButton("Generar Informe")
        self.btn_gen.setEnabled(False)
        self.btn_gen.clicked.connect(self.generate)
        
        self.btn_open = QPushButton("Abrir PDF")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_pdf)
        
        layout_btn.addWidget(self.btn_gen)
        layout_btn.addWidget(self.btn_open)
        layout.addLayout(layout_btn)
        
        # Log
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
    def select_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV de Bitpanda", "", "CSV Files (*.csv)")
        if filepath:
            self.txt_csv.setText(filepath)
            self.log_edit.append(f"CSV seleccionado: {filepath}")
            self.btn_gen.setEnabled(True)
            self.populate_years(filepath)
            
    def populate_years(self, filepath):
        try:
            _, df = parse_bitpanda_csv(filepath)
            years = get_available_years(df)
            self.cb_year.clear()
            for y in years:
                self.cb_year.addItem(str(y))
            if years:
                self.cb_year.setCurrentText(str(years[-1])) # Default to latest year
        except Exception as e:
            self.log_edit.append(f"Error al leer años del CSV: {e}")
            
    def select_fifo(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Seleccionar estado FIFO", "", "JSON Files (*.json)")
        if filepath:
            self.txt_fifo.setText(filepath)
            
    def update_output_path(self, year):
        if year:
            base_dir = os.path.dirname(self.txt_csv.text()) if self.txt_csv.text() else ""
            self.txt_out.setText(os.path.join(base_dir, f"informe_fiscal_{year}.pdf"))
            
    def generate(self):
        if not self.txt_fifo.text() and self.chk_warn.isChecked():
            res = QMessageBox.question(self, "Advertencia", 
                                       "No has seleccionado un archivo de estado FIFO previo.\n"
                                       "Si tienes compras de años anteriores a este CSV o no están completas, "
                                       "el coste de adquisición puede ser 0 EUR (incorrecto).\n\n"
                                       "¿Deseas continuar de todos modos?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No:
                return
                
        self.btn_gen.setEnabled(False)
        self.progress.setValue(0)
        self.log_edit.clear()
        
        self.worker = WorkerThread(
            self.txt_csv.text(), 
            self.cb_year.currentText(),
            self.txt_fifo.text() if self.txt_fifo.text() else None,
            self.txt_out.text()
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log_edit.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, success, msg):
        self.btn_gen.setEnabled(True)
        if success:
            self.btn_open.setEnabled(True)
        else:
            QMessageBox.critical(self, "Error", msg)
            
    def open_pdf(self):
        import subprocess
        pdf_path = self.txt_out.text()
        if os.path.exists(pdf_path):
            if sys.platform == "win32":
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", pdf_path])
            else:
                subprocess.call(["xdg-open", pdf_path])
        else:
            QMessageBox.warning(self, "Error", "El archivo PDF no se encuentra.")

def run_gui():
    app = QApplication(sys.argv)
    
    # Try to set a modern style
    app.setStyle("Fusion") 
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
