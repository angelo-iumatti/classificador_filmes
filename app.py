import streamlit as st
import requests
import os
import mysql.connector  # type: ignore
from dotenv import load_dotenv  # type: ignore
import logging
import traceback
import hashlib

logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Carregar variáveis do .env
load_dotenv()

# API Key TMDb
API_KEY = os.getenv("TMDB_API_KEY")
IMG_BASE = "https://image.tmdb.org/t/p/w500"

# Conexão com o banco
def conectar_mysql():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3305")),
        user=os.getenv("DB_USER", "angeloiumatti"),
        password=os.getenv("DB_PASSWORD", "Gfi#261022"),
        database=os.getenv("DB_NAME", "filmes_db")
    )

# Função de hash de senha
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Função para autenticação
def autenticar_usuario(email, senha):
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha_hash FROM usuarios WHERE email = %s", (email,))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        if resultado and resultado[1] == hash_senha(senha):
            return resultado[0]
    except:
        pass
    return None

# Função para registrar novo usuário
def registrar_usuario(email, senha):
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (email, senha_hash) VALUES (%s, %s)", (email, hash_senha(senha)))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except:
        return False

# Autenticação
if "usuario_id" not in st.session_state:
    st.subheader("🔐 Login ou Cadastro")
    aba = st.radio("Escolha uma opção:", ["Login", "Cadastro"])
    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")

    if aba == "Login":
        if st.button("Entrar"):
            usuario_id = autenticar_usuario(email, senha)
            if usuario_id:
                st.session_state.usuario_id = usuario_id
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")
    else:
        if st.button("Cadastrar"):
            if registrar_usuario(email, senha):
                st.success("Usuário cadastrado! Faça login.")
            else:
                st.error("Erro ao cadastrar. Tente outro email.")
    st.stop()

# Usuário logado
usuario_id = st.session_state.usuario_id

try:
    conn = conectar_mysql()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    conn.close()
except Exception as e:
    st.error(f"❌ Erro de conexão com o MySQL: {e}")

def buscar_filmes(titulo):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": API_KEY,
        "query": titulo,
        "language": "pt-BR"
    }
    resposta = requests.get(url, params=params)
    if resposta.status_code == 200:
        return resposta.json().get("results", [])
    return []

def classificar_filme(nota):
    if nota <= 4:
        return "Ruim"
    elif 4 < nota <= 6:
        return "Mediano"
    elif 7 <= nota <= 9:
        return "Bom"
    else:
        return "Filmão"

def salvar_filme(titulo, ano, assistido_em, poster_url, nota, classificacao):
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()

        sql_select = "SELECT id FROM filmes WHERE titulo = %s AND ano = %s AND usuario_id = %s"
        cursor.execute(sql_select, (titulo, ano, usuario_id))
        resultado = cursor.fetchone()

        if resultado:
            sql_update = """
                UPDATE filmes
                SET assistido_em = %s, poster_url = %s, nota = %s, classificacao = %s
                WHERE id = %s
            """
            cursor.execute(sql_update, (assistido_em, poster_url, nota, classificacao, resultado[0]))
        else:
            sql_insert = """
                INSERT INTO filmes (titulo, ano, assistido_em, poster_url, nota, classificacao, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (titulo, ano, assistido_em, poster_url, nota, classificacao, usuario_id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        erro = traceback.format_exc()
        print("❌ Erro ao salvar filme:\n", erro)
        st.error("❌ Erro ao salvar no banco.")
        logging.error("Erro ao salvar filme:\n%s", erro)

# Interface principal após login
st.title("🎬 Classificador de Filmes")

col1, col2 = st.columns([1, 1])

with col1:
    if "mostrar_filmes" not in st.session_state:
        st.session_state.mostrar_filmes = False
    if st.button("🎞️ Ver filmes salvos"):
        st.session_state.mostrar_filmes = not st.session_state.mostrar_filmes

with col2:
    if "mostrar_estatisticas" not in st.session_state:
        st.session_state.mostrar_estatisticas = False
    if st.button("📊 Ver estatísticas"):
        st.session_state.mostrar_estatisticas = not st.session_state.mostrar_estatisticas

if st.session_state.mostrar_filmes:
    try:
        conn = conectar_mysql()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT DISTINCT assistido_em FROM filmes WHERE usuario_id = %s ORDER BY assistido_em DESC", (usuario_id,))
        anos = [row['assistido_em'] for row in cursor.fetchall() if row['assistido_em']]

        ano_filtro = st.selectbox("Filtrar por ano assistido", ["Todos"] + anos)
        classificacoes = st.multiselect("Filtrar por classificação", ["Ruim", "Mediano", "Bom", "Filmão"], default=["Ruim", "Mediano", "Bom", "Filmão"])
        nota_min = st.slider("Nota mínima", 0.0, 10.0, 0.0, 0.5)
        nota_max = st.slider("Nota máxima", 0.0, 10.0, 10.0, 0.5)

        query = "SELECT * FROM filmes WHERE usuario_id = %s"
        params = [usuario_id]

        if ano_filtro != "Todos":
            query += " AND assistido_em = %s"
            params.append(ano_filtro)
        if classificacoes:
            query += " AND classificacao IN (%s)" % (",".join(["%s"] * len(classificacoes)))
            params.extend(classificacoes)
        query += " AND nota BETWEEN %s AND %s"
        params.extend([nota_min, nota_max])

        cursor.execute(query, tuple(params))
        filmes = cursor.fetchall()
        cursor.close()
        conn.close()

        for filme in filmes:
            cols = st.columns([1, 4])
            with cols[0]:
                if filme[4]:
                    st.image(filme[4], width=80)
            with cols[1]:
                st.write(f"**{filme[1]} ({filme[2]})**")
                st.caption(f"🎞️ Assistido em: {filme[3]} | ⭐ Nota: {filme[5]} | 📌 {filme[6]}")

    except Exception as e:
        st.error("Erro ao carregar filmes salvos.")
