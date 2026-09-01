# Especificação Técnica — Gerenciador de Processos de um Simulador de Sistema Operacional

**Versão:** 1.0
**Tipo de documento:** Especificação funcional e de estrutura de dados (entrada para geração de código via Harness — Claude Code / Open Code)
**Status:** Pronto para implementação

---

## 1. Introdução e Contexto do Simulador

### 1.1 Visão Geral

Este documento especifica o **módulo de Gerenciamento de Processos** de um simulador de Sistema Operacional (SO). O simulador é uma aplicação executada inteiramente em **modo usuário**, cujo objetivo é reproduzir, de forma didática e determinística, o comportamento essencial do núcleo (kernel) de um SO real no que diz respeito à criação, escalonamento, execução e finalização de processos.

Por se tratar de um ambiente simulado, **não há interação real com hardware, interrupções físicas ou chamadas de sistema (syscalls) reais**. Todos os elementos — CPU, registradores, relógio, interrupções e dispositivos de E/S — são **entidades de software** que representam, em código, o comportamento lógico desses componentes.

### 1.2 Objetivos do Simulador

- Demonstrar o ciclo de vida de processos (criação, escalonamento, execução, bloqueio, término).
- Demonstrar o funcionamento de algoritmos de escalonamento de CPU de forma intercambiável.
- Gerar métricas e visualizações (Gantt textual, logs) que permitam análise de desempenho dos algoritmos.
- Servir como base didática para o estudo de conceitos de Sistemas Operacionais sem necessidade de um kernel real ou máquina virtual completa.

### 1.3 Escopo

Este documento cobre:

1. Estrutura simplificada do hardware simulado (CPU virtual).
2. Estrutura de dados do Bloco de Controle de Processo (PCB) e da Tabela de Processos.
3. Ciclo de vida dos processos e grafo de transição de estados.
4. Especificação de algoritmos de escalonamento (Round Robin e Prioridades).
5. Formato de entrada (arquivo de tarefas) e formato de saída (relatórios, logs, Gantt).
6. Diretrizes de entrega para geração de código automatizada.

Está **fora do escopo**: gerenciamento de memória (paginação/segmentação), sistema de arquivos simulado, comunicação entre processos (IPC) e escalonamento multiprocessador.

---

## 2. Fluxo Geral de Execução do Simulador

O simulador opera em um **laço principal (main loop)** guiado por um relógio lógico (*logical clock*), que avança em unidades discretas de tempo (*ticks*). A cada tick, o núcleo simulado executa uma sequência fixa de etapas:

```
┌─────────────────────────────────────────────────────────────┐
│                     LAÇO PRINCIPAL (por tick)                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Incrementar o Relógio Lógico Global                        │
│ 2. Verificar chegada de novos processos (arquivo de tarefas)  │
│    → Criar PCB e inserir na fila de Prontos (fork simulado)   │
│ 3. Verificar processos Bloqueados                              │
│    → Decrementar tempo de E/S restante                        │
│    → Se E/S concluída, mover para fila de Prontos              │
│ 4. Verificar Processo em Execução (se houver)                  │
│    a. Decrementar quantum / rajada de CPU restante              │
│    b. Verificar se o processo solicitou E/S                     │
│    c. Verificar se o processo terminou (exit)                   │
│    d. Verificar se o quantum expirou (interrupção de relógio)   │
│ 5. Invocar o Escalonador (se CPU ociosa ou preempção ocorrida)  │
│    → Selecionar próximo processo da fila de Prontos             │
│    → Restaurar contexto (registradores) do processo escolhido   │
│ 6. Atualizar estatísticas (tempo de espera, tempo de CPU, etc.) │
│ 7. Registrar eventos no log de transições                       │
│ 8. Verificar condição de parada (todas as tarefas finalizadas)  │
└─────────────────────────────────────────────────────────────┘
```

Esse laço se repete até que **todos os processos declarados no arquivo de tarefas tenham atingido o estado Terminado**.

### 2.1 Ordem de Precedência de Eventos em um Mesmo Tick

Para garantir determinismo (requisito essencial para reprodutibilidade dos testes), a ordem de avaliação de eventos simultâneos deve seguir sempre a seguinte prioridade:

1. Término de processo (`exit`).
2. Conclusão de E/S (processo Bloqueado → Pronto).
3. Expiração de quantum (interrupção de relógio).
4. Chegada de novo processo (`fork`).
5. Decisão do escalonador.

---

## 3. Estrutura Simplificada do Hardware Simulado

O hardware é representado por uma **CPU Virtual (Virtual CPU / vCPU)** com os seguintes componentes mínimos:

### 3.1 Registradores Básicos

| Registrador | Descrição |
|---|---|
| `PC` (Program Counter) | Contador de programa — indica a próxima instrução lógica/rajada a ser processada dentro do processo em execução. |
| `ACC` (Acumulador) | Registrador genérico de propósito geral, usado para simular operações internas do processo. |
| `SP` (Stack Pointer) | Ponteiro de pilha simulado (não implica pilha real de memória, apenas valor representativo salvo/restaurado). |
| `FLAGS` | Registrador de estado/flags (ex.: indicador de solicitação de E/S pendente). |

### 3.2 Relógio Lógico (Logical Clock)

- Contador global inteiro, incrementado em uma unidade a cada iteração do laço principal.
- Não representa tempo real (wall-clock); representa **unidades de tempo simuladas (uts)**.
- É a base temporal para: cálculo de tempo de espera, tempo de CPU consumido, geração do Gantt e disparo de interrupções de quantum.

### 3.3 Interrupção de Relógio (Timer Interrupt)

- Mecanismo lógico (não um sinal de hardware real) que sinaliza ao núcleo simulado que o quantum do processo em execução expirou.
- Implementado como uma verificação condicional no laço principal: `tempo_no_quantum_atual >= quantum_configurado`.

### 3.4 Estrutura Conceitual da vCPU

```
VCPU
├── registradores: RegisterSet { PC, ACC, SP, FLAGS }
├── relogio_logico: inteiro (global, compartilhado com o núcleo)
├── processo_em_execucao: ponteiro/referência para PCB (ou nulo, se ociosa)
└── quantum_restante: inteiro (unidades de tempo restantes no fatiamento atual)
```

---

## 4. Bloco de Controle de Processo (PCB) e Tabela de Processos

### 4.1 Especificação do PCB

O **Bloco de Controle de Processo (PCB)** é a estrutura de dados central do simulador. Cada processo criado deve possuir exatamente um PCB associado, contendo todas as informações necessárias para suspender e retomar sua execução.

#### 4.1.1 Campos Obrigatórios

| Campo | Tipo sugerido | Descrição |
|---|---|---|
| `pid` | inteiro (único) | Identificador do processo. Gerado sequencialmente pelo núcleo simulado no momento da criação (fork). |
| `estado` | enum | Estado atual do processo: `NOVO`, `PRONTO`, `EM_EXECUCAO`, `BLOQUEADO`, `TERMINADO`. |
| `registradores_salvos` | struct/objeto | Cópia do `RegisterSet` (PC, ACC, SP, FLAGS) no momento da última preempção/bloqueio. |
| `prioridade` | inteiro | Valor numérico da prioridade (quanto menor o número, maior a prioridade — convenção sugerida, deve ser documentada no código). |
| `prioridade_original` | inteiro | Valor de prioridade original, preservado para fins de aging/starvation. |
| `tempo_cpu_gasto` | inteiro | Total acumulado de unidades de tempo em que o processo esteve no estado `EM_EXECUCAO`. |
| `tempo_espera` | inteiro | Total acumulado de unidades de tempo em que o processo esteve no estado `PRONTO` aguardando a CPU. |
| `tempo_chegada` | inteiro | Instante (tick) em que o processo foi criado/chegou ao sistema. |
| `tempo_termino` | inteiro (opcional) | Instante em que o processo atingiu o estado `TERMINADO`. |
| `rajadas_cpu` | lista de inteiros | Sequência de rajadas de CPU pendentes, extraídas do arquivo de tarefas. |
| `rajadas_io` | lista de inteiros | Sequência de durações de E/S pendentes, intercaladas com as rajadas de CPU. |
| `indice_rajada_atual` | inteiro | Ponteiro lógico indicando qual rajada (CPU ou E/S) está em processamento. |
| `quantum_restante` | inteiro | Unidades de tempo restantes na fatia de tempo atual (relevante para Round Robin). |

#### 4.1.2 Representação Estrutural (pseudocódigo / independente de linguagem)

```
estrutura PCB:
    pid: inteiro
    estado: EstadoProcesso  // enum { NOVO, PRONTO, EM_EXECUCAO, BLOQUEADO, TERMINADO }
    registradores_salvos: RegisterSet
    prioridade: inteiro
    prioridade_original: inteiro
    tempo_cpu_gasto: inteiro = 0
    tempo_espera: inteiro = 0
    tempo_chegada: inteiro
    tempo_termino: inteiro | nulo = nulo
    rajadas_cpu: lista<inteiro>
    rajadas_io: lista<inteiro>
    indice_rajada_atual: inteiro = 0
    quantum_restante: inteiro

estrutura RegisterSet:
    PC: inteiro = 0
    ACC: inteiro = 0
    SP: inteiro = 0
    FLAGS: inteiro = 0
```

> **Nota para geração de código:** a estrutura acima deve ser implementada como classe/`struct`/`dataclass` (dependendo da linguagem-alvo escolhida pelo Harness), com métodos de acesso controlado (getters/setters) e um método `__repr__`/`toString` que auxilie na geração dos logs de transição.

### 4.2 Tabela de Processos

A **Tabela de Processos** é a estrutura que mantém todos os PCBs do sistema simulado, independentemente do estado em que se encontrem.

#### 4.2.1 Requisitos Funcionais

- Deve permitir busca de um processo por `pid` em tempo O(1) (ex.: mapa/dicionário indexado por `pid`).
- Deve permitir iteração completa sobre todos os processos (para geração de estatísticas finais).
- Deve ser a única fonte de verdade sobre o estado de um processo — as filas do escalonador (Prontos, Bloqueados) devem armazenar **referências/ponteiros** aos PCBs contidos na tabela, nunca cópias independentes.

#### 4.2.2 Representação Estrutural

```
estrutura TabelaDeProcessos:
    processos: mapa<inteiro, PCB>   // chave = pid

    metodo adicionar(pcb: PCB)
    metodo obter(pid: inteiro) -> PCB
    metodo remover(pid: inteiro)
    metodo listar_todos() -> lista<PCB>
    metodo listar_por_estado(estado: EstadoProcesso) -> lista<PCB>
```

#### 4.2.3 Filas Auxiliares do Núcleo

Além da Tabela de Processos, o núcleo simulado mantém estruturas de fila que organizam os PCBs conforme seu estado:

| Fila | Estrutura sugerida | Uso |
|---|---|---|
| `fila_prontos` | fila circular (Round Robin) ou fila de prioridade (Escalonamento por Prioridade) | Processos aguardando alocação de CPU. |
| `fila_bloqueados` | lista ou fila simples | Processos aguardando conclusão de operação de E/S. |
| `lista_terminados` | lista | Processos finalizados, mantidos para geração do relatório final. |

---

## 5. Ciclo de Vida do Processo e Grafo de Transição de Estados

### 5.1 Estados Modelados

O simulador deve modelar obrigatoriamente os três estados clássicos de execução, além dos estados de fronteira (`NOVO` e `TERMINADO`) necessários para representar corretamente a criação e o encerramento:

- **Pronto (`PRONTO`)** — o processo está apto a ser executado e aguarda a alocação da CPU pelo escalonador.
- **Em Execução (`EM_EXECUCAO`)** — o processo detém a CPU virtual e está consumindo sua rajada de CPU corrente.
- **Bloqueado (`BLOQUEADO`)** — o processo aguarda a conclusão de uma operação fictícia de Entrada/Saída.

### 5.2 Grafo de Transição de Estados

```
                    (fork / criação)
        [NOVO] ─────────────────────────► [PRONTO]
                                              │  ▲
                          escalonador escolhe │  │ E/S concluída
                          o processo (dispatch)│  │ (interrupção de E/S)
                                              ▼  │
                                        [EM_EXECUCAO]
                                          │   │   │
             quantum expira (interrupção  │   │   │ solicitação de E/S
             de relógio) ─────────────────┘   │   └───────────► [BLOQUEADO]
                     volta para PRONTO         │
                                                │ exit() /
                                                │ fim das rajadas
                                                ▼
                                          [TERMINADO]
```

### 5.3 Especificação Detalhada das Transições

| # | Transição | Evento disparador | Estado origem | Estado destino | Ações executadas |
|---|---|---|---|---|---|
| T1 | Criação de processo | `fork` simulado — leitura de uma nova entrada no arquivo de tarefas cujo `tempo_chegada` foi atingido | `NOVO` (implícito) | `PRONTO` | Criar PCB; atribuir `pid` sequencial; inicializar registradores zerados; inicializar `tempo_cpu_gasto = 0`, `tempo_espera = 0`; inserir na `fila_prontos`; registrar log de criação. |
| T2 | Despacho (dispatch) | Escalonador seleciona processo da `fila_prontos` (CPU ociosa ou preempção) | `PRONTO` | `EM_EXECUCAO` | Remover da `fila_prontos`; restaurar `registradores_salvos` na vCPU; (re)iniciar `quantum_restante` com o valor de quantum configurado (se Round Robin); registrar log de despacho. |
| T3 | Expiração de quantum | Interrupção de relógio — `quantum_restante == 0` e ainda há rajada de CPU pendente | `EM_EXECUCAO` | `PRONTO` | Salvar registradores no PCB; incrementar `tempo_cpu_gasto`; reinserir ao final da `fila_prontos` (Round Robin) ou reordenar fila de prioridade; registrar log de preempção. |
| T4 | Solicitação de E/S | O processo consome sua rajada de CPU corrente e a próxima operação da sequência é uma rajada de E/S | `EM_EXECUCAO` | `BLOQUEADO` | Salvar registradores; mover PCB para `fila_bloqueados`; armazenar duração da E/S (`rajadas_io[indice_rajada_atual]`); registrar log de bloqueio. |
| T5 | Conclusão de E/S | Contador de E/S do processo em `fila_bloqueados` chega a zero | `BLOQUEADO` | `PRONTO` | Avançar `indice_rajada_atual`; mover PCB de volta para `fila_prontos`; registrar log de desbloqueio. |
| T6 | Término do processo | Chamada `exit` simulada — não há mais rajadas de CPU/E/S pendentes | `EM_EXECUCAO` | `TERMINADO` | Registrar `tempo_termino`; mover PCB para `lista_terminados`; liberar processo da vCPU (CPU torna-se ociosa); registrar log de término com estatísticas finais do processo. |

### 5.4 Regras Complementares

- Um processo **nunca** transita diretamente de `PRONTO` para `BLOQUEADO` ou de `BLOQUEADO` para `EM_EXECUCAO` — deve sempre passar por `EM_EXECUCAO` ou `PRONTO`, respectivamente, respeitando o grafo acima.
- O campo `tempo_espera` deve ser incrementado a cada tick em que um PCB permanece no estado `PRONTO` (para qualquer processo na fila, não apenas o próximo a ser escolhido).
- O campo `tempo_cpu_gasto` deve ser incrementado a cada tick em que um PCB permanece no estado `EM_EXECUCAO`.

---

## 6. Especificação do Escalonador de CPU

O simulador deve implementar uma **interface de escalonamento intercambiável**, permitindo alternar entre algoritmos sem alterar o núcleo do simulador (padrão de projeto sugerido: *Strategy*).

### 6.1 Interface Genérica do Escalonador

```
interface Escalonador:
    metodo selecionar_proximo(fila_prontos) -> PCB
    metodo ao_inserir_processo(pcb: PCB, fila_prontos)      // hook opcional
    metodo ao_expirar_quantum(pcb: PCB, fila_prontos)       // hook opcional
    metodo obter_quantum(pcb: PCB) -> inteiro | nulo        // nulo se não aplicável
```

### 6.2 Algoritmo 1 — Round Robin (Circular)

#### 6.2.1 Estrutura de Dados

- Fila **circular** (implementável como fila FIFO comum, dado que reinserção ao final já simula a circularidade).
- Parâmetro de configuração global: `QUANTUM` (unidades de tempo, definido na inicialização do simulador ou no arquivo de tarefas).

#### 6.2.2 Comportamento

1. O processo no início da fila é despachado para a CPU (`selecionar_proximo`).
2. O `quantum_restante` do processo é definido como `QUANTUM` no momento do despacho.
3. A cada tick de execução, `quantum_restante` é decrementado.
4. Se `quantum_restante` chegar a zero **antes** de o processo terminar sua rajada de CPU ou solicitar E/S, ocorre a transição T3 (preempção) e o processo retorna ao **final** da fila de prontos.
5. Se o processo concluir a rajada de CPU (solicitar E/S ou terminar) antes de esgotar o quantum, a transição correspondente (T4 ou T6) ocorre normalmente, sem penalidade.

#### 6.2.3 Pseudocódigo

```
funcao round_robin.selecionar_proximo(fila_prontos):
    se fila_prontos vazia:
        retornar nulo
    pcb = fila_prontos.remover_do_inicio()
    pcb.quantum_restante = QUANTUM
    retornar pcb

funcao round_robin.ao_expirar_quantum(pcb, fila_prontos):
    fila_prontos.inserir_no_final(pcb)
```

### 6.3 Algoritmo 2 — Escalonamento por Prioridades (com prevenção de starvation)

#### 6.3.1 Estrutura de Dados

- Fila de prioridade (heap mínimo, ordenada por `prioridade` — menor valor = maior prioridade) **ou** lista ordenada reordenada a cada seleção.
- Suporte a prioridades **estáticas** (definidas na criação, imutáveis) ou **dinâmicas** (ajustadas ao longo da execução via *aging*).

#### 6.3.2 Mecanismo de Prevenção de Starvation — Aging (Envelhecimento de Prioridade)

Para evitar que processos de baixa prioridade nunca sejam executados:

- A cada tick em que um processo permanece na `fila_prontos` sem ser escolhido, seu `tempo_espera` é incrementado (conforme já especificado).
- Quando `tempo_espera` atingir um limiar configurável `LIMIAR_AGING`, a `prioridade` do processo é incrementada em prioridade (isto é, seu valor numérico é reduzido, aproximando-se da prioridade máxima), e o contador de espera para fins de aging é reiniciado.
- Ao ser finalmente despachado para execução, a `prioridade` do processo deve retornar ao valor de `prioridade_original` (no caso de prioridade dinâmica com reset pós-execução) — este comportamento deve ser configurável.

#### 6.3.3 Pseudocódigo

```
funcao prioridade.selecionar_proximo(fila_prontos):
    se fila_prontos vazia:
        retornar nulo
    pcb = fila_prontos.remover_de_maior_prioridade()  // menor valor numerico
    retornar pcb

funcao prioridade.aplicar_aging(fila_prontos):
    para cada pcb em fila_prontos:
        se pcb.tempo_espera >= LIMIAR_AGING:
            pcb.prioridade = max(pcb.prioridade - 1, PRIORIDADE_MAXIMA)
            pcb.tempo_espera = 0  // reinicia contador de aging (não o tempo_espera estatístico global, se houver separação dos dois contadores)
    reordenar fila_prontos por prioridade
```

> **Nota de implementação:** recomenda-se manter dois contadores distintos no PCB caso o aging reinicie: `tempo_espera` (estatística acumulada, nunca reiniciada) e `tempo_espera_aging` (reiniciado a cada promoção). Caso o Harness opte por simplificar, um único contador pode ser usado, desde que documentado no código gerado.

#### 6.3.4 Preempção em Escalonamento por Prioridade

- Deve ser configurável se o algoritmo de prioridade é **preemptivo** (um processo de maior prioridade que chega interrompe o processo em execução) ou **não-preemptivo** (a troca só ocorre quando o processo em execução libera a CPU voluntariamente, por E/S ou término).
- O comportamento padrão sugerido para o simulador didático é **não-preemptivo**, com preempção opcional configurável via parâmetro de inicialização.

### 6.4 Seleção do Algoritmo em Tempo de Configuração

O núcleo do simulador deve receber o algoritmo de escalonamento desejado como parâmetro de configuração (linha de comando, arquivo de configuração ou cabeçalho do arquivo de tarefas), instanciando a implementação correspondente da interface `Escalonador` — sem exigir alterações no restante do código do núcleo.

---

## 7. Entradas do Simulador — Arquivo de Tarefas

### 7.1 Objetivo

O arquivo de tarefas descreve, de forma declarativa, os processos que o simulador deve criar, incluindo seus tempos de chegada e suas sequências alternadas de rajadas de CPU e E/S.

### 7.2 Formato Sugerido (texto estruturado, ex.: um processo por linha)

```
# Formato: PID_SUGERIDO;TEMPO_CHEGADA;PRIORIDADE;SEQUENCIA_RAJADAS
# SEQUENCIA_RAJADAS alterna CPU e E/S, sempre iniciando e podendo terminar em CPU
# Sintaxe da sequência: CPU:<duracao> | IO:<duracao>, separados por vírgula

1;0;2;CPU:5,IO:3,CPU:2
2;1;1;CPU:8
3;2;3;CPU:3,IO:5,CPU:4,IO:2,CPU:1
```

### 7.3 Regras de Interpretação

- `PID_SUGERIDO` é um identificador do arquivo de entrada; o núcleo simulado pode reatribuir um `pid` interno sequencial no momento do `fork`, mantendo o mapeamento para fins de rastreabilidade no log.
- `TEMPO_CHEGADA` determina em qual tick do relógio lógico o processo realiza a transição T1 (`NOVO → PRONTO`).
- A `SEQUENCIA_RAJADAS` deve sempre iniciar com uma rajada de `CPU`. Rajadas `IO` subsequentes disparam a transição T4 ao serem alcançadas.
- Um cabeçalho opcional no início do arquivo pode definir parâmetros globais de simulação:

```
# CONFIG;ALGORITMO=ROUND_ROBIN;QUANTUM=4;LIMIAR_AGING=10
```

### 7.4 Validações Obrigatórias na Leitura

- Rejeitar arquivos com `PID_SUGERIDO` duplicado.
- Rejeitar sequências de rajadas vazias ou iniciadas por `IO`.
- Rejeitar valores de duração não positivos.
- Emitir mensagem de erro clara indicando a linha do arquivo com problema.

---

## 8. Saídas do Simulador

O simulador deve produzir, ao final da execução (ou opcionalmente em tempo real), três artefatos de saída:

### 8.1 Gráfico de Gantt Textual

Representação em texto (ASCII) da alocação da CPU ao longo do tempo, no formato:

```
Tick:     0    1    2    3    4    5    6    7    8    9   10
CPU:    [ P1 ][ P1 ][ P2 ][ P2 ][ P1 ][ -- ][ P3 ][ P3 ][ P1 ][ P2 ][ P3 ]
```

- Cada bloco representa uma unidade de tempo (tick) e o `pid` do processo que ocupava a CPU virtual naquele instante.
- `--` (ou símbolo equivalente configurável) indica CPU ociosa.

### 8.2 Log de Transições de Estado

Arquivo de log (texto simples ou estruturado, ex. CSV/JSON) contendo uma entrada por transição, com o seguinte conteúdo mínimo:

```
[tick=3] PID=2 TRANSICAO=PRONTO->EM_EXECUCAO (dispatch pelo escalonador ROUND_ROBIN)
[tick=7] PID=2 TRANSICAO=EM_EXECUCAO->BLOQUEADO (solicitacao de E/S, duracao=5)
[tick=12] PID=2 TRANSICAO=BLOQUEADO->PRONTO (E/S concluida)
[tick=15] PID=2 TRANSICAO=EM_EXECUCAO->TERMINADO (exit)
```

### 8.3 Estatísticas de Uso de CPU

Relatório-resumo final, contendo, no mínimo:

| Métrica | Escopo | Descrição |
|---|---|---|
| Tempo de retorno (*turnaround time*) | Por processo | `tempo_termino - tempo_chegada` |
| Tempo de espera total | Por processo | Valor final de `tempo_espera` |
| Tempo de CPU consumido | Por processo | Valor final de `tempo_cpu_gasto` |
| Tempo médio de espera | Global | Média de `tempo_espera` entre todos os processos |
| Tempo médio de retorno | Global | Média de turnaround entre todos os processos |
| Taxa de utilização da CPU | Global | `(ticks com CPU ocupada / total de ticks simulados) * 100` |
| Throughput | Global | Número de processos terminados / total de ticks simulados |

---

## 9. Diretrizes de Entrega para Geração de Código via Harness

Este documento constitui a **especificação de entrada** para a geração de código por um Harness de desenvolvimento assistido (ex.: Claude Code, Open Code). As seguintes diretrizes devem ser observadas na fase de implementação:

1. **Modularização:** o código gerado deve separar claramente os módulos de PCB/Tabela de Processos, Núcleo/Laço Principal, Escalonadores (com interface comum) e Módulo de Saída (Gantt/Logs/Estatísticas).
2. **Independência de algoritmo:** a troca entre Round Robin e Prioridades deve ser possível via configuração, sem edição do núcleo.
3. **Determinismo:** dada a mesma entrada e configuração, o simulador deve produzir sempre a mesma saída (essencial para os casos de teste).
4. **Testabilidade:** o Harness deve gerar, junto ao simulador, um conjunto de casos de teste automatizados cobrindo, no mínimo:
   - Um cenário com um único processo (sem concorrência).
   - Um cenário com múltiplos processos e Round Robin, validando a ordem de preempção.
   - Um cenário com múltiplos processos e Prioridades, validando a promoção por aging (starvation prevenida).
   - Um cenário com E/S intercalada, validando as transições T4/T5.
   - Um cenário de arquivo de tarefas inválido, validando o tratamento de erros de leitura.
5. **Documentação do código gerado:** cada estrutura de dados e função pública deve conter comentários/docstrings referenciando a seção correspondente deste documento (ex.: `// Ver Seção 5.3, Transição T3`).
6. **Linguagem de implementação:** a ser definida pelo desenvolvedor/Harness no momento da geração; este documento é agnóstico de linguagem, utilizando pseudocódigo estrutural nas seções acima.

---

## 10. Glossário

| Termo | Definição |
|---|---|
| PCB | Bloco de Controle de Processo — estrutura de dados que armazena o estado completo de um processo. |
| Fork (simulado) | Ato de criação de um novo processo no simulador, correspondente à transição `NOVO → PRONTO`. |
| Quantum | Fatia máxima de tempo que um processo pode ocupar a CPU antes de sofrer preempção (Round Robin). |
| Starvation | Situação em que um processo de baixa prioridade nunca (ou raramente) recebe tempo de CPU. |
| Aging | Técnica de aumento gradual da prioridade de um processo em espera, usada para evitar starvation. |
| Rajada de CPU (*CPU burst*) | Intervalo de tempo em que um processo utiliza efetivamente a CPU sem interrupção lógica de E/S. |
| Rajada de E/S (*I/O burst*) | Intervalo de tempo em que um processo permanece bloqueado aguardando conclusão de uma operação fictícia de E/S. |

---

*Fim do documento de especificação.*
