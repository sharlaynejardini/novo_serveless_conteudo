# ==========================================
# SCHEMAS.PY
# ==========================================

from pydantic import BaseModel
from uuid import UUID
from datetime import date


# =========================
# PROFESSOR
# =========================

class ProfessorResponse(BaseModel):
    id: UUID
    nome: str

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
    atribuicao_id: UUID
    bimestre: int
    conteudo: str
    data_avaliacao: date


# =========================
# CONTEÚDO RESPONSE
# =========================

class ConteudoResponse(BaseModel):
    id: UUID
    bimestre: int
    conteudo: str
    data_avaliacao: date
    atribuicao: AtribuicaoResponse

    class Config:
        from_attributes = True