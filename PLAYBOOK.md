# PLAYBOOK — Arena de Leilão

Referência interna para os 4 tipos de pedido recorrentes. Objetivo: eu ir direto
ao trecho certo com `grep`/`view -view_range` em vez de reler o arquivo inteiro.

Convenção de anchors: `arquivo :: função/const` — sempre `grep -n "^const NOME\|^function nome"`
pra achar a linha atual, porque edições deslocam número de linha mas não o texto-âncora.

---

## 1. Adicionar personagem (sem arte, sem transformação)

**Arquivos:** só o bloco de dados. Nunca mexe em lógica.

| O quê | Anchor | Formato |
|---|---|---|
| Nome + anime + nível + tipo | `const RAW = {` | `["Nome","weak\|medium\|strong","physical\|magic\|hybrid"]`, opcional 4º item `"ult"`, 5º `"once"` |
| Vida/escudos/3 ataques | `const CHAR_KIT = [` | mesma posição sequencial do `RAW` (ordem de anime → ordem dentro do anime) |
| Aparência (fallback stick figure) | `const APPEARANCE = [` | `[pele, corCabelo, estilo, roupa, roupa2]` |
| Classe + elemento | `const CLASS_TYPE = [` | `["Classe","Elemento"]` — elemento precisa existir em `ELEMENT_ICON`/`ELEMENT_GLOW` (`part7.html`) |
| 4º ataque | `const FOURTH_ATTACK = [` | `A(nome, tipo, dano, cooldown, efeito, onceOnly)` |
| Ultimate (se aplicável) | `const ULTIMATES = {` | chave = nome EXATO do personagem |

**Regra crítica:** as 5 listas (`CHAR_KIT`, `APPEARANCE`, `CLASS_TYPE`, `FOURTH_ATTACK`) são
posicionais e têm que crescer JUNTAS, na mesma ordem que `RAW`. Inserir um nome no meio de
`RAW` sem inserir nas outras 4 desalinha todo mundo depois dele. Mais seguro:
sempre adicionar personagem no FIM de um anime existente, ou criar anime novo no fim de `RAW`
(e adicionar o nome em `ANIMES`).

**Rank/raridade e Ultimate são automáticos** — não mexer. `rankCharacters()`
(`part5.html`, perto de `RANK_TIERS`) calcula tudo a partir de vida/escudo/dano/efeitos.

**Não precisa tocar:** motor de batalha, leilão, UI. Um personagem novo em `RAW`
+ as 4 listas já aparece no índice, no leilão e é jogável — com stick figure.

---

## 2. Adicionar animação de transformação (arte + Ultimate tipo "transform")

**Pré-requisito:** personagem já existe (seção 1) e tem entrada em `ULTIMATES` com
`kind` omitido/`"transform"` (não `"meteor"`).

### 2.1 — Preparar a arte (fora do HTML)
```bash
python3 prepare_sprite.py --slug <slug> --state front        arte.png
python3 prepare_sprite.py --slug <slug> --state back         arte.png
python3 prepare_sprite.py --slug <slug> --state charge-front arte.png   # opcional
python3 prepare_sprite.py --slug <slug> --state charge-back  arte.png   # opcional
python3 prepare_sprite.py --slug <slug> --state ssj-front    arte.png
python3 prepare_sprite.py --slug <slug> --state ssj-back     arte.png
python3 prepare_sprite.py --check <slug>          # SEMPRE — ver COMO-ADICIONAR-ARTE.md
```

### 2.2 — Uma entrada no HTML
Anchor: `const ART = {` (`part5.html`). Acrescentar:
```js
"Nome Exato": { slug: "slug-da-pasta", states: ["front","back","chargeFront","chargeBack","ssjFront","ssjBack"] },
```
`states` lista só o que existe de verdade — sem `charge*`, o jogo pula direto pro clarão.

### 2.3 — Nada mais.
`bitmapFor`, `chargeBitmapFor`, `preloadArt`, `artFailed`, `playTransformation` e a
faixa de título (`.ult-title` em `part2.html`) já são genéricos — funcionam pra
qualquer personagem que tenha entrada em `ART` + `ULTIMATES`. **Não duplicar
código de animação por personagem.**

**Se a transformação tiver custo especial** (ex.: Might Guy perde vida por rodada,
Edward perde escudo permanente) — isso já é dado, não código: ver campos
`selfRecoil`, `upfrontToll`, `permanentShieldCost`, `growPerHit/growCap/explodeOnDeath`
em `ULTIMATES` (`part4.html`) e a lógica que já os lê em `useUltimate()` (`part8.html`).
Não escrever `if(nome==="X")` em lugar nenhum — sempre generalizar por campo de dado.

---

## 3. Adicionar animação de ataque (ainda não implementado — só o gancho existe)

**Estado atual:** ataques só têm a animação genérica CSS de avanço/retorno
(`.anim-attack-player`/`.anim-attack-enemy`, `part2.html`, keyframes `lungeUp`/`lungeDown`).
Não existe troca de sprite por golpe.

**Quando formos implementar, o padrão é o mesmo da transformação — reaproveitar:**

| Peça | Já existe? | Onde |
|---|---|---|
| Troca de `src` sem deslocar pixel (ancoragem) | ✅ | `SPRITE_CANVAS`, `prepare_sprite.py` |
| Registro de estados extras por personagem | ✅ (padrão `states: []`) | `const ART` |
| Função que resolve qual arquivo mostrar | ✅ (`bitmapFor`) — precisaria 3º parâmetro `pose` | `part5.html` |
| Sequência timed com trava de polling | ✅ (`playTransformation`, `animLock`) | `part7.html` |
| Gatilho no motor de batalha (`lastFx`) | ✅ padrão (`kind:"transform"`) — replicar como `kind:"attackPose"` | `applyAction()`, `part8.html` |

**Plano quando pedir:** adicionar `attackFront`/`attackBack` em `STATE_FILE` e
`ART.states`; `bitmapFor(c, view, transformed, pose)` ganha checagem de pose;
`applyAction` seta `b.lastFx.kind="attackPose"` com o `attackerId`; `triggerBattleFx`
ganha um branch curto que troca o `src` por ~200-300ms e volta — sem precisar da
fase de "carga", então bem mais simples que a transformação. **Não implementar
isso preventivamente — só quando o pedido vier com a arte em mãos**, porque o
formato exato da pose (quantos frames, se tem contra-golpe, etc.) muda o design.

---

## 4. Adicionar nova mecânica (efeito de ataque, status, regra de batalha)

**Efeitos de ataque existentes:** `shield`, `heal`, `debuff`, `stun`, `dot`.
Todos seguem o mesmo padrão em 3 pontos que SEMPRE precisam mudar juntos:

1. **Criação do efeito nos dados** — `E(type, value)` (`part3.html`, perto de `function E`).
   Usado em `A(nome, tipo, dano, cooldown, E("novoTipo", valor), onceOnly)`.
2. **Aplicação em batalha** — bloco `if(atk.effect){ ... }` dentro de
   `applyAction()` (`part8.html`, anchor `if(atk.effect.type===`). Acrescentar
   `else if(atk.effect.type==="novoTipo" ...)`. Ler o padrão dos 5 existentes:
   sempre loga em `b.log.unshift`, sempre empurra em `fxEffects` se tiver visual.
3. **Descrição pro jogador** — `describeEffect()` (`part6.html`). Sem isso o
   efeito não aparece no texto do botão de ataque nem no índice de personagens.

**Se o efeito precisa "tickar" turno a turno** (como `dot`), olhar o padrão já
implementado no fim de `applyAction()` (bloco `Object.keys(b.dot).forEach`) — é
o único efeito hoje com persistência multi-turno. Novo efeito assim precisa de
storage próprio em `initBattle()` — procurar a linha `hp:{}, cooldowns:{}, ...`
dentro da função, é uma lista inline de objetos por-personagem — e tick equivalente.

**Se a mecânica é de REGRA GERAL de batalha** (não efeito de ataque específico —
ex: nova condição de vitória, novo tipo de troca, novo cálculo de dano):
não existe padrão único, mas os pontos de entrada mais prováveis são:
- Fórmula de dano → `applyAction()`, linha `const dmg = Math.max(5, ...)`
- Condição de vitória → `postAction()` (`part8.html`)
- Regra de troca → `doSwitch()` (`part8.html`)
- Novo tipo de Ultimate (além de `transform`/`meteor`) → `useUltimate()` (`part8.html`),
  seguir o padrão do `if(c.ultimate.kind==="meteor"){...} else {...}`

**Sempre perguntar antes de implementar mecânica nova:** ela é POR PERSONAGEM
(vai em dado, tipo os campos de `ULTIMATES`) ou É REGRA DO JOGO (vai em código)?
Confundir os dois é o erro mais caro — mecânica de personagem hardcoded vira
`if(nome===)` espalhado; regra geral guardada como dado por personagem quebra
na primeira exceção.

---

## Como validar qualquer mudança sem reler tudo

```bash
node --check game.js                    # sintaxe
node run.js                              # renderiza sprites/bitmaps isolados, se mexeu em arte
node sim.js                              # partida completa headless: leilão → ultimates → batalha até o fim
```

`sim.js`/`run.js` não fazem parte do jogo — são arneses de teste que criei
(stubs de `document`/`firebase`, harness de composição de imagem). Ficam fora
do HTML final. Recriá-los é rápido: stub de DOM + `eval` do JS extraído do
`<script>` inline do HTML (ver histórico desta conversa se precisar reconstruir).

## O que NUNCA precisa reler o arquivo inteiro para mudar
Dado (seções 1, parte de 4) = só grep pela const certa.
O que exige entender o fluxo antes de mexer = motor de batalha (`applyAction`,
`useUltimate`, `postAction`) e a máquina de fases (`draw()`/`state.phase`) —
essas duas áreas têm efeitos colaterais entre si (cooldown, stun, dot, transform
todos tickam na mesma função) e merecem leitura da função inteira, não só do trecho.
