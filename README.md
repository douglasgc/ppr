# PPR · um estudo de produto privado e consumo governamental

[English](README.en.md) · [Guia para LLMs](llms.txt)

Pipeline do Banco Mundial, ranking interativo, mapa-múndi e API/MCP para explorar:

```text
PPR = PIB − α × G
α = 0 → PIB     α = 1 → PIB − G     α = 2 → PIB − 2G
```

## A tese de Rothbard, em resumo

Rothbard questiona contar os serviços do governo pelo seu custo como se esse custo
demonstrasse valor de mercado: ao contrário das transações privadas voluntárias,
gastos financiados por tributação não revelariam a mesma preferência dos consumidores.
Ele propõe separar o produto privado e descontar os recursos absorvidos pelo Estado.

Em *America’s Great Depression*, seu cálculo retira renda originada no governo e em
empresas governamentais do produto nacional, depois considera despesas ou receitas
governamentais, o que for maior, com ajustes por esfera de governo. **A metodologia
histórica não se reduz universalmente a PIB − 2G.**

Aqui usamos `PIB − αG` como **simulação simplificada inspirada nessa tese**. O parâmetro
compara premissas; não estima empiricamente o “peso correto” do governo. Nosso G é
**consumo final governamental**, não despesa pública total: faltam, entre outros,
transferências, investimentos públicos e os ajustes fiscais da construção original.
O resultado não é medida oficial de bem-estar, renda disponível ou comprovação de
que serviços públicos não têm valor. A hipótese de Rothbard é controversa; ausência
de preço de mercado não demonstra, por si só, ausência de benefício social.

Fontes:
- [Rothbard — *America’s Great Depression*, apêndice sobre produto nacional](https://mises.org/online-book/americas-great-depression/appendix-government-and-national-product-1929-1932).
- [Rothbard — *Power and Market*, apêndice sobre gastos nas estatísticas de produto](https://mises.org/online-book/man-economy-and-state-power-and-market/5-binary-intervention-government-expenditures/appendix-role-government-expenditures-national-product-statistics).
- [Discussão crítica: “GNP, PPR, and the Standard of Living”](https://mises.org/online-book/review-austrian-economics/gnp-ppr-and-standard-living).

## Abrir o estudo

Python 3.11+ e [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run streamlit run app.py
```

Abra **http://localhost:8501**. Alternativa: crie um ambiente virtual,
execute `pip install -e .` e depois `streamlit run app.py`.

- **Todos os resultados:** a lista começa em **Todos**. Também há 15/30/50/100 por página.
- **População sempre presente:** ranking, destaques, detalhe, hover do mapa e todos os registros exportados/API/MCP.
  Para China agregada, é a soma das três populações. Ausência na fonte permanece `null` nos dados brutos.
- **PT / EN:** idioma no menu lateral, incluindo nomes, números, explicações e gráficos.
  Campos técnicos/API permanecem estáveis em inglês para integração.
- **Ranking:** por PPR por pessoa, PIB por pessoa, PPR total, parcela mantida ou ganho de posições.
- **Mapa-múndi:** cores por posição no ranking escolhido; hover com valores. Cinza indica
  ausência de resultado no grupo. Busca e seleção da lista não recortam o mapa.
  A cartografia do Plotly requer internet; territórios pequenos podem não ser visíveis.
- **Busca:** nome em português/inglês ou código; não recalcula as posições do grupo.
- **Por país:** PIB − desconto = PPR; comparação dos três cenários e valores totais.
- **Downloads:** CSV e **JSON completo**, com todas as linhas encontradas, indicadores,
  dados brutos, exclusões e metadados — independentemente da paginação.

As setas comparam PIB e PPR **no mesmo ano**, não evolução histórica. Empates usam
posições `1, 1, 3`. Rankings usam valores não arredondados. Mudar a população mínima
altera o grupo; buscar ou selecionar países apenas recorta a visualização.

### China: separada ou agregada

No menu lateral, escolha:

1. **Séries separadas:** China continental (CHN), Hong Kong (China, HKG) e Macau (China, MAC).
   Hong Kong e Macau são regiões administrativas especiais, não países independentes.
2. **China agregada:** soma os níveis de PIB, G e população das três séries **antes**
   de calcular PPR e valores por pessoa. **Não faz média simples dos valores per capita.**
   Substitui as três linhas por `CHN_AGG`, uma construção sintética, não uma série oficial.

O agregado usa dados do mesmo ano, antes do filtro de população. Exige PIB, G e
população válidos nas três regiões. Se faltar algum, a interface informa o motivo
e mantém apenas as séries separadas disponíveis, **sem agregado parcial ou imputação**.
Componentes opcionais ficam nulos se faltar qualquer parcela. Somar exportações e
importações não elimina comércio intragrupo; não trate esses totais como comércio
externo consolidado. O mapa colore CHN/HKG/MAC com a mesma posição no modo agregado.

## HTTP e mini MCP para LLMs

Em outro terminal:

```bash
uv run ppr-serve
```

O mesmo processo expõe **http://127.0.0.1:8000**:

| Endereço | Conteúdo |
| --- | --- |
| `/api/data` | Dataset completo: `metadata`, `records`, `excluded`, `raw_records` |
| `/api/metadata?lang=en` | Dicionário dos campos, unidades, tese, indicadores e limites |
| `/api/countries/BRA` | Todos os campos de uma economia e seus dados brutos; posições preservadas |
| `/llms.txt` | Instruções de leitura para agentes |
| `/docs` / `/openapi.json` | Documentação interativa e contrato OpenAPI |
| `/mcp` | MCP real, transporte **Streamable HTTP**, pelo SDK oficial |

```bash
curl 'http://127.0.0.1:8000/api/data?year=2023&alpha=2&min_population=0&lang=pt' -o estudo_completo.json
curl 'http://127.0.0.1:8000/api/data?year=2023&china_mode=combined&countries=CHN_AGG&lang=pt'
curl 'http://127.0.0.1:8000/api/data?countries=BRA,USA&sort_by=ppr'
```

Parâmetros: `year`, `alpha` (0–2), `min_population`, `lang` (`pt`/`en`),
`china_mode` (`separate`/`combined`), `countries` (códigos separados por vírgula) e
`sort_by` (`ppr_per_capita`, `gdp_per_capita`, `ppr`, `private_retention_pct`, `rank_change`).
Seleção de países preserva o ranking do grupo inteiro, diferente de `custom_country_codes`
do cliente Python, que define o universo de cálculo. Para CHN_AGG, use `china_mode=combined`.

**MCP:** configure seu cliente para Streamable HTTP em `http://127.0.0.1:8000/mcp`.
Ferramentas: `get_metadata`, `get_dataset`, `get_country`. Recurso: `ppr://metadata`.
Os argumentos seguem a API, mas `countries` é uma lista de códigos. O transporte implementa
`initialize`, `tools/list` e `tools/call`; não é apenas um endpoint JSON com nome de MCP.

### Contrato para leitura completa

- Não há top-N, paginação ou corte silencioso nos endpoints/ferramentas.
- `record_count == len(records)`; `raw_record_count == len(raw_records)`.
- `complete: true` e `truncated: false` descrevem **a resposta da consulta**, não garantem
  que a fonte tenha dados para todos os países. Leia `excluded` e os dados brutos.
- JSON preserva números, usa `null` para ausências e inclui todas as colunas de cálculo.
- `generated_at` é a hora da resposta, **não** a data de publicação/atualização da fonte.
- LLMs/clientes ainda podem limitar contexto: baixe o arquivo ou consulte por país.
  Não conclua nada sobre linhas que o modelo não conseguiu ler.

O servidor é somente leitura e local por padrão. Pode baixar dados para o cache quando
não existem; não há ferramenta de alteração, execução de código ou atualização remota.
Token opcional via `PPR_API_TOKEN`; quando configurado, todas as rotas exigem
`Authorization: Bearer ...`. Não exponha diretamente na internet: use proxy autenticado
com TLS e limites de requisição. O comando aceita apenas hosts de loopback. Nenhum
token deve ser colocado no README, URL ou repositório. Não há envio automático a LLM externa.

## Cliente e CLI

```bash
uv run ppr --year 2023 --alpha 2 --top 20
uv run ppr --year 2023 --alpha 1 --countries BRA USA ARG --export exports/ppr.csv
uv run ppr --year 2023 --alpha 0 --export exports/ppr.json --refresh
```

`--export` salva todo o resultado filtrado, não só o top N; é a exportação legada do
cliente. Para o contrato completo com metadados e agregação, use o dashboard ou HTTP/MCP.
`--cache-dir` altera o cache; `--refresh` incorpora revisões do Banco Mundial.
Atalhos: `uv run python -m ppr ...` ou `uv run python ppr_client.py ...`.

```python
from ppr import PPRConfig, RothbardPPRClient

client = RothbardPPRClient(PPRConfig(year=2023, alpha_g=2))
print(client.get_top(10))
print(client.get_country("BRA"))
client.set_config(alpha_g=1)  # recalcula sem baixar o mesmo ano
client.export("exports/ppr.json")
```

Para dados próprios: `RothbardEngine().calculate(df, PPRConfig(...))`, com uma linha
por economia e colunas `country_code`, `gdp`, `gastos_governo`, `populacao` do mesmo ano.
Para o contrato completo offline: `ppr.dataset.build_dataset(df, config, lang="en", china_mode="combined")`.

## Dados e limites

| Campo API | Banco Mundial |
| --- | --- |
| `gdp` | `NY.GDP.MKTP.CD` |
| `government_consumption` | `NE.CON.GOVT.CD` |
| `private_consumption` | `NE.CON.PRVT.CD` |
| `gross_capital_formation` | `NE.GDI.TOTL.CD` — inclui estoques, não necessariamente privado |
| `exports` / `imports` | `NE.EXP.GNFS.CD` / `NE.IMP.GNFS.CD` |
| `population` | `SP.POP.TOTL` |

USD correntes, sem PPC ou ajuste por inflação. PIB/população positivos; G não negativo;
todos finitos. PPR negativo é preservado. Componentes C/I/X/M não são obrigatórios
para o ranking. `gpp = gdp − government_consumption`; `gpp_components = C + I + X − M`;
`accounting_residual` registra diferenças, sem forçar reconciliação. Sem preenchimento
com dados de outros anos. Agregados regionais da fonte são excluídos. O cache local
em `.cache/ppr/` é um snapshot que **não expira automaticamente**.

[Documentação da API do Banco Mundial](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation).

## Estrutura e testes

```text
Banco Mundial → data.py → aggregation.py → engine.py → dataset.py
                                         ↘ client.py / cli.py
                           apresentação: app.py / i18n.py / charts.py
                           acesso LLM: server.py → HTTP JSON + MCP
```

```bash
uv run python -m unittest discover -s tests -v
```

Testes offline com dados fictícios: cálculos, agregação, idiomas, interface, mapa,
contrato completo, HTTP e protocolo MCP. Nenhum banco de dados ou serviço externo de LLM é necessário.
