from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

import jwt

from database import SessionLocal, engine, Base
import models
import schemas
import crud

# ==========================================
# APP
# ==========================================

app = FastAPI()

# ==========================================
# 🔥 ADMIN
# ==========================================

ADMIN_EMAILS = {
    "sharlayne.fonseca@professor.barueri.br",
    "wilber.garcia@professor.barueri.br"
}

# ==========================================
# 🔒 SEGURANÇA TOKEN SUPABASE
# ==========================================

security = HTTPBearer(auto_error=False)

def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"]
        )

        return payload.get("email")

    except Exception as e:
        print("🔥 ERRO TOKEN:", str(e))
        return None

# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://conteudosessenciais-takaoka-2026.vercel.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# OPTIONS (VERCEL)
# ==========================================

@app.options("/{rest_of_path:path}")
async def options_handler(request: Request, rest_of_path: str):
    return JSONResponse(content={"message": "ok"})

# ==========================================
# BANCO
# ==========================================

Base.metadata.create_all(bind=engine)

def garantir_colunas_conteudo():
    inspector = inspect(engine)
    colunas = {coluna["name"] for coluna in inspector.get_columns("conteudos")}

    if "tipo_avaliacao" not in colunas:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE conteudos "
                "ADD COLUMN tipo_avaliacao VARCHAR NOT NULL DEFAULT 'regular'"
            ))

    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE conteudos "
            "SET tipo_avaliacao = 'simulado' "
            "WHERE bimestre = 2 "
            "AND data_avaliacao BETWEEN '2026-05-20' AND '2026-05-22' "
            "AND tipo_avaliacao = 'regular'"
        ))

def garantir_unicidade_conteudo():
    inspector = inspect(engine)
    chave_antiga = {"atribuicao_id", "bimestre"}

    with engine.begin() as conn:
        for constraint in inspector.get_unique_constraints("conteudos"):
            nome = constraint.get("name")
            colunas = set(constraint.get("column_names") or [])

            if nome and colunas == chave_antiga:
                conn.execute(text(f'ALTER TABLE conteudos DROP CONSTRAINT IF EXISTS "{nome}"'))

        for index in inspector.get_indexes("conteudos"):
            nome = index.get("name")
            colunas = set(index.get("column_names") or [])

            if nome and index.get("unique") and colunas == chave_antiga:
                conn.execute(text(f'DROP INDEX IF EXISTS "{nome}"'))

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS conteudos_atribuicao_bimestre_tipo_idx "
            "ON conteudos (atribuicao_id, bimestre, tipo_avaliacao)"
        ))

garantir_colunas_conteudo()
garantir_unicidade_conteudo()

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
# ATRIBUIÇÕES
# ==========================================

@app.get("/atribuicoes/{professor_id}", response_model=list[schemas.AtribuicaoResponse])
def get_atribuicoes(
    professor_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if not email:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # 🔥 ADMIN pode tudo
    if email in ADMIN_EMAILS:
        return crud.listar_atribuicoes_por_professor(db, professor_id)

    professor = db.query(models.Professor).filter(models.Professor.email == email).first()

    if not professor or professor.id != professor_id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    return crud.listar_atribuicoes_por_professor(db, professor_id)

# ==========================================
# BUSCAR CONTEÚDO
# ==========================================

@app.get("/conteudos", response_model=schemas.ConteudoResponse)
def buscar_conteudo(
    atribuicao_id: UUID = Query(...),
    bimestre: int = Query(...),
    tipo_avaliacao: str = Query("regular"),
    db: Session = Depends(get_db)
):
    conteudo = crud.buscar_conteudo(db, atribuicao_id, bimestre, tipo_avaliacao)

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    return conteudo

# ==========================================
# SALVAR CONTEÚDO
# ==========================================

@app.post("/conteudos", response_model=schemas.ConteudoResponse)
def salvar_conteudo(
    dados: schemas.ConteudoCreate,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if not email:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # 🔥 ADMIN pode tudo
    if email not in ADMIN_EMAILS:
        professor = db.query(models.Professor).filter(models.Professor.email == email).first()

        atribuicao = db.query(models.Atribuicao).filter(
            models.Atribuicao.id == dados.atribuicao_id
        ).first()

        if not professor or not atribuicao or atribuicao.professor_id != professor.id:
            raise HTTPException(status_code=403, detail="Sem permissão")

    try:
        conteudo = crud.salvar_conteudo(db, dados)
    except SQLAlchemyError as e:
        db.rollback()
        print("ERRO AO SALVAR CONTEUDO:", str(e))
        raise HTTPException(status_code=500, detail="Erro no banco ao salvar conteudo")
    except Exception as e:
        db.rollback()
        print("ERRO INESPERADO AO SALVAR CONTEUDO:", str(e))
        raise HTTPException(status_code=500, detail="Erro inesperado ao salvar conteudo")

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    return conteudo


@app.put("/conteudos/{conteudo_id}", response_model=schemas.ConteudoResponse)
def atualizar_conteudo(
    conteudo_id: UUID,
    dados: schemas.ConteudoUpdate,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if not email:
        raise HTTPException(status_code=401, detail="Não autenticado")

    conteudo_atual = crud.buscar_conteudo_por_id(db, conteudo_id)

    if not conteudo_atual:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    if email not in ADMIN_EMAILS:
        professor = db.query(models.Professor).filter(models.Professor.email == email).first()

        if not professor or conteudo_atual.atribuicao.professor_id != professor.id:
            raise HTTPException(status_code=403, detail="Sem permissão")

        if dados.atribuicao_id is not None:
            atribuicao = db.query(models.Atribuicao).filter(
                models.Atribuicao.id == dados.atribuicao_id
            ).first()

            if not atribuicao or atribuicao.professor_id != professor.id:
                raise HTTPException(status_code=403, detail="Sem permissão")

    conteudo = crud.atualizar_conteudo(db, conteudo_id, dados)

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    return conteudo

# ==========================================
# TURMAS
# ==========================================

@app.get("/turmas", response_model=list[schemas.TurmaResponse])
def get_turmas(db: Session = Depends(get_db)):
    return crud.listar_turmas(db)

# ==========================================
# CALENDÁRIO
# ==========================================

@app.get("/calendario/{turma_id}", response_model=list[schemas.ConteudoResponse])
def get_calendario(turma_id: UUID, db: Session = Depends(get_db)):
    return crud.buscar_calendario_por_turma(db, turma_id)

# ==========================================
# CRONOGRAMA
# ==========================================

@app.get("/cronograma", response_model=list[schemas.ConteudoResponse])
def get_cronograma(
    turma_id: UUID,
    bimestre: int,
    tipo_avaliacao: str = Query("regular"),
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
            models.Conteudo.bimestre == bimestre,
            models.Conteudo.tipo_avaliacao == tipo_avaliacao
        )
        .all()
    )

    return resultados

# ==========================================
# TRABALHOS
# ==========================================

@app.get("/trabalhos", response_model=schemas.TrabalhoResponse)
def buscar_trabalho(
    atribuicao_id: UUID = Query(...),
    bimestre: int = Query(...),
    db: Session = Depends(get_db)
):
    trabalho = crud.buscar_trabalho(db, atribuicao_id, bimestre)

    if not trabalho:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado")

    return trabalho

# ==========================================
# SALVAR TRABALHO
# ==========================================

@app.post("/trabalhos", response_model=schemas.TrabalhoResponse)
def salvar_trabalho(
    dados: schemas.TrabalhoCreate,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    if not email:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # 🔥 ADMIN pode tudo
    if email not in ADMIN_EMAILS:
        professor = db.query(models.Professor).filter(models.Professor.email == email).first()

        atribuicao = db.query(models.Atribuicao).filter(
            models.Atribuicao.id == dados.atribuicao_id
        ).first()

        if not professor or not atribuicao or atribuicao.professor_id != professor.id:
            raise HTTPException(status_code=403, detail="Sem permissão")

    return crud.salvar_trabalho(db, dados)

# ==========================================
# CRONOGRAMA TRABALHOS
# ==========================================

@app.get("/cronograma-trabalhos", response_model=list[schemas.TrabalhoResponse])
def get_cronograma_trabalhos(
    turma_id: UUID,
    bimestre: int,
    db: Session = Depends(get_db)
):
    return crud.buscar_trabalhos_por_turma(db, turma_id, bimestre)

# ==========================================
# EXCLUIR CONTEÚDO
# ==========================================

@app.delete("/conteudos/{conteudo_id}")
def excluir_conteudo(
    conteudo_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    conteudo = db.query(models.Conteudo).filter(
        models.Conteudo.id == conteudo_id
    ).first()

    if not conteudo:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    if email not in ADMIN_EMAILS and conteudo.atribuicao.professor.email != email:
        raise HTTPException(status_code=403, detail="Sem permissão")

    db.delete(conteudo)
    db.commit()

    return {"message": "Avaliação excluída com sucesso"}

# ==========================================
# EXCLUIR TRABALHO
# ==========================================

@app.delete("/trabalhos/{trabalho_id}")
def excluir_trabalho(
    trabalho_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    trabalho = db.query(models.Trabalho).filter(
        models.Trabalho.id == trabalho_id
    ).first()

    if not trabalho:
        raise HTTPException(status_code=404, detail="Trabalho não encontrado")

    if email not in ADMIN_EMAILS and trabalho.atribuicao.professor.email != email:
        raise HTTPException(status_code=403, detail="Sem permissão")

    db.delete(trabalho)
    db.commit()

    return {"message": "Trabalho excluído com sucesso"}

# ==========================================
# PROFESSORES CRUD
# ==========================================

@app.post("/professores", response_model=schemas.ProfessorResponse)
def criar_professor(dados: schemas.ProfessorCreate, db: Session = Depends(get_db)):
    return crud.criar_professor(db, dados)


@app.put("/professores/{professor_id}", response_model=schemas.ProfessorResponse)
def atualizar_professor(professor_id: UUID, dados: schemas.ProfessorUpdate, db: Session = Depends(get_db)):
    prof = crud.atualizar_professor(db, professor_id, dados)

    if not prof:
        raise HTTPException(status_code=404, detail="Professor não encontrado")

    return prof


@app.delete("/professores/{professor_id}")
def deletar_professor(professor_id: UUID, db: Session = Depends(get_db)):
    ok = crud.deletar_professor(db, professor_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Professor não encontrado")

    return {"message": "Professor excluído"}


# ==========================================
# TURMAS CRUD
# ==========================================

@app.post("/turmas")
def criar_turma(dados: schemas.TurmaCreate, db: Session = Depends(get_db)):
    return crud.criar_turma(db, dados)


@app.delete("/turmas/{turma_id}")
def deletar_turma(turma_id: UUID, db: Session = Depends(get_db)):
    ok = crud.deletar_turma(db, turma_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    return {"message": "Turma excluída"}


# ==========================================
# DISCIPLINAS CRUD
# ==========================================

@app.get("/disciplinas", response_model=list[schemas.DisciplinaResponse])
def get_disciplinas(db: Session = Depends(get_db)):
    return crud.listar_disciplinas(db)


@app.post("/disciplinas")
def criar_disciplina(dados: schemas.DisciplinaCreate, db: Session = Depends(get_db)):
    return crud.criar_disciplina(db, dados)


@app.delete("/disciplinas/{disciplina_id}")
def deletar_disciplina(disciplina_id: UUID, db: Session = Depends(get_db)):
    ok = crud.deletar_disciplina(db, disciplina_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada")

    return {"message": "Disciplina excluída"}

# ==========================================
# NOVA ROTA - TODAS ATRIBUIÇÕES (OTIMIZADA)
# ==========================================

from sqlalchemy.orm import joinedload

@app.get("/atribuicoes", response_model=list[schemas.AtribuicaoResponse])
def get_todas_atribuicoes(
    db: Session = Depends(get_db)
):
    return (
        db.query(models.Atribuicao)
        .join(models.Atribuicao.professor)
        .join(models.Atribuicao.turma)
        .join(models.Atribuicao.disciplina)
        .options(
            joinedload(models.Atribuicao.professor),
            joinedload(models.Atribuicao.turma),
            joinedload(models.Atribuicao.disciplina)
        )
        .all()
    )

# ==========================================
# CRIAR ATRIBUIÇÃO
# ==========================================

@app.post("/atribuicoes", response_model=schemas.AtribuicaoResponse)
def criar_atribuicao(
    dados: schemas.AtribuicaoCreate,
    db: Session = Depends(get_db)
):
    return crud.criar_atribuicao(db, dados)


# ==========================================
# DELETAR ATRIBUIÇÃO
# ==========================================

@app.delete("/atribuicoes/{atribuicao_id}")
def deletar_atribuicao(
    atribuicao_id: UUID,
    db: Session = Depends(get_db)
):

    ok = crud.deletar_atribuicao(db, atribuicao_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Atribuição não encontrada")

    return {"message": "Atribuição excluída"}
