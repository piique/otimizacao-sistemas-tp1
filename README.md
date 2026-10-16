# TP1 — Resolução de Problemas Lineares Inteiros via Simplex e Branch and Bound

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/piique/otimizacao-sistemas-tp1/blob/main/notebooks/TP1_misc03.ipynb)

**Instância:** `misc03` — MIPLIB 2017 (Benchmark Set)
160 variáveis (159 binárias + 1 contínua), 96 restrições, 2.053 não-zeros.

| Resultado | Valor |
|---|---|
| Z relaxado (Simplex) | 1910,00 |
| Z inteiro ótimo | 3360,00 |
| Integrality gap | 43,15% |
| Nós do B&B próprio | 961 |

## Entrega

- **Notebook (Google Colab):**
  <https://colab.research.google.com/github/piique/otimizacao-sistemas-tp1/blob/main/notebooks/TP1_misc03.ipynb>
  — basta "Executar tudo"; o notebook baixa a instância, instala o PuLP e calcula tudo (não precisa de chave de IA).
- **Relatório (PDF):** [`report/relatorio.pdf`](report/relatorio.pdf) — subir no Google Drive e
  compartilhar como público.

## Estrutura

```
.
├── Dockerfile                 # ambiente reprodutível (pulp, scipy, jupyter...)
├── run.sh                     # roda comandos no container (nada é instalado no host)
├── requirements.txt
├── data/
│   ├── misc03.mps             # instância original (MPS)
│   ├── misc03_variables.csv   # exportação CSV
│   ├── misc03_constraints.csv
│   └── misc03_coefficients.csv
├── src/
│   ├── mps_parser.py          # parser MPS (sem dependências)
│   ├── export_csv.py          # MPS -> CSVs
│   ├── model_misc03.py        # modelagem + LP + IP com PuLP/CBC
│   ├── branch_and_bound.py    # B&B próprio (scipy/HiGHS) com registro da árvore
│   ├── visualization.py       # figuras da árvore, convergência e frações
│   ├── run_analysis.py        # pipeline completo -> results/resumo.json
│   └── build_notebook.py      # gera o notebook Colab
├── notebooks/
│   └── TP1_misc03.ipynb       # notebook autocontido (para o Colab)
├── figures/                   # arvore_3niveis.png, arvore_completa.png, ...
├── results/resumo.json        # métricas em formato estruturado
├── report/
│   ├── relatorio.md           # relatório (fonte)
│   ├── relatorio.pdf          # relatório final (pandoc + xelatex)
│   ├── build_pdf.sh           # gera o PDF em Docker
│   ├── Dockerfile.pdf         # imagem pandoc/LaTeX do PDF
│   ├── pdf_filter.lua         # ajuste de glifos Unicode
│   └── ai_answers/            # respostas das IAs (nao_agentico/, agentico/, preliminar/)
```

## Uso

Tudo roda em Docker — **nada é instalado no host**.

```bash
# 1. construir a imagem
docker build -t otimizacao-tp1 .

# 2. rodar a análise completa (gera figuras + results/resumo.json)
./run.sh python src/run_analysis.py

# 3. gerar o notebook Colab
./run.sh python src/build_notebook.py notebooks/TP1_misc03.ipynb

# 4. executar o notebook (valida ponta a ponta)
./run.sh bash -c "cd notebooks && jupyter nbconvert --to notebook --execute \
  TP1_misc03.ipynb --output TP1_misc03_executed.ipynb"

# shell interativo
./run.sh
```

## Notas

- O notebook é **autocontido**: baixa a instância, faz o parsing, exporta/le os CSVs,
  modela com PuLP, resolve a relaxação e o PLI, roda o B&B próprio e desenha a árvore.
  Basta abri-lo no Google Colab.
- `results/resumo.json` contém os limitantes de cada nó dos 3 primeiros níveis,
  o histórico de incumbentes e a solução ótima — insumo direto para o relatório.
- O uso de IA no relatório deve se restringir ao tópico 2 do enunciado.

## Respostas das IAs (tópico 2)

Três IAs foram avaliadas em **dois modos** via **Ollama Cloud (plano Pro)**, totalizando
seis respostas. Gabarito da equipe: `Z_LP=1910`, `Z_IP=3360`, gap `43,15%`.

**Modo não-agêntico** (só texto, dados embutidos no prompt):

| Modelo | Z_LP | Z_IP | Gap | Resultado |
|---|---|---|---|---|
| `glm-5.3` | 3360 | 3360 | 0% | Errou Z_LP (assumiu relaxação já inteira). |
| `deepseek-v4.1-flash` | 3360 | 3360 | 0% | Errou Z_LP (afirmou politopo integral). |
| `kimi-k2.7-code` | 1916,3 | 3360 | 42,97% | Único a reconhecer gap não nulo; aproximou Z_LP. |

**Modo agêntico** (escreve e executa Python/PuLP+CBC em container Docker isolado):

| Modelo | Z_LP | Z_IP | Gap | Resultado |
|---|---|---|---|---|
| `glm-5.3` | 1910 | 3360 | 43,15% | Correto. |
| `deepseek-v4.1-flash` | 1910 | 3360 | 43,15% | Correto. |
| `kimi-k2.7-code` | 1910 | 3360 | 43,15% | Correto. |

**Achado central:** sem solver, 2 de 3 erram o `Z_LP`; com código, os 3 acertam — a
limitação é de *cálculo*, não de conhecimento. Transcrições em
`report/ai_answers/nao_agentico/` e `report/ai_answers/agentico/`. Um lote preliminar com
modelos gratuitos (`gpt-oss`, `nemotron`, `gemma4`) está em `report/ai_answers/preliminar/`.
