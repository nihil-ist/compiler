import sys
from lexical import analizar_codigo_fuente, generar_tabla_tokens, generar_tabla_errores
from syntactic import analizar_sintacticamente, generar_tabla_errores_sintacticos
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QStatusBar, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QPlainTextEdit, QMessageBox, QSplitter, QToolBar, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QPainter, QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import QRect
import syntactic

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
        self.setFixedWidth(10 + 10 * digits)

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
                "CADENA": fmt("#A9DC76"),
                "OP_ENTRADA_SALIDA": fmt("#78DCE8"),
                "ERROR": fmt("#A9DC76", bold=True, underline=True),        
            }

        def highlightBlock(self, text):
            self.setCurrentBlockState(0)

            tokens, _ = self.lexer_func(text)
            for token in tokens:
                lexema = token["lexema"]
                tipo = token["tipo"]
                formato = self.token_format_map.get(tipo, QTextCharFormat())

                if lexema.isalnum() or lexema == "_":
                    pattern = QRegExp(r'\b' + QRegExp.escape(lexema) + r'\b')
                else:
                    pattern = QRegExp(QRegExp.escape(lexema))

                index = pattern.indexIn(text, 0)
                while index >= 0:
                    length = len(lexema)
                    self.setFormat(index, length, formato)
                    index = pattern.indexIn(text, index + length)

            comment_format = self.token_format_map.get("COMENTARIO", QTextCharFormat())
            start_tag = "/*"
            end_tag = "*/"

            if self.previousBlockState() == 1:
                start = 0
                end = text.find(end_tag)
                if end == -1:
                    self.setFormat(0, len(text), comment_format)
                    self.setCurrentBlockState(1)
                    return
                else:
                    self.setFormat(0, end + 2, comment_format)
                    self.setCurrentBlockState(0)
                    return

            start = text.find(start_tag)
            while start >= 0:
                end = text.find(end_tag, start + 2)
                if end == -1:
                    self.setFormat(start, len(text) - start, comment_format)
                    self.setCurrentBlockState(1)
                    return
                else:
                    length = end + 2 - start
                    self.setFormat(start, length, comment_format)
                    start = text.find(start_tag, end + 2)

            self.setCurrentBlockState(0)

    def __init__(self, parent):
        super().__init__(parent)
        self.setFont(QFont("consolas", 12))  
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.file_path = None
        self.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.highlighter = CodeEditor.LexicalHighlighter(self.document(), lambda code: analizar_codigo_fuente(code))
        self.is_modified = False
        self.cursorPositionChanged.connect(self.update_cursor_position)
        self.textChanged.connect(self.mark_modified)

    def update_cursor_position(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        parent = self.parent()
        while parent and not hasattr(parent, 'status_bar'):
            parent = parent.parent()
        if parent and hasattr(parent, 'status_bar') and parent.status_bar:
            parent.status_bar.showMessage(f"Línea: {line}, Columna: {col}")
        else:
            print(f"Error: status_bar no está inicializado en {parent}")

    def mark_modified(self):
        self.is_modified = True

    def reset_modified(self):
        self.is_modified = False

class TreeIndentDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() == 0:  # Columna "Nodo" (valores)
            depth = 0
            parent = index.parent()
            while parent.isValid():
                depth += 1
                parent = parent.parent()
            option.rect = QRect(option.rect.left() + depth * 15, option.rect.top(), 
                                option.rect.width() - depth * 15, option.rect.height())
        super().paint(painter, option, index)

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
            QTreeWidget {
                background-color: #2d2a2e;
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

    def run_syntactic_analysis(self):
        current_widget = self.editor_tabs.currentWidget()
        if not current_widget:
            return
        text_edit = current_widget.findChild(CodeEditor)
        if not text_edit:
            return
        source_code = text_edit.toPlainText()
        tokens, _ = analizar_codigo_fuente(source_code)
        filtered_tokens = [t for t in tokens if t["tipo"] not in ("COMENTARIO", "ERROR")]
        print("Tokens filtrados:", filtered_tokens)
        ast, errores = analizar_sintacticamente(filtered_tokens)
        
        self.syntax_analysis_box.setPlainText(str(ast))
        self.ast_tree.clear()
        self.populate_tree(ast, self.ast_tree.invisibleRootItem())
        self.syntax_errors_box.setPlainText(generar_tabla_errores_sintacticos(errores))

    def populate_tree(self, nodo, parent):
        # Tipos de nodos a omitir (excluir nodos intermedios sin valor significativo)
        excluded_types = [
            "programa", "lista_sentencias", "lista_declaracion", "expresion",
            "expresion_logica", "expresion_relacional", "expresion_aritmetica",
            "termino", "factor", "sent_in", "sent_out"
        ]
        
        # Si el nodo es de un tipo excluido y tiene hijos, procesar solo los hijos
        if nodo.tipo in excluded_types and nodo.hijos:
            for hijo in nodo.hijos:
                self.populate_tree(hijo, parent)
            return
        
        # Crear item para nodos visibles, incluyendo estructuras de control
        item = QTreeWidgetItem(parent)
        # Columna 0: Nodo
        if nodo.tipo == "ASIGNACION":
            item.setText(0, nodo.valor or "=")
        elif nodo.tipo in ("int", "float", "bool") or \
             (nodo.tipo == "RESERVADA" and nodo.valor in ("int", "float", "bool", "if", "then", "else", "end", "while", "do", "until")):
            item.setText(0, nodo.valor or nodo.tipo)
        elif nodo.tipo == "expresion_aritmetica":
            item.setText(0, "")  # No mostrar el tipo, solo los hijos
        else:
            item.setText(0, nodo.valor or "")
        # Columna 1: Tipo
        if nodo.tipo == "ASIGNACION":
            item.setText(1, nodo.valor or "=")
        elif nodo.tipo in ("int", "float", "bool") or \
             (nodo.tipo == "RESERVADA" and nodo.valor in ("int", "float", "bool", "if", "then", "else", "end", "while", "do", "until")):
            item.setText(1, nodo.tipo)
        elif nodo.tipo == "expresion_aritmetica":
            item.setText(1, "expresion_aritmetica")
        else:
            item.setText(1, nodo.tipo)
        # Columnas 2 y 3: Línea y Columna
        item.setText(2, str(nodo.linea or ""))
        item.setText(3, str(nodo.columna or ""))
        # Procesar hijos, incluyendo anidamiento de estructuras de control
        for hijo in nodo.hijos:
            self.populate_tree(hijo, item)
        # Expandir automáticamente para ver la estructura
        item.setExpanded(True)


    def initUI(self):
        self.main_splitter = QSplitter(Qt.Vertical)
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

        ast_widget = QWidget()
        ast_layout = QVBoxLayout()
        ast_toolbar = QToolBar()
        ast_toolbar.setStyleSheet("background-color: #2d2a2e; padding: 5px;")
        expand_action = QAction(QIcon("assets/expand.svg"), "Expandir Todo", self)
        expand_action.triggered.connect(self.expand_all)
        ast_toolbar.addAction(expand_action)
        collapse_action = QAction(QIcon("assets/collapse.svg"), "Colapsar Todo", self)
        collapse_action.triggered.connect(self.collapse_all)
        ast_toolbar.addAction(collapse_action)

        self.ast_tree = QTreeWidget()
        self.ast_tree.setHeaderLabels(["Nodo", "Tipo", "Ln", "Col"])
        self.ast_tree.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.ast_tree.setItemDelegateForColumn(0, TreeIndentDelegate())
        ast_layout.addWidget(ast_toolbar)
        ast_layout.addWidget(self.ast_tree)
        ast_widget.setLayout(ast_layout)
        self.analysis_tabs.addTab(ast_widget, "Árbol Sintáctico")

        self.syntax_analysis_box = QPlainTextEdit()
        self.syntax_analysis_box.setReadOnly(True)
        self.syntax_analysis_box.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        self.analysis_tabs.addTab(self.syntax_analysis_box, "Análisis Sintáctico")
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
        self.lexical_errors_box = QPlainTextEdit()
        self.lexical_errors_box.setReadOnly(True)
        self.lexical_errors_box.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        error_tabs.addTab(self.lexical_errors_box, "Errores Léxicos")
        self.syntax_errors_box = QPlainTextEdit()
        self.syntax_errors_box.setReadOnly(True)
        self.syntax_errors_box.setStyleSheet("background-color: #2d2a2e; color: #ffffff;")
        error_tabs.addTab(self.syntax_errors_box, "Errores Sintácticos")
        error_tabs.addTab(QWidget(), "Errores Semánticos")
        error_tabs.addTab(QWidget(), "Resultados")

        self.main_splitter.addWidget(editor_splitter)
        self.main_splitter.addWidget(error_tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")

        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("background-color: #2d2a2e; color: white;")
        file_menu = menu_bar.addMenu("Archivo")
        compile_menu = menu_bar.addMenu("Compilar")

        compile_lexic = QAction(QIcon("assets/play.svg"), "Compilar léxico", self)
        compile_lexic.triggered.connect(self.run_lexical_analysis)
        compile_menu.addAction(compile_lexic)
        compile_sintactic = QAction(QIcon("assets/play.svg"), "Compilar sintáctica", self)
        compile_sintactic.triggered.connect(self.run_syntactic_analysis)
        compile_menu.addAction(compile_sintactic)

        new_action = QAction(QIcon("assets/file-circle-plus.svg"), "Nuevo", self)
        new_action.triggered.connect(self.create_new_file)
        file_menu.addAction(new_action)
        open_action = QAction(QIcon("assets/folder-open.svg"), "Abrir", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        close_action = QAction(QIcon("assets/xmark.svg"), "Cerrar", self)
        close_action.triggered.connect(self.close_current_file)
        file_menu.addAction(close_action)
        save_action = QAction(QIcon("assets/floppy-disk.svg"), "Guardar", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        save_as_action = QAction(QIcon("assets/file-export.svg"), "Guardar como...", self)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setStyleSheet("background-color: #2d2a2e; padding: 5px;")
        self.toolbar.addAction(open_action)
        self.toolbar.addAction(save_action)
        self.toolbar.addAction(save_as_action)
        self.toolbar.addAction(close_action)

        self.setCentralWidget(self.main_splitter)
        self.setGeometry(100, 100, 900, 600)
        self.setWindowTitle("Compilador - IDE")
        self.create_new_file()
        self.show()

    def create_new_file(self):
        try:
            text_edit = CodeEditor(self)
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
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear un nuevo archivo: {str(e)}")
            print(f"Error en create_new_file: {str(e)}")

    def open_file(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Abrir archivo", "", "Archivos de texto (*.txt);;Todos los archivos (*)")
            if file_name:
                with open(file_name, 'r', encoding='utf-8') as file:
                    content = file.read()
                container = QWidget()
                layout = QHBoxLayout()
                editor = CodeEditor(self)
                editor.setPlainText(content)
                number_bar = NumberBar(editor)
                layout.addWidget(number_bar)
                layout.addWidget(editor)
                layout.setContentsMargins(0, 0, 0, 0)
                container.setLayout(layout)
                if not hasattr(self, 'editor_tabs') or self.editor_tabs is None:
                    raise RuntimeError("editor_tabs no está inicializado")
                self.editor_tabs.addTab(container, file_name.split('/')[-1])
                self.editor_tabs.setCurrentWidget(container)
                self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el archivo: {str(e)}")
            print(f"Error en open_file: {str(e)}")

    def save_file(self):
        try:
            current_widget = self.editor_tabs.currentWidget()
            if current_widget:
                text_edit = current_widget.findChild(CodeEditor)
                if text_edit.file_path:
                    with open(text_edit.file_path, "w", encoding='utf-8') as file:
                        file.write(text_edit.toPlainText())
                    text_edit.reset_modified()
                else:
                    self.save_file_as()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {str(e)}")
            print(f"Error en save_file: {str(e)}")

    def save_file_as(self):
        try:
            current_widget = self.editor_tabs.currentWidget()
            if current_widget:
                text_edit = current_widget.findChild(CodeEditor)
                file_name, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo", "", "Archivos de Texto (*.txt);;Todos los archivos (*)")
                if file_name:
                    text_edit.file_path = file_name
                    self.save_file()
                    self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), file_name.split('/')[-1])
                    self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo: {str(e)}")
            print(f"Error en save_file_as: {str(e)}")

    def close_editor_tab(self, index):
        try:
            if self.editor_tabs.count() > 1:
                self.editor_tabs.removeTab(index)
            else:
                editor = self.editor_tabs.widget(index).findChild(CodeEditor)
                if editor:
                    editor.clear()
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cerrar la pestaña: {str(e)}")
            print(f"Error en close_editor_tab: {str(e)}")

    def close_current_file(self):
        try:
            index = self.editor_tabs.currentIndex()
            if index != -1:
                self.close_editor_tab(index)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cerrar el archivo: {str(e)}")
            print(f"Error en close_current_file: {str(e)}")

    def compile_code(self):
        print("Compilando...")

    def update_window_title(self):
        try:
            current_widget = self.editor_tabs.currentWidget()
            if current_widget:
                index = self.editor_tabs.indexOf(current_widget)
                self.setWindowTitle(f"Compilador - {self.editor_tabs.tabText(index)}")
            else:
                self.setWindowTitle("Compilador - IDE")
        except Exception as e:
            print(f"Error en update_window_title: {str(e)}")

    def expand_all(self):
        self.ast_tree.expandAll()

    def collapse_all(self):
        self.ast_tree.collapseAll()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = IDECompilador()
    sys.exit(app.exec_())