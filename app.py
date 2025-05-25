from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.secret_key = 'segredo123'

DB = 'usuarios.db'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                email TEXT UNIQUE,
                senha TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gabaritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT,
                nome_prova TEXT,
                questao INTEGER,
                alternativa_correta TEXT,
                valor REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respostas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                nome_prova TEXT NOT NULL,
                nome_aluno TEXT NOT NULL,
                nota REAL NOT NULL,
                data_correcao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = usuario[1]
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('base'))
        else:
            flash('Email ou senha incorretos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        email = nome + '@gmail.com'

        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha))
            conn.commit()
            flash('Cadastro realizado com sucesso!', 'success')
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Este email já está cadastrado.', 'danger')
            conn.close()
            return redirect(url_for('cadastro'))

    return render_template('cadastro.html')

@app.route('/base')
def base():
    if 'usuario' not in session:
        flash('Faça login para acessar o painel.', 'warning')
        return redirect(url_for('login'))
    return render_template('base.html', usuario=session['usuario'])

@app.route('/definir_gabarito', methods=['GET', 'POST'])
def definir_gabarito():
    if 'usuario' not in session:
        flash('Faça login para acessar.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        usuario = session['usuario']
        nome_prova = request.form.get('nome_prova')
        num_questoes = int(request.form.get('num_questoes'))

        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM gabaritos WHERE usuario = ? AND nome_prova = ?', (usuario, nome_prova))
            conn.commit()

        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            for i in range(1, num_questoes + 1):
                alternativa = request.form.get(f'gabarito_{i}')
                valor = float(request.form.get(f'valor_{i}', 1))
                cursor.execute('''
                    INSERT INTO gabaritos (usuario, nome_prova, questao, alternativa_correta, valor)
                    VALUES (?, ?, ?, ?, ?)
                ''', (usuario, nome_prova, i, alternativa, valor))
            conn.commit()

        flash(f'Gabarito da prova "{nome_prova}" salvo com sucesso!', 'success')
        return redirect(url_for('base'))

    return render_template('definir_gabarito.html')

@app.route('/corrigir', methods=['GET', 'POST'])
def corrigir():
    if 'usuario' not in session:
        flash('Faça login para acessar.', 'warning')
        return redirect(url_for('login'))
    usuario = session['usuario']

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT nome_prova FROM gabaritos WHERE usuario = ?', (usuario,))
        provas = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        nome_prova = request.form.get('nome_prova')
        nome_aluno = request.form.get('nome_aluno')
        foto_arquivo = request.files.get('fotoGabarito')
        foto_camera = request.form.get('fotoCamera')

        if not nome_aluno or not nome_prova:
            flash('Nome da prova e do aluno são obrigatórios.', 'danger')
            return redirect(url_for('corrigir'))

        filename = secure_filename(f"{nome_aluno}_{nome_prova}.jpg")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Salvar a foto da câmera (Base64) ou o arquivo
        if foto_camera and foto_camera.startswith('data:image'):
            header, encoded = foto_camera.split(",", 1)
            image_data = base64.b64decode(encoded)
            with open(filepath, "wb") as f:
                f.write(image_data)
        elif foto_arquivo:
            foto_arquivo.save(filepath)
        else:
            flash('Nenhuma foto enviada.', 'danger')
            return redirect(url_for('corrigir'))

        # Nota fixa - você pode substituir pela lógica de correção real
        nota = 8.5

        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO respostas (usuario, nome_prova, nome_aluno, nota)
                VALUES (?, ?, ?, ?)
            ''', (usuario, nome_prova, nome_aluno, nota))
            conn.commit()

        flash(f'Prova de "{nome_aluno}" corrigida com nota {nota:.2f}!', 'success')
        return redirect(url_for('resultados'))

    return render_template('corrigir.html', provas=provas)

@app.route('/resultados')
def resultados():
    if 'usuario' not in session:
        flash('Faça login para acessar.', 'warning')
        return redirect(url_for('login'))
    usuario = session['usuario']

    prova_selecionada = request.args.get('nome_prova', None)

    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT nome_prova FROM gabaritos WHERE usuario = ?', (usuario,))
        provas = [row[0] for row in cursor.fetchall()]

        resultados = []
        media = None

        if prova_selecionada:
            cursor.execute('''
                SELECT nome_aluno, nota FROM respostas
                WHERE usuario = ? AND nome_prova = ?
                ORDER BY nome_aluno
            ''', (usuario, prova_selecionada))
            resultados = [{'nome_aluno': r[0], 'nota': r[1]} for r in cursor.fetchall()]

            if resultados:
                soma = sum(r['nota'] if r['nota'] is not None else 0 for r in resultados)
                media = soma / len(resultados)
            else:
                media = 0

    return render_template('resultados.html', provas=provas, prova_selecionada=prova_selecionada, resultados=resultados, media=media)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
