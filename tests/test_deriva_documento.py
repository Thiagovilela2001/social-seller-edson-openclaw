"""Teste de DERIVA entre o Documento Mestre e o schema real (Doutrina de 29/09/2026).

**O que este arquivo é.** A v3 do Documento Mestre não morreu de envelhecer.
Morreu porque três dias de trabalho pesado foram entregues sem que ninguém
atualizasse o documento, e a sessão seguinte descobriu um motor diferente do
descrito. A doutrina ratificada pelo Gian em 29/09/2026 é: *o documento acompanha
o código — toda mudança que toca uma seção do documento atualiza a seção no MESMO
commit, com data e hash.*

Doutrina que ninguém verifica é letra morta. Este teste é o que a verifica.

**O que ele compara.** A tabela canônica da §48 do
`Agente_Social_Seller_Documento_Mestre_v4.md` contra o schema real do SQLite e
contra o dicionário `RETENCAO_DIAS` / `RETENCAO_PERMANENTE` do `rules.py`, nos
dois sentidos e também no NÚMERO do prazo:

1. toda tabela do schema está declarada no documento;
2. toda tabela declarada no documento existe no schema;
3. todo prazo declarado bate com o prazo no código.

**Sobre a robustez.** Se a §48 for movida, renumerada ou reformatada, este teste
tem de falhar com uma mensagem que diga o que fazer — nunca com `IndexError` ou
qualquer outra exceção de parse. É o mesmo princípio que vale para o relatório de
eliminação: um relatório que mente sobre a própria cegueira é pior que a
cegueira.

Rodar:  python3 -m unittest discover -s tests
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Caminho estável: relativo ao arquivo de teste, nunca ao cwd de quem roda.
RAIZ = Path(__file__).resolve().parents[1]
DOCUMENTO = RAIZ / "Agente_Social_Seller_Documento_Mestre_v4.md"
sys.path.insert(0, str(RAIZ / "engine" / "instagram_seller"))

import rules  # noqa: E402

# Cabeçalho da tabela canônica. É a âncora de parse: o teste lê a tabela que
# começa por esta linha, e só ela. As outras tabelas da §48 (a de regras de
# coluna, por exemplo) ficam de fora de propósito.
CABECALHO_CANONICO = "| `tabela` | `status` | `prazo` |"

# Tabelas que não são dado de pessoa: o mesmo critério já usado em
# `tests/test_lgpd.py:108` (`manutencao` guarda o relógio do expurgo,
# `sqlite_sequence` é do próprio SQLite).
ISENTAS_DE_PRAZO = frozenset({"manutencao", "sqlite_sequence"})

_RE_PRAZO_NUMERICO = re.compile(r"^(\d+)\s+dias?$")


class TestDerivaDocumentoSchema(unittest.TestCase):
    """A tabela canônica da §48 e o schema real precisam contar a mesma história."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["IG_STATE_DB"] = str(Path(self._tmp.name) / "estado.db")
        os.environ["IG_KILL_SWITCH"] = str(Path(self._tmp.name) / "kill")

    def tearDown(self) -> None:
        for var in ("IG_STATE_DB", "IG_KILL_SWITCH"):
            os.environ.pop(var, None)
        self._tmp.cleanup()

    # -- infraestrutura de leitura -------------------------------------------

    def texto_documento(self) -> str:
        self.assertTrue(
            DOCUMENTO.exists(),
            f"Documento Mestre v4 não encontrado em {DOCUMENTO}. "
            "O teste de deriva não tem o que comparar: ou o documento foi movido "
            "ou apagado.",
        )
        return DOCUMENTO.read_text(encoding="utf-8")

    def linhas_canonicas(self) -> dict[str, tuple[str, str]]:
        """Lê a §48 e devolve {tabela: (status, prazo)}.

        Falha com mensagem explícita — não com exceção de parse — quando a seção
        foi movida, renumerada ou reformatada.
        """
        texto = self.texto_documento()
        linhas = texto.splitlines()

        inicio = None
        for i, linha in enumerate(linhas):
            if linha.strip() == CABECALHO_CANONICO:
                inicio = i + 2  # pula o cabeçalho e o separador `| --- |`
                break

        if inicio is None:
            self.fail(
                "A tabela canônica de tabelas não foi encontrada no Documento Mestre.\n"
                f"Procurei, em {DOCUMENTO.name}, a linha de cabeçalho exatamente igual a:\n"
                f"  {CABECALHO_CANONICO}\n"
                "Ela é a âncora de parse do teste de deriva. Se a §48 foi movida, "
                "renumerada ou reescrita, restaure esse cabeçalho literal e as "
                "linhas `| `tabela` | `status` | `prazo` |` logo abaixo.\n"
                "Não é para afrouxar o teste: é para corrigir o documento."
            )

        canonicas: dict[str, tuple[str, str]] = {}
        for linha in linhas[inicio:]:
            if not linha.strip().startswith("|"):
                break  # fim da tabela
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            if len(celulas) < 3 or not celulas[0].startswith("`"):
                continue
            nome = celulas[0].strip("`")
            if nome:
                canonicas[nome] = (celulas[1], celulas[2])

        self.assertTrue(
            canonicas,
            "A tabela canônica foi localizada mas está vazia. Declare pelo menos "
            "uma linha `| `tabela` | `status` | `prazo` |`.",
        )
        return canonicas

    def tabelas_do_schema(self) -> set[str]:
        with rules.db() as conn:
            return {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

    # -- as três afirmações -------------------------------------------------

    def test_toda_tabela_do_schema_esta_declarada_no_documento(self) -> None:
        declaradas = set(self.linhas_canonicas())
        faltando = self.tabelas_do_schema() - declaradas
        self.assertFalse(
            faltando,
            "tabela(s) que existem no schema e NÃO estão declaradas na tabela "
            f"canônica da §48 do Documento Mestre v4: {sorted(faltando)}\n"
            "O que fazer: declarar a linha na §48 com status e prazo. Se a tabela "
            "é dado de pessoa e ainda não tem prazo, o prazo é decisão do "
            "jurídico do Edson (Pendência 8) — NÃO invente o número para o teste "
            "ficar verde.",
        )

    def test_toda_tabela_declarada_existe_no_schema(self) -> None:
        declaradas = set(self.linhas_canonicas())
        fantasma = declaradas - self.tabelas_do_schema()
        self.assertFalse(
            fantasma,
            "tabela(s) declaradas na §48 do Documento Mestre v4 que NÃO existem "
            f"no schema: {sorted(fantasma)}\n"
            "O que fazer: ou corrigir o nome na §48, ou o código foi removido e "
            "o documento ficou para trás. Documento que descreve o que não "
            "existe é pior que ausência de documentação.",
        )

    def test_prazo_declarado_bate_com_o_codigo(self) -> None:
        """O número é a parte do documento que envelhece em silêncio.

        Um prazo trocado no `rules.py` sem trocar na §48 produz retenção que
        ninguém consegue defender na hora em que o cliente perguntar.
        """
        canonicas = self.linhas_canonicas()
        divergencias: list[str] = []

        for tabela, (_status, prazo_doc) in sorted(canonicas.items()):
            if tabela in ISENTAS_DE_PRAZO:
                continue

            codigo = rules.RETENCAO_DIAS.get(tabela)
            permanente = tabela in rules.RETENCAO_PERMANENTE

            declarado = prazo_doc.strip()
            numerico = _RE_PRAZO_NUMERICO.match(declarado)

            if numerico:
                if codigo is None:
                    divergencias.append(
                        f"{tabela}: documento diz '{declarado}' mas "
                        "RETENCAO_DIAS não tem a tabela"
                    )
                elif codigo != int(numerico.group(1)):
                    divergencias.append(
                        f"{tabela}: documento diz '{declarado}', código diz {codigo} dias"
                    )
            elif declarado == "permanente":
                if not permanente:
                    divergencias.append(
                        f"{tabela}: documento diz 'permanente' mas a tabela não "
                        "está em RETENCAO_PERMANENTE"
                    )
                elif codigo is not None:
                    divergencias.append(
                        f"{tabela}: está em RETENCAO_PERMANENTE e também tem "
                        f"{codigo} dias em RETENCAO_DIAS — as duas coisas"
                    )
            elif declarado == "sem prazo":
                if codigo is not None or permanente:
                    divergencias.append(
                        f"{tabela}: documento diz 'sem prazo' mas o código tem "
                        f"{codigo or 'RETENCAO_PERMANENTE'}"
                    )
            elif declarado == "TTL na linha":
                # §46.3: `ownership` é reserva com TTL, categoria diferente de
                # prazo de guarda. O teste existe para ninguém "resolver" isso
                # colocando um número inventado em RETENCAO_DIAS.
                if codigo is not None:
                    divergencias.append(
                        f"{tabela}: é TTL na linha e NÃO pode ter entrada em "
                        f"RETENCAO_DIAS (o código põe {codigo} dias)"
                    )
            else:
                divergencias.append(
                    f"{tabela}: prazo '{declarado}' não é um valor aceito. Use "
                    "'N dias', 'permanente', 'TTL na linha', 'sem prazo' ou '—'."
                )

        self.assertFalse(
            divergencias,
            "prazo(s) do documento que divergem do código:\n  - "
            + "\n  - ".join(divergencias)
            + "\nO que fazer: mudar nos DOIS lados no mesmo commit — o dicionário "
              "RETENCAO_DIAS/RETENCAO_PERMANENTE em engine/instagram_seller/rules.py "
              "e a tabela da §48 deste documento.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
