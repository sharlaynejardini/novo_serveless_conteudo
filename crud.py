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


# ==========================================
# TRABALHOS
# ==========================================

def buscar_trabalho(db, atribuicao_id, bimestre):
    return (
        db.query(models.Trabalho)
        .options(
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.professor),
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.disciplina),
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.turma),
        )
        .filter(
            models.Trabalho.atribuicao_id == atribuicao_id,
            models.Trabalho.bimestre == bimestre
        )
        .first()
    )


def salvar_trabalho(db, dados):

    trabalho = (
        db.query(models.Trabalho)
        .filter(
            models.Trabalho.atribuicao_id == dados.atribuicao_id,
            models.Trabalho.bimestre == dados.bimestre
        )
        .first()
    )

    if trabalho:
        trabalho.conteudo = dados.conteudo
        trabalho.instrucoes = dados.instrucoes
        trabalho.data_entrega = dados.data_entrega
    else:
        trabalho = models.Trabalho(
            atribuicao_id=dados.atribuicao_id,
            bimestre=dados.bimestre,
            conteudo=dados.conteudo,
            instrucoes=dados.instrucoes,
            data_entrega=dados.data_entrega
        )
        db.add(trabalho)

    db.commit()
    db.refresh(trabalho)

    return trabalho


def buscar_trabalhos_por_turma(db, turma_id, bimestre):
    return (
        db.query(models.Trabalho)
        .options(
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.professor),
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.disciplina),
            joinedload(models.Trabalho.atribuicao)
            .joinedload(models.Atribuicao.turma),
        )
        .join(models.Atribuicao)
        .filter(
            models.Atribuicao.turma_id == turma_id,
            models.Trabalho.bimestre == bimestre
        )
        .all()
    )


# ==========================================
# EXCLUIR CONTEÚDO (AVALIAÇÃO)
# ==========================================

def excluir_conteudo(db, conteudo_id):

    conteudo = (
        db.query(models.Conteudo)
        .filter(models.Conteudo.id == conteudo_id)
        .first()
    )

    if not conteudo:
        return False

    db.delete(conteudo)
    db.commit()

    return True


# ==========================================
# EXCLUIR TRABALHO
# ==========================================

def excluir_trabalho(db, trabalho_id):

    trabalho = (
        db.query(models.Trabalho)
        .filter(models.Trabalho.id == trabalho_id)
        .first()
    )

    if not trabalho:
        return False

    db.delete(trabalho)
    db.commit()

    return True

# ==========================================
# PROFESSORES CRUD
# ==========================================

def criar_professor(db, dados):
    prof = models.Professor(nome=dados.nome, email=dados.email)
    db.add(prof)
    db.commit()
    db.refresh(prof)
    return prof


def atualizar_professor(db, id, dados):
    prof = db.query(models.Professor).filter(models.Professor.id == id).first()

    if not prof:
        return None

    prof.nome = dados.nome
    prof.email = dados.email

    db.commit()
    db.refresh(prof)
    return prof


def deletar_professor(db, id):
    prof = db.query(models.Professor).filter(models.Professor.id == id).first()

    if not prof:
        return False

    db.delete(prof)
    db.commit()
    return True


# ==========================================
# TURMAS CRUD
# ==========================================

def criar_turma(db, dados):
    turma = models.Turma(nome=dados.nome)
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return turma


def deletar_turma(db, id):
    turma = db.query(models.Turma).filter(models.Turma.id == id).first()

    if not turma:
        return False

    db.delete(turma)
    db.commit()
    return True


# ==========================================
# DISCIPLINAS CRUD
# ==========================================

def listar_disciplinas(db):
    return db.query(models.Disciplina).all()


def criar_disciplina(db, dados):
    disc = models.Disciplina(nome=dados.nome)
    db.add(disc)
    db.commit()
    db.refresh(disc)
    return disc


def deletar_disciplina(db, id):
    disc = db.query(models.Disciplina).filter(models.Disciplina.id == id).first()

    if not disc:
        return False

    db.delete(disc)
    db.commit()
    return True