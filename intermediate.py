from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class TACInstruction:
    op: str
    arg1: Optional[Any] = None
    arg2: Optional[Any] = None
    result: Optional[Any] = None

    def format(self) -> str:
        if self.op == "label":
            return f"{self.result}:"
        if self.op == "goto":
            return f"goto {self.result}"
        if self.op == "if_false":
            return f"ifFalse {self.arg1} goto {self.result}"
        if self.op == "input":
            return f"input -> {self.result}"
        if self.op == "print":
            return f"print {self.arg1}"
        if self.op == "declare":
            return f"declare {self.result} : {self.arg1}"
        if self.op == "=" and self.arg2 is None:
            return f"{self.result} = {self.arg1}"
        if self.arg2 is None:
            return f"{self.result} = {self.op} {self.arg1}"
        return f"{self.result} = {self.arg1} {self.op} {self.arg2}"


@dataclass
class ExecutionResult:
    output: str
    variables: Dict[str, Any]
    errors: List[str]


class TACGenerator:
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
        "pot_op",
    }

    def __init__(self) -> None:
        self.instructions: List[TACInstruction] = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"_t{self.temp_counter}"

    def new_label(self, hint: str = "L") -> str:
        self.label_counter += 1
        return f"{hint}{self.label_counter}"

    def emit(self, op: str, arg1: Any = None, arg2: Any = None, result: Any = None) -> TACInstruction:
        inst = TACInstruction(op, arg1, arg2, result)
        self.instructions.append(inst)
        return inst

    def generate(self, ast_root) -> List[TACInstruction]:
        if ast_root is None:
            return []
        self.instructions.clear()
        self.temp_counter = 0
        self.label_counter = 0
        self._gen_node(ast_root)
        return list(self.instructions)

    def _gen_node(self, node):
        if node is None:
            return
        handler = getattr(self, f"_gen_{node.tipo}", None)
        if handler:
            handler(node)
            return
        for child in getattr(node, "hijos", []):
            self._gen_node(child)

    def _gen_programa(self, node):
        for child in node.hijos:
            self._gen_node(child)

    def _gen_lista_declaracion(self, node):
        for child in node.hijos:
            self._gen_node(child)

    def _gen_int(self, node):
        self._gen_declaracion_tipo(node, "int")

    def _gen_float(self, node):
        self._gen_declaracion_tipo(node, "float")

    def _gen_bool(self, node):
        self._gen_declaracion_tipo(node, "bool")

    def _gen_declaracion_tipo(self, node, tipo: str):
        for child in node.hijos:
            if child.tipo == "ID":
                self.emit("declare", tipo, None, child.valor)

    def _gen_ASIGNACION(self, node):
        if not node.hijos:
            return
        target = node.hijos[0]
        expr_node = node.hijos[1] if len(node.hijos) > 1 else None
        value_temp = self._gen_expr(expr_node)
        self.emit("=", value_temp, None, target.valor)

    def _gen_lista_sentencias(self, node):
        for child in node.hijos:
            self._gen_node(child)

    def _gen_sent_expresion(self, node):
        for child in node.hijos:
            if child.tipo in self.expression_nodes:
                self._gen_expr(child)

    def _gen_seleccion(self, node):
        expr_node = None
        then_block = None
        else_block = None
        temp_blocks: List[Any] = []
        for child in node.hijos:
            if child.tipo == "lista_sentencias":
                temp_blocks.append(child)
            elif child.tipo not in {"if", "then", "else", "end"}:
                expr_node = expr_node or child
        if temp_blocks:
            then_block = temp_blocks[0]
        if len(temp_blocks) > 1:
            else_block = temp_blocks[1]

        cond_temp = self._gen_expr(expr_node)
        label_else = self.new_label("Lelse")
        label_end = self.new_label("Lendif") if else_block else label_else
        self.emit("if_false", cond_temp, None, label_else)
        if then_block:
            self._gen_node(then_block)
        if else_block:
            self.emit("goto", None, None, label_end)
        self.emit("label", None, None, label_else)
        if else_block:
            self._gen_node(else_block)
            self.emit("label", None, None, label_end)

    def _gen_iteracion(self, node):
        start = self.new_label("Lwhile")
        end = self.new_label("Lwend")
        self.emit("label", None, None, start)
        expr_node = None
        body = None
        for child in node.hijos:
            if child.tipo == "lista_sentencias":
                body = child
            elif child.tipo not in {"while", "end"}:
                expr_node = expr_node or child
        cond_temp = self._gen_expr(expr_node)
        self.emit("if_false", cond_temp, None, end)
        if body:
            self._gen_node(body)
        self.emit("goto", None, None, start)
        self.emit("label", None, None, end)

    def _gen_repeticion(self, node):
        start = self.new_label("Ldo")
        self.emit("label", None, None, start)
        body = None
        expr_node = None
        for child in node.hijos:
            if child.tipo == "lista_sentencias":
                body = child
            elif child.tipo not in {"do", "until"}:
                expr_node = expr_node or child
        if body:
            self._gen_node(body)
        cond_temp = self._gen_expr(expr_node)
        self.emit("if_false", cond_temp, None, start)

    def _gen_sent_in(self, node):
        for child in node.hijos:
            if child.tipo in {"id", "ID"}:
                self.emit("input", None, None, child.valor)
                break

    def _gen_sent_out(self, node):
        for child in node.hijos:
            if child.tipo in self.expression_nodes:
                temp = self._gen_expr(child)
                self.emit("print", temp)
            elif child.tipo == "cadena":
                literal = f'"{child.valor}"'
                self.emit("print", literal)
        self.emit("print_nl")

    def _gen_expr(self, node) -> Any:
        if node is None:
            return None
        tipo = node.tipo
        if tipo in {"num_entero", "num_flotante", "bool_val"}:
            return self._literal_value(node)
        if tipo == "cadena":
            return f'"{node.valor}"'
        if tipo in {"id", "ID"}:
            return node.valor
        if tipo in {"arit_op", "rel_op", "op_logico", "log_op", "pot_op"}:
            op = node.valor
            if tipo == "log_op" or (op == "!" and len(node.hijos) == 1):
                operand = self._gen_expr(node.hijos[0]) if node.hijos else None
                temp = self.new_temp()
                self.emit(op, operand, None, temp)
                return temp
            left = self._gen_expr(node.hijos[0]) if node.hijos else None
            right = self._gen_expr(node.hijos[1]) if node.hijos and len(node.hijos) > 1 else None
            temp = self.new_temp()
            self.emit(op, left, right, temp)
            return temp
        last = None
        for child in node.hijos:
            last = self._gen_expr(child)
        return last

    def _literal_value(self, node):
        if node.tipo == "num_entero":
            try:
                return int(node.valor)
            except Exception:
                return node.valor
        if node.tipo == "num_flotante":
            try:
                return float(node.valor)
            except Exception:
                return node.valor
        if node.tipo == "bool_val":
            return True if str(node.valor).lower() == "true" else False
        return node.valor



def generar_codigo_intermedio(ast_root) -> List[TACInstruction]:
    generator = TACGenerator()
    return generator.generate(ast_root)


def formatear_codigo_intermedio(instructions: List[TACInstruction]) -> str:
    if not instructions:
        return "Sin código intermedio."
    lines: List[str] = []
    for idx, inst in enumerate(instructions):
        if inst.op == "label":
            lines.append(inst.format())
        else:
            lines.append(f"{idx:03d}: {inst.format()}")
    return "\n".join(lines)


class TACExecutor:
    def __init__(
        self,
        instructions: List[TACInstruction],
        inputs: Optional[List[str]] = None,
        input_callback: Optional[callable] = None,
        output_callback: Optional[callable] = None,
    ) -> None:
        self.instructions = instructions
        self.inputs = list(inputs) if inputs is not None else []
        self.input_callback = input_callback
        self.output_callback = output_callback
        self.env: Dict[str, Any] = {}
        self.output_parts: List[str] = []
        self.errors: List[str] = []
        self.labels = self._index_labels()

    def _index_labels(self) -> Dict[str, int]:
        labels: Dict[str, int] = {}
        for idx, inst in enumerate(self.instructions):
            if inst.op == "label" and inst.result:
                labels[inst.result] = idx
        return labels

    def _resolve(self, value: Any) -> Any:
        if isinstance(value, str):
            value = self._strip_quotes(value)
            if value.lower() in {"true", "false"}:
                return value.lower() == "true"
            if value in self.env:
                return self.env[value]
            try:
                return int(value)
            except Exception:
                try:
                    return float(value)
                except Exception:
                    return value
        return value

    def _strip_quotes(self, text: str) -> str:
        while len(text) >= 2 and (
            (text[0] == '"' and text[-1] == '"') or (text[0] == "'" and text[-1] == "'")
        ):
            text = text[1:-1]
        return text

    def _binary(self, op: str, a: Any, b: Any) -> Any:
        if op in {"+", "-", "*", "/", "%", "^"}:
            try:
                if op == "+":
                    return a + b
                if op == "-":
                    return a - b
                if op == "*":
                    return a * b
                if op == "/":
                    return a / b
                if op == "%":
                    return a % b
                if op == "^":
                    return a ** b
            except Exception as exc:
                self.errors.append(str(exc))
                return None
        if op in {"<", "<=", ">", ">=", "==", "!="}:
            try:
                if op == "<":
                    return a < b
                if op == "<=":
                    return a <= b
                if op == ">":
                    return a > b
                if op == ">=":
                    return a >= b
                if op == "==":
                    return a == b
                if op == "!=":
                    return a != b
            except Exception as exc:
                self.errors.append(str(exc))
                return None
        if op in {"&&", "||"}:
            try:
                if op == "&&":
                    return bool(a) and bool(b)
                if op == "||":
                    return bool(a) or bool(b)
            except Exception as exc:
                self.errors.append(str(exc))
                return None
        return None

    def run(self) -> ExecutionResult:
        pc = 0
        n = len(self.instructions)
        while pc < n:
            inst = self.instructions[pc]
            op = inst.op
            if op == "label":
                pc += 1
                continue
            if op == "goto":
                pc = self.labels.get(inst.result, pc + 1)
                continue
            if op == "if_false":
                cond = self._resolve(inst.arg1)
                if not cond:
                    pc = self.labels.get(inst.result, pc + 1)
                else:
                    pc += 1
                continue
            if op == "declare":
                if inst.result not in self.env:
                    self.env[inst.result] = None
                pc += 1
                continue
            if op == "input":
                if self.inputs:
                    raw = self.inputs.pop(0)
                elif self.input_callback:
                    raw = self.input_callback(f"cin >> {inst.result}: ")
                else:
                    raw = input(f"Ingrese valor para {inst.result}: ")
                value = self._auto_cast(raw)
                self.env[inst.result] = value
                pc += 1
                continue
            if op == "print":
                value = self._resolve(inst.arg1)
                if isinstance(value, bool):
                    value = "true" if value else "false"
                self.output_parts.append(str(value))
                if self.output_callback:
                    try:
                        self.output_callback(str(value))
                    except Exception:
                        pass
                pc += 1
                continue
            if op == "print_nl":
                self.output_parts.append("\n")
                if self.output_callback:
                    try:
                        self.output_callback("\n")
                    except Exception:
                        pass
                pc += 1
                continue
            if op == "=":
                value = self._resolve(inst.arg1)
                self.env[inst.result] = value
                pc += 1
                continue
            if op == "!":
                value = not bool(self._resolve(inst.arg1))
                self.env[inst.result] = value
                pc += 1
                continue
            value = self._binary(op, self._resolve(inst.arg1), self._resolve(inst.arg2))
            self.env[inst.result] = value
            pc += 1
        return ExecutionResult(output="".join(self.output_parts), variables=dict(self.env), errors=self.errors)

    def _auto_cast(self, raw: str) -> Any:
        text = raw.strip()
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        try:
            return int(text)
        except Exception:
            try:
                return float(text)
            except Exception:
                return text


def ejecutar_codigo_intermedio(
    instructions: List[TACInstruction],
    inputs: Optional[List[str]] = None,
    input_callback: Optional[callable] = None,
    output_callback: Optional[callable] = None,
) -> ExecutionResult:
    executor = TACExecutor(
        instructions,
        inputs=inputs,
        input_callback=input_callback,
        output_callback=output_callback,
    )
    return executor.run()
