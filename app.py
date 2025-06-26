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

# Função para salvar filme no banco de dados
def salvar_filme(titulo, ano, poster_url, nota, classificacao):
    print("🔍 Salvando filme:", titulo, ano, nota, classificacao)  # DEBUG
    try:
        conn = conectar_mysql()

        cursor = conn.cursor()
        sql = """
        INSERT INTO filmes (titulo, ano, poster_url, nota, classificacao)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            nota = VALUES(nota),
            classificacao = VALUES(classificacao),
            poster_url = VALUES(poster_url)
        """
        valores = (titulo, ano, poster_url, nota, classificacao)
        print("📦 Valores:", valores)
        print("DEBUG FINAL: tentando inserir no banco...")
        cursor.execute(sql, valores)
        conn.commit()
        print("🎉 Filme inserido com sucesso!")

        cursor.close()
        conn.close()
    except Exception as e:
        erro = traceback.format_exc()
        print("❌ Erro ao salvar filme:\n", erro)  # ADICIONE ISSO
        st.error("❌ Erro ao salvar no banco.")
        logging.error("Erro ao salvar filme:\n%s", erro)


# Interface
st.title("🎬 Classificador de Filmes")
tabs = st.tabs(["🎥 Classificar", "📊 Estatísticas"])

with tabs[0]:
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
            col1, col2 = st.columns([1, 3])
            with col1:
                if poster_url:
                    st.image(poster_url, width=150)
            with col2:
                st.subheader(f"{titulo} ({ano})")
                nota = st.slider(
                    f"Nota para '{titulo}'", 0.0, 10.0, 7.0, 0.5, key=f"nota_{id_filme}"
                )
                submitted = st.form_submit_button("Salvar avaliação")
                if submitted:
                    classificacao = "Gostei" if nota >= 7 else "Não gostei"
                    salvar_filme(titulo, int(ano) if ano else None, poster_url, nota, classificacao)
                    st.success(f"Filme salvo com classificação: {classificacao}")

    with st.expander("🎞️ Ver filmes salvos"):
        try:
            conn = conectar_mysql()
            cursor = conn.cursor()
            cursor.execute("SELECT titulo, ano, nota, classificacao FROM filmes ORDER BY ano DESC, titulo")
            filmes = cursor.fetchall()
            for f in filmes:
                st.write(f"📽️ {f[0]} ({f[1]}) — Nota: {f[2]} — {f[3]}")
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Erro ao buscar filmes: {e}")

with tabs[1]:
    try:
        conn = conectar_mysql()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*), AVG(nota), SUM(CASE WHEN classificacao = 'Gostei' THEN 1 ELSE 0 END)
            FROM filmes
        """)
        total, media, gostou = cursor.fetchone()
        st.metric("🎬 Total de filmes", total)
        st.metric("⭐ Nota média", round(media or 0, 2))
        perc = (gostou / total * 100) if total else 0
        st.metric("👍 % Gostei", f"{perc:.1f}%")
        cursor.close()
        conn.close()
    except Exception as e:
        st.error("Erro ao gerar estatísticas.")
