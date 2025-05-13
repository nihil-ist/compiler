# lexer.py

RESERVADAS = {
    "if", "else", "end", "do", "while", "then", "until", "switch", "case",
    "int", "float", "main", "cin", "cout"
}

OPERADORES = {
    "+": "OP_ARITMETICO",
    "-": "OP_ARITMETICO",
    "*": "OP_ARITMETICO",
    "/": "OP_ARITMETICO",
    "%": "OP_ARITMETICO",
    "^": "OP_ARITMETICO",
    "==": "OP_RELACIONAL",
    "!=": "OP_RELACIONAL",
    "<": "OP_RELACIONAL",
    "<=": "OP_RELACIONAL",
    ">": "OP_RELACIONAL",
    ">=": "OP_RELACIONAL",
    "&&": "OP_LOGICO",
    "||": "OP_LOGICO",
    "!": "OP_LOGICO",
    "=": "ASIGNACION",
    "++": "ASIGNACION",
    "--": "ASIGNACION"
}

DELIMITADORES = {"(", ")", "{", "}", ",", ";"}

def es_letra(c):
    return c.isalpha() or c == "_"

def es_digito(c):
    return c.isdigit()

def analizar_codigo_fuente(codigo):
    tokens = []
    errores = []
    i = 0
    fila = 1
    columna = 1
    longitud = len(codigo)
    notValidNumber = False

    while i < longitud:
        c = codigo[i]

        # Ignorar espacios y tabulaciones
        if c in " \t":
            i += 1
            columna += 1
            continue

        # Nueva línea
        if c == "\n":
            fila += 1
            columna = 1
            i += 1
            continue

        # Comentario de una línea
        if c == "/" and i + 1 < longitud and codigo[i + 1] == "/":
            inicio_col = columna
            lexema = "//"
            i += 2
            columna += 2
            while i < longitud and codigo[i] != "\n":
                lexema += codigo[i]
                i += 1
                columna += 1
            tokens.append({"lexema": lexema, "tipo": "COMENTARIO", "linea": fila, "columna": inicio_col})
            continue

        # Comentario multilínea
        if c == "/" and i + 1 < longitud and codigo[i + 1] == "*":
            inicio_col = columna
            lexema = "/*"
            i += 2
            columna += 2
            cerrado = False
            while i < longitud:
                if codigo[i] == "*" and i + 1 < longitud and codigo[i + 1] == "/":
                    lexema += "*/"
                    i += 2
                    columna += 2
                    cerrado = True
                    break
                lexema += codigo[i]
                if codigo[i] == "\n":
                    fila += 1
                    columna = 1
                else:
                    
                    columna += 1
                i += 1
            if cerrado:
                tokens.append({"lexema": lexema, "tipo": "COMENTARIO", "linea": fila, "columna": inicio_col})
            else:
                errores.append({"linea": fila, "columna": inicio_col, "descripcion": "Comentario multilínea no cerrado", "valor": lexema})
            continue

        # Números (enteros o flotantes)
        if c.isdigit():
            inicio_col = columna
            lexema = c
            i += 1
            columna += 1
            tiene_punto = False
            while i < longitud and (codigo[i].isdigit() or (codigo[i] == '.' and not tiene_punto)):
                if codigo[i] == '.':
                    # Verificar que haya al menos un dígito después del punto
                    if i + 1 < longitud and codigo[i + 1].isdigit():
                        lexema += codigo[i]
                        tiene_punto = True
                        i += 1
                        columna += 1
                    else:
                        lexema += codigo[i]
                        notValidNumber = True
                        break  # No es un número válido, salir del bucle
                lexema += codigo[i]
                i += 1
                columna += 1
            if notValidNumber: tipo="ERROR"
            else: tipo = "NUM_FLOTANTE" if tiene_punto else "NUM_ENTERO"
            tokens.append({"lexema": lexema, "tipo": tipo, "linea": fila, "columna": inicio_col})
            continue

        # Identificadores o palabras reservadas
        if es_letra(c):
            inicio_col = columna
            lexema = c
            i += 1
            columna += 1
            while i < longitud and (es_letra(codigo[i]) or es_digito(codigo[i])):
                lexema += codigo[i]
                i += 1
                columna += 1
            tipo = "RESERVADA" if lexema in RESERVADAS else "IDENTIFICADOR"
            tokens.append({"lexema": lexema, "tipo": tipo, "linea": fila, "columna": inicio_col})
            continue

        # Operadores de dos caracteres
        if i + 1 < longitud and codigo[i:i+2] in OPERADORES:
            lexema = codigo[i:i+2]
            tokens.append({"lexema": lexema, "tipo": OPERADORES[lexema], "linea": fila, "columna": columna})
            i += 2
            columna += 2
            continue

        # Operadores de un carácter
        if c in OPERADORES:
            tokens.append({"lexema": c, "tipo": OPERADORES[c], "linea": fila, "columna": columna})
            i += 1
            columna += 1
            continue

        # Delimitadores
        if c in DELIMITADORES:
            tokens.append({"lexema": c, "tipo": "DELIMITADOR", "linea": fila, "columna": columna})
            i += 1
            columna += 1
            continue

        # Carácter no reconocido
        if notValidNumber:
            errores.append({"linea": fila, "columna": columna, "descripcion": f"Se uso un punto de forma erronea: '{c}'", "valor": c})
            notValidNumber =False
        else:
            errores.append({"linea": fila, "columna": columna, "descripcion": f"Carácter no reconocido: '{c}'", "valor": c})
            tipo = "ERROR"
            tokens.append({"lexema": c, "tipo": tipo, "linea": fila, "columna": columna})
        i += 1
        columna += 1

    return tokens, errores

def generar_tabla_tokens(tokens):
    tabla = "Lexema\t\tTipo\t\tLínea\tColumna\n"
    tabla += "-" * 50 + "\n"
    for t in tokens:
        # if (t['tipo'] != "ERROR"):
        if (t['tipo'] != "ERROR" or t['tipo'] != "COMENTARIO"):
            tabla += f"{t['lexema']}\t\t{t['tipo']}\t\t{t['linea']}\t{t['columna']}\n"
    return tabla

def generar_tabla_errores(errores):
    if not errores:
        return "Sin errores léxicos."
    tabla = "Línea\tColumna\tCarácter\tDescripción\n"
    tabla += "-" * 60 + "\n"
    for e in errores:
        tabla += f"{e['linea']}\t{e['columna']}\t{e['valor']}\t\t{e['descripcion']}\n"
    return tabla

def analizar_desde_archivo(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        codigo = f.read()
    return analizar_codigo_fuente(codigo)

def guardar_tokens(tokens, archivo="tokens.txt"):
    with open(archivo, "w", encoding="utf-8") as f:
        for t in tokens:
            f.write(f"{t['lexema']}\t{t['tipo']}\n")

def guardar_errores(errores, archivo="errores.txt"):
    with open(archivo, "w", encoding="utf-8") as f:
        for e in errores:
            f.write(f"{e['linea']}\t{e['columna']}\t{e['valor']}\t{e['descripcion']}\n")
