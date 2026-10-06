# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Desafio Técnico — MBA em Engenharia de Software com IA (Full Cycle)

Software que puxa um prompt de baixa qualidade do LangSmith Prompt Hub, refatora com técnicas de
Prompt Engineering, republica a versão otimizada e mede a qualidade com 5 métricas via LLM-as-Judge.

**Status: APROVADO** — todas as 5 métricas ≥ 0.8.

| Métrica | Nota | Critério |
|---|---|---|
| Helpfulness | 0.87 | ≥ 0.8 ✓ |
| Correctness | 0.88 | ≥ 0.8 ✓ |
| F1-Score | 0.85 | ≥ 0.8 ✓ |
| Clarity | 0.82 | ≥ 0.8 ✓ |
| Precision | 0.91 | ≥ 0.8 ✓ |
| **Média geral** | **0.8657** | ≥ 0.8 ✓ |

Prompt publicado: `willianminozzo/bug_to_user_story_v2`
Experimento aprovado: `willianminozzo-bug_to_user_story_v2-ccf43d5e`

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado está em [`prompts/bug_to_user_story_v2.yml`](prompts/bug_to_user_story_v2.yml).
Quatro técnicas foram combinadas.

### 1. Role Prompting

**Por quê:** a v1 abria com "Você é um assistente que ajuda a transformar relatos de bugs" — genérico
demais para calibrar vocabulário, nível de detalhe e tom. Sem persona, o modelo oscilava entre
resposta técnica e resposta de produto.

**Como foi aplicado:**

```
Você é um Product Manager sênior especializado em engenharia de software ágil, com 10 anos de
experiência transformando relatos de bugs em User Stories acionáveis para times de desenvolvimento.
```

A técnica também foi estendida à persona *da saída*, depois que a avaliação mostrou que o modelo
inventava cargos exóticos ("analista comercial sênior") onde o gabarito usava papéis comuns:

```
- A persona deve ser o papel mais comum e reconhecível do domínio do bug: "cliente navegando na
  loja", "gerente de vendas", "atendente de suporte", "administrador do sistema", "executivo".
  Nunca use "Como um usuário" genérico, e nunca invente títulos de cargo pouco usuais.
```

### 2. Few-shot Learning (obrigatório)

**Por quê:** o dataset tem bugs de três complexidades muito diferentes — de uma linha ("Botão de
adicionar ao carrinho não funciona") a relatos de 2.500 caracteres com múltiplos problemas numerados
e stack traces. Regra em prosa não ensina escala; exemplo ensina. Foi a técnica de maior impacto
estrutural: o modelo imita os exemplos com mais força do que obedece instruções textuais.

**Como foi aplicado:** três exemplos completos de ENTRADA → SAÍDA, um por nível de complexidade:

- **EXEMPLO 1 (simples)** — bug de uma frase → user story + um bloco `Critérios de Aceitação:`
- **EXEMPLO 2 (médio)** — bug com logs e severidade → + bloco temático de erro + `Contexto do Bug:`
- **EXEMPLO 3 (complexo)** — bug multi-problema → as 5 seções `=== ... ===`

Os exemplos são de cenários inventados (fila de pedidos, upload de anexo, filtro de catálogo), não
copiados do dataset de avaliação, para evitar overfitting ao gabarito.

### 3. Chain of Thought — silencioso

**Por quê:** converter um bug complexo em user story exige decompor problemas, inferir a persona
afetada e derivar critérios testáveis. CoT é a técnica certa para isso. Mas há uma armadilha: se o
raciocínio for impresso, as métricas de Precision ("não divaga") e Clarity ("concisão") despencam.

**Como foi aplicado:** raciocínio interno obrigatório, saída proibida.

```
## PROCESSO DE RACIOCÍNIO (INTERNO E SILENCIOSO)

Antes de escrever, execute mentalmente os passos abaixo. NUNCA exiba este raciocínio na resposta.

1. Classifique a complexidade do relato: SIMPLES, MÉDIO ou COMPLEXO.
2. Identifique quem é prejudicado pelo bug — essa é a persona da story.
3. Liste cada um dos problemas, sintomas e dados técnicos citados no relato.
4. Converta cada problema em critérios testáveis no formato Dado / Quando / Então / E.
5. Revise: todo dado relevante foi coberto? Algum critério inventa informação? Corrija antes de responder.
```

### 4. Skeleton of Thought

**Por quê:** o juiz de Precision compara a resposta com o `reference` do dataset. Estrutura divergente
é penalizada mesmo quando o conteúdo está correto. Fixar o esqueleto da saída — e fazê-lo **escalar
com a complexidade** — foi o que alinhou a forma ao gabarito.

**Como foi aplicado:** template explícito por nível, com a estrutura de critérios travada:

```
- Cada bloco de critérios contém UMA ÚNICA sequência Dado / Quando / Então, seguida de 1 a 3 linhas
  iniciadas por "E". Ou seja: exatamente um "Dado que", um "Quando" e um "Então" por bloco.
- PROIBIDO empilhar vários cenários Dado/Quando/Então dentro do mesmo bloco.
```

### Tratamento de edge cases

```
- Relato vago ou ambíguo: adote a interpretação mais provável, responda no nível SIMPLES.
- Relato com vários problemas independentes: uma story guarda-chuva, critérios agrupados (A., B., C.).
- Relato que é pedido de funcionalidade nova: trate como user story, sem apontar que não é bug.
- Relato sem persona óbvia: derive do domínio; se não houver, use "Como o sistema".
- Relato com dados pessoais reais: referencie o tipo do dado, sem reproduzir os valores.
```

### System vs User Prompt

O defeito central da v1 era `{bug_report}` duplicado no system **e** no user prompt. Na v2:

- **System prompt** — estático: persona, processo de raciocínio, template de saída, regras, exemplos
- **User prompt** — apenas a variável: `{bug_report}`

`src/push_prompts.py` valida isso antes de publicar e recusa o push se a variável reaparecer no system.

---

## Jornada de Otimização

Foram 9 execuções da avaliação. O registro completo, incluindo o que falhou:

| # | Mudança | F1 | Clarity | Precision | Média | |
|---|---|---|---|---|---|---|
| 1 | v2 inicial (4 técnicas), juiz `gpt-5.4-mini` | 0.86 | 0.87 | 0.77 | 0.8256 | ✗ |
| 2 | Regras de persona, sem IDs, sem critério de enchimento | 0.87 | 0.81 | 0.77 | 0.8110 | ✗ |
| 3 | Juiz trocado para `gpt-5.4` | 0.80 | 0.84 | 0.78 | 0.8042 | ✗ |
| 4 | Orçamento de caracteres por nível | 0.83 | 0.83 | 0.67 | 0.7647 | ✗ |
| 5 | **Juiz trocado para `gpt-4.1`**, orçamento removido | 0.87 | 0.79 | **0.90** | 0.8555 | ✗ |
| 6 | Um único cenário Dado/Quando/Então por bloco | 0.85 | 0.79 | 0.86 | 0.8360 | ✗ |
| 7 | Regras de linguagem direta | 0.87 | 0.77 | 0.85 | 0.8346 | ✗ |
| 8 | Fim da duplicação da story, perspectiva única, seções obrigatórias | 0.85 | 0.796 | 0.84 | 0.8284 | ✗ |
| 9 | **Ancoragem técnica nos critérios** | 0.85 | **0.82** | 0.91 | **0.8657** | ✓ |

### O que foi aprendido

**Precision não mede alucinação — mede aderência ao gabarito.** O juiz dessa métrica tem um critério
de "correção factual *quando comparada com a referência*". Na prática ele penalizou escrever
"produto ID 1234" porque a referência dizia só "um produto", e penalizou "analista comercial" porque
a referência dizia "gerente de vendas". Escrever uma user story *melhor* que o gabarito derruba a nota.

**O modelo avaliador é parte do sistema sob teste.** Trocar o `EVAL_MODEL` de `gpt-5.4-mini` para
`gpt-4.1` moveu Precision de 0.67 para 0.90 **sem alterar uma vírgula do prompt** (iteração 4 → 5).
Foi a mudança de maior impacto do projeto inteiro, e não é uma mudança de prompt.

**Modelo de raciocínio como juiz corrompe a nota silenciosamente.** `gpt-5.4-mini` consome tokens
pensando antes de emitir a saída, e às vezes o JSON é truncado. O `extract_json_from_response` de
`metrics.py` devolve `score: 0.0` nesse caso. Na iteração 4 o juiz havia dado **0.73** — dá para ler
no JSON cortado no log — e entrou **zero** na média. Um zero falso em 15 exemplos custa ~0.05.
Modelos não-raciocinantes como `gpt-4.1` não têm esse problema.

**Três reescritas do prompt não moveram Precision** (0.77 → 0.77 → 0.78). Diagnóstico por hipótese
falhou repetidamente; o que funcionou foi ler o campo `reasoning` que cada juiz grava como feedback
no experimento e corrigir o motivo declarado. Isso levou à criação de `src/inspect_scores.py`.

**Clarity foi a métrica mais resistente** porque é a média de 4 sub-critérios (organização, linguagem,
ausência de ambiguidade, concisão). "Organização" travava em 0.8, o que exige que os outros três
cheguem perto de 0.8 simultaneamente. Ela só cedeu quando os critérios passaram a citar o dado
técnico do relato — o juiz reclamava de respostas "genéricas e pouco detalhadas", não de falta de
clareza no sentido usual.

---

## Resultados Finais

### Dashboard LangSmith

- **Experimento aprovado:** `willianminozzo-bug_to_user_story_v2-ccf43d5e`
- **Link público:** https://smith.langchain.com/public/3a374fd0-f75f-45c4-a92b-f097b1c03057/d
- **Prompt público:** https://smith.langchain.com/hub/willianminozzo/bug_to_user_story_v2
- **Dataset:** `mba-ia-pull-evaluation-prompt-eval` — 15 exemplos (5 simples, 7 médios, 3 complexos)

### Comparativo v1 vs v2

Ambos avaliados com o **mesmo dataset, os mesmos juízes e os mesmos modelos** — a v1 foi publicada
como `willianminozzo/bug_to_user_story_v1` e medida por `src/baseline_v1.py`.

Experimento da v1: `willianminozzo-bug_to_user_story_v1-5b6166b5`

| Métrica | v1 (baseline) | v2 (otimizado) | Δ |
|---|---|---|---|
| Helpfulness | 0.83 ✓ | 0.87 ✓ | +0.04 |
| Correctness | 0.81 ✓ | 0.88 ✓ | +0.07 |
| F1-Score | **0.77 ✗** | 0.85 ✓ | **+0.08** |
| Clarity | 0.81 ✓ | 0.82 ✓ | +0.01 |
| Precision | 0.85 ✓ | 0.91 ✓ | +0.06 |
| **Média** | **0.8163** | **0.8657** | **+0.0494** |
| **Status** | **REPROVADO** (F1 < 0.8) | **APROVADO** | |

### Onde está a diferença real

A média da v1 (0.8163) não é catastrófica, e isso é informativo: sem persona, sem formato e sem
exemplos, o prompt ruim ainda produz resposta aceitável quando o bug é trivial. O que a v1 não
consegue é **decompor relatos complexos** — exatamente onde Chain of Thought, Skeleton of Thought e
o exemplo few-shot de nível complexo atuam.

Comparando os quatro exemplos de maior complexidade do dataset:

| Exemplo | v1 — F1 / Clarity | v2 — F1 / Clarity |
|---|---|---|
| 12 | 0.57 / 0.70 | 0.69 / 0.85 |
| 13 | 0.75 / 0.70 | 0.89 / 0.85 |
| 14 | 0.57 / 0.70 | 0.95 / 0.95 |
| 15 | 0.57 / 0.55 | 1.00 / 0.85 |

É esse colapso nos bugs complexos que derruba o F1 agregado da v1 para 0.77 e a reprova. A v2
mantém F1 entre 0.69 e 1.00 nos mesmos quatro casos.

### Diferenças estruturais entre as versões

| | v1 | v2 |
|---|---|---|
| Persona | ausente ("um assistente") | Product Manager sênior |
| `{bug_report}` | duplicado no system e no user | apenas no user prompt |
| Exemplos | nenhum | 3 (simples, médio, complexo) |
| Formato de saída | não especificado | template por nível de complexidade |
| Critérios de aceitação | não exigidos | Dado/Quando/Então obrigatório |
| Edge cases | não tratados | 5 casos cobertos |
| Raciocínio | não orientado | CoT silencioso em 5 passos |

### Screenshots

| Evidência | Arquivo |
|---|---|
| Métricas agregadas ≥ 0.8 | `screenshots/metricas-aprovadas.png` |
| Dataset com 15 exemplos | `screenshots/dataset.png` |
| Tracing — exemplo simples | `screenshots/tracing-1.png` |
| Tracing — exemplo médio | `screenshots/tracing-2.png` |
| Tracing — exemplo complexo | `screenshots/tracing-3.png` |

---

## Como Executar

### Pré-requisitos

- Python 3.9+
- Conta no [LangSmith](https://smith.langchain.com) com API Key
- Conta na [OpenAI](https://platform.openai.com) com crédito (~US$ 5 cobrem o desafio inteiro)

### 1. Ambiente

```bash
git clone https://github.com/WillianMinozzo/mba-ia-pull-evaluation-prompt.git
cd mba-ia-pull-evaluation-prompt

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Credenciais

```bash
cp .env.example .env            # Windows: copy .env.example .env
```

Preencha:

```ini
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=mba-ia-pull-evaluation-prompt
USERNAME_LANGSMITH_HUB=seu-handle
OPENAI_API_KEY=sk-proj-...
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4-mini
EVAL_MODEL=gpt-4.1
```

O handle do Hub é criado na primeira publicação pública. Para descobrir o seu:

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); from langsmith import Client; print(Client()._get_settings().tenant_handle)"
```

Se retornar `None`, crie um:

```bash
python -c "import os,requests; from dotenv import load_dotenv; load_dotenv(); r=requests.post('https://api.smith.langchain.com/api/v1/settings/handle', headers={'X-API-Key':os.environ['LANGSMITH_API_KEY']}, json={'tenant_handle':'seu-handle'}); print(r.status_code, r.text)"
```

**Sobre a escolha dos modelos:** `EVAL_MODEL` deve ser um modelo **não-raciocinante**. Modelos de
raciocínio consomem tokens antes de emitir a saída e truncam o JSON dos juízes, o que vira `score: 0.0`
silenciosamente (ver "Jornada de Otimização"). Ambos precisam aceitar `temperature=0`.

### 3. Pipeline

Execute sempre a partir da raiz do repositório — `evaluate.py` lê `datasets/` por caminho relativo.

```bash
# Fase 1 — pull do prompt ruim do Hub
python src/pull_prompts.py

# Validação offline, custo zero
pytest tests/test_prompts.py -v

# Fase 3 — publica a v2 como prompt público
python src/push_prompts.py

# Fase 4 — avaliação (15 exemplos × 4 chamadas = 60 por execução, alguns minutos)
python src/evaluate.py
```

### 4. Ferramentas auxiliares

```bash
# Baseline da v1, para o comparativo
python src/baseline_v1.py

# Debug das iterações: mostra os piores exemplos de uma métrica
# com o raciocínio que o juiz gravou
python src/inspect_scores.py <nome-do-experimento> <metrica> <quantidade>
python src/inspect_scores.py willianminozzo-bug_to_user_story_v2-ccf43d5e clarity 4
```

`inspect_scores.py` foi a ferramenta central do processo: em vez de supor por que uma nota caiu, ele
lê o campo `reasoning` que cada juiz grava como feedback no experimento.

---

## Estrutura

```
mba-ia-pull-evaluation-prompt/
├── .env.example
├── requirements.txt
├── README.md
│
├── prompts/
│   ├── bug_to_user_story_v1.yml      # puxado do Hub (baixa qualidade)
│   └── bug_to_user_story_v2.yml      # otimizado
│
├── datasets/
│   └── bug_to_user_story.jsonl       # 15 bugs (não alterar)
│
├── src/
│   ├── pull_prompts.py               # implementado
│   ├── push_prompts.py               # implementado
│   ├── baseline_v1.py                # auxiliar — baseline da v1
│   ├── inspect_scores.py             # auxiliar — debug das iterações
│   ├── evaluate.py                   # pronto, não alterado
│   ├── metrics.py                    # pronto, não alterado
│   └── utils.py                      # pronto, não alterado
│
├── tests/
│   └── test_prompts.py               # 6 testes implementados
│
└── screenshots/                      # evidências
```

## Testes

```bash
pytest tests/test_prompts.py -v
```

| Teste | Verifica |
|---|---|
| `test_prompt_has_system_prompt` | campo existe e não está vazio |
| `test_prompt_has_role_definition` | define persona ("Você é um/uma ...") |
| `test_prompt_mentions_format` | exige template de user story e critérios de aceitação |
| `test_prompt_has_few_shot_examples` | contém ao menos 2 exemplos entrada/saída |
| `test_prompt_no_todos` | nenhum `TODO` remanescente |
| `test_minimum_techniques` | ao menos 2 técnicas em `techniques_applied` |

O último teste reaproveita `validate_prompt_structure()` de `src/utils.py`.

> Nota: `utils.validate_prompt_structure` checa `'TODO' in system_prompt` como substring
> case-sensitive. Em português isso colide com "TODOS" em caixa alta — o texto do prompt evita
> essa forma de propósito.
