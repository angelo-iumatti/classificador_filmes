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
    st.success("✅ Conexão com o MySQL funcionando!")
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

# Interface
st.title("🎬 Classificador de Filmes")

titulo_busca = st.text_input("Digite o nome de um filme:")

if "resultados" not in st.session_state:
    st.session_state["resultados"] = []

if st.button("Buscar"):
    st.session_state["resultados"] = buscar_filmes(titulo_busca)

for filme in st.session_state["resultados"][:5]:
    titulo = filme.get("title")
    ano = filme.get("release_date", "")[:4]
    poster = filme.get("poster_path")
    poster_url = f"{IMG_BASE}{poster}" if poster else ""
    id_filme = filme.get("id")

    with st.form(key=f"form_{id_filme}"):
        st.subheader(f"{titulo} ({ano})")
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
            st.write("📩 Dados prontos para salvar:", titulo, ano, assistido_em, poster_url, nota, classificacao)
            salvar_filme(titulo, int(ano) if ano else None, assistido_em, poster_url, nota, classificacao)
            st.success(f"Filme salvo com classificação: {classificacao}")

if st.button("Testar Inserção Manual"):
    salvar_filme("Filme Teste", 2024, 2023, "https://exemplo.com/poster.jpg", 8.5, "Bom")
    st.success("Teste de inserção manual concluído!")
