import random
import time
from models import GameState
from actions import init_game, roll_dice, check_winner, get_legal_moves
# CHANGE 2: Import cached functions
from heuristics import get_best_move, _evaluate_board_tuple, get_dynamic_weights 

# --- GA Configuration ---
POPULATION_SIZE = 20
GENERATIONS = 1500
MUTATION_RATE = 0.15 
MUTATION_AMOUNT = 1.2 

# The Baseline "Smart" Agent (Your tuned heuristics)
ADAM_DNA = (
    # Safe Strategy (0-6): off, cap, pos, util, prime_pure, flex_safety, free
    40.0, -50.0, 0.5, 1.0, 3.5, 1.5, 3.0,
    # Aggressive Strategy (7-13): off, cap, pos, util, prime_pure, flex_safety, free
    40.0, -40.0, 0.5, 1.5, 5.0, 0.5, 0.5,
    # Race Strategy (14-17): off, pip, outside, spread
    40.0, -1.5, -10.0, 2.0,
    # Checker Util (18-21): prime, mid, dead, stack
    2.0, 1.0, -0.5, -0.8,
    # Primes & Purity (22-25): exp, block, non_block, gap
    1.5, 2.0, 1.0, 1.5,
    # Flex & Safety (26-30): base, close, dir_threat, indir_threat, safe_blot
    1.0, 0.5, 15.0, 1.0, 0.2
)


DNA_BOUNDS = [
    (0, 100), (-100, 0), (0, 10), (0, 10), (0, 20), (0, 10), (0, 15),
    (0, 100), (-100, 0), (0, 10), (0, 10), (0, 20), (0, 10), (0, 15),
    (0, 100), (-10, 0), (-30, 0), (0, 20),
    (0, 10), (0, 10), (-5, 5), (-5, 0),
    (0.5, 5.0), (0.0, 10.0), (0.0, 5.0), (0.0, 10.0),
    (0, 10), (0.0, 5.0), (0, 50), (0, 20), (0, 10)
]

def create_random_agent() -> tuple:
    dna = []
    for bounds in DNA_BOUNDS:
        dna.append(random.uniform(bounds[0], bounds[1]))
    return tuple(dna)

def crossover(parent1: tuple, parent2: tuple) -> tuple:
    child_dna = []
    for i in range(31):
        if random.random() > 0.5:
            child_dna.append(parent1[i])
        else:
            child_dna.append(parent2[i])
    return tuple(child_dna)

def mutate(dna: tuple) -> tuple:
    mutated_dna = list(dna)
    for i in range(31):
        if random.random() < MUTATION_RATE:
            mutated_dna[i] += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
            mutated_dna[i] = max(DNA_BOUNDS[i][0], min(DNA_BOUNDS[i][1], mutated_dna[i]))
    return tuple(mutated_dna)

def play_headless_match(dna_1: tuple, dna_2: tuple) -> int:
    # Clear cache between completely unique agents
    _evaluate_board_tuple.cache_clear()
    get_dynamic_weights.cache_clear()
    
    state = init_game()
    
    while True:
        winner = check_winner(state)
        if winner: return winner

        dice = roll_dice()
        
        # 1. Calculate the legal moves exactly ONCE using the unpacked signature
        possible_moves = get_legal_moves(state.board, state.current_turn, dice)
        
        # 2. Check the saved list to see if the turn is skipped
        if not possible_moves:
            state = GameState(board=state.board, current_turn=-state.current_turn)
            continue
            
        current_dna = dna_1 if state.current_turn == 1 else dna_2
        
        # 3. Pass the already-calculated possible_moves into get_best_move
        best_move, _ = get_best_move(state, possible_moves, weights=current_dna)
        
        state = GameState(board=best_move.board, current_turn=-state.current_turn)

def run_evolution():
    print("Initializing Primordial Soup...")
    
    population = [ADAM_DNA, ADAM_DNA, ADAM_DNA, ADAM_DNA, ADAM_DNA] + [create_random_agent() for _ in range(POPULATION_SIZE - 5)]
    
    # CHANGE 6: Open file once and wrap the loop
    with open("best_dna_log.txt", "w") as f:
        f.write("--- Backgammon GA Training Log ---\n")
        
        for gen in range(GENERATIONS):
            start_time = time.time()
            print(f"\n=== Starting Generation {gen + 1}/{GENERATIONS} ===")
            scores = {i: 0 for i in range(POPULATION_SIZE)}
            
            # CHANGE 4: Shuffle the population before pairing so seeds fight others
            random.shuffle(population)
            
            for idx1 in range(0, POPULATION_SIZE, 2):
                idx2 = idx1 + 1
                agent1_dna = population[idx1]
                agent2_dna = population[idx2]
                
                winner = play_headless_match(agent1_dna, agent2_dna)
                if winner == 1:
                    scores[idx1] += 1
                else:
                    scores[idx2] += 1
                    
            ranked_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
            best_agent_idx = ranked_indices[0]
            
            survivors = [population[i] for i in ranked_indices[:POPULATION_SIZE // 2]]
            
            new_population = list(survivors)
            while len(new_population) < POPULATION_SIZE:
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)
                child = crossover(parent1, parent2)
                child = mutate(child)
                new_population.append(child)
                
            population = new_population
            
            best_dna = survivors[0]
            gen_time = time.time() - start_time
            print(f"Generation {gen + 1} complete in {gen_time:.1f} seconds. Top Score: {scores[best_agent_idx]} win(s)")
            
            # CHANGE 6: Append directly to the already open file and flush to disk
            f.write(f"\nGeneration {gen + 1} Best DNA:\n")
            f.write(f"{best_dna}\n")
            f.flush()

    print("\nEvolution Complete. Check 'best_dna_log.txt' for the results!")

if __name__ == "__main__":
    run_evolution()