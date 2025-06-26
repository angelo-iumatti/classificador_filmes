import streamlit as st
import requests
import os
import mysql.connector
from dotenv import load_dotenv

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
        user=os.getenv("DB_USER", "angelo"),
        password=os.getenv("DB_PASSWORD", "261022"),
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

def salvar_filme(titulo, ano, poster_url, nota, classificacao):
    conn = conectar_mysql()
    cursor = conn.cursor()
    sql = "INSERT INTO filmes (titulo, ano, poster_url, nota, classificacao) VALUES (%s, %s, %s, %s, %s)"
    valores = (titulo, ano, poster_url, nota, classificacao)
    cursor.execute(sql, valores)
    conn.commit()
    cursor.close()
    conn.close()

# Interface
st.title("🎬 Classificador de Filmes")

titulo_busca = st.text_input("Digite o nome de um filme:")

if st.button("Buscar"):
    resultados = buscar_filmes(titulo_busca)
    if resultados:
        for filme in resultados[:5]:
            titulo = filme.get("title")
            ano = filme.get("release_date", "")[:4]
            poster = filme.get("poster_path")
            poster_url = f"{IMG_BASE}{poster}" if poster else ""

            st.subheader(f"{titulo} ({ano})")
            if poster_url:
                st.image(poster_url, width=200)

            nota = st.slider(f"Dê uma nota para '{titulo}'", 0.0, 10.0, 7.0, 0.5)
            if st.button(f"Salvar avaliação de '{titulo}'"):
                classificacao = "Gostei" if nota >= 7 else "Não gostei"
                salvar_filme(titulo, int(ano) if ano else None, poster_url, nota, classificacao)
                st.success(f"Filme salvo com classificação: {classificacao}")
            st.markdown("---")
    else:
        st.warning("Nenhum filme encontrado.")
