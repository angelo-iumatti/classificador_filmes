import streamlit as st
import requests
import os
import mysql.connector  # type: ignore
from dotenv import load_dotenv  # type: ignore
import logging
import traceback

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

# Função para classificar filme com base na nota
def classificar_filme(nota):
    if nota <= 4:
        return "Ruim"
    elif 4 < nota <= 6:
        return "Mediano"
    elif 7 <= nota <= 9:
        return "Bom"
    else:
        return "Filmão"

# Função para salvar ou atualizar filme no banco de dados
def salvar_filme(titulo, ano, assistido_em, poster_url, nota, classificacao):
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()

        sql_select = "SELECT id FROM filmes WHERE titulo = %s AND ano = %s"
        cursor.execute(sql_select, (titulo, ano))
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
                INSERT INTO filmes (titulo, ano, assistido_em, poster_url, nota, classificacao)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (titulo, ano, assistido_em, poster_url, nota, classificacao))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        erro = traceback.format_exc()
        print("❌ Erro ao salvar filme:\n", erro)
        st.error("❌ Erro ao salvar no banco.")
        logging.error("Erro ao salvar filme:\n%s", erro)

# Função para exibir filmes salvos
def listar_filmes_salvos():
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()
        cursor.execute("SELECT titulo, ano, assistido_em, poster_url, nota, classificacao FROM filmes ORDER BY assistido_em DESC")
        dados = cursor.fetchall()
        cursor.close()
        conn.close()

        if dados:
            st.subheader("🎞️ Filmes Salvos")
            for titulo, ano, assistido_em, poster_url, nota, classificacao in dados:
                cols = st.columns([1, 5])
                with cols[0]:
                    if poster_url:
                        st.image(poster_url, width=60)
                with cols[1]:
                    st.markdown(f"<div style='margin-top: 5px;'><strong>{titulo}</strong> ({ano}) - Assistido em {assistido_em}<br>Nota: {nota} - Classificação: {classificacao}</div>", unsafe_allow_html=True)
        else:
            st.info("Nenhum filme salvo ainda.")
    except Exception as e:
        st.error("Erro ao listar filmes salvos.")

# Interface
st.title("🎬 Classificador de Filmes")

if "mostrar_filmes" not in st.session_state:
    st.session_state.mostrar_filmes = False

if st.button("📂 Ver Filmes Salvos"):
    st.session_state.mostrar_filmes = not st.session_state.mostrar_filmes

if st.session_state.mostrar_filmes:
    listar_filmes_salvos()

st.markdown("---")

titulo_busca = st.text_input("Digite o nome de um filme:")

if "resultados" not in st.session_state:
    st.session_state["resultados"] = []

if st.button("Buscar"):
    st.session_state["resultados"] = buscar_filmes(titulo_busca)

# Obter filmes já salvos para comparação
filmes_salvos = set()
try:
    conn = conectar_mysql()
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, ano FROM filmes")
    filmes_salvos = set((titulo, str(ano)) for titulo, ano in cursor.fetchall())
    cursor.close()
    conn.close()
except:
    pass

resultados = st.session_state["resultados"][:5]

cols = st.columns(2)  # Layout com 2 colunas
for idx, filme in enumerate(resultados):
    with cols[idx % 2]:
        titulo = filme.get("title")
        ano = filme.get("release_date", "")[:4]
        poster = filme.get("poster_path")
        poster_url = f"{IMG_BASE}{poster}" if poster else ""
        id_filme = filme.get("id")

        ja_assistido = (titulo, ano) in filmes_salvos
        icone = " ✅" if ja_assistido else ""

        with st.form(key=f"form_{id_filme}"):
            st.subheader(f"{titulo} ({ano}){icone}")
            if poster_url:
                st.image(poster_url, width=200)

            nota = st.slider(
                f"Dê uma nota para '{titulo}'",
                0.0, 10.0, 7.0, 0.5,
                key=f"nota_{id_filme}"
            )

            assistido_em = st.number_input(
                "Ano em que assistiu ao filme:",
                min_value=1900, max_value=2100, value=2024,
                key=f"assistido_{id_filme}"
            )

            submitted = st.form_submit_button("Salvar avaliação")

            if submitted:
                classificacao = classificar_filme(nota)
                salvar_filme(titulo, int(ano) if ano else None, assistido_em, poster_url, nota, classificacao)
                st.success(f"Filme salvo com classificação: {classificacao}")
