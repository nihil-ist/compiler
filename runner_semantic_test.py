from lexical import analizar_codigo_fuente
from syntactic import analizar_sintacticamente
from semantic import analizar_semantica, formatear_errores_semanticos

with open('TestSemantico.txt', 'r', encoding='utf-8') as f:
    src = f.read()

tokens, lex_errors = analizar_codigo_fuente(src)
print('Lexical errors:', lex_errors)
filtered = [t for t in tokens if t['tipo'] not in ('COMENTARIO', 'ERROR')]
ast, syn_errors = analizar_sintacticamente(filtered)
print('\nSyntactic errors:', syn_errors)
print('\nAST:')
print(ast if (ast:=ast if False else ast) is not None else 'No AST')

print('\nAST (str):')
print(str(ast))

sem_res = analizar_semantica(ast)
print('\nAnnotated AST:')
print(sem_res.annotated_tree)
print('\nSymbol table:')
print(sem_res.symbol_table_text)
print('\nSemantic errors:')
print(formatear_errores_semanticos(sem_res.errors))
