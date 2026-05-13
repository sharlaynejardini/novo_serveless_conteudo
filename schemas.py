# ==========================================
# SCHEMAS.PY
# ==========================================

from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import date
from typing import List, Union
import json


# =========================
# PROFESSOR
# =========================

class ProfessorResponse(BaseModel):
    id: UUID
    nome: str
    email: str | None

    class Config:
        from_attributes = True


# =========================
# DISCIPLINA
# =========================

class DisciplinaResponse(BaseModel):
    id: UUID
    nome: str

    class Config:
        from_attributes = True


# =========================
# TURMA
# =========================

class TurmaResponse(BaseModel):
    id: UUID
    nome: str

    class Config:
        from_attributes = True


# =========================
# ATRIBUIÇÃO
# =========================

class AtribuicaoResponse(BaseModel):
    id: UUID
    professor: ProfessorResponse
    disciplina: DisciplinaResponse
    turma: TurmaResponse

    class Config:
        from_attributes = True


# =========================
# CONTEÚDO CREATE
# =========================

class ConteudoCreate(BaseModel):
    id: UUID | None = None
    atribuicao_id: UUID
    bimestre: int
    conteudo: Union[str, List[str]]  # aceita string ou lista
    data_avaliacao: date


# =========================
# CONTEÚDO RESPONSE
# =========================

class ConteudoResponse(BaseModel):
    id: UUID
    bimestre: int
    conteudo: List[str]  # 🔥 agora sempre será lista
    data_avaliacao: date
    atribuicao: AtribuicaoResponse

    class Config:
        from_attributes = True

    @field_validator("conteudo", mode="before")
    @classmethod
    def converter_para_lista(cls, value):
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                convertido = json.loads(value)
                if isinstance(convertido, list):
                    return convertido
                return [convertido]
            except:
                return [value]

        return []
    
    #teste##

    # =========================
# TRABALHO CREATE
# =========================

class TrabalhoCreate(BaseModel):
    atribuicao_id: UUID
    bimestre: int  # 🔥 NOVO
    conteudo: Union[str, List[str]]
    instrucoes: str
    data_entrega: date


# =========================
# TRABALHO RESPONSE
# =========================

class TrabalhoResponse(BaseModel):
    id: UUID
    bimestre: int  # 🔥 NOVO
    conteudo: List[str]
    instrucoes: str
    data_entrega: date
    atribuicao: AtribuicaoResponse

    class Config:
        from_attributes = True

    @field_validator("conteudo", mode="before")
    @classmethod
    def converter_para_lista(cls, value):
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                convertido = json.loads(value)
                if isinstance(convertido, list):
                    return convertido
                return [convertido]
            except:
                return [value]

        return []
    
    # =========================
# CREATE PROFESSOR
# =========================

class ProfessorCreate(BaseModel):
    nome: str
    email: str


class ProfessorUpdate(BaseModel):
    nome: str
    email: str


# =========================
# TURMA CREATE
# =========================

class TurmaCreate(BaseModel):
    nome: str


# =========================
# DISCIPLINA CREATE
# =========================

class DisciplinaCreate(BaseModel):
    nome: str


# =========================
# ATRIBUIÇÃO CREATE
# =========================

class AtribuicaoCreate(BaseModel):
    professor_id: UUID
    turma_id: UUID
    disciplina_id: UUID
