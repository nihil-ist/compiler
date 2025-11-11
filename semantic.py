from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

TYPE_SIZES = {
    "int": 4,
    "float": 8,
    "bool": 1,
    "string": 0,
}


@dataclass
class SymbolTableEntry:
    name: str
    type: str
    scope: str
    level: int
    offset: int
    line: Optional[int]
    column: Optional[int]
    value: Any = None
    # Lista de todas las lineas donde aparece el identificador (declaracion + usos)
    lines: List[int] = field(default_factory=list)


class SymbolTable:
    def __init__(self) -> None:
        self.scopes: List[Dict[str, SymbolTableEntry]] = [{}]
        self.scope_names: List[str] = ["global"]
        self.offset_stack: List[int] = [0]
        self.entries: List[SymbolTableEntry] = []
        self.scope_counter: int = 0

    def enter_scope(self, hint: str) -> str:
        self.scope_counter += 1
        scope_name = f"{hint or 'scope'}#{self.scope_counter}"
        self.scopes.append({})
        self.scope_names.append(scope_name)
        self.offset_stack.append(0)
        return scope_name

    def exit_scope(self) -> None:
        if len(self.scopes) <= 1:
            return
        self.scopes.pop()
        self.scope_names.pop()
        self.offset_stack.pop()

    def declare(self, name: str, sym_type: str, line: Optional[int], column: Optional[int]) -> SymbolTableEntry:
        current_scope = self.scopes[-1]
        if name in current_scope:
            raise ValueError(f"Identificador '{name}' ya declarado en el ambito actual.")
        offset = self.offset_stack[-1]
        entry = SymbolTableEntry(
            name=name,
            type=sym_type,
            scope=self.scope_names[-1],
            level=len(self.scopes) - 1,
            offset=offset,
            line=line,
            column=column,
        )
        # registrar la linea de declaracion si esta disponible
        if line is not None:
            entry.lines.append(line)
        current_scope[name] = entry
        self.entries.append(entry)
        self.offset_stack[-1] += TYPE_SIZES.get(sym_type, 4)
        return entry

    def lookup(self, name: str) -> Optional[SymbolTableEntry]:
        for scope in reversed(self.scopes):
            entry = scope.get(name)
            if entry:
                return entry
        return None

    def record_occurrence(self, name: str, line: Optional[int]) -> None:
        """Registra una aparicion (uso) del identificador en la linea dada."""
        if line is None:
            return
        for scope in reversed(self.scopes):
            entry = scope.get(name)
            if entry:
                if line not in entry.lines:
                    entry.lines.append(line)
                return

    def format(self) -> str:
        # Mostrar solo: nombre, tipo, ambito, valor, lineas (todas las apariciones)
        if not self.entries:
            return "Tabla de simbolos vacia."
        header = "{:<20}{:<10}{:<18}{:<15}{}\n".format(
            "Nombre", "Tipo", "Ambito", "Valor", "Lineas"
        )
        lines = [header, "-" * 80 + "\n"]
        for entry in self.entries:
            value_text = "-" if entry.value is None else str(entry.value)
            lines_list = ",".join(str(l) for l in sorted(set(entry.lines))) if entry.lines else "-"
            lines.append("{:<20}{:<10}{:<18}{:<15}{}\n".format(entry.name, entry.type, entry.scope, value_text, lines_list))
        return "".join(lines)


@dataclass
class SemanticAnalysisResult:
    annotated_tree: str
    symbol_table_text: str
    errors: List[str]
    entries: List[SymbolTableEntry]


class SemanticAnalyzer:
    expression_nodes = {
        "arit_op",
        "rel_op",
        "op_logico",
        "log_op",
        "num_entero",
        "num_flotante",
        "bool_val",
        "cadena",
        "id",
        "ID",
    }

    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: List[str] = []

    def analyze(self, ast_root) -> SemanticAnalysisResult:
        if ast_root is None:
            return SemanticAnalysisResult(
                annotated_tree="AST no disponible para analisis semantico.",
                symbol_table_text=self.symbol_table.format(),
                errors=["No se recibio un AST valido."],
                entries=list(self.symbol_table.entries),
            )
        self.visit(ast_root)
        annotated = self.format_annotated_tree(ast_root)
        table_text = self.symbol_table.format()
        return SemanticAnalysisResult(
            annotated_tree=annotated,
            symbol_table_text=table_text,
            errors=list(self.errors),
            entries=list(self.symbol_table.entries),
        )

    def visit(self, node) -> None:
        if node is None:
            return
        handler = getattr(self, f"visit_{node.tipo}", None)
        if handler:
            handler(node)
            return
        for child in node.hijos:
            self.visit(child)

    def visit_programa(self, node) -> None:
        node.tipo_semantico = "program"
        for child in node.hijos:
            self.visit(child)

    def visit_lista_declaracion(self, node) -> None:
        for child in node.hijos:
            self.visit(child)

    def visit_int(self, node) -> None:
        self._handle_declaration(node, "int")

    def visit_float(self, node) -> None:
        self._handle_declaration(node, "float")

    def visit_bool(self, node) -> None:
        self._handle_declaration(node, "bool")

    def visit_ASIGNACION(self, node) -> None:
        if not node.hijos:
            return
        target_node = node.hijos[0]
        expr_node = node.hijos[1] if len(node.hijos) > 1 else None
        entry = None
        if target_node.tipo in {"ID", "id"}:
            entry = self.symbol_table.lookup(target_node.valor)
            if not entry:
                self.report_error(target_node, f"Variable '{target_node.valor}' no declarada antes de la asignacion.")
            else:
                target_node.tipo_semantico = entry.type
                target_node.valor_semantico = entry.value
                # registrar uso en la tabla de simbolos
                self.symbol_table.record_occurrence(entry.name, getattr(target_node, 'linea', None))
        expr_type, expr_value = self.evaluate_expression(expr_node)
        if entry and expr_type:
            if self.is_assignment_compatible(entry.type, expr_type):
                if expr_value is not None:
                    entry.value = expr_value
                    target_node.valor_semantico = expr_value
            else:
                self.report_error(node, f"Tipos incompatibles en la asignacion a '{entry.name}': se esperaba {entry.type}, se obtuvo {expr_type}.")
        node.tipo_semantico = entry.type if entry else None
        node.valor_semantico = entry.value if entry else None

    def visit_seleccion(self, node) -> None:
        expr_node = None
        blocks: List[Any] = []
        for child in node.hijos:
            if child.tipo == "lista_sentencias":
                blocks.append(child)
            elif child.tipo not in {"if", "then", "else", "end"} and expr_node is None:
                expr_node = child
        expr_type, _ = self.evaluate_expression(expr_node)
        if expr_type and expr_type != "bool":
            self.report_error(expr_node, f"La condicion del if debe ser bool, se obtuvo {expr_type}.")
        if blocks:
            self.visit_block(blocks[0], "if_then")
        if len(blocks) > 1:
            self.visit_block(blocks[1], "if_else")
        node.tipo_semantico = "void"

    def visit_iteracion(self, node) -> None:
        expr_node = None
        body = None
        for child in node.hijos:
            if child.tipo == "lista_sentencias" and body is None:
                body = child
            elif child.tipo not in {"while", "end"} and expr_node is None:
                expr_node = child
        expr_type, _ = self.evaluate_expression(expr_node)
        if expr_type and expr_type != "bool":
            self.report_error(expr_node, f"La condicion del while debe ser bool, se obtuvo {expr_type}.")
        if body:
            self.visit_block(body, "while_body")
        node.tipo_semantico = "void"

    def visit_repeticion(self, node) -> None:
        body = None
        expr_node = None
        for child in node.hijos:
            if child.tipo == "lista_sentencias" and body is None:
                body = child
            elif child.tipo not in {"do", "until"}:
                expr_node = child
        if body:
            self.visit_block(body, "do_body")
        expr_type, _ = self.evaluate_expression(expr_node)
        if expr_type and expr_type != "bool":
            self.report_error(expr_node, f"La condicion del until debe ser bool, se obtuvo {expr_type}.")
        node.tipo_semantico = "void"

    def visit_sent_in(self, node) -> None:
        for child in node.hijos:
            if child.tipo in {"id", "ID"}:
                entry = self.symbol_table.lookup(child.valor)
                if not entry:
                    self.report_error(child, f"Variable '{child.valor}' no declarada para entrada.")
                else:
                    child.tipo_semantico = entry.type
                    child.valor_semantico = entry.value
                    self.symbol_table.record_occurrence(entry.name, getattr(child, 'linea', None))
        node.tipo_semantico = "void"

    def visit_sent_out(self, node) -> None:
        for child in node.hijos:
            if child.tipo == "cadena":
                child.tipo_semantico = "string"
                child.valor_semantico = child.valor
            elif child.tipo in {"id", "ID"}:
                self.evaluate_expression(child)
            elif child.tipo in self.expression_nodes:
                self.evaluate_expression(child)
        node.tipo_semantico = "void"

    def visit_sent_expresion(self, node) -> None:
        expr_node = None
        for child in node.hijos:
            if child.tipo in self.expression_nodes:
                expr_node = child
                break
        self.evaluate_expression(expr_node)
        node.tipo_semantico = "void"

    def visit_lista_sentencias(self, node) -> None:
        for child in node.hijos:
            self.visit(child)

    def visit_block(self, node, hint: str) -> None:
        scope_name = self.symbol_table.enter_scope(hint)
        try:
            for child in node.hijos:
                self.visit(child)
        finally:
            self.symbol_table.exit_scope()

    def _handle_declaration(self, node, declared_type: str) -> None:
        node.tipo_semantico = declared_type
        for child in node.hijos:
            if child.tipo == "ID":
                try:
                    entry = self.symbol_table.declare(child.valor, declared_type, child.linea, child.columna)
                    child.tipo_semantico = declared_type
                    child.valor_semantico = None
                except ValueError as exc:
                    self.report_error(child, str(exc))
            else:
                self.visit(child)

    def evaluate_expression(self, node) -> Tuple[Optional[str], Optional[Any]]:
        if node is None:
            return None, None
        tipo = node.tipo.lower()
        if tipo == "num_entero":
            value = self._to_int(node.valor)
            node.tipo_semantico = "int"
            node.valor_semantico = value
            return "int", value
        if tipo == "num_flotante":
            value = self._to_float(node.valor)
            node.tipo_semantico = "float"
            node.valor_semantico = value
            return "float", value
        if tipo == "bool_val":
            value = str(node.valor).lower() == "true"
            node.tipo_semantico = "bool"
            node.valor_semantico = value
            return "bool", value
        if tipo == "cadena":
            node.tipo_semantico = "string"
            node.valor_semantico = node.valor
            return "string", node.valor
        if node.tipo in {"id", "ID"}:
            entry = self.symbol_table.lookup(node.valor)
            if not entry:
                self.report_error(node, f"Identificador '{node.valor}' no declarado.")
                node.tipo_semantico = None
                node.valor_semantico = None
                return None, None
            # registrar uso en la tabla (aparece en esta linea)
            self.symbol_table.record_occurrence(entry.name, getattr(node, 'linea', None))
            node.tipo_semantico = entry.type
            node.valor_semantico = entry.value
            return entry.type, entry.value
        # Normalize checks using the lower-cased node.tipo so we accept
        # variants produced by the parser (e.g. 'OP_ARITMETICO') as well
        # as normalized names like 'arit_op', 'rel_op', 'op_logico', 'log_op'.
        if "arit" in tipo:
            return self._evaluate_arithmetic(node)
        if "rel" in tipo:
            return self._evaluate_relational(node)
        if tipo == "op_logico" or tipo == "op_logico" or "op_logico" in tipo:
            return self._evaluate_logical(node)
        if tipo == "log_op" or "log_op" in tipo:
            return self._evaluate_unary_logical(node)
        # Fallback: evaluate children to propagate annotations
        last_type: Optional[str] = None
        last_value: Optional[Any] = None
        for child in node.hijos:
            last_type, last_value = self.evaluate_expression(child)
        node.tipo_semantico = last_type
        node.valor_semantico = last_value
        return last_type, last_value

    def _evaluate_arithmetic(self, node) -> Tuple[Optional[str], Optional[Any]]:
        if len(node.hijos) < 2:
            child_type, child_value = self.evaluate_expression(node.hijos[0]) if node.hijos else (None, None)
            node.tipo_semantico = child_type
            node.valor_semantico = child_value
            return child_type, child_value
        left_type, left_value = self.evaluate_expression(node.hijos[0])
        right_type, right_value = self.evaluate_expression(node.hijos[1])
        if not self.is_numeric(left_type) or not self.is_numeric(right_type):
            self.report_error(node, f"Operador '{node.valor}' requiere operandos numericos.")
            node.tipo_semantico = None
            node.valor_semantico = None
            return None, None
        if node.valor == "%" and (left_type != "int" or right_type != "int"):
            self.report_error(node, "El operador '%' solo acepta operandos int.")
            node.tipo_semantico = None
            node.valor_semantico = None
            return None, None
        # Determine result type: if any operand is float -> float.
        # For division: if both operands are int, produce an int (truncating division).
        if node.valor == "/":
            if left_type == "int" and right_type == "int":
                result_type = "int"
            else:
                result_type = "float"
        else:
            result_type = "float" if "float" in {left_type, right_type} else "int"

        # Compute value respecting integer-division semantics when appropriate
        if node.valor == "/" and result_type == "int":
            try:
                # Truncate toward zero to match common integer-division semantics
                value = None if left_value is None or right_value is None else int(left_value / right_value)
            except ZeroDivisionError:
                self.errors.append("Division entre cero detectada.")
                value = None
        else:
            value = self.compute_arithmetic(node.valor, left_value, right_value)
        node.tipo_semantico = result_type
        node.valor_semantico = value
        return result_type, value

    def _evaluate_relational(self, node) -> Tuple[Optional[str], Optional[Any]]:
        if len(node.hijos) < 2:
            return None, None
        left_type, left_value = self.evaluate_expression(node.hijos[0])
        right_type, right_value = self.evaluate_expression(node.hijos[1])
        if node.valor in {"<", "<=", ">", ">="}:
            if not self.is_numeric(left_type) or not self.is_numeric(right_type):
                self.report_error(node, f"Operador '{node.valor}' requiere operandos numericos.")
                node.tipo_semantico = None
                node.valor_semantico = None
                return None, None
        else:
            if left_type is None or right_type is None:
                node.tipo_semantico = None
                node.valor_semantico = None
                return None, None
            if left_type != right_type:
                if self.is_numeric(left_type) and self.is_numeric(right_type):
                    pass
                else:
                    self.report_error(node, "Comparacion entre tipos incompatibles.")
                    node.tipo_semantico = None
                    node.valor_semantico = None
                    return None, None
        value = self.compute_relational(node.valor, left_value, right_value)
        node.tipo_semantico = "bool"
        node.valor_semantico = value
        return "bool", value

    def _evaluate_logical(self, node) -> Tuple[Optional[str], Optional[Any]]:
        if len(node.hijos) < 2:
            return None, None
        left_type, left_value = self.evaluate_expression(node.hijos[0])
        right_type, right_value = self.evaluate_expression(node.hijos[1])
        if left_type != "bool" or right_type != "bool":
            self.report_error(node, f"Operador '{node.valor}' requiere operandos bool.")
            node.tipo_semantico = None
            node.valor_semantico = None
            return None, None
        value = self.compute_logical(node.valor, left_value, right_value)
        node.tipo_semantico = "bool"
        node.valor_semantico = value
        return "bool", value

    def _evaluate_unary_logical(self, node) -> Tuple[Optional[str], Optional[Any]]:
        if not node.hijos:
            return None, None
        child_type, child_value = self.evaluate_expression(node.hijos[0])
        if child_type != "bool":
            self.report_error(node, "El operador '!' requiere un operando bool.")
            node.tipo_semantico = None
            node.valor_semantico = None
            return None, None
        value = None if child_value is None else not child_value
        node.tipo_semantico = "bool"
        node.valor_semantico = value
        return "bool", value

    def compute_arithmetic(self, op: str, left_value: Optional[Any], right_value: Optional[Any]) -> Optional[Any]:
        if left_value is None or right_value is None:
            return None
        try:
            if op in {"+", "++"}:
                return left_value + right_value
            if op in {"-", "--"}:
                return left_value - right_value
            if op == "*":
                return left_value * right_value
            if op == "/":
                return left_value / right_value
            if op == "%":
                return left_value % right_value
            if op == "^":
                return left_value ** right_value
        except ZeroDivisionError:
            self.errors.append("Division entre cero detectada.")
            return None
        return None

    def compute_relational(self, op: str, left_value: Optional[Any], right_value: Optional[Any]) -> Optional[bool]:
        if left_value is None or right_value is None:
            return None
        if op == "<":
            return left_value < right_value
        if op == "<=":
            return left_value <= right_value
        if op == ">":
            return left_value > right_value
        if op == ">=":
            return left_value >= right_value
        if op == "==":
            return left_value == right_value
        if op == "!=":
            return left_value != right_value
        return None

    def compute_logical(self, op: str, left_value: Optional[Any], right_value: Optional[Any]) -> Optional[bool]:
        if left_value is None or right_value is None:
            return None
        if op == "&&":
            return left_value and right_value
        if op == "||":
            return left_value or right_value
        return None

    def is_numeric(self, sym_type: Optional[str]) -> bool:
        return sym_type in {"int", "float"}

    def is_assignment_compatible(self, target_type: str, expr_type: str) -> bool:
        if target_type == expr_type:
            return True
        if target_type == "float" and expr_type == "int":
            return True
        return False

    def report_error(self, node, message: str) -> None:
        line = getattr(node, "linea", None)
        column = getattr(node, "columna", None)
        if line is not None and column is not None:
            self.errors.append(f"Linea {line}, columna {column}: {message}")
        else:
            self.errors.append(message)

    def format_annotated_tree(self, node, level: int = 0) -> str:
        indent = "  " * level
        line = f"{indent}{node.tipo}"
        if node.valor:
            line += f" ({node.valor})"
        type_attr = getattr(node, "tipo_semantico", None)
        value_attr = getattr(node, "valor_semantico", None)
        if type_attr or value_attr is not None:
            type_text = type_attr if type_attr else "-"
            value_text = "-" if value_attr is None else repr(value_attr)
            line += f" [tipo={type_text}, valor={value_text}]"
        line += "\n"
        for child in node.hijos:
            line += self.format_annotated_tree(child, level + 1)
        return line

    def _to_int(self, value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _to_float(self, value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def analizar_semantica(ast_root) -> SemanticAnalysisResult:
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(ast_root)


def formatear_errores_semanticos(errors: List[str]) -> str:
    if not errors:
        return "Sin errores semanticos."
    return "\n".join(errors)
