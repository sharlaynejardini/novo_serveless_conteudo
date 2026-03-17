from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
import jwt

from database import SessionLocal, engine, Base
import models
import schemas
import crud

app = FastAPI()

# ==========================================
# 🔒 SEGURANÇA TOKEN SUPABASE
# ==========================================

security = HTTPBearer()

def get_current_user_email(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        email = payload.get("email")

        if not email:
            raise HTTPException(status_code=401, detail="Email não encontrado")

        return email

    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

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

@app.options("/{rest_of_path:path}")
async def options_handler(request: Request, rest_of_path: str):
    return JSONResponse(content={"message": "ok"})

Base.metadata.create_all(bind=engine)

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
# ATRIBUIÇÕES (PROTEGIDO 🔒)
# ==========================================

@app.get("/atribuicoes/{professor_id}", response_model=list[schemas.AtribuicaoResponse])
def get_atribuicoes(
    professor_id: UUID,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    professor = db.query(models.Professor).filter(models.Professor.email == email).first()

    if not professor or professor.id != professor_id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    return crud.listar_atribuicoes_por_professor(db, professor_id)

# ==========================================
# SALVAR CONTEÚDO (PROTEGIDO 🔒)
# ==========================================

@app.post("/conteudos", response_model=schemas.ConteudoResponse)
def salvar_conteudo(
    dados: schemas.ConteudoCreate,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    professor = db.query(models.Professor).filter(models.Professor.email == email).first()

    atribuicao = db.query(models.Atribuicao).filter(
        models.Atribuicao.id == dados.atribuicao_id
    ).first()

    if not atribuicao or atribuicao.professor_id != professor.id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    return crud.salvar_conteudo(db, dados)

# ==========================================
# SALVAR TRABALHO (PROTEGIDO 🔒)
# ==========================================

@app.post("/trabalhos", response_model=schemas.TrabalhoResponse)
def salvar_trabalho(
    dados: schemas.TrabalhoCreate,
    email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db)
):
    professor = db.query(models.Professor).filter(models.Professor.email == email).first()

    atribuicao = db.query(models.Atribuicao).filter(
        models.Atribuicao.id == dados.atribuicao_id
    ).first()

    if not atribuicao or atribuicao.professor_id != professor.id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    return crud.salvar_trabalho(db, dados)

# ==========================================
# EXCLUIR CONTEÚDO (PROTEGIDO 🔒)
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

    if conteudo.atribuicao.professor.email != email:
        raise HTTPException(status_code=403, detail="Sem permissão")

    db.delete(conteudo)
    db.commit()

    return {"message": "Avaliação excluída com sucesso"}

# ==========================================
# EXCLUIR TRABALHO (PROTEGIDO 🔒)
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

    if trabalho.atribuicao.professor.email != email:
        raise HTTPException(status_code=403, detail="Sem permissão")

    db.delete(trabalho)
    db.commit()

    return {"message": "Trabalho excluído com sucesso"}