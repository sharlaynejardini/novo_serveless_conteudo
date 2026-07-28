from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from datetime import date
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

TURMAS_OBMEP_2026 = {"6A", "6B", "7A", "7B", "8A", "8B", "8C", "9A", "9B", "9C"}
TURMAS_SIMULADO_FUND2_2026 = {"6A", "6B", "7A", "7B", "8A", "8B", "8C", "9A", "9B", "9C"}
DATA_OBMEP_2026 = date(2026, 6, 9)
DATA_REMANEJADA_OBMEP_2026 = date(2026, 6, 16)
PERIODOS_SIMULADO_FUND2_2026 = {
    2: (date(2026, 5, 20), date(2026, 5, 22)),
    3: (date(2026, 8, 19), date(2026, 8, 21)),
}
PERIODOS_PROVA_BIMESTRAL_2026 = {
    3: (date(2026, 9, 14), date(2026, 9, 18)),
}
LIMITE_PROVAS_BIMESTRAIS_POR_DIA = 2


def normalizar_nome_turma(nome: str | None):
    if not nome:
        return ""

    return (
        nome.upper()
        .replace(" ", "")
        .replace("º", "")
        .replace("°", "")
        .replace("ANO", "")
    )


def turma_tem_obmep_2026(nome: str | None):
    return normalizar_nome_turma(nome) in TURMAS_OBMEP_2026


def turma_pode_simulado_fund2(nome: str | None):
    return normalizar_nome_turma(nome) in TURMAS_SIMULADO_FUND2_2026


def validar_avaliacao_conteudo(db, dados, atribuicao):
    if dados.tipo_avaliacao not in {"regular", "simulado"}:
        raise HTTPException(status_code=400, detail="Tipo de avaliacao invalido.")

    if not atribuicao:
        raise HTTPException(status_code=404, detail="Atribuicao nao encontrada")

    if dados.tipo_avaliacao == "simulado":
        periodo = PERIODOS_SIMULADO_FUND2_2026.get(dados.bimestre)

        if not periodo or not turma_pode_simulado_fund2(atribuicao.turma.nome):
            raise HTTPException(
                status_code=400,
                detail="O simulado esta liberado apenas para as turmas 6A, 6B, 7A, 7B, 8A, 8B, 8C, 9A, 9B e 9C no 2o e 3o bimestres."
            )

        inicio, fim = periodo
        if dados.data_avaliacao < inicio or dados.data_avaliacao > fim:
            raise HTTPException(
                status_code=400,
                detail=f"Data do simulado fora do periodo permitido: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}."
            )

    if dados.tipo_avaliacao == "regular" and dados.bimestre in PERIODOS_PROVA_BIMESTRAL_2026:
        inicio, fim = PERIODOS_PROVA_BIMESTRAL_2026[dados.bimestre]

        if dados.data_avaliacao < inicio or dados.data_avaliacao > fim:
            raise HTTPException(
                status_code=400,
                detail=f"Data da prova bimestral fora do periodo permitido: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}."
            )

        conteudo_existente = None
        if dados.id:
            conteudo_existente = db.query(models.Conteudo).filter(models.Conteudo.id == dados.id).first()

        if not conteudo_existente:
            conteudo_existente = (
                db.query(models.Conteudo)
                .filter(
                    models.Conteudo.atribuicao_id == dados.atribuicao_id,
                    models.Conteudo.bimestre == dados.bimestre,
                    models.Conteudo.tipo_avaliacao == "regular"
                )
                .first()
            )

        query = (
            db.query(models.Conteudo)
            .join(models.Atribuicao)
            .filter(
                models.Atribuicao.turma_id == atribuicao.turma_id,
                models.Conteudo.bimestre == dados.bimestre,
                models.Conteudo.tipo_avaliacao == "regular",
                models.Conteudo.data_avaliacao == dados.data_avaliacao
            )
        )

        if conteudo_existente:
            query = query.filter(models.Conteudo.id != conteudo_existente.id)

        if query.count() >= LIMITE_PROVAS_BIMESTRAIS_POR_DIA:
            raise HTTPException(
                status_code=400,
                detail="Limite de 2 materias por dia para a prova bimestral desta turma."
            )

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

def remanejar_conteudos_obmep_2026():
    turmas = ", ".join(f"'{turma}'" for turma in sorted(TURMAS_OBMEP_2026))

    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE conteudos "
            "SET data_avaliacao = '2026-06-16' "
            "FROM atribuicoes "
            "JOIN turmas ON turmas.id = atribuicoes.turma_id "
            "WHERE conteudos.atribuicao_id = atribuicoes.id "
            "AND conteudos.data_avaliacao = '2026-06-09' "
            f"AND UPPER(REPLACE(REPLACE(REPLACE(turmas.nome, ' ', ''), 'º', ''), '°', '')) IN ({turmas})"
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
remanejar_conteudos_obmep_2026()
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

    else:
        atribuicao = db.query(models.Atribuicao).filter(
            models.Atribuicao.id == dados.atribuicao_id
        ).first()

    validar_avaliacao_conteudo(db, dados, atribuicao)

    if (
        dados.tipo_avaliacao == "regular"
        and
        atribuicao
        and dados.data_avaliacao == DATA_OBMEP_2026
        and turma_tem_obmep_2026(atribuicao.turma.nome)
    ):
        raise HTTPException(
            status_code=400,
            detail="09/06/2026 esta reservado para OBMEP. Use 16/06/2026 para essa turma."
        )

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

    atribuicao_para_validar = conteudo_atual.atribuicao
    if dados.atribuicao_id is not None:
        atribuicao_para_validar = db.query(models.Atribuicao).filter(
            models.Atribuicao.id == dados.atribuicao_id
        ).first()

    dados_para_validar = schemas.ConteudoCreate(
        id=conteudo_id,
        atribuicao_id=dados.atribuicao_id or conteudo_atual.atribuicao_id,
        bimestre=dados.bimestre if dados.bimestre is not None else conteudo_atual.bimestre,
        tipo_avaliacao=dados.tipo_avaliacao or conteudo_atual.tipo_avaliacao,
        conteudo=dados.conteudo if dados.conteudo is not None else conteudo_atual.conteudo,
        data_avaliacao=dados.data_avaliacao or conteudo_atual.data_avaliacao
    )

    validar_avaliacao_conteudo(db, dados_para_validar, atribuicao_para_validar)

    if (
        dados_para_validar.tipo_avaliacao == "regular"
        and dados_para_validar.data_avaliacao == DATA_OBMEP_2026
        and atribuicao_para_validar
        and turma_tem_obmep_2026(atribuicao_para_validar.turma.nome)
    ):
        raise HTTPException(
            status_code=400,
            detail="09/06/2026 está reservado para OBMEP. Use 16/06/2026 para essa turma."
        )

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
    else:
        atribuicao = db.query(models.Atribuicao).filter(
            models.Atribuicao.id == dados.atribuicao_id
        ).first()
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
