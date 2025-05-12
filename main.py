import sys
from lexical import analizar_codigo_fuente, generar_tabla_tokens, generar_tabla_errores
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QStatusBar, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPlainTextEdit, QMessageBox, QSplitter, QToolBar
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QSyntaxHighlighter, QTextCharFormat


def load_svg_icon(path, color=Qt.white):
    renderer = QSvgRenderer(path)
    pixmap = QPixmap(renderer.defaultSize())
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QIcon(pixmap)

class NumberBar(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setStyleSheet("background-color: #2d2a2e; color: #ffffff; font-weight: bold;")
        self.setFont(self.editor.font())
        
        self.editor.blockCountChanged.connect(self.update)
        self.editor.updateRequest.connect(self.update)
        self.editor.verticalScrollBar().valueChanged.connect(self.update)
        self.editor.cursorPositionChanged.connect(self.update)
        
        self.adjust_width(self.editor.blockCount())

    def adjust_width(self, block_count):
        digits = len(str(block_count))
        self.setFixedWidth(20 + 10 * digits)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#2d2a2e"))

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        font_metrics = painter.fontMetrics()
        line_height = font_metrics.height()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = self.rect().bottom()

        while block.isValid() and top <= bottom:
            if block.isVisible():
                number = str(block_number + 1)
                painter.setPen(Qt.white)
                painter.drawText(0, int(top), self.width() - 5, line_height, Qt.AlignRight, number)
            block = block.next()
            top += line_height
            block_number += 1

        painter.end()

    def update(self, *args):
        self.adjust_width(self.editor.blockCount())
        self.repaint()

class CodeEditor(QPlainTextEdit):
    
    class LexicalHighlighter(QSyntaxHighlighter):
        def __init__(self, parent, lexer_func):
            super().__init__(parent)
            self.lexer_func = lexer_func
            self.token_format_map = self.create_format_map()

        def create_format_map(self):
            def fmt(color, bold=False, underline=False):
                f = QTextCharFormat()
                f.setForeground(QColor(color))
                if bold:
                    f.setFontWeight(QFont.Bold)
                if underline:
                    f.setUnderlineStyle(QTextCharFormat.WaveUnderline)
                    f.setUnderlineColor(QColor(color))
                return f

            return {
                "IDENTIFICADOR": fmt("#FCFCFA"),
                "RESERVADA": fmt("#FF6188", bold=True),
                "NUM_ENTERO": fmt("#AB9DF2"),
                "NUM_FLOTANTE": fmt("#AB9DF2"),
                "COMENTARIO": fmt("#727072"),
                "OP_ARITMETICO": fmt("#FF6188"),
                "OP_RELACIONAL": fmt("#FFD866"),
                "OP_LOGICO": fmt("#FFD866"),
                "ASIGNACION": fmt("#FF6188"),
                "DELIMITADOR": fmt("#FD9353"),
                "ERROR": fmt("#A9DC76", bold=True, underline=True),        
            }

        def highlightBlock(self, text):
            tokens, _ = self.lexer_func(text)
            for token in tokens:
                lexema = token["lexema"]
                tipo = token["tipo"]
                formato = self.token_format_map.get(tipo, QTextCharFormat())

                # Si el lexema es un símbolo, no usar \b
                if lexema.isalnum() or lexema == "_":
                    pattern = QRegExp(r'\b' + QRegExp.escape(lexema) + r'\b')
                else:
                    pattern = QRegExp(QRegExp.escape(lexema))

                index = pattern.indexIn(text, 0)
                while index >= 0:
                    length = len(lexema)
                    self.setFormat(index, length, formato)
                    index = pattern.indexIn(text, index + length)



    def __init__(self, status_bar):
        super().__init__()
        self.setFont(QFont("consolas", 12))  
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.file_path = None
        self.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.highlighter = CodeEditor.LexicalHighlighter(self.document(), lambda code: analizar_codigo_fuente(code))
        self.status_bar = status_bar
        self.is_modified = False
        self.cursorPositionChanged.connect(self.update_cursor_position)
        self.textChanged.connect(self.mark_modified)

    def update_cursor_position(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        self.status_bar.showMessage(f"Línea: {line}, Columna: {col}")

    def mark_modified(self):
        self.is_modified = True

    def reset_modified(self):
        self.is_modified = False


class IDECompilador(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2a2e;
            }
            QTabWidget {
                background-color: #2d2a2e;
            }
            QPlainTextEdit {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QToolBar {
                background-color: #2d2a2e;
            }
            QWidget {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QMenuBar {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QMenuBar::item {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #727072;
                color: #ffffff;
            }
            QMenu {
                background-color: #2d2a2e;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #727072;
                color: #ffffff;
            }
        """)

    def run_lexical_analysis(self):
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget:
            return

        text_edit = current_widget.findChild(CodeEditor)
        if not text_edit:
            return

        source_code = text_edit.toPlainText()
        tokens, errores = analizar_codigo_fuente(source_code)

        self.lexical_analysis_box.setPlainText(generar_tabla_tokens(tokens))
        self.lexical_errors_box.setPlainText(generar_tabla_errores(errores))


    def initUI(self):
        main_splitter = QSplitter(Qt.Vertical)

        editor_splitter = QSplitter(Qt.Horizontal)

        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.setStyleSheet("""
            QTabWidget::pane { background: #2d2a2e; }
            QTabBar::tab { background: #2d2a2e; color: white; padding: 5px; }
            QTabBar::tab:selected { background: #727072; }
        """)
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        self.editor_tabs.currentChanged.connect(self.update_window_title)

        self.analysis_tabs = QTabWidget()
        self.analysis_tabs.setStyleSheet("""
            QTabWidget { background-color: #2d2a2e; }
            QTabWidget::pane { background: #2d2a2e; }
            QTabBar::tab { background: #2d2a2e; color: white; padding: 5px; }
            QTabBar::tab:selected { background: #727072; }
        """)
        self.lexical_analysis_box = QPlainTextEdit()
        self.lexical_analysis_box.setReadOnly(True)
        self.lexical_analysis_box.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.analysis_tabs.addTab(self.lexical_analysis_box, "Análisis Léxico")
        self.analysis_tabs.addTab(QWidget(), "Análisis Sintáctico")
        self.analysis_tabs.addTab(QWidget(), "Análisis Semántico")
        self.analysis_tabs.addTab(QWidget(), "Código Intermedio")
        self.analysis_tabs.addTab(QWidget(), "Tabla Hash")

        for i in range(self.analysis_tabs.count()):
            widget = self.analysis_tabs.widget(i)
            widget.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")

        editor_splitter.addWidget(self.editor_tabs)
        editor_splitter.addWidget(self.analysis_tabs)

        error_tabs = QTabWidget()
        error_tabs.setStyleSheet("""
            QTabWidget { background-color: #2d2a2e; }
            QTabWidget::pane { background: #2d2a2e; }
            QTabBar::tab { background: #2d2a2e; color: white; padding: 5px; }
            QTabBar::tab:selected { background: #727072; }
        """)

        self.lexical_errors = QWidget()
        self.syntax_errors = QWidget()
        self.semantic_errors = QWidget()
        self.results = QWidget()

        self.lexical_errors.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.syntax_errors.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.semantic_errors.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.results.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")

        self.lexical_errors_box = QPlainTextEdit()
        self.lexical_errors_box.setReadOnly(True)
        self.lexical_errors_box.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        error_tabs.insertTab(0, self.lexical_errors_box, "Errores Léxicos")
        error_tabs.addTab(self.syntax_errors, "Errores Sintácticos")
        error_tabs.addTab(self.semantic_errors, "Errores Semánticos")
        error_tabs.addTab(self.results, "Resultados")

        main_splitter.addWidget(editor_splitter)
        main_splitter.addWidget(error_tabs)

        self.setCentralWidget(main_splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("background-color: #2d2a2e; color: white;")
        file_menu = menu_bar.addMenu("Archivo")
        compile_menu = menu_bar.addMenu("Compilar")
        compile_semantic = QAction(load_svg_icon("assets/play.svg"), "Compilar semántica", self)
        
        compile_menu.addAction(compile_semantic)
        compile_lexic = QAction(load_svg_icon("assets/play.svg"), "Compilar léxico", self)
        compile_lexic.triggered.connect(self.run_lexical_analysis)

        compile_menu.addAction(compile_lexic)
        compile_sintactic = QAction(load_svg_icon("assets/play.svg"), "Compilar sintáctica", self)
        
        compile_menu.addAction(compile_sintactic)
        new_action = QAction(load_svg_icon("assets/file-circle-plus.svg"), "Nuevo", self)
        new_action.triggered.connect(self.create_new_file)
        file_menu.addAction(new_action)

        open_action = QAction(load_svg_icon("assets/folder-open.svg"), "Abrir", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        close_action = QAction(load_svg_icon("assets/xmark.svg"), "Cerrar", self)
        close_action.triggered.connect(self.close_current_file)
        file_menu.addAction(close_action)
        
        save_action = QAction(load_svg_icon("assets/floppy-disk.svg"), "Guardar", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(load_svg_icon("assets/file-export.svg"), "Guardar como...", self)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setStyleSheet("background-color: #2d2a2e; padding: 5px;")
        self.toolbar.addAction(open_action)
        self.toolbar.addAction(save_action)
        self.toolbar.addAction(save_as_action)
        self.toolbar.addAction(close_action)

        self.setGeometry(100, 100, 900, 600)
        self.setWindowTitle("Compilador - IDE")

        self.create_new_file()
        self.show()

    def create_new_file(self):
        text_edit = CodeEditor(self.status_bar)
        number_bar = NumberBar(text_edit)
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(number_bar)
        layout.addWidget(text_edit)
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)
        
        self.editor_tabs.addTab(container, "Nuevo Archivo")
        self.editor_tabs.setCurrentWidget(container)
        self.update_window_title()

    def open_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir Archivo", "", "Archivos de Texto (*.txt);;Todos los archivos (*)", options=options)
        if file_name:
            with open(file_name, "r") as file:
                text_edit = CodeEditor(self.status_bar)
                text_edit.setPlainText(file.read())
                text_edit.file_path = file_name
                text_edit.reset_modified() 
                number_bar = NumberBar(text_edit)
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.addWidget(number_bar)
                layout.addWidget(text_edit)
                layout.setContentsMargins(0, 0, 0, 0)
                container.setLayout(layout)
                
                self.editor_tabs.addTab(container, file_name.split('/')[-1])
                self.editor_tabs.setCurrentWidget(container)

    def save_file(self):
        current_widget = self.editor_tabs.currentWidget()
        if current_widget:
            text_edit = current_widget.findChild(CodeEditor)
            if text_edit.file_path:
                with open(text_edit.file_path, "w") as file:
                    file.write(text_edit.toPlainText())
                text_edit.reset_modified() 
            else:
                self.save_file_as()
    
    def save_file_as(self):
        current_widget = self.editor_tabs.currentWidget()
        if current_widget:
            text_edit = current_widget.findChild(CodeEditor)
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo", "", "Archivos de Texto (*.txt);;Todos los archivos (*)", options=options)
            if file_name:
                text_edit.file_path = file_name
                self.save_file()
                self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), file_name.split('/')[-1])

    def close_editor_tab(self, index):
        current_widget = self.editor_tabs.widget(index)
        if current_widget:
            text_edit = current_widget.findChild(CodeEditor)
            if text_edit.is_modified:
                reply = QMessageBox.question(self, "Cerrar Archivo", "¿Desea guardar los cambios antes de cerrar?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                if reply == QMessageBox.Yes:
                    self.save_file()
                    self.editor_tabs.removeTab(index)
                elif reply == QMessageBox.No:
                    self.editor_tabs.removeTab(index)
            else:
                self.editor_tabs.removeTab(index)

    def close_current_file(self):
        index = self.editor_tabs.currentIndex()
        if index != -1:
            self.close_editor_tab(index)

    def compile_code(self):
        print("Compilando...")
    
    def update_window_title(self):
        current_widget = self.editor_tabs.currentWidget()
        if current_widget:
            index = self.editor_tabs.indexOf(current_widget)
            self.setWindowTitle(f"Compilador - {self.editor_tabs.tabText(index)}")
        else:
            self.setWindowTitle("Compilador - IDE")
    
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = IDECompilador()
    sys.exit(app.exec_())