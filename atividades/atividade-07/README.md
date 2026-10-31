# Atividade 07 - Algoritmo dos Banqueiros

**Aluno:** Matheus Levi Fava do Carmo Pessoa  
**Disciplina:** Sistemas Operacionais  

## Sobre a Atividade
Este repositório contém a implementação em Python (`bankers_algorithm.py`) do **Algoritmo dos Banqueiros** (criado por Dijkstra). O objetivo desse algoritmo é gerenciar a distribuição de recursos do sistema operacional entre vários processos, garantindo que o sistema nunca entre em *deadlock* (impasse/travamento).

## O que o script faz
O código simula um cenário com 5 processos (P0 a P4) e 3 tipos de recursos (R0, R1, R2), executando automaticamente os seguintes testes:

1. **Leitura do Estado Inicial:** Mostra o total de recursos, o que já está alocado para cada processo e o que falta (necessidade).
2. **Verificação de Estado Seguro:** Testa e prova matematicamente que o sistema consegue rodar todos os processos até o fim com os recursos disponíveis, sem travar.
3. **Teste de Requisição Aceita:** O processo P1 pede uma quantidade de recursos que é válida e segura. O algoritmo aprova e entrega os recursos.
4. **Teste de Requisição Negada/Bloqueada:** O processo P4 pede recursos que não estão disponíveis no momento em estoque. O algoritmo bloqueia o pedido para evitar que o sistema trave (deadlock).

## Como rodar
Para testar, basta abrir o terminal na pasta do projeto e executar:

```bash
python bankers_algorithm.py
