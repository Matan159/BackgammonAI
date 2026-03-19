import random
import time
import multiprocessing
from multiprocessing.pool import Pool
from models import GameState
from actions import init_game, roll_dice, check_winner, get_legal_moves
from heuristics import get_best_move, _evaluate_board_tuple, get_dynamic_weights, get_both_pip_counts

# --- GA Configuration ---
POPULATION_SIZE = 20
GENERATIONS = 5
SWISS_ROUNDS = 4
MUTATION_RATE = 0.15 
MUTATION_AMOUNT = 1.2 
MAX_ROLLS_PER_GAME = 500

# The Baseline "Smart" Agent (Immortal Adam)
ADAM_DNA = (
    40.0, -50.0, 0.5, 1.0, 3.5, 1.5, 3.0,
    40.0, -40.0, 0.5, 1.5, 5.0, 0.5, 0.5,
    40.0, -1.5, -10.0, 2.0,
    2.0, 1.0, -0.5, -0.8,
    1.5, 2.0, 1.0, 1.5,
    1.0, 0.5, 15.0, 1.0, 0.2
)

SPECIAL_AGENTS = [
    (54.2, -63.5, 0.62, 1.34, 4.98, 1.11, 3.42, 48.1, -55.8, 0.73, 1.11, 6.92, 0.74, 0.63, 48.9, -1.97, -13.7, 2.41, 2.41, 1.42, -0.73, -1.03, 1.86, 2.41, 1.42, 1.86, 1.42, 0.73, 19.8, 1.42, 0.27),

    (33.1, -58.4, 0.41, 1.22, 3.91, 1.88, 2.62, 52.3, -48.2, 0.58, 1.88, 4.21, 0.58, 0.74, 44.7, -1.88, -12.4, 2.62, 2.62, 1.22, -0.62, -0.91, 1.88, 2.62, 1.22, 1.88, 1.22, 0.62, 17.4, 1.22, 0.29),

    (47.5, -42.6, 0.74, 1.41, 4.62, 1.74, 3.41, 59.1, -52.3, 0.74, 1.74, 6.11, 0.62, 0.62, 59.1, -1.62, -11.2, 2.74, 2.74, 1.41, -0.74, -0.91, 1.74, 2.74, 1.41, 1.74, 1.41, 0.62, 18.6, 1.41, 0.24),

    (28.4, -71.2, 0.38, 1.11, 3.11, 1.11, 2.11, 44.2, -44.2, 0.44, 1.11, 5.88, 0.44, 0.44, 44.2, -1.11, -14.2, 2.11, 2.11, 1.11, -0.44, -0.66, 1.11, 2.11, 1.11, 1.11, 1.11, 0.44, 16.6, 1.11, 0.22),

    (51.1, -57.7, 0.66, 1.33, 4.77, 1.66, 3.66, 51.1, -51.1, 0.66, 1.66, 7.22, 0.66, 0.66, 51.1, -1.66, -12.2, 2.66, 2.66, 1.33, -0.66, -0.99, 1.66, 2.66, 1.33, 1.66, 1.33, 0.66, 19.9, 1.33, 0.26),

    (36.2, -45.5, 0.55, 1.44, 4.22, 1.22, 2.55, 36.2, -36.2, 0.55, 1.22, 4.55, 0.55, 0.55, 36.2, -1.22, -11.5, 2.22, 2.22, 1.44, -0.55, -0.77, 1.22, 2.22, 1.44, 1.22, 1.44, 0.55, 17.7, 1.44, 0.23),

    (58.8, -62.2, 0.74, 1.48, 5.11, 1.48, 3.11, 58.8, -58.8, 0.74, 1.48, 6.44, 0.74, 0.74, 58.8, -1.48, -14.8, 2.48, 2.48, 1.48, -0.74, -1.11, 1.48, 2.48, 1.48, 1.48, 1.48, 0.74, 20.2, 1.48, 0.30),

    (42.2, -52.2, 0.52, 1.22, 3.88, 1.22, 3.22, 42.2, -42.2, 0.52, 1.22, 5.22, 0.52, 0.52, 42.2, -1.22, -12.2, 2.22, 2.22, 1.22, -0.52, -0.88, 1.22, 2.22, 1.22, 1.22, 1.22, 0.52, 16.8, 1.22, 0.24),

    (49.5, -66.1, 0.61, 1.31, 4.31, 1.61, 3.61, 49.5, -49.5, 0.61, 1.61, 6.31, 0.61, 0.61, 49.5, -1.61, -13.1, 2.61, 2.61, 1.31, -0.61, -0.91, 1.61, 2.61, 1.31, 1.61, 1.31, 0.61, 18.1, 1.31, 0.25)
]


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

# --- Seeded Match Logic ---
# Added starting_player argument
def play_headless_match_seeded(dna_1: tuple, dna_2: tuple, p1_seq: list, p2_seq: list, starting_player: int = 1) -> int:
    state = init_game(starting_player=starting_player)
    p1_turn_idx = 0
    p2_turn_idx = 0
    
    total_turns = 0 # Track how long the game has been running
    
    while True:
        winner = check_winner(state)
        if winner: return winner

        # --- NEW: Adjudicator (Stop infinite loops) ---
        if total_turns > 250:
            p1_pips, p2_pips = get_both_pip_counts(tuple(state.board), 1)
            # Player with the lowest pip count wins the tiebreaker
            return 1 if p1_pips < p2_pips else -1
            
        # --- NEW: Mid-Game Cache Nuke (Protect RAM with 0 penalty) ---
        if total_turns > 0 and total_turns % 50 == 0:
            _evaluate_board_tuple.cache_clear()

        # Dice buffer warnings...
        if state.current_turn == 1:
            if p1_turn_idx < len(p1_seq):
                dice = list(p1_seq[p1_turn_idx])
            else:
                print(f"[WARNING] p1 dice buffer exceeded at turn {p1_turn_idx}. Falling back to random roll.")
                dice = roll_dice()
        else:
            if p2_turn_idx < len(p2_seq):
                dice = list(p2_seq[p2_turn_idx])
            else:
                print(f"[WARNING] p2 dice buffer exceeded at turn {p2_turn_idx}. Falling back to random roll.")
                dice = roll_dice()
        
        possible_moves = get_legal_moves(state.board, state.current_turn, dice)
        
        if not possible_moves:
            state = GameState(board=state.board, current_turn=-state.current_turn)
            total_turns += 1 # Count skipped turns
            continue
            
        if state.current_turn == 1:
            p1_turn_idx += 1
        else:
            p2_turn_idx += 1
            
        current_dna = dna_1 if state.current_turn == 1 else dna_2
        
        best_move, _ = get_best_move(state, possible_moves, weights=current_dna)
        state = GameState(board=best_move.board, current_turn=-state.current_turn)
        
        total_turns += 1 # Count played turns

# --- Multiprocessing Worker ---
def worker_duplicate_match(args) -> tuple:
    """Runs a 2-game duplicate match between two agents and returns the score."""
    
    # Clear stale cache from any previous matchup this worker may have handled.
    # The cache will then build up during Game 1 and be reused during Game 2,
    # since both games share the same two agents and therefore the same weights.
    _evaluate_board_tuple.cache_clear()
    get_dynamic_weights.cache_clear()
    
    idx1, dna1, idx2, dna2 = args
    
    seq_A = [roll_dice() for _ in range(MAX_ROLLS_PER_GAME)]
    seq_B = [roll_dice() for _ in range(MAX_ROLLS_PER_GAME)]
    
    # Pass opposite starting players explicitly to fix side-swap guarantee
    winner1 = play_headless_match_seeded(dna1, dna2, seq_A, seq_B, starting_player=1)
    winner2 = play_headless_match_seeded(dna2, dna1, seq_A, seq_B, starting_player=-1)
    
    score1 = (1 if winner1 == 1 else 0) + (1 if winner2 == -1 else 0)
    score2 = (1 if winner1 == -1 else 0) + (1 if winner2 == 1 else 0)
    
    return idx1, score1, idx2, score2

# --- Swiss Tournament Logic ---
def run_swiss_tournament(population: list, pool: Pool) -> dict:
    scores = {i: 0 for i in range(POPULATION_SIZE)}
    played_pairs = set()
    
    for round_num in range(1, SWISS_ROUNDS + 1):
        print(f"\n  [Round {round_num}/{SWISS_ROUNDS}] Generating pairings...")
        
        score_groups = {}
        for i in scores:
            score_groups.setdefault(scores[i], []).append(i)
            
        ranked_agents = []
        for score in sorted(score_groups.keys(), reverse=True):
            group = score_groups[score]
            random.shuffle(group)
            ranked_agents.extend(group)
            
        pairings = []
        unpaired = list(ranked_agents)
        
        while unpaired:
            p1 = unpaired.pop(0)
            p2 = None
            
            for i, potential_p2 in enumerate(unpaired):
                pair_key = tuple(sorted((p1, potential_p2)))
                if pair_key not in played_pairs:
                    p2 = unpaired.pop(i)
                    played_pairs.add(pair_key)
                    break
                    
            if p2 is None:
                p2 = unpaired.pop(0)
                
            pairings.append((p1, population[p1], p2, population[p2]))
            
        matchup_strings = [f"Agent {p1} vs Agent {p2}" for p1, _, p2, _ in pairings]
        print(f"    Matchups: {', '.join(matchup_strings)}")
        print("    Simulating matches...")
            
        results = []
        total_pairings = len(pairings)
        for i, res in enumerate(pool.imap_unordered(worker_duplicate_match, pairings), 1):
            results.append(res)
            # The \r at the start makes it overwrite the current line, acting like a live progress bar!
            print(f"\r    -> Progress: {i}/{total_pairings} matchups finished...", end="", flush=True)
        print() # Move to the next line when the round is fully complete
        
        for idx1, s1, idx2, s2 in results:
            scores[idx1] += s1
            scores[idx2] += s2
            
        top_3 = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)[:3]
        print(f"  -> Round {round_num} Leaderboard: 1st: Agent {top_3[0]} ({scores[top_3[0]]} pts) | 2nd: Agent {top_3[1]} ({scores[top_3[1]]} pts) | 3rd: Agent {top_3[2]} ({scores[top_3[2]]} pts)")
        
    return scores

def run_evolution():
    print("Initializing Swiss Tournament Primordial Soup...")
    
    population = [ADAM_DNA] + SPECIAL_AGENTS + [create_random_agent() for _ in range(POPULATION_SIZE - 1 - len(SPECIAL_AGENTS))]
    
    with open("best_dna_log.txt", "w") as f:
        f.write("--- Backgammon Swiss GA Training Log ---\n")
        
        with multiprocessing.Pool() as pool:
            for gen in range(GENERATIONS):
                start_time = time.time()
                print(f"\n" + "="*40)
                print(f"=== Starting Generation {gen + 1}/{GENERATIONS} ===")
                print("="*40)
                
                scores = run_swiss_tournament(population, pool)
                
                ranked_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
                best_agent_idx = ranked_indices[0]
                best_dna = population[best_agent_idx]
                
                survivors = [population[i] for i in ranked_indices[:POPULATION_SIZE // 2]]
                
                if population[0] not in survivors:
                    survivors[-1] = population[0] 
                    
                new_population = [population[0]] 
                
                for survivor in survivors:
                    if survivor != population[0]:
                        new_population.append(survivor)
                        
                while len(new_population) < POPULATION_SIZE:
                    parent1 = random.choice(survivors)
                    parent2 = random.choice(survivors)
                    child = crossover(parent1, parent2)
                    child = mutate(child)
                    new_population.append(child)
                    
                population = new_population
                
                gen_time = time.time() - start_time
                print(f"\nGeneration {gen + 1} complete in {gen_time:.1f} seconds. Top Agent Score: {scores[best_agent_idx]}/{SWISS_ROUNDS * 2} win(s)")
                
                print(f"  Survivors: {[(i, scores[i]) for i in ranked_indices[:POPULATION_SIZE // 2]]}")
                
                is_adam = (best_dna == ADAM_DNA)
                f.write(f"\nGeneration {gen + 1} Best DNA (Agent {best_agent_idx}, {'ADAM' if is_adam else 'evolved'}, Score {scores[best_agent_idx]}/{SWISS_ROUNDS * 2}):\n")
                f.write(f"{best_dna}\n")
                f.flush()

    print("\nEvolution Complete. Check 'best_dna_log.txt' for the results!")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_evolution()