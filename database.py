# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Criação do engine
engine = create_engine(DATABASE_URL)

# Criação da sessão
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para os modelos
Base = declarative_base()