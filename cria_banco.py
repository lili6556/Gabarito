import sqlite3

# Nome do banco de dados
DB = 'usuarios.db'

# Conectar ao banco de dados (se não existir, será criado)
conn = sqlite3.connect(DB)

# Criar um cursor
cursor = conn.cursor()

# Criar a tabela usuarios
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL
    )
''')

# Salvar as alterações e fechar a conexão
conn.commit()
conn.close()

print('Banco de dados criado com sucesso!')
