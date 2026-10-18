"""Small explicit PT/EN catalog; calculation and API field identifiers stay stable."""

LANGUAGES = ("pt", "en")
TEXT = {
    "china_mode": ("Recorte da China", "China coverage"),
    "china_separate": ("Séries separadas", "Separate series"),
    "china_combined": ("China agregada", "Combined China"),
    "china_aggregate": ("China agregada", "Combined China"),
    "aggregate_scope": ("Continental + Hong Kong + Macau · sintético", "Mainland + Hong Kong + Macao · synthetic"),
    "aggregate_note": ("China agregada é uma construção deste estudo: soma CHN + HKG + MAC antes de calcular PPR e valores por pessoa. Substitui as três séries no ranking; não é uma série oficial do Banco Mundial. Componentes de comércio não são consolidados para eliminar fluxos internos.", "Combined China is constructed for this study: CHN + HKG + MAC are summed before calculating PPR and per-person values. It replaces the three source series in the ranking; it is not an official World Bank series. Trade components are not consolidated to remove internal flows."),
    "aggregate_missing": ("China agregada indisponível: faltam dados essenciais válidos em {details}. As séries separadas continuam disponíveis; nenhum agregado parcial foi criado.", "Combined China unavailable: valid essential data are missing for {details}. Separate series remain available; no partial aggregate was created."),
    "title": ("Ranking de países", "Country ranking"),
    "intro": ("Compare o PIB por pessoa com o valor que permanece após o desconto governamental.", "Compare GDP per person with the amount remaining after deducting government consumption."),
    "configure": ("Configure a comparação", "Configure the comparison"),
    "year": ("Ano dos dados", "Data year"),
    "scenario": ("Como descontar o governo?", "How should government consumption be deducted?"),
    "double": ("Desconto em dobro", "Double deduction"),
    "single": ("Desconto simples", "Single deduction"),
    "none": ("Sem desconto", "No deduction"),
    "custom": ("Personalizar", "Custom weight"),
    "none_help": ("O resultado é o próprio PIB", "The result is GDP itself"),
    "custom_help": ("Escolha um peso entre 0 e 2", "Choose a weight between 0 and 2"),
    "weight": ("Peso do desconto", "Deduction weight"),
    "g_warning": ("G é o consumo governamental informado pelo Banco Mundial, não o gasto público total.", "G is government consumption reported by the World Bank, not total public spending."),
    "options": ("Opções dos dados", "Data options"),
    "min_pop": ("População mínima", "Minimum population"),
    "refresh": ("Atualizar dados da API", "Refresh data from API"),
    "cache": ("O download fica salvo localmente. Atualize para buscar revisões da fonte.", "Downloads are cached locally. Refresh to fetch source revisions."),
    "year_chip": ("Dados de {year}", "{year} data"),
    "source": ("Banco Mundial", "World Bank"),
    "usd": ("US$ correntes", "Current US dollars"),
    "deduction": ("Desconto: {alpha} × G", "Deduction: {alpha} × G"),
    "loading": ("Preparando o ranking… Na primeira consulta, buscamos os dados do Banco Mundial.", "Preparing the ranking… The first request downloads World Bank data."),
    "load_error": ("Não foi possível preparar o ranking: {error}", "Unable to prepare the ranking: {error}"),
    "retry": ("Tente novamente ou escolha outro ano no menu lateral.", "Try again or choose a different year in the sidebar."),
    "empty": ("Nenhum país com dados suficientes. Escolha outro ano ou reduza a população mínima no menu lateral.", "No economies have sufficient data. Choose another year or lower the minimum population in the sidebar."),
    "ranking": ("Ranking", "Ranking"),
    "map": ("Mapa-múndi", "World map"),
    "country_tab": ("Entenda um país", "Explore a country"),
    "about": ("Sobre os dados", "About the data"),
    "cohort": ("{count} países e territórios · {scenario} · valores anuais por pessoa, salvo indicação de total", "{count} countries and territories · {scenario} · annual per-person values unless marked as totals"),
    "search": ("Buscar país", "Search countries"),
    "search_hint": ("Ex.: Brasil, Estados Unidos ou BRA", "E.g. Brazil, United States or BRA"),
    "sort": ("Ordenar por", "Sort by"),
    "filter": ("Filtrar lista", "Filter list"),
    "select_countries": ("Selecionar países", "Select countries"),
    "show_countries": ("Mostrar apenas estes países", "Only show these countries"),
    "filter_help": ("A seleção não altera as posições no ranking geral.", "Selection does not change positions in the overall ranking."),
    "no_matches": ("Nenhum país encontrado. Tente outro nome, código ou remova a seleção de países.", "No matches. Try another name or code, or clear the country selection."),
    "results": ("Resultados na tela", "Results on screen"),
    "all": ("Todos ({count})", "All ({count})"),
    "range": ("**{start}–{end}** de **{count}** países · do maior para o menor valor", "**{start}–{end}** of **{count}** economies · highest to lowest"),
    "page": ("Página", "Page"),
    "page_of": ("{page} de {pages}", "{page} of {pages}"),
    "rank_note": ("¹ PPR vs. PIB: posições ganhas (↑) ou perdidas (↓) ao trocar PIB por pessoa por PPR por pessoa. Não representa evolução ao longo dos anos. ‘PIB mantido’ é o PPR dividido pelo PIB.", "¹ PPR vs. GDP: places gained (↑) or lost (↓) when switching from GDP per person to PPR per person. This is not change over time. ‘GDP retained’ means PPR divided by GDP."),
    "china_question": ("Por que China, Hong Kong e Macau aparecem separados?", "Why are China, Hong Kong and Macao listed separately?"),
    "china_context": ("Hong Kong e Macau são regiões administrativas especiais da China, com séries econômicas separadas no Banco Mundial. Aqui, ‘China continental’ é a série CHN, que não inclui essas duas regiões. Cada linha usa seus próprios dados e população; os valores não são somados. A separação é estatística, não indica que Hong Kong e Macau sejam países independentes.", "Hong Kong and Macao are special administrative regions of China, reported separately by the World Bank. Here, ‘Mainland China’ refers to the CHN series, excluding both regions. Each row uses its own data and population; values are not combined. This is a statistical distinction, not a claim that Hong Kong or Macao are independent countries."),
    "china_missing": ("China continental não participa do ranking de {year}: {reason}. Hong Kong e Macau não substituem a série da China continental.", "Mainland China is not in the {year} ranking: {reason}. Hong Kong and Macao do not substitute for the mainland series."),
    "not_returned": ("a série não foi retornada pela fonte", "the source did not return the series"),
    "invalid": ("dado ausente ou inválido de {fields}", "missing or invalid data for {fields}"),
    "below_population": ("a população está abaixo do mínimo selecionado ({count} habitantes)", "population is below the selected minimum ({count} people)"),
    "china": ("China continental", "Mainland China"),
    "hong_kong": ("Hong Kong (China)", "Hong Kong (China)"),
    "macao": ("Macau (China)", "Macao (China)"),
    "mainland_scope": ("Não inclui Hong Kong e Macau", "Excludes Hong Kong and Macao"),
    "sar_scope": ("Região administrativa especial", "Special administrative region"),
    "comparison": ("Ver comparação visual dos primeiros 10 países desta lista", "Compare the first 10 economies in this list"),
    "comparison_note": ("A ordem segue o critério selecionado. Valores em US$ por pessoa, no mesmo ano.", "Order follows your selected criterion. Values are US dollars per person for the same year."),
    "export": ("Exportar esta lista", "Export this list"),
    "export_note": ("Inclui todos os países encontrados e todos os indicadores, não apenas a página atual. Valores numéricos sem arredondamento de tela.", "Includes all matching economies and all indicators, not just the current page. Numeric values are not rounded for display."),
    "csv": ("Baixar CSV", "Download CSV"),
    "json": ("Baixar JSON completo · LLM", "Download full JSON · LLM"),
    "country_intro": ("O que o resultado significa na prática?", "What does the result mean in practice?"),
    "choose_country": ("Escolha um país", "Choose a country"),
    "country_rank": ("{ppr}º de {count} no PPR por pessoa · {gdp}º no PIB por pessoa · {change}", "#{ppr} of {count} by PPR per person · #{gdp} by GDP per person · {change}"),
    "gdp_pc": ("PIB por pessoa", "GDP per person"),
    "ppr_pc": ("PPR por pessoa", "PPR per person"),
    "discount_pc": ("− Desconto simulado por pessoa", "− Simulated deduction per person"),
    "result_pc": ("= PPR por pessoa", "= PPR per person"),
    "explanation": ("Para cada <strong>US$ 100 de PIB</strong>, <strong>{retained}</strong> permanecem nesta simulação. O consumo governamental representa <strong>{share}</strong> do PIB; o cenário escolhido desconta <strong>{alpha} vez(es)</strong> esse valor. O resultado não representa renda disponível ou dinheiro recebido pela população.", "For every <strong>US$100 of GDP</strong>, <strong>{retained}</strong> remains in this simulation. Government consumption is <strong>{share}</strong> of GDP; the selected scenario deducts <strong>{alpha} times</strong> that amount. This is not disposable income or money received by residents."),
    "negative": ("O desconto é maior que o PIB neste cenário, por isso o PPR fica negativo. Isso é um resultado da fórmula, não uma renda negativa observada.", "The deduction exceeds GDP in this scenario, making PPR negative. This is a formula result, not observed negative income."),
    "scenarios": ("O mesmo país em diferentes cenários", "The same country under different scenarios"),
    "scenario_column": ("Cenário", "Scenario"),
    "result_column": ("Resultado por pessoa", "Result per person"),
    "retention": ("PIB mantido", "GDP retained"),
    "retention_column": ("Parcela do PIB mantida", "Share of GDP retained"),
    "totals": ("Ver valores totais e população", "See totals and population"),
    "indicator": ("Indicador", "Indicator"),
    "value": ("Valor", "Value"),
    "population": ("População", "Population"),
    "population_note": ("População: {count} habitantes", "Population: {count} people"),
    "series": ("série", "series"),
    "gdp_total": ("PIB total", "Total GDP"),
    "government": ("Consumo governamental", "Government consumption"),
    "government_field": ("consumo governamental (G)", "government consumption (G)"),
    "ppr_total": ("PPR total", "Total PPR"),
    "position": ("Pos.", "Rank"),
    "country": ("País / território", "Country / territory"),
    "movement": ("PPR vs. PIB¹", "PPR vs. GDP¹"),
    "unchanged": ("= sem mudança", "= unchanged"),
    "places": ("{arrow} {count} {unit}", "{arrow} {count} {unit}"),
    "place_one": ("posição", "place"),
    "place_many": ("posições", "places"),
    "retained_hint": ("{value} do PIB mantido", "{value} of GDP retained"),
    "table_caption": ("Ranking de países, ordenado do maior para o menor valor", "Country ranking, highest to lowest value"),
    "sort_ppr_pc": ("Maior PPR por pessoa", "Highest PPR per person"),
    "sort_gdp_pc": ("Maior PIB por pessoa", "Highest GDP per person"),
    "sort_ppr": ("Maior PPR total", "Highest total PPR"),
    "sort_retention": ("Maior parcela do PIB mantida", "Highest share of GDP retained"),
    "sort_change": ("Maior ganho de posições", "Most places gained"),
    "gain": ("Ganho de posições", "Places gained"),
    "map_title": ("A posição de cada país no mundo", "Each country’s position in the world"),
    "map_note": ("Cores seguem ‘{criterion}’ no ranking completo de {count} economias. Verde = primeiras posições; vermelho = últimas. Cinza = sem resultado neste grupo. Busca e seleção da lista não recortam o mapa.", "Colors follow ‘{criterion}’ across the full ranking of {count} economies. Green = leading positions; red = lower positions. Gray = no result in this group. List search and selection do not filter the map."),
    "map_rank": ("Posição no ranking", "Ranking position"),
    "map_scope": ("Limites cartográficos servem à visualização, não definem soberania. Hong Kong e Macau usam suas próprias séries, mas podem ser difíceis de visualizar na escala mundial. A base cartográfica do Plotly requer acesso à internet.", "Map boundaries are for visualization, not statements of sovereignty. Hong Kong and Macao use their own series but may be hard to see at world scale. Plotly’s map basemap requires internet access."),
    "about_title": ("Como ler este estudo", "How to read this study"),
    "technical": ("Dados técnicos completos e indicadores", "Full technical data and indicators"),
    "technical_note": ("Base de cálculo completa, sem o limite de linhas da lista. JSON usa campos estáveis em inglês e inclui metadados e dados brutos.", "Complete calculation dataset, independent of list pagination. JSON uses stable English fields and includes metadata and raw data."),
    "machine": ("Dados completos para LLMs / API / MCP", "Full data for LLMs / API / MCP"),
    "machine_help": ("Baixe o JSON completo abaixo ou execute `uv run ppr-serve`. JSON: `http://127.0.0.1:8000/api/data`. Instruções para agentes: `/llms.txt`. MCP HTTP: `/mcp`. O servidor é um processo separado do dashboard.", "Download the full JSON below or run `uv run ppr-serve`. JSON: `http://127.0.0.1:8000/api/data`. Agent instructions: `/llms.txt`. HTTP MCP: `/mcp`. The server runs separately from the dashboard."),
    "source_link": ("Consultar a fonte no Banco Mundial", "View the World Bank source"),
    "coverage": ("**Ano:** {year} · **Cobertura:** {count} de {raw} economias · **População mínima:** {population}. Apenas dados do ano selecionado; sem substituir lacunas por outros anos. O cache local só muda mediante atualização explícita.", "**Year:** {year} · **Coverage:** {count} of {raw} economies · **Minimum population:** {population}. Only the selected year is used; gaps are not filled from other years. The local cache changes only when explicitly refreshed."),
}

ABOUT = {
    "pt": """### A tese de Rothbard, em resumo
Rothbard argumenta que as contas nacionais não deveriam tratar gastos governamentais
como produção valorizada voluntariamente pelo mercado. Como esses serviços não são
vendidos em trocas voluntárias comparáveis às privadas, avaliá-los pelo custo não
demonstraria sua contribuição econômica. Em *America’s Great Depression*, ele
separa o produto privado da renda originada no governo e deduz a absorção fiscal,
considerando despesas ou receitas, o que for maior, com ajustes por esfera de governo.

**Neste simulador**, representamos essa ideia de forma simplificada como
**PIB − G − G = PIB − 2G** quando o peso é 2. Isso não é uma identidade histórica exata.

Este estudo **simula essa premissa**, sem apresentá-la como consenso ou medida oficial.
O peso ajustável permite comparar o PIB (0), uma exclusão simples (1) e a dedução em dobro (2).
**G aqui é consumo final governamental, não gasto público total**; portanto a aplicação
é uma aproximação operacional, não uma reprodução completa da metodologia histórica.

### Como interpretar
- O padrão é **por pessoa**, para não favorecer automaticamente países maiores.
- ‘PIB mantido’ é PPR/PIB: não é renda disponível nem dinheiro recebido pelos habitantes.
- Setas comparam posições de PPR e PIB **no mesmo ano**, não evolução histórica.
- Busca, seleção e paginação não recalculam posições. Mudar a população mínima muda o grupo.
- Empates recebem posições 1, 1, 3; valores negativos são preservados.
- Valores em **USD correntes**, sem ajuste por inflação ou PPC; não são uma medida de bem-estar.
- PIB e população precisam ser positivos; G não negativo; todos finitos. Componentes
  opcionais ausentes não eliminam países. GPP = PIB − G; C + I + X − M é exibido
  separadamente, com resíduo contábil. I inclui estoques e não é necessariamente privado.

Referência: Murray N. Rothbard, *America’s Great Depression*, apêndice
“Government and the National Product, 1929–1932”. Veja o README para fontes e limites.
""",
    "en": """### Rothbard’s thesis, briefly
Rothbard argues that national accounts should not treat government expenditure as
output valued through voluntary market exchange. Because these services are not sold
in comparable voluntary transactions, valuing them at cost would not demonstrate
their economic contribution. In *America’s Great Depression*, he separates private
product from income originating in government, then deducts fiscal absorption using
expenditure or receipts, whichever is higher, with adjustments by level of government.

**This simulator** represents the idea in simplified form as **GDP − G − G = GDP − 2G**
at weight 2. This is not an exact historical identity.

This study **simulates that premise**; it is not a consensus or official measure.
Adjustable weights compare GDP (0), simple exclusion (1) and double deduction (2).
**G here is government final consumption, not total public spending**, so this is an
operational approximation, not a full reconstruction of the historical methodology.

### Interpretation
- The default is **per person**, avoiding an automatic advantage for larger economies.
- ‘GDP retained’ is PPR/GDP, not disposable income or money received by residents.
- Arrows compare PPR and GDP ranks **in the same year**, not change over time.
- Search, country selection and pagination do not rerank. Minimum population changes the group.
- Ties use ranks 1, 1, 3; negative results are preserved.
- Values are **current USD**, without inflation or PPP adjustment; not a well-being measure.
- GDP and population must be positive, G nonnegative, all finite. Missing optional
  components do not exclude an economy. GPP = GDP − G; C + I + X − M is shown separately
  with an accounting residual. I includes inventories and is not necessarily private.

Reference: Murray N. Rothbard, *America’s Great Depression*, appendix
“Government and the National Product, 1929–1932”. See the README for sources and limitations.
""",
}


def t(key: str, lang: str = "pt", **values) -> str:
    if lang not in LANGUAGES:
        raise ValueError("Supported languages: pt, en")
    return TEXT[key][LANGUAGES.index(lang)].format(**values)
