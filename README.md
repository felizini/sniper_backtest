# sniper_backtest
O backtest deve estar fundamentado nos 2 artigos abaixo:

A Teoria das Ondas de Elliott, desenvolvida por Ralph Nelson Elliott nas décadas de 1920 e 1930, baseia-se na premissa de que os mercados financeiros não se movem de forma caótica, mas sim em padrões repetitivos impulsionados pela psicologia de massa e pelo comportamento coletivo dos investidores, alternando ciclos de medo e ganância. O princípio central da teoria define que os movimentos de preço se organizam em estruturas fractais compostas por ondas de impulso e correção, repetindo-se em diferentes escalas temporais. Em tese, isso permitiria antecipar movimentos futuros do mercado por meio da identificação dessas formações e da utilização de projeções matemáticas baseadas nas razões de Fibonacci. 

No entanto, embora seja considerada uma ferramenta sofisticada e respeitada em mercados tradicionais mais maduros, sua aplicação ao mercado de criptomoedas apresenta limitações importantes. O setor cripto ainda é relativamente incipiente, altamente especulativo e frequentemente influenciado por narrativas, baixa liquidez em diversos ativos, movimentos abruptos, liquidações em cascata e mudanças repentinas de sentimento.

Nesse contexto, metodologias excessivamente complexas e dependentes de interpretação subjetiva podem se tornar pouco práticas e inconsistentes no calor do mercado, especialmente porque diferentes analistas frequentemente chegam a contagens de ondas distintas para o mesmo gráfico. Assim, em um ambiente ainda marcado por forte volatilidade e comportamento extremo, pode ser mais eficiente ao operador dedicar esforços ao domínio de ferramentas quantitativas mais simples, objetivas e igualmente úteis, voltadas à medição de tendência, volatilidade, momentum e esticamento estatístico do preço, reduzindo subjetividades e favorecendo maior consistência operacional.

---

## Estratégia de Bot de Trading – Os 3 Elementos Essenciais que Todo Bot Precisa

A maioria dos traders que automatizam sua estratégia de bot de trading compartilha um problema comum: eles fizeram apenas metade do trabalho.

A lógica de entrada pode ser sólida em tese. Mas os elementos que realmente determinam se uma estratégia sobrevive ao contato com os mercados reais — os filtros, a lógica de saída — estão faltando ou são mal definidos. O resultado é um bot que parece promissor nos backtests e desmorona na produção.

Este post detalha os três elementos essenciais que toda estratégia de bot de trading deve ter. Deixar de projetar corretamente qualquer um deles significa construir sobre uma base incompleta.

### 1. Lógica de Entrada: Saiba Por Que Você Está Fazendo a Operação

Sua lógica de entrada responde a uma pergunta: por que você está fazendo esta operação agora?

Mas o que diferencia uma lógica de entrada funcional dos sinais aleatórios que destroem contas é o seguinte: cada entrada deve ser baseada em uma premissa explícita sobre o comportamento do mercado.

Não basta dizer “o preço cruzou acima da média móvel de 20 dias”. Você precisa dizer: “Quando o preço cruza acima dessa média móvel, acredito que o momentum está mudando para esta direção e provavelmente continuará”.

Essa distinção é importante porque, quando suas entradas pararem de funcionar, você precisará saber se sua premissa central foi quebrada ou se você está apenas passando por uma variação normal. Esses são dois problemas completamente diferentes, exigindo respostas completamente diferentes.

Uma boa lógica de entrada é explicável. Se você não consegue articular claramente por que sua estratégia entra em operações, não saberá quando confiar nela e quando desligá-la.

Considere uma entrada simples de seguir tendência: aguardar o fechamento do preço acima da máxima de 20 dias. A premissa é que rompimentos tendem a continuar. Isso é testável. Você pode avaliar se essa premissa se mantém nas condições atuais do mercado.

Compare isso com uma entrada baseada em quinze indicadores com parâmetros ajustados a dados históricos. Qual é a premissa subjacente? Quando ela funciona? Você não consegue responder a essas perguntas — o que significa que não conseguirá manter a confiança quando uma sequência inevitável de perdas acontecer.

A conclusão: sua lógica de entrada precisa de uma premissa clara e testável sobre o comportamento do mercado. Todo o resto é construído sobre isso em sua estratégia de bot de trading.

### 2. Qualificadores de Entrada (Filtros): Decida Quando Agir com Base nos Sinais

Sinais de entrada brutos vão te destruir.

Um cruzamento de médias móveis pode gerar 50 sinais em um mercado lateral e volátil — a maioria deles falsos. Os qualificadores de entrada são os filtros que determinam quando você realmente deve aproveitar esses sinais e quando deve ignorá-los.

Os qualificadores têm dois propósitos:

- Eliminam configurações de baixa probabilidade
- Confirmam que sua premissa central de entrada é válida no momento atual

Tipos comuns de qualificadores incluem:

- **Filtros de tendência** — Só aceite entradas compradas quando o preço estiver acima de uma média móvel de longo prazo, filtrando o alinhamento com a tendência.
- **Filtros de volume** — Exija volume acima da média na vela de entrada, confirmando momentum real por trás do movimento.
- **Confirmação de múltiplos timeframes** — Seu gráfico de 15 minutos gera um sinal, mas você só age se o gráfico de 4 horas mostrar estrutura de alta.

A regra crítica: os qualificadores devem reforçar sua premissa central de entrada, não contradizê-la. Se sua lógica de entrada assume continuação de tendência, seus qualificadores devem verificar se você realmente está em um ambiente de tendência.

Não acumule filtros aleatórios na esperança de melhorar os números do backtest. Cada qualificador deve ter uma razão lógica para existir.

### 3. Lógica de Saída: Proteja os Ganhos e Corte as Perdas com Eficiência

Suas regras de saída precisam realizar três coisas: garantir lucros quando as operações funcionam, cortar perdas quando não funcionam e dar espaço suficiente para as operações se desenvolverem antes de fazer qualquer uma das duas coisas.

**Take profit e stop loss fixos** é a abordagem mais simples. Entre na operação, defina imediatamente um take profit de 2% e um stop loss de 1%. Relação risco/recompensa clara, fácil de testar.

A limitação: saídas fixas não se adaptam às condições do mercado. Às vezes, uma operação tem muito mais espaço para correr. Às vezes, precisa ser cortada mais rápido.

**Saídas parciais** adicionam flexibilidade. Tire metade da sua posição no primeiro alvo e deixe o restante correr com um stop trailing. Isso garante lucro realizado enquanto mantém exposição a movimentos maiores.

**Stops trailing** ajustam seu nível de saída à medida que o preço se move a seu favor. Você compra, o preço sobe, seu stop sobe junto — eventualmente indo para o ponto de equilíbrio e depois para o lucro. As operações vencedoras correm; os ganhos ainda são protegidos.

Uma decisão importante: sua estratégia fica zerada na saída ou inverte imediatamente? Estratégias que alternam entre comprado e vendido mantêm você sempre posicionado — útil em mercados com tendência, mas perigoso em condições laterais, onde você será prejudicado repetidamente.

**O princípio de correspondência:** sua lógica de saída deve corresponder às suas premissas de entrada. Alvos fixos funcionam em mercados de região (range). Stops trailing funcionam em mercados com tendência. Saídas parciais funcionam quando você precisa de flexibilidade. Se sua entrada assume continuação de tendência, sua saída deve ser projetada para capturar movimentos de tendência estendidos — não para cortá-los precocemente em um fixo de 2%.

---

### Juntando Tudo: Exemplo de uma Estratégia Completa de Bot de Trading

Aqui está a aparência de todos os três elementos quando integrados adequadamente em uma estratégia de seguir tendência:

| Elemento | Projeto |
|----------|---------|
| Sinal de entrada | Preço fecha acima da máxima de 20 dias |
| Premissa de entrada | Rompimentos acima de máximas recentes tendem a continuar |
| Qualificadores | Preço deve estar acima da média de 50 dias; volume deve estar acima da média |
| Stop loss | Stop inicial na mínima recente do swing |
| Regras de saída | Mover o stop para o ponto de equilíbrio aos +10%; tirar 50% aos +15%; trailing stop de 5% no restante |

Cada nível tem uma lógica clara. A entrada assume continuação do rompimento. Os qualificadores confirmam condições de tendência. As saídas protegem o capital enquanto permitem o desenvolvimento dos ganhos.

Agora compare isso com: “Comprar quando o RSI cruzar acima de 30, vender quando cruzar abaixo de 70.”

Isso pode funcionar em certos mercados. Mas qual é a premissa subjacente? Quando exatamente você sai? Essas perguntas não são respondidas — o que significa que você não tem uma estratégia completa, você tem apenas um sinal.

### Os Três Elementos de uma Estratégia de Bot de Trading, Resumidos

1. **Lógica de entrada** — uma premissa clara e testável sobre o comportamento do mercado
2. **Qualificadores de entrada** — filtros que confirmam que sua premissa é válida no momento atual
3. **Lógica de saída** — regras que correspondem às suas premissas de entrada e protegem tanto o capital quanto os ganhos

Esses três elementos funcionam como um sistema. Altere qualquer um deles e você altera o comportamento de toda a estratégia. É por isso que copiar os sinais de entrada de outra pessoa raramente funciona isoladamente — você está vendo apenas uma peça de três.

Construa todos os três elementos. Entenda como eles interagem. Teste-os juntos, não isoladamente.
