# syntactic.py

class NodoAST:
    def __init__(self, tipo, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.hijos = []

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)

    def __str__(self, nivel=0):
        resultado = "  " * nivel + f"{self.tipo}: {self.valor if self.valor else ''}\n"
        for hijo in self.hijos:
            resultado += hijo.__str__(nivel + 1)
        return resultado

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errores = []

    def token_actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def avanzar(self):
        self.pos += 1

    def coincidir(self, tipo_esperado, lexema_esperado=None):
        actual = self.token_actual()
        if actual and actual["tipo"] == tipo_esperado and (lexema_esperado is None or actual["lexema"] == lexema_esperado):
            self.avanzar()
            return actual
        else:
            if actual:
                mensaje = f"Se esperaba '{lexema_esperado or tipo_esperado}' pero se encontró '{actual['lexema']}' ({actual['tipo']}) en línea {actual['linea']}, columna {actual['columna']}"
                self.errores.append(mensaje)
                sincronizadores = {";", "}", "end", "while", "do", "if", "else", "cin", "cout", "then", "main", "int", "float", "bool"}
                while actual and actual["lexema"] not in sincronizadores:
                    self.avanzar()
                    actual = self.token_actual()
                if actual and actual["lexema"] in sincronizadores:
                    self.avanzar()
            else:
                self.errores.append(f"Fin inesperado, se esperaba '{lexema_esperado or tipo_esperado}'")
            return None

    def analizar(self):
        ast = self.programa()
        return ast, self.errores

    def programa(self):
        nodo = NodoAST("programa")
        if not self.coincidir("RESERVADA", "main"):
            return nodo
        nodo.agregar_hijo(NodoAST("main", "main"))

        if not self.coincidir("DELIMITADOR", "{"):
            return nodo
        nodo.agregar_hijo(NodoAST("{", "{"))

        declaraciones = self.lista_declaracion()
        if declaraciones:
            nodo.agregar_hijo(declaraciones)

        if not self.coincidir("DELIMITADOR", "}"):
            return nodo
        nodo.agregar_hijo(NodoAST("}", "}"))

        return nodo

    def lista_declaracion(self):
        print("Iniciando lista_declaracion, token actual:", self.token_actual())
        nodo = NodoAST("lista_declaracion")
        actual = self.token_actual()
        while actual and actual["lexema"] != "}":
            if actual["tipo"] == "RESERVADA" and actual["lexema"] in ("int", "float", "bool"):
                decl = self.declaracion_variable()
                if decl:
                    nodo.agregar_hijo(decl)
            elif actual["tipo"] == "IDENTIFICADOR" or (actual["tipo"] == "RESERVADA" and actual["lexema"] in ("if", "while", "do", "cin", "cout")):
                sent = self.sentencia()
                if sent:
                    nodo.agregar_hijo(sent)
            else:
                self.errores.append(f"Token inesperado '{actual['lexema']}' en línea {actual['linea']}, columna {actual['columna']}")
                self.avanzar()  # Avanzar para evitar bucles infinitos
            actual = self.token_actual()
        print("Fin de lista_declaracion, token actual:", self.token_actual())
        return nodo

    def declaracion(self):
        actual = self.token_actual()
        if actual is None:
            return None
        if actual["tipo"] == "RESERVADA" and actual["lexema"] in ("int", "float", "bool"):
            return self.declaracion_variable()
        elif actual["tipo"] in ("RESERVADA", "IDENTIFICADOR"):
            return self.sentencia()
        return None

    def declaracion_variable(self):
        nodo = NodoAST("declaracion_variable")
        tipo = self.coincidir("RESERVADA")
        if not tipo:
            return nodo
        nodo.agregar_hijo(NodoAST("tipo", tipo["lexema"]))

        id_token = self.coincidir("IDENTIFICADOR")
        if not id_token:
            return nodo
        nodo.agregar_hijo(NodoAST("identificador", id_token["lexema"]))

        while self.token_actual() and self.token_actual()["lexema"] == ",":
            self.avanzar()
            coma_node = NodoAST("coma", ",")
            siguiente_id = self.coincidir("IDENTIFICADOR")
            if siguiente_id:
                coma_node.agregar_hijo(NodoAST("identificador", siguiente_id["lexema"]))
                nodo.agregar_hijo(coma_node)

        if not self.coincidir("DELIMITADOR", ";"):
            return nodo
        nodo.agregar_hijo(NodoAST(";", ";"))

        return nodo

    def sentencia(self):
        actual = self.token_actual()
        if not actual:
            return None
        if actual["tipo"] == "IDENTIFICADOR":
            return self.asignacion()
        elif actual["tipo"] == "RESERVADA":
            if actual["lexema"] == "if":
                return self.seleccion()
            elif actual["lexema"] == "while":
                return self.iteracion()
            elif actual["lexema"] == "do":
                return self.repeticion()
            elif actual["lexema"] == "cin":
                return self.sent_in()
            elif actual["lexema"] == "cout":
                return self.sent_out()
        return None

    def seleccion(self):
        print("Iniciando seleccion, token actual:", self.token_actual())
        nodo = NodoAST("seleccion")
        if not self.coincidir("RESERVADA", "if"):
            return nodo
        nodo.agregar_hijo(NodoAST("if"))

        expr = self.expresion()
        if expr:
            nodo.agregar_hijo(expr)

        if not self.coincidir("RESERVADA", "then"):
            return nodo
        nodo.agregar_hijo(NodoAST("then"))

        if self.token_actual() and self.token_actual()["lexema"] == "{":
            self.coincidir("DELIMITADOR", "{")
            nodo.agregar_hijo(NodoAST("{", "{"))
            cuerpo_then = self.lista_sentencias()
            if cuerpo_then:
                nodo.agregar_hijo(cuerpo_then)
            if not self.coincidir("DELIMITADOR", "}"):
                return nodo
            nodo.agregar_hijo(NodoAST("}", "}"))
        else:
            cuerpo_then = self.lista_sentencias()
            if cuerpo_then:
                nodo.agregar_hijo(cuerpo_then)

        if self.token_actual() and self.token_actual()["lexema"] == "else":
            self.avanzar()
            nodo.agregar_hijo(NodoAST("else"))
            if self.token_actual() and self.token_actual()["lexema"] == "{":
                self.coincidir("DELIMITADOR", "{")
                nodo.agregar_hijo(NodoAST("{", "{"))
                cuerpo_else = self.lista_sentencias()
                if cuerpo_else:
                    nodo.agregar_hijo(cuerpo_else)
                if not self.coincidir("DELIMITADOR", "}"):
                    return nodo
                nodo.agregar_hijo(NodoAST("}", "}"))
            else:
                cuerpo_else = self.lista_sentencias()
                if cuerpo_else:
                    nodo.agregar_hijo(cuerpo_else)

        if not self.coincidir("RESERVADA", "end"):
            return nodo
        nodo.agregar_hijo(NodoAST("end"))

        if not self.coincidir("DELIMITADOR", ";"):
            return nodo
        nodo.agregar_hijo(NodoAST(";", ";"))

        print("Fin de seleccion, token actual:", self.token_actual())
        return nodo

    def iteracion(self):
        print("Iniciando iteracion, token actual:", self.token_actual())
        nodo = NodoAST("iteracion")
        if not self.coincidir("RESERVADA", "while"):
            return nodo
        nodo.agregar_hijo(NodoAST("while"))

        expr = self.expresion()
        if expr:
            nodo.agregar_hijo(expr)

        if self.token_actual() and self.token_actual()["lexema"] == "{":
            self.coincidir("DELIMITADOR", "{")
            nodo.agregar_hijo(NodoAST("{", "{"))
            sent_list = self.lista_sentencias()
            if sent_list:
                nodo.agregar_hijo(sent_list)
            if not self.coincidir("DELIMITADOR", "}"):
                return nodo
            nodo.agregar_hijo(NodoAST("}", "}"))
        else:
            sent_list = self.lista_sentencias()
            if sent_list:
                nodo.agregar_hijo(sent_list)
            if not self.coincidir("RESERVADA", "end"):
                return nodo
            nodo.agregar_hijo(NodoAST("end"))
            if not self.coincidir("DELIMITADOR", ";"):
                return nodo
            nodo.agregar_hijo(NodoAST(";", ";"))

        print("Fin de iteracion, token actual:", self.token_actual())
        return nodo

    def repeticion(self):
        print("Iniciando repeticion, token actual:", self.token_actual())
        nodo = NodoAST("repeticion")
        if not self.coincidir("RESERVADA", "do"):
            return nodo
        nodo.agregar_hijo(NodoAST("do"))

        if self.token_actual() and self.token_actual()["lexema"] == "{":
            self.coincidir("DELIMITADOR", "{")
            nodo.agregar_hijo(NodoAST("{", "{"))
            sent_list = self.lista_sentencias()
            if sent_list:
                nodo.agregar_hijo(sent_list)
            if not self.coincidir("DELIMITADOR", "}"):
                self.errores.append(f"Se esperaba '}}' pero se encontró '{self.token_actual()['lexema']}' en línea {self.token_actual()['linea']}, columna {self.token_actual()['columna']}")
                return nodo
            nodo.agregar_hijo(NodoAST("}", "}"))
        else:
            sent_list = self.lista_sentencias()
            if sent_list:
                nodo.agregar_hijo(sent_list)

        if not self.coincidir("RESERVADA", "while"):
            self.errores.append(f"Se esperaba 'while' pero se encontró '{self.token_actual()['lexema']}' en línea {self.token_actual()['linea']}, columna {self.token_actual()['columna']}")
            return nodo
        nodo.agregar_hijo(NodoAST("while"))

        if not self.coincidir("DELIMITADOR", "("):
            return nodo
        nodo.agregar_hijo(NodoAST("(", "("))

        expr = self.expresion()  # Procesar la expresión completa, incluyendo < 20.0
        if expr:
            nodo.agregar_hijo(expr)

        if not self.coincidir("DELIMITADOR", ")"):
            self.errores.append(f"Se esperaba ')' pero se encontró '{self.token_actual()['lexema']}' en línea {self.token_actual()['linea']}, columna {self.token_actual()['columna']}")
            return nodo
        nodo.agregar_hijo(NodoAST(")", ")"))

        if not self.coincidir("DELIMITADOR", ";"):
            self.errores.append(f"Se esperaba ';' pero se encontró '{self.token_actual()['lexema']}' en línea {self.token_actual()['linea']}, columna {self.token_actual()['columna']}")
            return nodo
        nodo.agregar_hijo(NodoAST(";", ";"))

        print("Fin de repeticion, token actual:", self.token_actual())
        return nodo

    def sent_in(self):
        nodo = NodoAST("sent_in")
        if not self.coincidir("RESERVADA", "cin"):
            return nodo
        nodo.agregar_hijo(NodoAST("cin"))

        if not self.coincidir("OP_ENTRADA_SALIDA", ">>"):
            return nodo
        nodo.agregar_hijo(NodoAST(">>", ">>"))

        id_token = self.coincidir("IDENTIFICADOR")
        if id_token:
            nodo.agregar_hijo(NodoAST("id", id_token["lexema"]))

        if not self.coincidir("DELIMITADOR", ";"):
            return nodo
        nodo.agregar_hijo(NodoAST(";", ";"))

        return nodo

    def sent_out(self):
        print("Iniciando sent_out, token actual:", self.token_actual())
        nodo = NodoAST("sent_out")
        if not self.coincidir("RESERVADA", "cout"):
            return nodo
        nodo.agregar_hijo(NodoAST("cout"))

        salida = self.salida()
        if salida:
            nodo.agregar_hijo(salida)

        if not self.coincidir("DELIMITADOR", ";"):
            return nodo
        nodo.agregar_hijo(NodoAST(";", ";"))

        print("Fin de sent_out, token actual:", self.token_actual())
        return nodo

    def salida(self):
        print("Iniciando salida, token actual:", self.token_actual())
        nodo = NodoAST("salida")
        actual = self.token_actual()
        if not actual:
            return nodo

        while actual:
            if actual["tipo"] == "CADENA":
                self.avanzar()
                nodo.agregar_hijo(NodoAST("cadena", actual["lexema"]))
            else:
                expr = self.expresion()
                if expr:
                    nodo.agregar_hijo(expr)
                else:
                    break

            actual = self.token_actual()
            if actual and actual["lexema"] == "<<":
                self.coincidir("OP_ENTRADA_SALIDA", "<<")
                nodo.agregar_hijo(NodoAST("<<", "<<"))
                actual = self.token_actual()
            else:
                break

        print("Fin de salida, token actual:", self.token_actual())
        return nodo

    def asignacion(self):
        print("Iniciando asignacion, token actual:", self.token_actual())
        nodo = NodoAST("asignacion")
        id_token = self.coincidir("IDENTIFICADOR")
        if not id_token:
            return nodo
        nodo.agregar_hijo(NodoAST("id", id_token["lexema"]))

        actual = self.token_actual()
        if actual and actual["lexema"] in ("=", "++", "--"):
            op = self.coincidir("ASIGNACION")
            nodo.agregar_hijo(NodoAST(op["lexema"], op["lexema"]))
            if op["lexema"] == "=":
                expr = self.expresion()
                if expr:
                    nodo.agregar_hijo(expr)
                if not self.coincidir("DELIMITADOR", ";"):
                    return nodo
                nodo.agregar_hijo(NodoAST(";", ";"))
            else:
                if not self.coincidir("DELIMITADOR", ";"):
                    return nodo
                nodo.agregar_hijo(NodoAST(";", ";"))
        else:
            self.errores.append(f"Se esperaba '=', '++' o '--' pero se encontró '{actual['lexema']}' en línea {actual['linea']}, columna {actual['columna']}")
            return nodo
        print("Fin de asignacion, token actual:", self.token_actual())
        return nodo

    def sent_expresion(self):
        nodo = NodoAST("sent_expresion")
        if self.token_actual() and self.token_actual()["lexema"] == ";":
            self.coincidir("DELIMITADOR", ";")
            nodo.agregar_hijo(NodoAST(";", ";"))
        else:
            expr = self.expresion()
            if expr:
                nodo.agregar_hijo(expr)
            if not self.coincidir("DELIMITADOR", ";"):
                return nodo
            nodo.agregar_hijo(NodoAST(";", ";"))
        return nodo

    def expresion(self):
        print("Iniciando expresion, token actual:", self.token_actual())
        nodo = NodoAST("expresion")
        expr_simple = self.expresion_simple()
        if expr_simple:
            nodo.agregar_hijo(expr_simple)

        actual = self.token_actual()
        while actual and actual["tipo"] in ("OP_RELACIONAL", "OP_LOGICO"):
            if actual["tipo"] == "OP_RELACIONAL":
                op = self.coincidir("OP_RELACIONAL")
                nodo_op = NodoAST("rel_op", op["lexema"])
            else:
                op = self.coincidir("OP_LOGICO")
                nodo_op = NodoAST("log_op", op["lexema"])
            expr_simple2 = self.expresion_simple()
            if expr_simple2:
                nodo_op.agregar_hijo(expr_simple2)
                nodo.agregar_hijo(nodo_op)
            else:
                self.errores.append(f"Se esperaba una expresión después del operador '{op['lexema']}' en línea {op['linea']}, columna {op['columna']}")
                break
            actual = self.token_actual()
        print("Fin de expresion, token actual:", self.token_actual())
        return nodo

    def expresion_simple(self):
        nodo = NodoAST("expresion_simple")
        term = self.termino()
        if term:
            nodo.agregar_hijo(term)
        while self.token_actual() and self.token_actual()["lexema"] in ("+", "-", "++", "--"):
            op = self.coincidir("OP_ARITMETICO") or self.coincidir("ASIGNACION")
            nodo_op = NodoAST("suma_op", op["lexema"])
            term = self.termino()
            if term:
                nodo_op.agregar_hijo(term)
                nodo.agregar_hijo(nodo_op)
            else:
                self.errores.append(f"Se esperaba un término después del operador '{op['lexema']}' en línea {op['linea']}, columna {op['columna']}")
        return nodo

    def termino(self):
        nodo = NodoAST("termino")
        factor = self.factor()
        if factor:
            nodo.agregar_hijo(factor)
        while self.token_actual() and self.token_actual()["lexema"] in ("*", "/", "%"):
            op = self.coincidir("OP_ARITMETICO")
            nodo_op = NodoAST("mult_op", op["lexema"])
            factor = self.factor()
            if factor:
                nodo_op.agregar_hijo(factor)
                nodo.agregar_hijo(nodo_op)
            else:
                self.errores.append(f"Se esperaba un factor después del operador '{op['lexema']}' en línea {op['linea']}, columna {op['columna']}")
        return nodo

    def factor(self):
        nodo = NodoAST("factor")
        comp = self.componente()
        if comp:
            nodo.agregar_hijo(comp)
        while self.token_actual() and self.token_actual()["lexema"] == "^":
            op = self.coincidir("OP_ARITMETICO")
            nodo_op = NodoAST("pot_op", op["lexema"])
            comp = self.componente()
            if comp:
                nodo_op.agregar_hijo(comp)
                nodo.agregar_hijo(nodo_op)
            else:
                self.errores.append(f"Se esperaba un componente después del operador '^' en línea {op['linea']}, columna {op['columna']}")
        return nodo
        
    def componente(self):
        print("Iniciando componente, token actual:", self.token_actual())
        nodo = NodoAST("componente")
        actual = self.token_actual()
        if not actual:
            return nodo
        if actual["lexema"] == "(":
            self.avanzar()
            nodo.agregar_hijo(NodoAST("(", "("))
            expr = self.expresion()
            if expr:
                nodo.agregar_hijo(expr)
            if not self.coincidir("DELIMITADOR", ")"):
                return nodo
            nodo.agregar_hijo(NodoAST(")", ")"))
        elif actual["tipo"] in ("NUM_ENTERO", "NUM_FLOTANTE"):
            self.avanzar()
            nodo.agregar_hijo(NodoAST(actual["tipo"].lower(), actual["lexema"]))
        elif actual["tipo"] == "IDENTIFICADOR":
            self.avanzar()
            nodo.agregar_hijo(NodoAST("id", actual["lexema"]))
        elif actual["tipo"] == "RESERVADA" and actual["lexema"] in ("true", "false"):
            self.avanzar()
            nodo.agregar_hijo(NodoAST("bool_val", actual["lexema"]))
        elif actual["tipo"] == "OP_LOGICO" and actual["lexema"] == "!":
            op = self.coincidir("OP_LOGICO")
            nodo_op = NodoAST("log_op", op["lexema"])
            comp = self.componente()
            if comp:
                nodo_op.agregar_hijo(comp)
                nodo.agregar_hijo(nodo_op)
            else:
                self.errores.append(f"Se esperaba un componente después del operador lógico '{op['lexema']}' en línea {op['linea']}, columna {op['columna']}")
        return nodo

    def lista_sentencias(self):
        print("Iniciando lista_sentencias, token actual:", self.token_actual())
        nodo = NodoAST("lista_sentencias")
        actual = self.token_actual()
        while actual and (
            actual["tipo"] == "IDENTIFICADOR" or
            (actual["tipo"] == "RESERVADA" and actual["lexema"] in ("if", "while", "do", "cin", "cout"))
        ):
            stmt = self.sentencia()
            if stmt:
                nodo.agregar_hijo(stmt)
            actual = self.token_actual()
        print("Fin de lista_sentencias, token actual:", self.token_actual())
        return nodo

def generar_tabla_errores_sintacticos(errores):
    if not errores:
        return "Sin errores sintácticos encontrados."
    return "\n".join(errores)

def analizar_sintacticamente(tokens):
    parser = Parser(tokens)
    ast, errores = parser.analizar()
    return ast, errores