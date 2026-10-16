import os
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Banco: Firebase Realtime Database acessado pela API REST.
# Tudo fica sob /crm para não misturar com outros dados do banco.
FIREBASE_URL = os.environ.get(
    "FIREBASE_URL", "https://teresa-cdc74-default-rtdb.firebaseio.com"
).rstrip("/")

ETAPAS = ["novo", "contactado", "proposta", "ganho", "perdido"]
CAMPOS_CONTATO = ["nome", "email", "telefone", "empresa"]


# ---------- Acesso ao Firebase ----------
def _url(caminho):
    return f"{FIREBASE_URL}/crm/{caminho}.json"


def fb_listar(colecao):
    """Retorna lista de itens da coleção, cada um com seu 'id'."""
    dados = requests.get(_url(colecao), timeout=10).json() or {}
    return [{"id": k, **v} for k, v in dados.items()]


def fb_obter(colecao, id_):
    dado = requests.get(_url(f"{colecao}/{id_}"), timeout=10).json()
    return {"id": id_, **dado} if dado else None


def fb_criar(colecao, dado):
    resposta = requests.post(_url(colecao), json=dado, timeout=10).json()
    return {"id": resposta["name"], **dado}


def fb_atualizar(colecao, id_, campos):
    requests.patch(_url(f"{colecao}/{id_}"), json=campos, timeout=10)


def fb_apagar(colecao, id_):
    requests.delete(_url(f"{colecao}/{id_}"), timeout=10)


# ---------- Utilitários ----------
def _agora():
    return datetime.now().isoformat(timespec="seconds")


def _erro(mensagem, codigo):
    return jsonify({"erro": mensagem}), codigo


def _json():
    return request.get_json(silent=True) or {}


# ---------- Interface ----------
@app.get("/")
def interface():
    return render_template("index.html", etapas=ETAPAS)


@app.get("/api")
def info():
    return jsonify({"servico": "CRM Simples", "etapas": ETAPAS})


# ---------- Contatos ----------
@app.get("/contatos")
def listar_contatos():
    """Lista contatos. ?busca= filtra por nome, email ou empresa."""
    itens = fb_listar("contatos")
    busca = request.args.get("busca", "").lower()
    if busca:
        itens = [
            c for c in itens
            if busca in (c.get("nome") or "").lower()
            or busca in (c.get("email") or "").lower()
            or busca in (c.get("empresa") or "").lower()
        ]
    return jsonify(itens)


@app.post("/contatos")
def criar_contato():
    dados = _json()
    if not dados.get("nome"):
        return _erro("Campo 'nome' é obrigatório", 422)
    contato = {k: dados.get(k) for k in CAMPOS_CONTATO}
    contato["criado_em"] = _agora()
    return jsonify(fb_criar("contatos", contato)), 201


@app.get("/contatos/<contato_id>")
def obter_contato(contato_id):
    """Retorna o contato com seus negócios e notas."""
    contato = fb_obter("contatos", contato_id)
    if not contato:
        return _erro(f"Contato {contato_id} não encontrado", 404)
    return jsonify({
        **contato,
        "negocios": [n for n in fb_listar("negocios") if n.get("contato_id") == contato_id],
        "notas": [n for n in fb_listar("notas") if n.get("contato_id") == contato_id],
    })


@app.patch("/contatos/<contato_id>")
def atualizar_contato(contato_id):
    if not fb_obter("contatos", contato_id):
        return _erro(f"Contato {contato_id} não encontrado", 404)
    dados = _json()
    fb_atualizar("contatos", contato_id, {k: dados[k] for k in CAMPOS_CONTATO if k in dados})
    return jsonify(fb_obter("contatos", contato_id))


@app.delete("/contatos/<contato_id>")
def apagar_contato(contato_id):
    if not fb_obter("contatos", contato_id):
        return _erro(f"Contato {contato_id} não encontrado", 404)
    fb_apagar("contatos", contato_id)
    for colecao in ("negocios", "notas"):
        for item in fb_listar(colecao):
            if item.get("contato_id") == contato_id:
                fb_apagar(colecao, item["id"])
    return jsonify({"status": "apagado", "id": contato_id})


# ---------- Negócios ----------
@app.get("/negocios")
def listar_negocios():
    """Lista negócios. Filtros opcionais: ?etapa= e ?contato_id="""
    itens = fb_listar("negocios")
    etapa = request.args.get("etapa")
    contato_id = request.args.get("contato_id")
    if etapa:
        itens = [n for n in itens if n.get("etapa") == etapa]
    if contato_id:
        itens = [n for n in itens if n.get("contato_id") == contato_id]
    return jsonify(itens)


@app.post("/negocios")
def criar_negocio():
    dados = _json()
    if not dados.get("contato_id") or not fb_obter("contatos", dados["contato_id"]):
        return _erro("contato_id inválido ou inexistente", 404)
    if not dados.get("titulo"):
        return _erro("Campo 'titulo' é obrigatório", 422)
    etapa = dados.get("etapa", "novo")
    if etapa not in ETAPAS:
        return _erro(f"Etapa inválida. Use uma de: {ETAPAS}", 422)
    negocio = {
        "contato_id": dados["contato_id"],
        "titulo": dados["titulo"],
        "valor": float(dados.get("valor") or 0),
        "etapa": etapa,
        "criado_em": _agora(),
    }
    return jsonify(fb_criar("negocios", negocio)), 201


@app.patch("/negocios/<negocio_id>")
def atualizar_negocio(negocio_id):
    """Atualiza titulo, valor ou etapa (use para mover no funil)."""
    if not fb_obter("negocios", negocio_id):
        return _erro(f"Negócio {negocio_id} não encontrado", 404)
    dados = _json()
    if "etapa" in dados and dados["etapa"] not in ETAPAS:
        return _erro(f"Etapa inválida. Use uma de: {ETAPAS}", 422)
    campos = {k: dados[k] for k in ("titulo", "valor", "etapa") if k in dados}
    fb_atualizar("negocios", negocio_id, campos)
    return jsonify(fb_obter("negocios", negocio_id))


@app.delete("/negocios/<negocio_id>")
def apagar_negocio(negocio_id):
    if not fb_obter("negocios", negocio_id):
        return _erro(f"Negócio {negocio_id} não encontrado", 404)
    fb_apagar("negocios", negocio_id)
    return jsonify({"status": "apagado", "id": negocio_id})


# ---------- Notas ----------
@app.get("/notas")
def listar_notas():
    itens = fb_listar("notas")
    contato_id = request.args.get("contato_id")
    if contato_id:
        itens = [n for n in itens if n.get("contato_id") == contato_id]
    return jsonify(itens)


@app.post("/notas")
def criar_nota():
    dados = _json()
    if not dados.get("contato_id") or not fb_obter("contatos", dados["contato_id"]):
        return _erro("contato_id inválido ou inexistente", 404)
    if not dados.get("texto"):
        return _erro("Campo 'texto' é obrigatório", 422)
    nota = {
        "contato_id": dados["contato_id"],
        "texto": dados["texto"],
        "criado_em": _agora(),
    }
    return jsonify(fb_criar("notas", nota)), 201


# ---------- Resumo ----------
@app.get("/resumo")
def resumo():
    """Visão geral do funil: totais e valor por etapa."""
    negocios = fb_listar("negocios")
    por_etapa = {
        e: {
            "quantidade": sum(1 for n in negocios if n.get("etapa") == e),
            "valor_total": sum(n.get("valor", 0) for n in negocios if n.get("etapa") == e),
        }
        for e in ETAPAS
    }
    return jsonify({
        "total_contatos": len(fb_listar("contatos")),
        "total_negocios": len(negocios),
        "por_etapa": por_etapa,
    })


if __name__ == "__main__":
    app.run(debug=True)
