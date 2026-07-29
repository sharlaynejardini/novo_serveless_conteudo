from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from uuid import UUID
import csv
import hashlib
import os
import re
import smtplib
import ssl
import urllib.request

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
PLANILHA_CALENDARIO_ID = os.getenv(
    "PLANILHA_CALENDARIO_ID",
    "1nSpwVBX2LH6iUVAibtthXIfMO1lViEP1PmV1vH9Ihg0"
)
GID_CALENDARIO_2_SEMESTRE = os.getenv("GID_CALENDARIO_2_SEMESTRE", "1366818204")
GID_PROFESSORES_CALENDARIO = os.getenv("GID_PROFESSORES_CALENDARIO", "504314047")
GID_PROFESSORES_PEBI = os.getenv("GID_PROFESSORES_PEBI", "908908081")
FORMULARIO_REGISTROS_PEBI = "https://forms.gle/jmQxu2UF8QW6SVHi8"

CRONOGRAMA_ENVIO_PEBI = [
    {"inicio": date(2026, 7, 27), "fim": date(2026, 7, 31), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
    {"inicio": date(2026, 8, 3), "fim": date(2026, 8, 8), "turmas": ["2A", "2B"], "turmas_texto": "2ºA e 2ºB"},
    {"inicio": date(2026, 8, 10), "fim": date(2026, 8, 14), "turmas": ["3A", "3B"], "turmas_texto": "3ºA e 3ºB"},
    {"inicio": date(2026, 8, 17), "fim": date(2026, 8, 21), "turmas": ["5A", "5B"], "turmas_texto": "5ºA e 5ºB"},
    {"inicio": date(2026, 8, 24), "fim": date(2026, 8, 28), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
    {"inicio": date(2026, 9, 1), "fim": date(2026, 9, 4), "turmas": ["2A", "2B"], "turmas_texto": "2ºA e 2ºB"},
    {"inicio": date(2026, 9, 7), "fim": date(2026, 9, 11), "turmas": ["3A", "3B"], "turmas_texto": "3ºA e 3ºB"},
    {"inicio": date(2026, 9, 14), "fim": date(2026, 9, 18), "turmas": ["5A", "5B"], "turmas_texto": "5ºA e 5ºB"},
    {"inicio": date(2026, 9, 21), "fim": date(2026, 9, 25), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
    {"inicio": date(2026, 9, 28), "fim": date(2026, 10, 2), "turmas": ["2A", "2B"], "turmas_texto": "2ºA e 2ºB"},
    {"inicio": date(2026, 10, 5), "fim": date(2026, 10, 9), "turmas": ["3A", "3B"], "turmas_texto": "3ºA e 3ºB"},
    {"inicio": date(2026, 10, 12), "fim": date(2026, 10, 16), "turmas": ["5A", "5B"], "turmas_texto": "5ºA e 5ºB"},
    {"inicio": date(2026, 10, 19), "fim": date(2026, 10, 23), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
    {"inicio": date(2026, 10, 26), "fim": date(2026, 10, 30), "turmas": ["2A", "2B"], "turmas_texto": "2ºA e 2ºB"},
    {"inicio": date(2026, 11, 2), "fim": date(2026, 11, 6), "turmas": ["3A", "3B"], "turmas_texto": "3ºA e 3ºB"},
    {"inicio": date(2026, 11, 9), "fim": date(2026, 11, 13), "turmas": ["5A", "5B"], "turmas_texto": "5ºA e 5ºB"},
    {"inicio": date(2026, 11, 16), "fim": date(2026, 11, 20), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
    {"inicio": date(2026, 11, 23), "fim": date(2026, 11, 30), "turmas": ["2A", "2B"], "turmas_texto": "2ºA e 2ºB"},
    {"inicio": date(2026, 12, 1), "fim": date(2026, 12, 4), "turmas": ["3A", "3B"], "turmas_texto": "3ºA e 3ºB"},
    {"inicio": date(2026, 12, 7), "fim": date(2026, 12, 11), "turmas": ["5A", "5B"], "turmas_texto": "5ºA e 5ºB"},
    {"inicio": date(2026, 12, 14), "fim": date(2026, 12, 18), "turmas": ["1A", "4A"], "turmas_texto": "1ºA e 4ºA"},
]

REGISTROS_OBRIGATORIOS_PEBI = [
    "Cantinho da Leitura",
    "Elefante Letrado",
    "Matific",
    "Cultura 10",
    "Biblioteca",
    "Atividades dos alunos de inclusão",
    "PEE",
    "Avaliações Externas e Diagnósticas (quando houver)",
]


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

def baixar_csv_planilha(gid: str):
    cache_buster = int(datetime.utcnow().timestamp())
    url = (
        f"https://docs.google.com/spreadsheets/d/{PLANILHA_CALENDARIO_ID}/export"
        f"?format=csv&gid={gid}&cache_buster={cache_buster}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    )

    with urllib.request.urlopen(request, timeout=20) as resposta:
        conteudo = resposta.read().decode("utf-8-sig")

    return list(csv.DictReader(conteudo.splitlines()))


def limpar_texto(valor):
    return (valor or "").strip()


def normalizar_cabecalho(valor):
    return limpar_texto(valor).upper()


def valor_linha(linha, *nomes):
    nomes_normalizados = {normalizar_cabecalho(nome) for nome in nomes}

    for chave, valor in linha.items():
        if normalizar_cabecalho(chave) in nomes_normalizados:
            return limpar_texto(valor)

    return ""


def parse_data_evento(valor):
    texto_data = limpar_texto(valor)
    match = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?", texto_data)

    if match:
        dia, mes, ano = match.groups()
        return date(int(ano or 2026), int(mes), int(dia))

    match_periodo_sem_mes_no_inicio = re.search(
        r"^(\d{1,2})\s*(?:a|e)\s*\d{1,2}/(\d{1,2})(?:/(\d{4}))?",
        texto_data,
        re.IGNORECASE
    )

    if match_periodo_sem_mes_no_inicio:
        dia, mes, ano = match_periodo_sem_mes_no_inicio.groups()
        return date(int(ano or 2026), int(mes), int(dia))

    return None


def carregar_eventos_calendario():
    linhas = baixar_csv_planilha(GID_CALENDARIO_2_SEMESTRE)
    eventos = []

    for linha in linhas:
        data_texto = valor_linha(linha, "DATA")
        evento = valor_linha(linha, "EVENTO / ATIVIDADE", "EVENTO", "ATIVIDADE")

        if not data_texto or not evento:
            continue

        data_evento = parse_data_evento(data_texto)

        if not data_evento:
            continue

        eventos.append({
            "data": data_texto,
            "dia": valor_linha(linha, "DIA DA SEMANA"),
            "evento": evento,
            "obs": valor_linha(linha, "OBS", "OBSERVAÇÃO", "OBSERVACOES"),
            "data_evento": data_evento
        })

    return eventos


def carregar_professores_calendario():
    linhas = baixar_csv_planilha(GID_PROFESSORES_CALENDARIO)
    professores = []

    for linha in linhas:
        email = valor_linha(linha, "EMAIL").lower()

        if "@" not in email:
            continue

        professores.append({
            "email": email,
            "nome": valor_linha(linha, "NOME") or email
        })

    return professores


def carregar_professores_pebi():
    linhas = baixar_csv_planilha(GID_PROFESSORES_PEBI)
    professores = []

    for linha in linhas:
        email = valor_linha(linha, "EMAIL").lower()
        turma = normalizar_nome_turma(valor_linha(linha, "TURMA"))

        if "@" not in email or not turma:
            continue

        professores.append({
            "email": email,
            "nome": valor_linha(linha, "NOME") or email,
            "turma": turma
        })

    return professores


def eventos_calendario_para_resposta():
    return [
        {
            "data": evento["data"],
            "dia": evento["dia"],
            "evento": evento["evento"],
            "obs": evento["obs"],
            "data_evento": evento["data_evento"].isoformat()
        }
        for evento in carregar_eventos_calendario()
    ]


def smtp_configurado():
    obrigatorias = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]
    return all(os.getenv(nome) for nome in obrigatorias)


def smtp_status():
    return {
        "configurado": smtp_configurado(),
        "host_configurado": bool(os.getenv("SMTP_HOST")),
        "porta": int(os.getenv("SMTP_PORT", "587")),
        "usuario_configurado": bool(os.getenv("SMTP_USER")),
        "senha_configurada": bool(os.getenv("SMTP_PASSWORD")),
        "remetente_configurado": bool(os.getenv("SMTP_FROM")),
        "ssl": os.getenv("SMTP_USE_SSL", "").lower() in {"1", "true", "sim", "yes"}
            or os.getenv("SMTP_PORT") == "465",
        "starttls": os.getenv("SMTP_STARTTLS", "true").lower() not in {"0", "false", "nao", "não", "no"}
    }


def abrir_servidor_smtp():
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    usar_ssl = os.getenv("SMTP_USE_SSL", "").lower() in {"1", "true", "sim", "yes"} or smtp_port == 465
    usar_starttls = os.getenv("SMTP_STARTTLS", "true").lower() not in {"0", "false", "nao", "não", "no"}
    contexto = ssl.create_default_context()

    if usar_ssl:
        servidor = smtplib.SMTP_SSL(smtp_host, smtp_port, context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(smtp_host, smtp_port, timeout=30)

    if not usar_ssl and usar_starttls:
        servidor.starttls(context=contexto)

    servidor.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
    return servidor


def montar_listas_eventos_email(eventos):
    itens_html = []
    itens_texto = []

    for evento in eventos:
        obs_html = f" <em>({evento['obs']})</em>" if evento.get("obs") else ""
        obs_texto = f" ({evento['obs']})" if evento.get("obs") else ""
        itens_html.append(f"<li><strong>{evento['data']}</strong> - {evento['evento']}{obs_html}</li>")
        itens_texto.append(f"- {evento['data']} - {evento['evento']}{obs_texto}")

    return "".join(itens_html), "\n".join(itens_texto)


def nome_mes_portugues(numero_mes):
    meses = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro",
    }
    return meses[numero_mes]


def periodo_pebi_texto(periodo):
    inicio = periodo["inicio"]
    fim = periodo["fim"]

    if inicio.month == fim.month:
        return f"{inicio.day:02d} a {fim.day:02d} de {nome_mes_portugues(inicio.month)}"

    return (
        f"{inicio.day:02d} de {nome_mes_portugues(inicio.month)} "
        f"a {fim.day:02d} de {nome_mes_portugues(fim.month)}"
    )


def registros_pebi_html():
    return "".join(f"<li>{registro}</li>" for registro in REGISTROS_OBRIGATORIOS_PEBI)


def registros_pebi_texto():
    return "\n".join(REGISTROS_OBRIGATORIOS_PEBI)


def enviar_email_alerta(destinatario, nome, eventos, data_alvo):
    if not smtp_configurado():
        raise RuntimeError("SMTP nao configurado")

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    usar_ssl = os.getenv("SMTP_USE_SSL", "").lower() in {"1", "true", "sim", "yes"} or smtp_port == 465
    usar_starttls = os.getenv("SMTP_STARTTLS", "true").lower() not in {"0", "false", "nao", "não", "no"}
    lista_eventos_html, lista_eventos_texto = montar_listas_eventos_email(eventos)
    compromisso = eventos[0]["evento"] if len(eventos) == 1 else "compromissos do calendario"

    mensagem = EmailMessage()
    mensagem["Subject"] = f"Evento: {compromisso} - {data_alvo.strftime('%d/%m/%Y')}"
    mensagem["From"] = smtp_from
    mensagem["To"] = destinatario
    mensagem.set_content(
        f"Ola, {nome}!\n\n"
        f"Em breve: {compromisso}.\n\n"
        f"{lista_eventos_texto}\n\n"
        "Fique ligado!"
    )
    mensagem.add_alternative(
        f"""
        <div style="font-family: Arial, sans-serif; color: #1f2937;">
          <h2>Em breve: {compromisso}.</h2>
          <p>Olá, {nome}!</p>
          <p>Fique ligado!</p>
          <ul>{lista_eventos_html}</ul>
        </div>
        """,
        subtype="html"
    )

    contexto = ssl.create_default_context()

    if usar_ssl:
        servidor = smtplib.SMTP_SSL(smtp_host, smtp_port, context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(smtp_host, smtp_port, timeout=30)

    with servidor:
        if not usar_ssl and usar_starttls:
            servidor.starttls(context=contexto)
        servidor.login(smtp_user, smtp_password)
        servidor.send_message(mensagem)


def montar_email_cronograma_pebi(destinatario, nome, periodo, tipo_alerta):
    smtp_from = os.getenv("SMTP_FROM", os.getenv("SMTP_USER"))
    turmas_texto = periodo["turmas_texto"]
    intervalo = periodo_pebi_texto(periodo)
    lista_texto = registros_pebi_texto()
    lista_html = registros_pebi_html()

    mensagem = EmailMessage()
    mensagem["Subject"] = f"Registros PEBI - {turmas_texto}"
    mensagem["From"] = smtp_from
    mensagem["To"] = destinatario

    if tipo_alerta == "inicio":
        mensagem.set_content(
            f"Olá, {nome}!\n\n"
            f"Este é um lembrete de que, dos dias {intervalo}, deverá ser realizado o envio dos registros das turmas {turmas_texto} por meio do formulário abaixo:\n\n"
            f"{FORMULARIO_REGISTROS_PEBI}\n\n"
            "Registros a serem informados:\n\n"
            f"{lista_texto}\n\n"
            "Agradecemos pela colaboração!\n\n"
            "Atenciosamente,\n\n"
            "Coordenação Pedagógica"
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.5;">
          <p>Olá, <strong>{nome}</strong>!</p>
          <p>Este é um lembrete de que, <strong>dos dias {intervalo}</strong>, deverá ser realizado o envio dos registros das turmas <strong>{turmas_texto}</strong> por meio do formulário abaixo:</p>
          <p><a href="{FORMULARIO_REGISTROS_PEBI}">{FORMULARIO_REGISTROS_PEBI}</a></p>
          <p><strong>Registros a serem informados:</strong></p>
          <ul>{lista_html}</ul>
          <p>Agradecemos pela colaboração!</p>
          <p>Atenciosamente,</p>
          <p><strong>Coordenação Pedagógica</strong></p>
        </div>
        """
    else:
        mensagem.set_content(
            f"Olá, {nome}!\n\n"
            "Passando para lembrar sobre o envio dos registros de atividades.\n\n"
            "Caso você já tenha enviado, desconsidere este e-mail.\n\n"
            f"Se ainda não realizou o envio, pedimos a gentileza de preenchê-lo pelo link abaixo:\n\n"
            f"{FORMULARIO_REGISTROS_PEBI}\n\n"
            f"Turmas da semana: {turmas_texto}\n\n"
            "Registros:\n\n"
            f"{lista_texto}\n\n"
            "Agradecemos pela colaboração!\n\n"
            "Atenciosamente,\n\n"
            "Coordenação Pedagógica"
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.5;">
          <p>Olá, <strong>{nome}</strong>!</p>
          <p>Passando para lembrar sobre o envio dos registros de atividades.</p>
          <p>Caso você <strong>já tenha enviado</strong>, desconsidere este e-mail. 😊</p>
          <p>Se ainda não realizou o envio, pedimos a gentileza de preenchê-lo pelo link abaixo:</p>
          <p><a href="{FORMULARIO_REGISTROS_PEBI}">{FORMULARIO_REGISTROS_PEBI}</a></p>
          <p><strong>Turmas da semana: {turmas_texto}</strong></p>
          <p><strong>Registros:</strong></p>
          <ul>{lista_html}</ul>
          <p>Agradecemos pela colaboração!</p>
          <p>Atenciosamente,</p>
          <p><strong>Coordenação Pedagógica</strong></p>
        </div>
        """

    mensagem.add_alternative(html, subtype="html")
    return mensagem


def enviar_email_cronograma_pebi(destinatario, nome, periodo, tipo_alerta):
    if not smtp_configurado():
        raise RuntimeError("SMTP nao configurado")

    mensagem = montar_email_cronograma_pebi(destinatario, nome, periodo, tipo_alerta)

    with abrir_servidor_smtp() as servidor:
        servidor.send_message(mensagem)


def chave_alerta(email, data_evento, evento):
    bruto = f"{email}|{data_evento.isoformat()}|{evento}".encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()


def validar_cron_secret(request: Request):
    cron_secret = os.getenv("CRON_SECRET")

    if not cron_secret:
        return

    authorization = request.headers.get("authorization")

    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Cron nao autorizado")


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
# ALERTAS DO CALENDARIO ESCOLAR
# ==========================================

@app.get("/calendario-escolar")
def get_calendario_escolar():
    try:
        return JSONResponse(
            content={
                "eventos": eventos_calendario_para_resposta(),
                "atualizado_em": datetime.utcnow().isoformat()
            },
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao ler a planilha do calendario escolar: {str(e)}"
        )


@app.get("/alertas/calendario-escolar/status")
def get_status_alertas_calendario():
    try:
        eventos = carregar_eventos_calendario()
        professores = carregar_professores_calendario()

        return {
            "smtp": smtp_status(),
            "eventos_lidos": len(eventos),
            "professores_com_email": len(professores)
        }
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao verificar alertas do calendario: {str(e)}"
        )


@app.get("/alertas/calendario-escolar")
def enviar_alertas_calendario_escolar(
    request: Request,
    data_referencia: date | None = Query(None),
    reenviar: bool = Query(False),
    db: Session = Depends(get_db)
):
    validar_cron_secret(request)

    hoje = data_referencia or date.today()
    data_alvo = hoje + timedelta(days=2)
    eventos = [
        evento
        for evento in carregar_eventos_calendario()
        if evento["data_evento"] == data_alvo
    ]

    if not eventos:
        return {
            "message": "Nenhum evento para alertar",
            "data_alerta": data_alvo.isoformat(),
            "eventos": 0,
            "enviados": 0,
            "ignorados": 0
        }

    professores = carregar_professores_calendario()

    if not professores:
        return {
            "message": "Nenhum professor com email cadastrado na aba PROFESSORES",
            "data_alerta": data_alvo.isoformat(),
            "eventos": len(eventos),
            "enviados": 0,
            "ignorados": 0
        }

    enviados = 0
    ignorados = 0

    for professor in professores:
        eventos_para_enviar = []

        for evento in eventos:
            chave = chave_alerta(professor["email"], evento["data_evento"], evento["evento"])
            ja_enviado = (
                db.query(models.AlertaCalendarioEnviado)
                .filter(models.AlertaCalendarioEnviado.chave == chave)
                .first()
            )

            if ja_enviado and not reenviar:
                ignorados += 1
                continue

            eventos_para_enviar.append((chave, evento, ja_enviado))

        if not eventos_para_enviar:
            continue

        try:
            enviar_email_alerta(
                professor["email"],
                professor["nome"],
                [evento for _, evento, _ in eventos_para_enviar],
                data_alvo
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao enviar email para {professor['email']}: {str(e)}"
            )

        for chave, evento, ja_enviado in eventos_para_enviar:
            if ja_enviado:
                ja_enviado.enviado_em = datetime.utcnow()
            else:
                db.add(models.AlertaCalendarioEnviado(
                    chave=chave,
                    email=professor["email"],
                    data_evento=evento["data_evento"],
                    evento=evento["evento"],
                    enviado_em=datetime.utcnow()
                ))
            enviados += 1

        db.commit()

    return {
        "message": "Alertas processados",
        "data_alerta": data_alvo.isoformat(),
        "eventos": len(eventos),
        "professores": len(professores),
        "enviados": enviados,
        "ignorados": ignorados
    }


@app.get("/alertas/cronograma-envio-pebi/status")
def get_status_alertas_cronograma_pebi():
    try:
        professores = carregar_professores_pebi()

        return {
            "smtp": smtp_status(),
            "professores_pebi_com_email": len(professores),
            "periodos_configurados": len(CRONOGRAMA_ENVIO_PEBI),
            "gid_professores_pebi": GID_PROFESSORES_PEBI
        }
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao verificar alertas do cronograma PEBI: {str(e)}"
        )


@app.get("/alertas/cronograma-envio-pebi")
def enviar_alertas_cronograma_pebi(
    request: Request,
    data_referencia: date | None = Query(None),
    reenviar: bool = Query(False),
    db: Session = Depends(get_db)
):
    validar_cron_secret(request)

    hoje = data_referencia or date.today()
    alertas_do_dia = []

    for periodo in CRONOGRAMA_ENVIO_PEBI:
        if periodo["inicio"] == hoje:
            alertas_do_dia.append(("inicio", periodo))
        if periodo["fim"] == hoje:
            alertas_do_dia.append(("fim", periodo))

    if not alertas_do_dia:
        return {
            "message": "Nenhum alerta PEBI para hoje",
            "data_referencia": hoje.isoformat(),
            "periodos": 0,
            "professores": 0,
            "enviados": 0,
            "ignorados": 0
        }

    professores = carregar_professores_pebi()

    if not professores:
        return {
            "message": "Nenhum professor com email cadastrado na aba PROFESSORES PEBI",
            "data_referencia": hoje.isoformat(),
            "periodos": len(alertas_do_dia),
            "professores": 0,
            "enviados": 0,
            "ignorados": 0
        }

    enviados = 0
    ignorados = 0
    detalhes = []
    emails_para_enviar = []

    for tipo_alerta, periodo in alertas_do_dia:
        turmas_periodo = set(periodo["turmas"])
        professores_do_periodo = [
            professor
            for professor in professores
            if professor["turma"] in turmas_periodo
        ]

        detalhes.append({
            "tipo": tipo_alerta,
            "turmas": periodo["turmas_texto"],
            "periodo": periodo_pebi_texto(periodo),
            "professores_encontrados": len(professores_do_periodo)
        })

        for professor in professores_do_periodo:
            evento = (
                f"cronograma-pebi|{tipo_alerta}|{periodo['inicio'].isoformat()}|"
                f"{periodo['fim'].isoformat()}|{periodo['turmas_texto']}"
            )
            chave = chave_alerta(professor["email"], hoje, evento)
            ja_enviado = (
                db.query(models.AlertaCalendarioEnviado)
                .filter(models.AlertaCalendarioEnviado.chave == chave)
                .first()
            )

            if ja_enviado and not reenviar:
                ignorados += 1
                continue

            emails_para_enviar.append({
                "professor": professor,
                "periodo": periodo,
                "tipo_alerta": tipo_alerta,
                "chave": chave,
                "evento": evento,
                "ja_enviado": ja_enviado
            })

    if not emails_para_enviar:
        return {
            "message": "Alertas PEBI processados",
            "data_referencia": hoje.isoformat(),
            "periodos": len(alertas_do_dia),
            "professores": len(professores),
            "enviados": 0,
            "ignorados": ignorados,
            "detalhes": detalhes
        }

    try:
        with abrir_servidor_smtp() as servidor:
            for item in emails_para_enviar:
                professor = item["professor"]
                mensagem = montar_email_cronograma_pebi(
                    professor["email"],
                    professor["nome"],
                    item["periodo"],
                    item["tipo_alerta"]
                )
                servidor.send_message(mensagem)

                if item["ja_enviado"]:
                    item["ja_enviado"].enviado_em = datetime.utcnow()
                else:
                    db.add(models.AlertaCalendarioEnviado(
                        chave=item["chave"],
                        email=professor["email"],
                        data_evento=hoje,
                        evento=item["evento"],
                        enviado_em=datetime.utcnow()
                    ))

                enviados += 1

            db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao enviar emails PEBI: {str(e)}"
        )

    return {
        "message": "Alertas PEBI processados",
        "data_referencia": hoje.isoformat(),
        "periodos": len(alertas_do_dia),
        "professores": len(professores),
        "enviados": enviados,
        "ignorados": ignorados,
        "detalhes": detalhes
    }

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
