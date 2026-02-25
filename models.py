# ==========================================
# MODELOS SQLALCHEMY
# ==========================================

from sqlalchemy import Column, String, Integer, ForeignKey, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import uuid


class Professor(Base):
    __tablename__ = "professores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False, unique=True)

    atribuicoes = relationship("Atribuicao", back_populates="professor")


class Turma(Base):
    __tablename__ = "turmas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False, unique=True)

    atribuicoes = relationship("Atribuicao", back_populates="turma")


class Disciplina(Base):
    __tablename__ = "disciplinas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String, nullable=False, unique=True)

    atribuicoes = relationship("Atribuicao", back_populates="disciplina")


class Atribuicao(Base):
    __tablename__ = "atribuicoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    professor_id = Column(UUID(as_uuid=True), ForeignKey("professores.id"))
    turma_id = Column(UUID(as_uuid=True), ForeignKey("turmas.id"))
    disciplina_id = Column(UUID(as_uuid=True), ForeignKey("disciplinas.id"))

    professor = relationship("Professor", back_populates="atribuicoes")
    turma = relationship("Turma", back_populates="atribuicoes")
    disciplina = relationship("Disciplina", back_populates="atribuicoes")

    conteudos = relationship("Conteudo", back_populates="atribuicao")


class Conteudo(Base):
    __tablename__ = "conteudos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    atribuicao_id = Column(UUID(as_uuid=True), ForeignKey("atribuicoes.id"))
    bimestre = Column(Integer, nullable=False)
    conteudo = Column(Text, nullable=False)

    # 🔥 OBRIGATÓRIA
    data_avaliacao = Column(Date, nullable=False)

    atribuicao = relationship("Atribuicao", back_populates="conteudos")