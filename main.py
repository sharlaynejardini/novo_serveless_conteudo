from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID

from database import SessionLocal, engine, Base
import models
import schemas
import crud

# ==========================================
# CRIAÇÃO DA APLICAÇÃO
# ==========================================

app = FastAPI()

# ==========================================
# CORS LIBERADO
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois podemos restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CRIA TABELAS (se não existirem)
# ==========================================

Base.metadata.create_all(bind=engine)

# ==========================================
# DEPENDÊNCIA DO BANCO
# ==========================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# PROFESSORES
# ==========================================

@app.get("/professores", response_model=list[schemas.ProfessorResponse])
def get_professores(db: Session = Depends(get_db)):
    return crud.listar_professores(db)

# ==========================================
# ATRIBUIÇÕES POR PROFESSOR
# ==========================================

@app.get("/atribuicoes/{professor_id}", response_model=list[schemas.AtribuicaoResponse])
def get_atribuicoes(professor_id: UUID, db: Session = Depends(get_db)):
    return crud.listar_atribuicoes_por_professor(db, professor_id)

# ==========================================
# BUSCAR CONTEÚDO
# ==========================================

@app.get("/conteudos", response_model=schemas.ConteudoResponse)
def buscar_conteudo(
    atribuicao_id: UUID = Query(...),
    bimestre: int = Query(...),
    db: Session = Depends(get_db)
):
    conteudo = crud.buscar_conteudo(db, atribuicao_id, bimestre)

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    return conteudo

# ==========================================
# SALVAR CONTEÚDO
# ==========================================

@app.post("/conteudos", response_model=schemas.ConteudoResponse)
def salvar_conteudo(dados: schemas.ConteudoCreate, db: Session = Depends(get_db)):
    return crud.salvar_conteudo(db, dados)

# ==========================================
# LISTAR TURMAS
# ==========================================

@app.get("/turmas", response_model=list[schemas.TurmaResponse])
def get_turmas(db: Session = Depends(get_db)):
    return crud.listar_turmas(db)

# ==========================================
# CALENDÁRIO POR TURMA
# ==========================================

@app.get("/calendario/{turma_id}", response_model=list[schemas.ConteudoResponse])
def get_calendario(turma_id: UUID, db: Session = Depends(get_db)):
    return crud.buscar_calendario_por_turma(db, turma_id)

# ==========================================
# CRONOGRAMA POR TURMA E BIMESTRE
# ==========================================

from sqlalchemy.orm import joinedload

# ==========================================
# CRONOGRAMA POR TURMA E BIMESTRE
# ==========================================

@app.get("/cronograma", response_model=list[schemas.ConteudoResponse])
def get_cronograma(
    turma_id: UUID,
    bimestre: int,
    db: Session = Depends(get_db)
):

    resultados = (
        db.query(models.Conteudo)
        .options(
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.professor),
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.disciplina)
        )
        .join(models.Atribuicao)
        .filter(
            models.Atribuicao.turma_id == turma_id,
            models.Conteudo.bimestre == bimestre
        )
        .all()
    )

    return resultados