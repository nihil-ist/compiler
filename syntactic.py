# syntactic.py

class NodoAST:
    def __init__(self, tipo, valor=None, linea=None, columna=None, gramatica=None):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.columna = columna
        self.gramatica = gramatica
        self.hijos = []

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)

    def __str__(self, nivel=0):
        indent = "  " * nivel
        posicion = f" (línea: {self.linea}, columna: {self.columna})" if self.linea and self.columna else ""
        grama = f" [{self.gramatica}]" if self.gramatica else ""
        resultado = f"{indent}{self.tipo}: {self.valor if self.valor else ''}{posicion}{grama}\n"
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

    def crear_nodo_token(self, token, tipo=None, gramatica=None):
        return NodoAST(tipo or token["tipo"], token["lexema"], token["linea"], token["columna"], gramatica)

    def coincidir(self, tipo_esperado, lexema_esperado=None):
        actual = self.token_actual()
        if actual and actual["tipo"] == tipo_esperado and (lexema_esperado is None or actual["lexema"] == lexema_esperado):
            self.avanzar()
            return actual
        else:
            if actual:
                mensaje = f"Se esperaba '{lexema_esperado or tipo_esperado}' pero se encontró '{actual['lexema']}' ({actual['tipo']}) en línea {actual['linea']}, columna {actual['columna']}"
                self.errores.append(mensaje)
                sincronizadores = {";", "}", "end", "while", "do", "if", "else", "cin", "cout", "then", "main", "int", "float", "bool", "until"}
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
        nodo = NodoAST("programa", gramatica="programa")
        token_main = self.coincidir("RESERVADA", "main")
        if not token_main:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(token_main, "main", "programa"))

        token_llave_abrir = self.coincidir("DELIMITADOR", "{")
        if not token_llave_abrir:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(token_llave_abrir, "{", "programa"))

        declaraciones = self.lista_declaracion()
        if declaraciones:
            nodo.agregar_hijo(declaraciones)

        token_llave_cerrar = self.coincidir("DELIMITADOR", "}")
        if not token_llave_cerrar:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(token_llave_cerrar, "}", "programa"))
        return nodo

    def lista_declaracion(self):
        nodo = NodoAST("lista_declaracion", gramatica="lista_declaracion")
        while True:
            actual = self.token_actual()
            if not actual or actual["lexema"] == "}":
                break
            if actual["tipo"] == "RESERVADA" and actual["lexema"] in ("int", "float", "bool"):
                hijo = self.declaracion_variable()
            else:
                hijo = self.sentencia()
            if hijo:
                nodo.agregar_hijo(hijo)
            else:
                break
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
        nodo = NodoAST("declaracion_variable", gramatica="declaracion_variable")
        tipo = self.coincidir("RESERVADA")
        if not tipo:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(tipo, "tipo", "tipo"))

        id_token = self.coincidir("IDENTIFICADOR")
        if not id_token:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(id_token, "identificador", "identificador"))

        while self.token_actual() and self.token_actual()["lexema"] == ",":
            coma_token = self.coincidir("DELIMITADOR", ",")
            nodo_coma = self.crear_nodo_token(coma_token, "coma", "identificador")
            siguiente_id = self.coincidir("IDENTIFICADOR")
            if siguiente_id:
                nodo_coma.agregar_hijo(self.crear_nodo_token(siguiente_id, "identificador", "identificador"))
                nodo.agregar_hijo(nodo_coma)

        fin = self.coincidir("DELIMITADOR", ";")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, ";", "declaracion_variable"))
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
        nodo = NodoAST("seleccion", gramatica="seleccion")
        si = self.coincidir("RESERVADA", "if")
        if si:
            nodo.agregar_hijo(self.crear_nodo_token(si, "if", "seleccion"))
        expr = self.expresion()
        if expr:
            nodo.agregar_hijo(expr)
        entonces = self.coincidir("RESERVADA", "then")
        if entonces:
            nodo.agregar_hijo(self.crear_nodo_token(entonces, "then", "seleccion"))
        cuerpo_then = self.lista_sentencias()
        if cuerpo_then:
            nodo.agregar_hijo(cuerpo_then)
        actual = self.token_actual()
        if actual and actual["lexema"] == "else":
            sino = self.coincidir("RESERVADA", "else")
            if sino:
                nodo.agregar_hijo(self.crear_nodo_token(sino, "else", "seleccion"))
                cuerpo_else = self.lista_sentencias()
                if cuerpo_else:
                    nodo.agregar_hijo(cuerpo_else)
        fin = self.coincidir("RESERVADA", "end")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, "end", "seleccion"))
        return nodo

    def iteracion(self):
        nodo = NodoAST("iteracion", gramatica="iteracion")
        mientras = self.coincidir("RESERVADA", "while")
        if mientras:
            nodo.agregar_hijo(self.crear_nodo_token(mientras, "while", "iteracion"))
        expr = self.expresion()
        if expr:
            nodo.agregar_hijo(expr)
        cuerpo = self.lista_sentencias()
        if cuerpo:
            nodo.agregar_hijo(cuerpo)
        fin = self.coincidir("RESERVADA", "end")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, "end", "iteracion"))
        return nodo

    def repeticion(self):
        nodo = NodoAST("repeticion", gramatica="repeticion")
        hacer = self.coincidir("RESERVADA", "do")
        if hacer:
            nodo.agregar_hijo(self.crear_nodo_token(hacer, "do", "repeticion"))
        cuerpo = self.lista_sentencias()
        if cuerpo:
            nodo.agregar_hijo(cuerpo)
        hasta = self.coincidir("RESERVADA", "until")
        if hasta:
            nodo.agregar_hijo(self.crear_nodo_token(hasta, "until", "repeticion"))
        expr = self.expresion()
        if expr:
            nodo.agregar_hijo(expr)
        return nodo

    def sent_in(self):
        nodo = NodoAST("sent_in", gramatica="sent_in")
        cin = self.coincidir("RESERVADA", "cin")
        if cin:
            nodo.agregar_hijo(self.crear_nodo_token(cin, "cin", "sent_in"))
        flecha = self.coincidir("OP_ENTRADA_SALIDA", ">>")
        if flecha:
            nodo.agregar_hijo(self.crear_nodo_token(flecha, ">>", "sent_in"))
        identificador = self.coincidir("IDENTIFICADOR")
        if identificador:
            nodo.agregar_hijo(self.crear_nodo_token(identificador, "id", "sent_in"))
        fin = self.coincidir("DELIMITADOR", ";")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, ";", "sent_in"))
        return nodo

    def sent_out(self):
        nodo = NodoAST("sent_out", gramatica="sent_out")
        cout = self.coincidir("RESERVADA", "cout")
        if cout:
            nodo.agregar_hijo(self.crear_nodo_token(cout, "cout", "sent_out"))
        actual = self.token_actual()
        while actual and actual["lexema"] == "<<":
            op = self.coincidir("OP_ENTRADA_SALIDA", "<<")
            nodo.agregar_hijo(self.crear_nodo_token(op, "<<", "salida"))
            actual = self.token_actual()
            if actual["tipo"] == "CADENA":
                nodo.agregar_hijo(self.crear_nodo_token(actual, "cadena", "salida"))
                self.avanzar()
            else:
                expr = self.expresion()
                if expr:
                    nodo.agregar_hijo(expr)
            actual = self.token_actual()
        fin = self.coincidir("DELIMITADOR", ";")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, ";", "sent_out"))
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
        nodo = NodoAST("asignacion", gramatica="asignacion")
        id_token = self.coincidir("IDENTIFICADOR")
        if not id_token:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(id_token, "id", "asignacion"))

        op_token = self.coincidir("ASIGNACION")
        if not op_token:
            return nodo
        nodo.agregar_hijo(self.crear_nodo_token(op_token, op_token["lexema"], "asignacion"))

        if op_token["lexema"] == "=":
            expr = self.expresion()
            if expr:
                nodo.agregar_hijo(expr)

        fin = self.coincidir("DELIMITADOR", ";")
        if fin:
            nodo.agregar_hijo(self.crear_nodo_token(fin, ";", "asignacion"))
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
        nodo = NodoAST("expresion", gramatica="expresion")
        izq = self.expresion_relacional()
        if izq:
            nodo.agregar_hijo(izq)

        while True:
            actual = self.token_actual()
            if actual and actual["tipo"] == "OP_LOGICO":
                op_token = self.coincidir("OP_LOGICO")
                op_nodo = self.crear_nodo_token(op_token, "op_logico", "op_logico")
                der = self.expresion_relacional()
                if der:
                    op_nodo.agregar_hijo(der)
                    nodo.agregar_hijo(op_nodo)
            else:
                break
        return nodo
    
    def expresion_relacional(self):
        nodo = NodoAST("expresion_relacional", gramatica="expresion")
        izq = self.expresion_simple()
        if izq:
            nodo.agregar_hijo(izq)

        actual = self.token_actual()
        if actual and actual["tipo"] == "OP_RELACIONAL":
            op_token = self.coincidir("OP_RELACIONAL")
            op_nodo = self.crear_nodo_token(op_token, "rel_op", "rel_op")
            der = self.expresion_simple()
            if der:
                op_nodo.agregar_hijo(der)
                nodo.agregar_hijo(op_nodo)
        return nodo

    def expresion_simple(self):
        nodo = NodoAST("expresion_simple", gramatica="expresion_simple")
        term = self.termino()
        if term:
            nodo.agregar_hijo(term)

        while True:
            actual = self.token_actual()
            if actual and actual["lexema"] in ("+", "-", "++", "--"):
                op = self.coincidir(actual["tipo"])
                op_nodo = self.crear_nodo_token(op, "suma_op", "suma_op")
                t = self.termino()
                if t:
                    op_nodo.agregar_hijo(t)
                    nodo.agregar_hijo(op_nodo)
            else:
                break
        return nodo

    def termino(self):
        nodo = NodoAST("termino", gramatica="termino")
        fact = self.factor()
        if fact:
            nodo.agregar_hijo(fact)

        while True:
            actual = self.token_actual()
            if actual and actual["lexema"] in ("*", "/", "%"):
                op = self.coincidir("OP_ARITMETICO")
                op_nodo = self.crear_nodo_token(op, "mult_op", "mult_op")
                f = self.factor()
                if f:
                    op_nodo.agregar_hijo(f)
                    nodo.agregar_hijo(op_nodo)
            else:
                break
        return nodo

    def factor(self):
        nodo = NodoAST("factor", gramatica="factor")
        comp = self.componente()
        if comp:
            nodo.agregar_hijo(comp)

        while True:
            actual = self.token_actual()
            if actual and actual["lexema"] == "^":
                op = self.coincidir("OP_ARITMETICO")
                op_nodo = self.crear_nodo_token(op, "pot_op", "pot_op")
                c = self.componente()
                if c:
                    op_nodo.agregar_hijo(c)
                    nodo.agregar_hijo(op_nodo)
            else:
                break
        return nodo
        
    def componente(self):
        nodo = NodoAST("componente", gramatica="componente")
        actual = self.token_actual()
        if not actual:
            return nodo

        if actual["lexema"] == "(":
            par_izq = self.coincidir("DELIMITADOR", "(")
            nodo.agregar_hijo(self.crear_nodo_token(par_izq, "(", "componente"))
            expr = self.expresion()
            if expr:
                nodo.agregar_hijo(expr)
            par_der = self.coincidir("DELIMITADOR", ")")
            if par_der:
                nodo.agregar_hijo(self.crear_nodo_token(par_der, ")", "componente"))
        elif actual["tipo"] in ("NUM_ENTERO", "NUM_FLOTANTE"):
            nodo.agregar_hijo(self.crear_nodo_token(actual, actual["tipo"].lower(), "componente"))
            self.avanzar()
        elif actual["tipo"] == "IDENTIFICADOR":
            nodo.agregar_hijo(self.crear_nodo_token(actual, "id", "componente"))
            self.avanzar()
        elif actual["tipo"] == "RESERVADA" and actual["lexema"] in ("true", "false"):
            nodo.agregar_hijo(self.crear_nodo_token(actual, "bool_val", "componente"))
            self.avanzar()
        elif actual["tipo"] == "OP_LOGICO" and actual["lexema"] == "!":
            op = self.coincidir("OP_LOGICO", "!")
            op_nodo = self.crear_nodo_token(op, "log_op", "op_logico")
            c = self.componente()
            if c:
                op_nodo.agregar_hijo(c)
                nodo.agregar_hijo(op_nodo)
        return nodo

    def lista_sentencias(self):
        nodo = NodoAST("lista_sentencias", gramatica="lista_sentencias")
        while True:
            actual = self.token_actual()
            if not actual or actual["lexema"] in ("end", "else", "until", "}"):
                break
            sent = self.sentencia()
            if sent:
                nodo.agregar_hijo(sent)
            else:
                break
        return nodo

def generar_tabla_errores_sintacticos(errores):
    if not errores:
        return "Sin errores sintácticos encontrados."
    return "\n".join(errores)

def analizar_sintacticamente(tokens):
    parser = Parser(tokens)
    ast, errores = parser.analizar()
    return ast, errores