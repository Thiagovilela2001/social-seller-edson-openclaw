#!/usr/bin/env python3
"""Pedido de credenciais — gera o texto e encaminha pelo canal disponivel.

POR QUE UM SCRIPT, E NAO UM TEXTO COLADO NO CHAT
    Pedido de chave escrito a mao diverge do codigo no primeiro commit: pede o
    que ja existe e esquece o que apareceu depois. Aqui a lista NAO e escrita:
    ela sai de `capacidades.py` (as variaveis que o contrato de ferramentas
    declara) mais as quatro que o ingress/gateway exigem e que nao sao
    capacidade de negocio. Se alguem declarar uma capacidade com uma variavel
    nova, o `--check` falha ate a ficha dela existir — pedido desatualizado e
    pior que pedido nenhum, porque manda a pessoa buscar a coisa errada.

REGRA DE SEGURANCA (sem excecao)
    Este script nunca le, imprime, grava, argumenta ou repassa VALOR de
    credencial. Ele pergunta por NOME e verifica PRESENCA (`set` / `ausente`).
    O valor entra pelo cofre de segredos do Gateway ou pelo `.env` da maquina —
    nunca pelo chat, nunca por print, nunca no repositorio (que e publico).
    E por isso que nao existe `--token`: o desenho impede o erro.

Uso:
    python tools/pedir_credenciais.py                       # gera e mostra o pedido do Edson
    python tools/pedir_credenciais.py --para todos          # os tres destinatarios de uma vez
    python tools/pedir_credenciais.py --para gian           # so o bloco do Gian
    python tools/pedir_credenciais.py --status              # o que ja esta setado agora
    python tools/pedir_credenciais.py --check               # CI: toda variavel do codigo tem ficha?
    python tools/pedir_credenciais.py --canal clipboard     # copia para a area de transferencia
    python tools/pedir_credenciais.py --canal whatsapp --para edson --telefone 5511999999999
    python tools/pedir_credenciais.py --canal email --para edson --destino x@y.com --confirmar
    python tools/pedir_credenciais.py --canal telegram --confirmar
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, urlencode, urlparse

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import capacidades as cap  # noqa: E402

DOCS = RAIZ / "docs"


def destino(para: str) -> tuple[Path, Path]:
    """Um par de arquivos POR destinatario.

    Nome unico para os tres fazia o ultimo gerado vencer — e o pedido do Edson
    virar o do Gian sem ninguem notar. Documento trocado e pior que documento
    ausente: manda a pessoa buscar o que nao e dela.
    """
    return (
        DOCS / f"PEDIDO-CREDENCIAIS-{para}.md",
        DOCS / f"PEDIDO-CREDENCIAIS-{para}.txt",
    )

try:  # console do Windows em cp1252 derruba o script no primeiro acento
    cast(Any, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    cast(Any, sys.stderr).reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass


# ---------------------------------------------------------------------------
# Ficha de cada variavel — o humano que vai buscar precisa disto, nao do nome
# ---------------------------------------------------------------------------

# bloco: 1-ingresso (sem ela o webhook nem sobe), 1-instagram, 1-telegram,
#        0-interno (nos inventamos), 3-fornecedor (contrato antes do token)
FICHAS: dict[str, dict[str, str]] = {
    # --- ingress: sem estas tres o sidecar recusa subir e nada entra --------
    "META_APP_SECRET": {
        "bloco": "1-ingresso",
        "dono": "edson",
        "o_que": "Chave secreta do app Meta (do app no nome do cliente, nao de um app de teste)",
        "onde": "App Meta > Configuracoes > Basico > Chave secreta do app",
        "armadilha": "Sem ela o sidecar nao valida a assinatura e nao sobe: nenhum comentario ou DM chega, mesmo com token de envio bom.",
    },
    "META_VERIFY_TOKEN": {
        "bloco": "0-interno",
        "dono": "interno",
        "o_que": "Frase longa aleatoria inventada por nos (handshake de verificacao do webhook)",
        "onde": "Geramos aqui: `python -c \"import secrets;print(secrets.token_urlsafe(32))\"`",
        "armadilha": "E inventada, nao pedida ao Edson. Vai tambem na tela do webhook da Meta, entao precisa ser combinada com quem cadastra o webhook.",
    },
    "OPENCLAW_HOOK_TOKEN": {
        "bloco": "0-interno",
        "dono": "interno",
        "o_que": "Bearer que o sidecar usa para falar com o Gateway",
        "onde": "Geramos aqui (mesmo comando) e colocamos em hooks.token do Gateway",
        "armadilha": "Se o Gateway subir sem esse token combinado, o intake recebe 401 e o evento morre na porta.",
    },
    "SOCIAL_SELLER_REPO": {
        "bloco": "0-interno",
        "dono": "interno",
        "o_que": "Caminho do repositorio na maquina que vai rodar (resolve workspace e MCP)",
        "onde": "No sandbox: /home/thiago/projetos/ClaudeCode/social-seller-edson-openclaw",
        "armadilha": "Sem ela o config do agente nem resolve: `openclaw gateway status` lista os warnings e o agente fica indisponivel.",
    },
    # --- envio no Instagram -------------------------------------------------
    "IG_ACCESS_TOKEN": {
        "bloco": "1-instagram",
        "dono": "edson",
        "o_que": "Token de longa duracao da conta profissional do Instagram",
        "onde": "App Meta > Instagram > API setup com a conta profissional; gerar token de longa duracao",
        "armadilha": "Token de curta duracao expira em 1h e o agente para de responder sem avisar. Ninguem renova sozinho: definir quem renova e a cada quanto tempo.",
    },
    "IG_USER_ID": {
        "bloco": "1-instagram",
        "dono": "edson",
        "o_que": "ID da conta profissional — numero interno, NAO o @",
        "onde": "App Meta > Instagram > ID da conta profissional (ou endpoint /me/accounts)",
        "armadilha": "@edsonburger nao serve: o ID e numerico e e o que entra nas chamadas de DM/reply.",
    },
    "TELEGRAM_BOT_TOKEN": {
        "bloco": "1-telegram",
        "dono": "edson",
        "o_que": "Token do bot do time (fila humana / escalada A0)",
        "onde": "Telegram > @BotFather > /newbot",
        "armadilha": "Sem bot nao existe fila humana: o agente bloqueia o caso A0 e o alerta nao chega a ninguem.",
    },
    "TELEGRAM_CHAT_ID": {
        "bloco": "1-telegram",
        "dono": "edson",
        "o_que": "ID do chat/grupo do plantao",
        "onde": "Convidar o bot no grupo e ler o id (ou @userinfobot)",
        "armadilha": "SLA sem gente do outro lado e numero decorativo — este id e metade da regra RN-012.",
    },
    # --- fornecedores: contrato antes de token ------------------------------
    "CLINT_MCP_URL": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Endpoint MCP SOMENTE LEITURA da Clint + credencial",
        "onde": "Contrato/suporte da Clint",
        "armadilha": "Antes de ligar, precisa a regra de ownership por caso (§19): senao Clint + canal nativo + n8n emitem a mesma mensagem para a mesma pessoa.",
    },
    "BLING_API_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Token de leitura de pedidos, rastreio e financeiro (Bling/ERP)",
        "onde": "Painel do Bling > integracoes/API",
        "armadilha": "O token e condicao necessaria, nao suficiente: a leitura no motor ainda nao esta implementada. Ter token nao libera a afirmacao de status (RN-019).",
    },
    "YAMPI_API_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Token de leitura de pedidos (Yampi)",
        "onde": "Painel da Yampi > API",
        "armadilha": "Confirmar a semantica de 'pedido pago' vs transacao antes de codar contra ela.",
    },
    "EDUZZ_API_KEY": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Leitura das faturas do contrato (Eduzz)",
        "onde": "Painel da Eduzz > API",
        "armadilha": "Fatura paga nao e recorrência quitada — o dado precisa vir com o que distingue os dois.",
    },
    "LIA_API_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Leitura de parcelas/fatura + segunda via (LIA financiamento)",
        "onde": "Contrato/suporte LIA",
        "armadilha": "Dado financeiro: exige vinculo verificado (§07). Sem isso e consulta sem titular.",
    },
    "TIKTOK_SHOP_APP_KEY": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "App key do TikTok Shop Partner",
        "onde": "TikTok Shop Partner Center",
        "armadilha": "Sem o escopo seller.customer_service aprovado para a loja BR, os metodos existem e nao respondem.",
    },
    "TIKTOK_SHOP_ACCESS_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Access token do TikTok Shop Partner",
        "onde": "TikTok Shop Partner Center (apos aprovacao do escopo)",
        "armadilha": "Mesma armadilha do app key: escopo aprovado e o que decide, nao o token.",
    },
    "YOUTUBE_API_KEY": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Projeto no Google Cloud com YouTube Data API v3",
        "onde": "Google Cloud Console > APIs > YouTube Data API v3",
        "armadilha": "Quota: comments.insert custa ~50 unidades. Dimensionar antes de planejar volume.",
    },
    "YOUTUBE_OAUTH_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "OAuth do canal do YouTube",
        "onde": "Google Cloud Console > OAuth consent + refresh do canal",
        "armadilha": "OAuth de canal errado modera o canal errado. Conferir o canal autorizado no go-live.",
    },
    "EMAIL_SMTP_URL": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "URL SMTP de remetente corporativo",
        "onde": "Provedor do dominio (com SPF/DKIM/DMARC)",
        "armadilha": "Sem autenticacao de dominio o e-mail cai em spam — e o agente acha que enviou.",
    },
    "BIGDATA_CONNECTION": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Acesso ao BigData interno (Assiny)",
        "onde": "§26: provedor, datasets, chaves, frequencia e SLA ainda sao DESCONHECIDOS",
        "armadilha": "Nao existe 'a credencial' para pedir enquanto o contrato nao definir os cinco itens. Pedir antes disso e adivinhacao.",
    },
    "WHATSAPP_TOKEN": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Token do WhatsApp (BLOQUEADO — ver §27)",
        "onde": "NAO PEDIR AINDA: cobranca/debt collection e restrita na plataforma",
        "armadilha": "Renomear o caso para 'utility' nao muda o enquadramento. Primeiro a decisao de conformidade do dono, depois o token.",
    },
    "WHATSAPP_PHONE_ID": {
        "bloco": "3-fornecedor",
        "dono": "gian",
        "o_que": "Phone ID do WhatsApp (BLOQUEADO — ver §27)",
        "onde": "NAO PEDIR AINDA: mesma decisao de conformidade pendente",
        "armadilha": "Pedir a credencial antes da decisao so cria a tentacao de usar.",
    },
}

# O que nao e chave e trava igual — custo zero, dependencia de decisao.
# Os itens do host vem MEDIDOS, nao supostos: ver secao "Como conferir".
SEM_CREDENCIAL: list[tuple[str, str, str]] = [
    ("Politica de garantia/devolucao/frete (RN-011)", "edson",
     "Uma linha escrita libera o agente para afirmar. Hoje ele nao pode afirmar nada, nem o que e direito legal."),
    ("Quem e o plantao (RN-012)", "edson",
     "SLA sem gente do outro lado e numero decorativo: e a diferenca entre a fila funcionar e existir."),
    ("Lista oficial de produtos, precos e links", "edson",
     "O agente nao calcula preco: recebe do banco. Sem catalogo nao ha venda."),
    ("Owner do caso por canal (§19/§28)", "gian",
     "Sem isso, Clint + canal nativo + n8n podem emitir a MESMA mensagem para a mesma pessoa."),
    ("Decisao §27 (WhatsApp e cobranca)", "gian",
     "Nao e config tecnica: e decisao de conformidade do dono."),
    ("1) Rota publica SEM login para /webhooks/instagram", "gian",
     "O tunel openclaw.edsonburger.com.br responde 302 (login do Cloudflare Access) em TODAS as rotas testadas: /, /health, "
     "/webhooks/instagram e /hooks/agent. A Meta nao faz login — ela espera 200 com o hub.challenge devolvido, e recebe um "
     "redirect para a tela de senha. Precisa de hostname dedicado (ou bypass de Access no caminho) para o webhook."),
    ("2) A rota tem de publicar o SIDECAR, nao o gateway", "gian",
     "O tunel aponta para o gateway (18789). O webhook mora no sidecar (8080), que e quem valida a assinatura e roda o intake. "
     "Sem uma regra de ingress para a porta do sidecar, a Meta bate no gateway e leva 404 — e o 302 do item 1 esconde isso."),
    ("3) Saida do container para graph.facebook.com e api.telegram.org", "gian",
     "Medido no sandbox: 'Could not resolve host' para graph.facebook.com, api.telegram.org e ate google.com. Sem saida, o "
     "agente nao responde DM e nao avisa o plantao — nao e ajuste nosso, e o isolamento do container. O host do tunel tem saida; "
     "o sandbox nao tem. Por isso importa saber ONDE roda o gateway que o tunel publica."),
    ("4) Acesso ao host do gateway (subir o sidecar e os hooks)", "gian",
     "O sidecar precisa rodar no mesmo host do gateway tunelado, e o gateway precisa de hooks.token + hooks.allowedAgentIds "
     "para aceitar /hooks/agent. Sem acesso a esse host, o agente fica construido e sem lugar para morar."),
]

DESTINATARIOS: dict[str, dict[str, object]] = {
    "edson": {
        "titulo": "Credenciais do Instagram e do plantao — Social Seller",
        "abertura": (
            "Para o agente sair do papel faltam acessos, nao codigo. Nada aqui\n"
            "precisa ir por chat: entrego o caminho seguro de entrega no fim do texto."
        ),
        "blocos": ("1-instagram", "1-telegram", "1-ingresso"),
        "sem_credencial": ("edson",),
    },
    "gian": {
        "titulo": "Acessos e decisoes pendentes — Social Seller (Instagram)",
        "abertura": (
            "O agente esta construido e testado; o que trava e acesso de terceiro e\n"
            "decisao de governanca. Segue o que depende de contrato, escopo ou decisao."
        ),
        "blocos": ("3-fornecedor",),
        "sem_credencial": ("gian",),
        "verificar": [
            "# 1. o tunel responde a Meta? (302 = Access no caminho; 200 + '12345' = pronto)",
            'curl -sS -w "\\nhttp %{http_code}\\n" '
            '"https://openclaw.edsonburger.com.br/webhooks/instagram'
            '?hub.mode=subscribe&hub.verify_token=x&hub.challenge=12345"',
            "",
            "# 2. o host do agente alcanca a API do Instagram? (400 = alcanca; resolve = sem saida)",
            'curl -sS -o /dev/null -w "graph: %{http_code}\\n" https://graph.facebook.com/v21.0/me',
            'curl -sS -o /dev/null -w "telegram: %{http_code}\\n" https://api.telegram.org/',
            "",
            "# 3. o container do sandbox alcanca? (medido em 13/10: falha de DNS nas tres)",
            'ssh thiago-sandbox \'curl -sS -o /dev/null -w "%{http_code}\\n" https://graph.facebook.com/v21.0/me\'',
        ],
    },
    "interno": {
        "titulo": "Variaveis que nos mesmos geramos e configuramos",
        "abertura": (
            "Nao dependem de terceiro. Entram no .env da maquina ou no cofre do\n"
            "Gateway, e o comando de cada uma esta na tabela."
        ),
        "blocos": ("0-interno",),
        "sem_credencial": (),
    },
}

BLOCO_TITULO = {
    "1-ingresso": "1. Ingress — sem estas o webhook nem sobe",
    "1-instagram": "2. Envio no Instagram",
    "1-telegram": "3. Fila humana (Telegram)",
    "0-interno": "0. Geradas por nos",
    "3-fornecedor": "4. Fornecedores — contrato antes de token",
}

REGRA_ENTREGA = (
    "COMO ENTREGAR (nunca pelo chat, nunca por print):\n"
    "  - o valor vai para um item de cofre de senhas (1Password/Bitwarden) ou para o .env da\n"
    "    maquina que vai rodar, com exatamente o nome da variavel da tabela;\n"
    "  - se preferir, use entrada mascarada no Gateway — o valor nao passa por texto;\n"
    "  - o repositorio e PUBLICO: chave colada em issue, commit ou print e chave vazada.\n"
    "Quando as chaves chegarem, o drill e este (nada de 'acho que esta ligado'):\n"
    "  python ingress/sidecar.py --check              # config completa?\n"
    "  python tools/checklist_credenciais.py --check   # tabela em dia com o codigo?\n"
    "  openclaw mcp doctor instagram-seller --probe    # o servidor MCP responde?"
)


# ---------------------------------------------------------------------------
# Derivacao: capacidades.py + fichas. Nada escrito a mao duas vezes.
# ---------------------------------------------------------------------------

def variaveis_do_contrato() -> dict[str, list[str]]:
    """var -> capacidades que ela destrava (fonte: capacidades.py)."""
    por_var: dict[str, list[str]] = {}
    for nome, c in cap.CAPACIDADES.items():
        for v in c.variaveis:
            por_var.setdefault(v, []).append(nome)
    return {v: sorted(c) for v, c in por_var.items()}


def fichas_sem_cobertura() -> list[str]:
    """Variavel que o codigo pede e a ficha nao cobre. Vazio e o estado sao."""
    return sorted(set(variaveis_do_contrato()) - set(FICHAS))


def presentes() -> dict[str, bool]:
    """Presenca apenas. Valor nunca e lido — nem aqui."""
    nomes: set[str] = set(FICHAS)
    for env_file in (RAIZ / ".env", Path.home() / ".openclaw" / ".env"):
        if env_file.exists():
            for linha in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                linha = linha.strip()
                if linha and not linha.startswith("#") and "=" in linha:
                    nomes.add(linha.split("=", 1)[0].strip())
    return {n: bool(os.environ.get(n)) for n in sorted(nomes)}


# ---------------------------------------------------------------------------
# Montagem do texto
# ---------------------------------------------------------------------------

def _linhas_tabela(blocos: tuple[str, ...]) -> list[list[str]]:
    """var, o que e, onde obter, por que importa (a armadilha + o que ela destrava)."""
    por_var = variaveis_do_contrato()
    linhas: list[list[str]] = []
    for var in sorted(FICHAS):
        f = FICHAS[var]
        if f["bloco"] not in blocos:
            continue
        destrava = por_var.get(var, [])
        if destrava:
            porque = f["armadilha"] + " Destrava: " + ", ".join(destrava) + "."
        else:
            porque = f["armadilha"] + " Nao e capacidade de negocio: e config."
        linhas.append([var, f["o_que"], f["onde"], porque])
    return linhas


def montar_markdown(para: str) -> str:
    d = DESTINATARIOS[para]
    out: list[str] = [f"# {d['titulo']}", "", str(d["abertura"]), ""]
    blocos = tuple(d["blocos"])  # type: ignore[arg-type]

    for bloco in ("1-ingresso", "1-instagram", "1-telegram", "0-interno", "3-fornecedor"):
        if bloco not in blocos:
            continue
        linhas = _linhas_tabela((bloco,))
        if not linhas:
            continue
        out += [f"## {BLOCO_TITULO[bloco]}", "", "| Variavel | O que e | Onde obter | Por que importa |", "|---|---|---|---|"]
        for var, o_que, onde, porque in linhas:
            out.append(f"| `{var}` | {o_que} | {onde} | {porque} |")
        out.append("")

    donos = tuple(d["sem_credencial"])  # type: ignore[arg-type]
    travam = [(n, por) for n, dono, por in SEM_CREDENCIAL if dono in donos]
    if travam:
        out += ["## Nao e chave, mas trava igual (custo zero)", ""]
        for nome, por in travam:
            out.append(f"- **{nome}** — {por}")
        out.append("")

    verificar = d.get("verificar")
    if verificar:
        out += [
            "## Como conferir (nao precisa acreditar em mim)",
            "",
            "```bash",
            *[str(linha) for linha in verificar],  # type: ignore[union-attr]
            "```",
            "",
        ]

    out += ["---", "", REGRA_ENTREGA, ""]
    return "\n".join(out)


def montar_texto_puro(para: str) -> str:
    """Versao de WhatsApp: sem tabela markdown, que nao renderiza em app de mensagem.

    Sai do MESMO markdown (uma fonte, dois formatos) — pedido que diverge entre
    o que foi revisado e o que foi enviado e pedido que ninguem conferiu.
    """
    linhas: list[str] = []
    for linha in montar_markdown(para).splitlines():
        s = linha.strip()
        if s.startswith("# "):
            linhas += [f"*{s[2:].strip()}*", ""]
        elif s.startswith("## "):
            linhas += ["", f"*{s[3:].strip()}*"]
        elif s.startswith("|---") or s.startswith("| Variavel"):
            continue
        elif s.startswith("```"):
            continue
        elif s.startswith("|"):
            celulas = [c.strip() for c in s.strip("|").split("|")]
            linhas.append(f"• {celulas[0]} — {celulas[1]}. Onde: {celulas[2]}")
            linhas.append(f"   motivo: {celulas[3]}")
        elif s.startswith("- **"):
            linhas.append("• " + s[2:].replace("**", ""))
        elif s == "---":
            continue
        else:
            linhas.append(s)
    return "\n".join(linhas).replace("\n\n\n", "\n\n").strip() + "\n"


# ---------------------------------------------------------------------------
# Canais de encaminhamento
# ---------------------------------------------------------------------------

def canal_arquivo(para: str, texto_md: str, texto_txt: str) -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    md_path, txt_path = destino(para)
    md_path.write_text(texto_md, encoding="utf-8", newline="\n")
    txt_path.write_text(texto_txt, encoding="utf-8", newline="\n")
    print(f"gerado: {md_path}")
    print(f"gerado: {txt_path}")
    return 0


def canal_clipboard(texto: str) -> int:
    if sys.platform == "win32":
        cmd = ["clip"]
    elif sys.platform == "darwin":
        cmd = ["pbcopy"]
    elif shutil.which("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    else:
        print("sem area de transferencia neste sistema — use --canal arquivo")
        return 1
    res = subprocess.run(cmd, input=texto.encode("utf-8"), capture_output=True)
    if res.returncode != 0:
        print(f"falha ao copiar: {res.stderr.decode(errors='replace')}")
        return 1
    print("texto copiado — cole no canal do destinatario e revise antes de enviar")
    return 0


def canal_whatsapp(texto: str, telefone: str) -> int:
    """Nao envia sozinho: abre a conversa com o texto pronto e a pessoa confere."""
    if not telefone:
        print("--telefone e obrigatorio no canal whatsapp (formato 55DDDNUMERO)")
        return 1
    url = f"https://wa.me/{telefone}?text={quote(texto)}"
    try:
        if sys.platform == "win32":
            os.startfile(url)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", url], check=False)
    except Exception as e:  # pragma: no cover
        print(f"nao consegui abrir o navegador ({e}). Link:\n{url}")
        return 1
    print("WhatsApp aberto com o texto pronto — confira antes de apertar enviar")
    return 0


def canal_email(texto: str, destino: str, confirmar: bool) -> int:
    """SMTP so se estiver configurado E confirmado. Sem credencial, diz o que falta."""
    smtp_url = os.environ.get("EMAIL_SMTP_URL", "")
    if not smtp_url:
        print("EMAIL_SMTP_URL ausente: sem SMTP configurado nao ha envio de e-mail.")
        print("Enquanto isso: --canal arquivo | --canal clipboard | --canal whatsapp")
        return 1
    if not destino:
        print("--destino e obrigatorio no canal email")
        return 1
    if not confirmar:
        print(f"[dry-run] enviaria para {destino} ({len(texto)} chars). Repita com --confirmar.")
        return 0
    import smtplib
    from email.message import EmailMessage

    partes = urlparse(smtp_url)
    msg = EmailMessage()
    msg["From"] = partes.username or "social-seller@localhost"
    msg["To"] = destino
    msg["Subject"] = "Acessos pendentes — Social Seller (Instagram)"
    msg.set_content(texto)
    with smtplib.SMTP(partes.hostname or "", partes.port or 587, timeout=30) as s:
        s.starttls()
        if partes.username:
            s.login(partes.username, partes.password or "")
        s.send_message(msg)
    print(f"enviado para {destino}")
    return 0


def canal_telegram(texto: str, confirmar: bool) -> int:
    """Bot do Hermes/Telegram, se houver token no ambiente. Nunca pede token em argumento."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("HERMES_TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ALLOWED_CHATS")
    if not token or not chat:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes — sem bot nao ha envio.")
        return 1
    if not confirmar:
        print(f"[dry-run] enviaria {len(texto)} chars para o chat {chat[:6]}... Repita com --confirmar.")
        return 0
    data = urlencode({"chat_id": chat.split(",")[0], "text": texto}).encode()
    with urllib.request.urlopen(
        urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=30
    ) as r:
        print("telegram:", json.loads(r.read().decode())["ok"])
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Pedido de credenciais — gera e encaminha")
    p.add_argument("--para", choices=sorted(DESTINATARIOS) + ["todos"], default="edson")
    p.add_argument("--canal", choices=("arquivo", "clipboard", "whatsapp", "email", "telegram"), default="arquivo")
    p.add_argument("--telefone", default="", help="canal whatsapp: 55DDDNUMERO")
    p.add_argument("--destino", default="", help="canal email: endereco")
    p.add_argument("--confirmar", action="store_true", help="envio real (sem isso e dry-run)")
    p.add_argument("--status", action="store_true", help="presenca das variaveis agora")
    p.add_argument("--check", action="store_true", help="CI: toda variavel do codigo tem ficha?")
    p.add_argument("--json", action="store_true", help="saida em json (com --status)")
    args = p.parse_args()

    if args.check:
        faltas = fichas_sem_cobertura()
        if faltas:
            print("FAIL  variavel no contrato sem ficha de pedido: " + ", ".join(faltas))
            print("      complete FICHAS neste arquivo — pedido incompleto manda buscar a coisa errada.")
            return 1
        print(f"PASS  {len(FICHAS)} variaveis com ficha, cobrindo {len(variaveis_do_contrato())} do contrato")
        return 0

    if args.status:
        estado = presentes()
        if args.json:
            print(json.dumps(estado, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        setadas = [v for v, ok in estado.items() if ok]
        print(f"setadas: {len(setadas)}/{len(estado)}")
        for var in sorted(FICHAS):
            print(f"  {'set  ' if estado.get(var) else 'AUSENTE'}  {var:<26} [{FICHAS[var]['bloco']}]")
        return 0

    if args.para == "todos":
        rc = 0
        for nome in sorted(DESTINATARIOS):
            rc |= canal_arquivo(nome, montar_markdown(nome), montar_texto_puro(nome))
        print("\npedido do Edson (revisar antes de encaminhar):\n")
        print(montar_texto_puro("edson"))
        return rc

    md = montar_markdown(args.para)
    txt = montar_texto_puro(args.para)

    if args.canal == "arquivo":
        rc = canal_arquivo(args.para, md, txt)
        if rc == 0:
            print("\n--- pedido (" + args.para + ") ---\n")
            print(md)
        return rc
    if args.canal == "clipboard":
        return canal_clipboard(txt)
    if args.canal == "whatsapp":
        return canal_whatsapp(txt, args.telefone)
    if args.canal == "email":
        return canal_email(txt, args.destino, args.confirmar)
    return canal_telegram(txt, args.confirmar)


if __name__ == "__main__":
    sys.exit(main())
