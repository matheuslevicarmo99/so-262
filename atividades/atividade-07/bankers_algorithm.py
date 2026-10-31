#!/usr/bin/env python3
"""
Simulador do Algoritmo do Banqueiro (Dijkstra)
Baseado nos conceitos do Capítulo 6 do livro "Sistemas Operacionais Modernos" (Tanenbaum & Bos).
"""

import copy

class BankersAlgorithm:
    def __init__(self, process_names, total_resources, allocation_matrix, max_matrix):
        self.process_names = process_names
        self.num_processes = len(process_names)
        self.num_resources = len(total_resources)
        self.total_resources = list(total_resources) 
        self.allocation = copy.deepcopy(allocation_matrix) 
        self.max_matrix = copy.deepcopy(max_matrix)
        
        self.need = [
            [self.max_matrix[i][j] - self.allocation[i][j] for j in range(self.num_resources)]
            for i in range(self.num_processes)
        ]
        
        self.available = list(self.total_resources)
        for j in range(self.num_resources):
            allocated_sum = sum(self.allocation[i][j] for i in range(self.num_processes))
            self.available[j] -= allocated_sum

    def display_state(self):
        print("\n" + "=" * 70)
        print("ESTADO ATUAL DO SISTEMA")
        print("ALUNO - Matheus Levi Fava do Carmo Pessoa")
        print("=" * 70)
        print(f"Recursos Totais (E):     {self.total_resources}")
        print(f"Recursos Disponíveis (A): {self.available}")
        print("-" * 70)
        print(f"{'Processo':<10} | {'Alocado (C)':<15} | {'Máximo (Max)':<15} | {'Necessidade (Need)':<15}")
        print("-" * 70)
        for i in range(self.num_processes):
            p_name = self.process_names[i]
            alloc_str = str(self.allocation[i])
            max_str = str(self.max_matrix[i])
            need_str = str(self.need[i])
            print(f"{p_name:<10} | {alloc_str:<15} | {max_str:<15} | {need_str:<15}")
        print("=" * 70)

    def is_safe_state(self, verbose=True):
        work = list(self.available)
        finish = [False] * self.num_processes
        safe_sequence = []

        if verbose:
            print("\n" + "-" * 70)
            print("[VERIFICAÇÃO DE ESTADO SEGURO]")
            print("ALUNO - Matheus Levi Fava do Carmo Pessoa")
            print("-" * 70)
            print(f"Vetor de Trabalho Inicial (Work/Disponível): {work}\n")

        step = 1
        while len(safe_sequence) < self.num_processes:
            found_candidate = False
            for i in range(self.num_processes):
                if not finish[i]:
                    can_satisfy = all(self.need[i][j] <= work[j] for j in range(self.num_resources))
                    if can_satisfy:
                        if verbose:
                            print(f"Passo {step}: {self.process_names[i]} pode ser atendido!")
                            print(f"  Necessidade {self.need[i]} <= Disponível {work}")
                            print(f"  {self.process_names[i]} executa e libera seus recursos alocados: {self.allocation[i]}")
                        
                        for j in range(self.num_resources):
                            work[j] += self.allocation[i][j]
                        
                        finish[i] = True
                        safe_sequence.append(self.process_names[i])
                        found_candidate = True
                        step += 1
                        
                        if verbose:
                            print(f"  Novo Vetor de Trabalho (Work): {work}\n")
                        break
            
            if not found_candidate:
                if verbose:
                    print("❌ ERRO: Nenhum processo pendente pode ser satisfeito com os recursos disponíveis.")
                    print("   O SISTEMA ENCONTRA-SE EM UM ESTADO INSEGURO!")
                return False, []

        if verbose:
            print("✅ SUCESSO: O sistema está em um ESTADO SEGURO!")
            print(f"   Sequência Segura de Execução: {' -> '.join(safe_sequence)}")
        return True, safe_sequence

    def request_resources(self, process_index, request_vector):
        p_name = self.process_names[process_index]
        print("\n" + "#" * 70)
        print(f"SOLICITAÇÃO DE RECURSOS PELO PROCESSO {p_name}: {request_vector}")
        print("ALUNO - Matheus Levi Fava do Carmo Pessoa")
        print("#" * 70)

        for j in range(self.num_resources):
            if request_vector[j] > self.need[process_index][j]:
                print(f"❌ REQUISIÇÃO NEGADA: {p_name} solicitou mais do que sua necessidade máxima declarada.")
                print(f"   Solicitado: {request_vector[j]} > Necessidade {self.need[process_index][j]} para o recurso R{j}")
                return False

        for j in range(self.num_resources):
            if request_vector[j] > self.available[j]:
                print(f"⏳ PROCESSO BLOQUEADO: Recursos insuficientes disponíveis no momento.")
                print(f"   Solicitado: {request_vector[j]} > Disponível {self.available[j]} para o recurso R{j}")
                print(f"   {p_name} deve aguardar a liberação de recursos por outros processos.")
                return False

        print("⚠️ TENTATIVA PROVISÓRIA: Recursos disponíveis no momento. Testando alocação...")
        for j in range(self.num_resources):
            self.available[j] -= request_vector[j]
            self.allocation[process_index][j] += request_vector[j]
            self.need[process_index][j] -= request_vector[j]

        is_safe, sequence = self.is_safe_state(verbose=True)

        if is_safe:
            print(f"\n✅ REQUISIÇÃO CONCEDIDA A {p_name}!")
            print("   O estado resultante permanece SEGURO.")
            return True
        else:
            print(f"\n❌ REQUISIÇÃO NEGADA A {p_name}!")
            print("   A alocação levaria a um ESTADO INSEGURO (risco de deadlock). Efetuando rollback...")
            for j in range(self.num_resources):
                self.available[j] += request_vector[j]
                self.allocation[process_index][j] -= request_vector[j]
                self.need[process_index][j] += request_vector[j]
            print("   Estado original restaurado. O processo deve aguardar.")
            return False


def run_demo():
    print("======================================================================")
    print("     SIMULAÇÃO DO ALGORITMO DO BANQUEIRO (TANENBAUM & BOS - CAP 6)    ")
    print("     ALUNO - Matheus Levi Fava do Carmo Pessoa                        ")
    print("======================================================================")
    
    process_names = ["P0", "P1", "P2", "P3", "P4"]
    total_resources = [10, 5, 7]
    
    allocation = [
        [0, 1, 0],  # P0
        [2, 0, 0],  # P1
        [3, 0, 2],  # P2
        [2, 1, 1],  # P3
        [0, 0, 2]   # P4
    ]
    
    max_matrix = [
        [7, 5, 3],  # P0
        [3, 2, 2],  # P1
        [9, 0, 2],  # P2
        [2, 2, 2],  # P3
        [4, 3, 3]   # P4
    ]

    banker = BankersAlgorithm(process_names, total_resources, allocation, max_matrix)
    
    # Testes executados em ordem
    banker.display_state()
    is_safe, sequence = banker.is_safe_state(verbose=True)
    
    banker.request_resources(process_index=1, request_vector=[1, 0, 2])
    banker.display_state()

    banker.request_resources(process_index=4, request_vector=[3, 3, 0])
    banker.display_state()

if __name__ == "__main__":
    run_demo()