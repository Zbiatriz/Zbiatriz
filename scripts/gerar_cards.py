"""Gera os cards kawaii de contribuições e linguagens do perfil.

Roda no GitHub Actions todo dia (veja .github/workflows/cards.yml).
Usa o calendário de contribuições do GitHub, que já inclui as contribuições
de repositórios privados quando "Private contributions" está ativado no perfil.

Uso: GITHUB_TOKEN=... USUARIO=Zbiatriz python scripts/gerar_cards.py
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

USUARIO = os.environ.get("USUARIO", "Zbiatriz")
TOKEN = os.environ["GITHUB_TOKEN"]
SAIDA = Path(os.environ.get("SAIDA", Path(__file__).resolve().parent.parent / "assets" / "cards"))

FUNDO = "#1a0d26"
BORDA = "#3d2352"
ROSA = "#ff8fd8"
LILAS = "#c77dff"
TEXTO = "#f3e8ff"
SUAVE = "#c9a7e8"
# Do "sem contribuição" ao "muitas contribuições"
NIVEIS = ["#2a1838", "#5c2a6e", "#9b4fb8", "#d36fd6", ROSA]
CORES_LINGUAGENS = [ROSA, LILAS, "#f7b2e6", "#9d6bff", "#ffc8dd", "#b388eb", "#e05fc0", "#7b5cd6"]
FONTE = "'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif"
LARGURA = 800


def graphql(query, **variaveis):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variaveis}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "cards-perfil"},
    )
    with urllib.request.urlopen(req) as resp:
        dados = json.load(resp)
    if "errors" in dados:
        raise RuntimeError(dados["errors"])
    return dados["data"]


def buscar_dias():
    """Todos os dias com contagem de contribuições, desde a criação da conta."""
    criado = graphql("query($u:String!){user(login:$u){createdAt}}", u=USUARIO)["user"]["createdAt"]
    hoje = dt.datetime.now(dt.timezone.utc)
    dias = {}
    for ano in range(int(criado[:4]), hoje.year + 1):
        inicio = max(dt.datetime(ano, 1, 1, tzinfo=dt.timezone.utc), dt.datetime.fromisoformat(criado.replace("Z", "+00:00")))
        fim = min(dt.datetime(ano, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc), hoje)
        cal = graphql(
            """query($u:String!,$de:DateTime!,$ate:DateTime!){user(login:$u){
                 contributionsCollection(from:$de,to:$ate){contributionCalendar{
                   weeks{contributionDays{date contributionCount}}}}}}""",
            u=USUARIO, de=inicio.isoformat(), ate=fim.isoformat(),
        )["user"]["contributionsCollection"]["contributionCalendar"]
        for semana in cal["weeks"]:
            for d in semana["contributionDays"]:
                dias[dt.date.fromisoformat(d["date"])] = d["contributionCount"]
    return dict(sorted(dias.items()))


def sequencias(dias):
    hoje = max(dias)
    atual, d = 0, hoje
    if dias.get(d, 0) == 0:  # hoje ainda não acabou: não quebra a sequência
        d -= dt.timedelta(days=1)
    while dias.get(d, 0) > 0:
        atual += 1
        d -= dt.timedelta(days=1)
    maior = corrida = 0
    for qtd in dias.values():
        corrida = corrida + 1 if qtd > 0 else 0
        maior = max(maior, corrida)
    return atual, maior


def nivel(qtd, maximo):
    if qtd == 0:
        return 0
    return min(4, 1 + int(3 * qtd / max(maximo, 1)))


def numero(n):
    return f"{n:,}".replace(",", ".")


def dias_txt(n):
    return f"{n} {'dia' if n == 1 else 'dias'}"


def moldura(altura, conteudo):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{altura}" viewBox="0 0 {LARGURA} {altura}">
<style>text {{ font-family: {FONTE}; }}</style>
<rect x="0.5" y="0.5" width="{LARGURA - 1}" height="{altura - 1}" rx="14" fill="{FUNDO}" stroke="{BORDA}"/>
{conteudo}
</svg>
"""


def card_contribuicoes(dias):
    hoje = max(dias)
    total = sum(dias.values())
    no_ano = sum(q for d, q in dias.items() if d.year == hoje.year)
    atual, maior = sequencias(dias)

    stats = [
        (numero(total), "contribuições no total"),
        (numero(no_ano), f"contribuições em {hoje.year}"),
        (dias_txt(atual), "sequência atual ♡"),
        (dias_txt(maior), "maior sequência"),
    ]
    partes = [f'<text x="26" y="40" fill="{ROSA}" font-size="18" font-weight="700">₊˚⊹♡ minhas contribuições</text>']
    coluna = LARGURA / len(stats)
    for i, (valor, rotulo) in enumerate(stats):
        cx = coluna * i + coluna / 2
        cor = ROSA if i == 2 else TEXTO
        partes.append(
            f'<g><text x="{cx:.0f}" y="88" text-anchor="middle" fill="{cor}" font-size="28" font-weight="700">{escape(valor)}</text>'
            f'<text x="{cx:.0f}" y="110" text-anchor="middle" fill="{SUAVE}" font-size="12.5">{escape(rotulo)}</text></g>'
        )

    # Mapa das últimas 53 semanas, começando num domingo como no GitHub
    cel, passo = 11, 14
    inicio = hoje - dt.timedelta(days=(hoje.weekday() + 1) % 7 + 52 * 7)
    janela = {d: q for d, q in dias.items() if d >= inicio}
    maximo = max(janela.values(), default=1)
    x0 = (LARGURA - (53 * passo - 3)) / 2
    y0 = 136
    d = inicio
    while d <= hoje:
        semana = (d - inicio).days // 7
        dia_semana = (d.weekday() + 1) % 7
        q = janela.get(d, 0)
        partes.append(
            f'<rect x="{x0 + semana * passo:.0f}" y="{y0 + dia_semana * passo}" width="{cel}" height="{cel}" rx="3" '
            f'fill="{NIVEIS[nivel(q, maximo)]}"><title>{d.strftime("%d/%m/%Y")}: {q}</title></rect>'
        )
        d += dt.timedelta(days=1)

    y_legenda = y0 + 7 * passo + 18
    lx = LARGURA - x0 - 5 * passo - 40
    partes.append(f'<text x="{lx - 8:.0f}" y="{y_legenda + 9}" text-anchor="end" fill="{SUAVE}" font-size="11">menos</text>')
    for i, cor in enumerate(NIVEIS):
        partes.append(f'<rect x="{lx + i * passo:.0f}" y="{y_legenda}" width="{cel}" height="{cel}" rx="3" fill="{cor}"/>')
    partes.append(f'<text x="{lx + 5 * passo + 4:.0f}" y="{y_legenda + 9}" fill="{SUAVE}" font-size="11">mais</text>')
    partes.append(
        f'<text x="{x0:.0f}" y="{y_legenda + 9}" fill="{SUAVE}" font-size="11">'
        f'atualizado em {dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y")} ✧</text>'
    )
    return moldura(y_legenda + 30, "\n".join(partes))


def card_linguagens():
    repos = graphql(
        """query($u:String!){user(login:$u){repositories(first:100,ownerAffiliations:OWNER,isFork:false){
             nodes{languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}""",
        u=USUARIO,
    )["user"]["repositories"]["nodes"]
    tamanhos = {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            tamanhos[e["node"]["name"]] = tamanhos.get(e["node"]["name"], 0) + e["size"]
    top = sorted(tamanhos.items(), key=lambda x: -x[1])[:8]
    total = sum(t for _, t in top)

    partes = [f'<text x="26" y="40" fill="{ROSA}" font-size="18" font-weight="700">₊˚⊹♡ linguagens que mais uso</text>']
    if not top:
        partes.append(f'<text x="{LARGURA / 2}" y="86" text-anchor="middle" fill="{SUAVE}" font-size="14">em breve, projetos públicos por aqui ♡</text>')
        return moldura(120, "\n".join(partes))

    barra_x, barra_w, barra_y = 26, LARGURA - 52, 60
    partes.append(f'<clipPath id="barra"><rect x="{barra_x}" y="{barra_y}" width="{barra_w}" height="12" rx="6"/></clipPath><g clip-path="url(#barra)">')
    x = barra_x
    for i, (_, t) in enumerate(top):
        w = barra_w * t / total
        partes.append(f'<rect x="{x:.2f}" y="{barra_y}" width="{w + 0.5:.2f}" height="12" fill="{CORES_LINGUAGENS[i]}"/>')
        x += w
    partes.append("</g>")

    por_linha = 4
    for i, (nome, t) in enumerate(top):
        lx = barra_x + (i % por_linha) * (barra_w / por_linha)
        ly = 102 + (i // por_linha) * 28
        partes.append(
            f'<g><circle cx="{lx + 6:.0f}" cy="{ly - 4}" r="6" fill="{CORES_LINGUAGENS[i]}"/>'
            f'<text x="{lx + 18:.0f}" y="{ly}" fill="{TEXTO}" font-size="13.5">{escape(nome)} '
            f'<tspan fill="{SUAVE}">{100 * t / total:.1f}%</tspan></text></g>'
        )
    linhas = (len(top) + por_linha - 1) // por_linha
    return moldura(102 + (linhas - 1) * 28 + 26, "\n".join(partes))


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    dias = buscar_dias()
    (SAIDA / "contribuicoes.svg").write_text(card_contribuicoes(dias), encoding="utf-8")
    (SAIDA / "linguagens.svg").write_text(card_linguagens(), encoding="utf-8")
    print(f"{sum(dias.values())} contribuições, sequências {sequencias(dias)}")


if __name__ == "__main__":
    main()
