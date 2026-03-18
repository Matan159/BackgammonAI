import random
import time
from models import GameState
from actions import init_game, roll_dice, check_winner, get_legal_moves
from heuristics import get_best_move

# --- GA Configuration ---
POPULATION_SIZE = 20
GENERATIONS = 70
MUTATION_RATE = 0.15 # 15% chance for a gene to mutate
MUTATION_AMOUNT = 1.2 # Wider mutation shifts for better exploration

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

GEN20_TOP_DNA_RUN1 = (
    61.6691607124848, -39.033144381120245, 10, 0.5535084782510173, 9.721618766521274, 7.097635479590709, 1.6044906618327563, 17.23610814921711, -9.782212038342335, 6.033525816981335, 9.784053347286369, 1.013505342022857, 0.9453352769856229, 14.582283023665612, 33.077933954958155, -10, -25.748617767756816, 8.803005116649675, 4.751101229243849, 2.7152417647426264, -5, -4.488054771072994, 3.4632656171982648, 9.737355650714154, 1.754327660443142, 7.8766651420437634, 6.780628411034597, 1.8251209264679717, 11.77923237056087, 18.228580734068142, 7.291008653259209
)

GEN20_TOP_DNA_RUN2 = (
    15.978269080456549, -25.520338381615247, 8.641029126648656, 5.8538351497916965, 9.228359438396282, 6.80662375114478, 0.5357715925767024, 15.568089473911451, -33.83187208865223, 0, 4.260121606255912, 11.174981628320076, 0.9601883121395782, 10.012594750033731, 71.09434729365171, -10, -9.730693255272104, 7.403977340013146, 5.766193831016121, 2.388718724760736, -0.9391698928795473, 0, 3.7048234999413143, 9.737355650714154, 0.488696085231922, 1.9095186257245378, 2.2079088948357883, 1.697871011107156, 14.523311774446828, 1.553875646868323, 6.160501864356524
    )

GEN39_TOP_DNA_RUN2 = (
    15.978269080456549, -40.57150388770723, 7.002577195236535, 5.060868679758681, 10.271284770564137, 6.374257428182323, 0, 15.35398169811127, -32.853997700459814, 1.3173760822678302, 0.8625728228345424, 11.364892039678438, 4.260274200365508, 7.5147892725066505, 71.73336734758155, -1.546951917212712, -5.34193812447907, 8.817512318374874, 6.53423901278557, 3.986264425468471, -0.9391698928795473, 0, 2.7285764289520364, 7.464286627718062, 2.3396906275312723, 1.9095186257245378, 2.925327818448932, 1.697871011107156, 14.523311774446828, 0.08563244559512295, 6.858517735117677
    )

GEN40_TOP_DNA_RUN2 = (
    16.47501417153483, -40.57150388770723, 8.641029126648656, 5.060868679758681, 10.271284770564137, 7.632538975091173, 0, 15.35398169811127, -32.853997700459814, 1.3173760822678302, 0.8625728228345424, 11.364892039678438, 0, 7.5147892725066505, 71.20164615396267, -1.546951917212712, -5.34193812447907, 7.403977340013146, 5.821322777388142, 3.986264425468471, -0.493149774981672, -0.5784147040279, 2.8493249097478506, 7.464286627718062, 0.9257990501377829, 1.7490866192587027, 2.925327818448932, 1.7991061585144992, 15.682099967748258, 3.1359393011589645, 6.858517735117677
    )



# Widened boundaries to allow the AI to discover radical strategies
DNA_BOUNDS = [
    # Safe Strategy (0-6)
    (0, 100), (-100, 0), (0, 10), (0, 10), (0, 20), (0, 10), (0, 15),
    # Aggressive Strategy (7-13)
    (0, 100), (-100, 0), (0, 10), (0, 10), (0, 20), (0, 10), (0, 15),
    # Race Strategy (14-17)
    (0, 100), (-10, 0), (-30, 0), (0, 20),
    # Checker Util (18-21)
    (0, 10), (0, 10), (-5, 5), (-5, 0),
    # Primes & Purity (22-25)
    (0.5, 5.0), (0.0, 10.0), (0.0, 5.0), (0.0, 10.0),
    # Flex & Safety (26-30)
    (0, 10), (0.0, 5.0), (0, 50), (0, 20), (0, 10)
]

def create_random_agent() -> tuple:
    """Creates a 31-element tuple of random weights based on the widened bounds."""
    dna = []
    for bounds in DNA_BOUNDS:
        dna.append(random.uniform(bounds[0], bounds[1]))
    return tuple(dna)

def crossover(parent1: tuple, parent2: tuple) -> tuple:
    """Randomly inherits each gene from either parent 1 or parent 2."""
    child_dna = []
    for i in range(31):
        if random.random() > 0.5:
            child_dna.append(parent1[i])
        else:
            child_dna.append(parent2[i])
    return tuple(child_dna)

def mutate(dna: tuple) -> tuple:
    """Alters genes to introduce new traits, keeping them within valid bounds."""
    mutated_dna = list(dna)
    for i in range(31):
        if random.random() < MUTATION_RATE:
            mutated_dna[i] += random.uniform(-MUTATION_AMOUNT, MUTATION_AMOUNT)
            # Clamp the mutated gene to ensure it doesn't break the logical bounds
            mutated_dna[i] = max(DNA_BOUNDS[i][0], min(DNA_BOUNDS[i][1], mutated_dna[i]))
    return tuple(mutated_dna)

def play_headless_match(dna_1: tuple, dna_2: tuple) -> int:
    """Plays a fast game with no prints. Returns 1 if dna_1 wins, -1 if dna_2 wins."""
    state = init_game()
    
    while True:
        winner = check_winner(state)
        if winner: return winner

        dice = roll_dice()
        
        # If no moves, swap turn immediately
        if not get_legal_moves(state, dice):
            state = GameState(board=state.board, current_turn=-state.current_turn)
            continue
            
        current_dna = dna_1 if state.current_turn == 1 else dna_2
        # Using depth=1 so the background tournament runs incredibly fast
        best_move, _ = get_best_move(state, dice, weights=current_dna)
        
        state = GameState(board=best_move.board, current_turn=-state.current_turn)

def run_evolution():
    print("Initializing Primordial Soup...")
    
    # Seed the population: the first 5 agents are the known good performers, the rest are random
    population = [ADAM_DNA, GEN20_TOP_DNA_RUN1, GEN20_TOP_DNA_RUN2, GEN39_TOP_DNA_RUN2, GEN40_TOP_DNA_RUN2] + [create_random_agent() for _ in range(POPULATION_SIZE - 5)]
    
    # Clear or create the log file at the start of the run
    with open("best_dna_log.txt", "w") as f:
        f.write("--- Backgammon GA Training Log ---\n")
    
    for gen in range(GENERATIONS):
        start_time = time.time()
        print(f"\n=== Starting Generation {gen + 1}/{GENERATIONS} ===")
        scores = {i: 0 for i in range(POPULATION_SIZE)}
        
        # Every agent plays exactly one match against a random opponent
        for idx1 in range(0, POPULATION_SIZE, 2):
            idx2 = idx1 + 1
            agent1_dna = population[idx1]
            agent2_dna = population[idx2]
            
            winner = play_headless_match(agent1_dna, agent2_dna)
            if winner == 1:
                scores[idx1] += 1
            else:
                scores[idx2] += 1
                
        # Rank the population
        ranked_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
        best_agent_idx = ranked_indices[0]
        
        # Keep the top 50%
        survivors = [population[i] for i in ranked_indices[:POPULATION_SIZE // 2]]
        
        # Refill the bottom 50% with children
        new_population = list(survivors)
        while len(new_population) < POPULATION_SIZE:
            parent1 = random.choice(survivors)
            parent2 = random.choice(survivors)
            child = crossover(parent1, parent2)
            child = mutate(child)
            new_population.append(child)
            
        population = new_population
        
        # Save the best DNA of this generation to the text file
        best_dna = survivors[0]
        gen_time = time.time() - start_time
        print(f"Generation {gen + 1} complete in {gen_time:.1f} seconds. Top Score: {scores[best_agent_idx]} win(s)")
        
        with open("best_dna_log.txt", "a") as f:
            f.write(f"\nGeneration {gen + 1} Best DNA:\n")
            f.write(f"{best_dna}\n")

    print("\nEvolution Complete. Check 'best_dna_log.txt' for the results!")

if __name__ == "__main__":
    run_evolution()