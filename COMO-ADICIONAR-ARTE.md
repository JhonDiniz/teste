# Como adicionar arte de um personagem

## Estrutura

```
arena-de-leilao.html
prepare_sprite.py
assets/sprites/
    son-goku/
        front.png
        back.png
        charge-front.png     (opcional)
        charge-back.png      (opcional)
        ssj-front.png        (opcional)
        ssj-back.png         (opcional)
```

O `assets/` fica **ao lado** do HTML. Funciona no GitHub Pages e abrindo o
arquivo direto no navegador.

## Passo a passo

**1. Processe cada estado**

```bash
python3 prepare_sprite.py --slug vegeta --state front       frente.png
python3 prepare_sprite.py --slug vegeta --state back        costas.png
python3 prepare_sprite.py --slug vegeta --state charge-front carga-frente.png
python3 prepare_sprite.py --slug vegeta --state ssj-front    ssj-frente.png
```

**2. Confira o alinhamento — este passo não é opcional**

```bash
python3 prepare_sprite.py --check vegeta
```

Abra `assets/sprites/vegeta/_contato.png`:

- **Linha dourada** = chão. Todos precisam pisar nela.
- **Linha verde** = topo do corpo. As alturas precisam bater.

Se algum estado estiver fora, reprocesse **só ele**:

```bash
python3 prepare_sprite.py --slug vegeta --state ssj-front ssj-frente.png --scale 1.06
python3 prepare_sprite.py --slug vegeta --state charge-front carga.png --dy -4
```

`--scale 1.06` deixa 6% maior. `--dy -4` sobe 4px.

**3. Declare no HTML**

Procure por `const ART = {` e acrescente:

```js
"Vegeta": {
  slug: "vegeta",
  states: ["front","back","chargeFront","chargeBack","ssjFront","ssjBack"]
},
```

O nome da chave tem que ser **exatamente** o nome do personagem em `RAW`.
Em `states`, liste só o que existe de verdade na pasta.

**4. Nome da transformação**

O texto da faixa que cruza a tela vem de `ULTIMATES[nome].name`. Já está
preenchido para todos os personagens com Ultimate — só edite se quiser mudar.

## Por que o alinhamento importa tanto

A animação de transformação é só uma troca de `src` na mesma `<img>`. Isso só
funciona porque as seis artes compartilham o mesmo canvas, com a sola dos pés e
o centro do corpo no mesmo ponto.

Arte solta, no recorte que veio da fonte, faz o personagem pular de tamanho e
desgrudar do chão na hora da troca. O script existe por causa disso.

## Regras que o jogo segue sozinho

- Personagem sem entrada em `ART` → stick figure. Nada quebra.
- Estado não declarado em `states` → o jogo nunca pede aquele arquivo.
- Sem `charge-*` → pula a fase de carga de ki e transforma direto, mas a faixa
  com o nome ainda aparece.
- Arquivo faltando ou com erro de carregamento → cai no stick figure em vez de
  mostrar ícone de imagem quebrada.
- Só entram na pré-carga os dois lutadores em campo.

## Se mudar o tamanho do canvas

`CANVAS_W`, `CANVAS_H`, `BODY_H`, `ANCHOR_X` e `ANCHOR_Y` no script são um
contrato com o `SPRITE_CANVAS` do HTML. Mudar um exige mudar o outro **e
reprocessar todas as artes de todos os personagens**.
