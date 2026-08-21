#!/usr/bin/env python3
"""
prepare_sprite.py — prepara arte de personagem para a Arena de Leilão.

O trabalho difícil aqui NÃO é recortar o fundo. É o ALINHAMENTO.

As artes chegam de fontes diferentes, cada uma com seu enquadramento, sua escala
e sua pose. Se cada uma entrar no jogo no recorte que veio, o personagem pula de
tamanho e desgruda do chão a cada troca de estado — e a animação de transformação,
que é só uma troca de `src`, fica visivelmente quebrada.

Este script joga toda arte num canvas comum, com a SOLA DOS PÉS e o CENTRO DO
CORPO no mesmo ponto. Depois disso trocar a imagem não desloca um pixel.

USO
    python3 prepare_sprite.py --slug son-goku --state front  arte.png
    python3 prepare_sprite.py --slug son-goku --state charge-front  aura.png
    python3 prepare_sprite.py --check son-goku

    Estados válidos: front, back, charge-front, charge-back, ssj-front, ssj-back

FLUXO RECOMENDADO
    1. Processe todos os estados do personagem.
    2. Rode --check e ABRA a folha de contato. Todos devem pisar na mesma linha
       e ter mais ou menos a mesma altura.
    3. Se algum estiver fora, reprocesse só ele com --scale / --dy.
       Não existe detecção automática que acerte 100% dos enquadramentos; por
       isso os knobs existem e a folha de contato é passo obrigatório.

DEPENDÊNCIA
    pip install pillow
"""

import argparse, os, sys
from collections import deque

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Falta a Pillow. Rode:  pip install pillow")

import numpy as np

# ---------------------------------------------------------------------------
# Estes números são um CONTRATO com o jogo. Se mudar aqui, tem que mudar
# SPRITE_CANVAS no HTML e reprocessar TODAS as artes de TODOS os personagens.
CANVAS_W, CANVAS_H = 210, 245
BODY_H             = 220          # altura do corpo (topo do cabelo -> sola)
ANCHOR_X           = 105          # centro horizontal do corpo
ANCHOR_Y           = 241          # linha do chão
# ---------------------------------------------------------------------------

STATES = ["front", "back", "charge-front", "charge-back", "ssj-front", "ssj-back"]


def key_background(a):
    """Apaga o fundo por preenchimento a partir das BORDAS.

    Por que não "todo pixel claro vira transparente": isso comeria o emblema
    branco nas costas, o cano claro das botas e qualquer detalhe branco interno.
    Partindo das bordas, só some o que está conectado ao lado de fora.

    Aceita branco puro e também o xadrez de transparência quando ele veio
    chapado na imagem (acontece com print de PNG salvo como JPG).
    Exige baixa saturação para não comer auras coloridas claras.
    """
    h, w, _ = a.shape
    rgb = a[:, :, :3]
    lo, hi = rgb.min(axis=2), rgb.max(axis=2)
    bg_like = (lo > 205) & ((hi - lo) < 14)

    seen = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if bg_like[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg_like[y, x] and not seen[y, x]:
                seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg_like[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    a[seen, 3] = 0

    # JPEG deixa um halo claro na borda que o preenchimento não alcança porque
    # ele é levemente mais escuro que o limiar. Uma erosão de 1px resolve.
    op = a[:, :, 3] > 0
    halo = op & bg_like
    nb = np.zeros_like(op)
    nb[1:, :] |= ~op[:-1, :]; nb[:-1, :] |= ~op[1:, :]
    nb[:, 1:] |= ~op[:, :-1]; nb[:, :-1] |= ~op[:, 1:]
    a[halo & nb, 3] = 0
    return a


def body_box(a, exclude_glow=True):
    """Caixa do CORPO, ignorando aura/brilho.

    Isso importa porque um quadro com aura é muito maior que o mesmo personagem
    sem aura. Medir a escala pela imagem inteira encolheria o personagem toda vez
    que ele acendesse — exatamente o que a animação não pode fazer.

    A aura é clara e saturada em azul/ciano. Botas azuis escuras NÃO entram no
    filtro porque ele exige brilho alto. Para aura de outra cor (fogo, trevas),
    use --no-glow e ajuste com --scale.
    """
    op = a[:, :, 3] > 60
    m = op
    if exclude_glow:
        r, b = a[:, :, 0], a[:, :, 2]
        lum = a[:, :, :3].max(axis=2)
        aura = (b > r + 28) & (lum > 145)
        white = (a[:, :, :3].min(axis=2) > 195) & (b >= r)
        m = op & ~aura & ~white
    # descarta linhas/colunas com só um punhado de pixels (ruído de borda)
    rows = np.where(m.sum(axis=1) >= 6)[0]
    cols = np.where(m.sum(axis=0) >= 6)[0]
    if len(rows) == 0 or len(cols) == 0:
        raise SystemExit("Não achei corpo na imagem. Tente --no-glow.")
    return dict(top=int(rows.min()), bot=int(rows.max()),
                cx=int((cols.min() + cols.max()) // 2),
                h=int(rows.max() - rows.min() + 1))


def process(path, scale_mult=1.0, dy=0, dx=0, exclude_glow=True, colors=160):
    a = np.array(Image.open(path).convert("RGBA")).astype(int)
    a = key_background(a)
    box = body_box(a, exclude_glow)

    s = (BODY_H / box["h"]) * scale_mult
    im = Image.fromarray(a.astype(np.uint8), "RGBA")
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                   Image.LANCZOS)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    px = ANCHOR_X - round(box["cx"] * s) + dx
    py = ANCHOR_Y - round(box["bot"] * s) + dy
    canvas.alpha_composite(im, (px, py))

    # Quantizar corta o peso quase pela metade sem diferença visível nesta escala.
    # O alpha é reaplicado em cima porque a quantização o achata.
    q = canvas.quantize(colors=colors, method=Image.FASTOCTREE,
                        dither=Image.Dither.NONE).convert("RGBA")
    q.putalpha(canvas.split()[3].point(lambda v: 255 if v > 90 else 0))

    # O aviso tem que olhar o CONTEÚDO, não a caixa da imagem: quase toda arte
    # vem com margem transparente, e comparar a caixa acusaria corte sempre.
    over = []
    src_al = np.array(im)[:, :, 3] > 40
    ys, xs = np.where(src_al)
    if len(xs):
        if px + xs.min() < 0 or px + xs.max() >= CANVAS_W:
            over.append("lateral")
        if py + ys.min() < 0:
            over.append("topo")
    return q, box, s, over


def contact_sheet(slug, out_root):
    """Folha de contato com a linha do chão e a altura alvo desenhadas.

    Passo obrigatório. É olhando isto que se percebe um personagem 8% menor ou
    flutuando 3px acima do chão — coisas invisíveis no arquivo isolado e muito
    visíveis quando a animação troca de quadro.
    """
    d = os.path.join(out_root, slug)
    found = [(st, os.path.join(d, st + ".png")) for st in STATES
             if os.path.exists(os.path.join(d, st + ".png"))]
    if not found:
        sys.exit(f"Nenhuma arte encontrada em {d}")
    sheet = Image.new("RGBA", (CANVAS_W * len(found), CANVAS_H + 18), (22, 25, 34, 255))
    for i, (st, p) in enumerate(found):
        sheet.alpha_composite(Image.open(p).convert("RGBA"), (CANVAS_W * i, 0))
    dr = ImageDraw.Draw(sheet)
    dr.line([(0, ANCHOR_Y), (sheet.width, ANCHOR_Y)], fill=(224, 181, 89, 200))
    dr.line([(0, ANCHOR_Y - BODY_H), (sheet.width, ANCHOR_Y - BODY_H)], fill=(79, 179, 169, 140))
    for i, (st, _) in enumerate(found):
        dr.line([(CANVAS_W * i, 0), (CANVAS_W * i, CANVAS_H)], fill=(50, 56, 70))
        dr.text((CANVAS_W * i + 5, CANVAS_H + 3), st, fill=(154, 160, 175))
    out = os.path.join(out_root, slug, "_contato.png")
    sheet.convert("RGB").save(out)
    print(f"Folha de contato: {out}")
    print("  linha DOURADA = chão (todos devem pisar nela)")
    print("  linha VERDE   = topo do corpo (alturas devem bater)")
    print("  fora do lugar? reprocesse esse estado com --scale / --dy")


def main():
    ap = argparse.ArgumentParser(description="Prepara arte de personagem para a Arena de Leilão.")
    ap.add_argument("imagem", nargs="?")
    ap.add_argument("--slug", help="pasta do personagem, ex: son-goku")
    ap.add_argument("--state", choices=STATES)
    ap.add_argument("--out", default="assets/sprites")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="multiplica a escala automática (1.05 = 5%% maior)")
    ap.add_argument("--dy", type=int, default=0, help="empurra N px pra baixo")
    ap.add_argument("--dx", type=int, default=0, help="empurra N px pra direita")
    ap.add_argument("--no-glow", action="store_true",
                    help="não tenta separar aura do corpo (aura não-azul)")
    ap.add_argument("--colors", type=int, default=160)
    ap.add_argument("--check", metavar="SLUG", help="gera a folha de contato e sai")
    args = ap.parse_args()

    if args.check:
        contact_sheet(args.check, args.out); return
    if not (args.imagem and args.slug and args.state):
        ap.error("informe imagem, --slug e --state (ou use --check)")

    q, box, s, over = process(args.imagem, args.scale, args.dy, args.dx,
                              not args.no_glow, args.colors)
    d = os.path.join(args.out, args.slug)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, args.state + ".png")
    q.save(out, optimize=True)

    print(f"{out}  ({os.path.getsize(out)//1024} KB)")
    print(f"  corpo detectado: {box['h']}px de altura -> escala {s:.3f}")
    if over:
        print(f"  AVISO: a arte transborda o canvas ({', '.join(over)}). "
              f"Use --scale menor que 1 se estiver cortando algo importante.")
    print(f"\nAgora rode:  python3 {os.path.basename(__file__)} --check {args.slug}")


if __name__ == "__main__":
    main()
