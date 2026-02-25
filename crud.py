# ==========================================
# CRUD.PY
# ==========================================

import models
from sqlalchemy.orm import joinedload


def listar_professores(db):
    return db.query(models.Professor).all()


def listar_atribuicoes_por_professor(db, professor_id):
    return (
        db.query(models.Atribuicao)
        .options(
            joinedload(models.Atribuicao.professor),
            joinedload(models.Atribuicao.disciplina),
            joinedload(models.Atribuicao.turma)
        )
        .filter(models.Atribuicao.professor_id == professor_id)
        .all()
    )


def buscar_conteudo(db, atribuicao_id, bimestre):
    return (
        db.query(models.Conteudo)
        .options(
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.professor),
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.disciplina),
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.turma),
        )
        .filter(
            models.Conteudo.atribuicao_id == atribuicao_id,
            models.Conteudo.bimestre == bimestre
        )
        .first()
    )


def salvar_conteudo(db, dados):
    conteudo = buscar_conteudo(db, dados.atribuicao_id, dados.bimestre)

    if conteudo:
        conteudo.conteudo = dados.conteudo
        conteudo.data_avaliacao = dados.data_avaliacao
    else:
        conteudo = models.Conteudo(
            atribuicao_id=dados.atribuicao_id,
            bimestre=dados.bimestre,
            conteudo=dados.conteudo,
            data_avaliacao=dados.data_avaliacao
        )
        db.add(conteudo)

    db.commit()
    db.refresh(conteudo)

    return buscar_conteudo(db, dados.atribuicao_id, dados.bimestre)


def buscar_calendario_por_turma(db, turma_id):
    return (
        db.query(models.Conteudo)
        .options(
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.professor),
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.disciplina),
            joinedload(models.Conteudo.atribuicao)
            .joinedload(models.Atribuicao.turma),
        )
        .join(models.Atribuicao)
        .filter(models.Atribuicao.turma_id == turma_id)
        .all()
    )

# =========================
# LISTAR TODAS AS TURMAS
# =========================

def listar_turmas(db):
    return db.query(models.Turma).all()