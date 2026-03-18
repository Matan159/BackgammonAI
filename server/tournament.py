import time
from models import GameState
from actions import init_game, roll_dice, check_winner, get_legal_moves
from heuristics import get_best_move

# Your hand-crafted baseline
ADAM_DNA = (
    40.0, -50.0, 0.5, 1.0, 3.5, 1.5, 3.0, 
    40.0, -40.0, 0.5, 1.5, 5.0, 0.5, 0.5, 
    40.0, -1.5, -10.0, 2.0, 2.0, 1.0, -0.5, -0.8, 
    1.5, 2.0, 1.0, 1.5, 1.0, 0.5, 15.0, 1.0, 0.2
)

# The ultimate winner from Run 3, Generation 70
GEN70_DNA = (
    18.847880015284428, -74.81219862276485, 8.387039378264834, 9.533345817044353, 
    20, 0.8412882359712837, 2.6617594630315877, 16.28758477357009, -26.410852862649218, 
    3.3878763894338966, 0.6910940469782425, 17.540537939529173, 2.935921981605652, 
    7.558428651900881, 62.837770873530786, -7.035821081134346, -9.673201835130772, 
    0, 2.7075455850314807, 6.8966028597014155, -1.149809114074207, -1.168205407298458, 
    2.9706612627538664, 8.521248865051552, 0.7599706384912608, 2.55537539463229, 
    4.285359956372804, 2.5171846285117345, 23.242778558222692, 0.8465189451402619, 
    0.6888440889948981
)

TOTAL_GAMES = 50

def play_tournament_match(adam_is_p1: bool) -> str:
    """Plays a single match. adam_is_p1 determines if Adam goes first."""
    state = init_game()
    
    while True:
        winner = check_winner(state)
        if winner == 1:
            return "Adam" if adam_is_p1 else "Gen70"
        elif winner == -1:
            return "Gen70" if adam_is_p1 else "Adam"

        dice = roll_dice()
        
        # Pass turn if no legal moves
        if not get_legal_moves(state, dice):
            state = GameState(board=state.board, current_turn=-state.current_turn)
            continue
            
        # Dynamically assign the correct DNA based on the current turn and who is P1
        if state.current_turn == 1:
            current_dna = ADAM_DNA if adam_is_p1 else GEN70_DNA
        else:
            current_dna = GEN70_DNA if adam_is_p1 else ADAM_DNA
            
        best_move, _ = get_best_move(state, dice, weights=current_dna)
        state = GameState(board=best_move.board, current_turn=-state.current_turn)

def run_tournament():
    print(f"--- Starting {TOTAL_GAMES}-Game Tournament: Adam vs. Gen70 ---")
    adam_wins = 0
    gen70_wins = 0
    start_time = time.time()
    
    for game in range(1, TOTAL_GAMES + 1):
        # Alternate who plays as Player 1 (White) to ensure a perfectly fair fight
        adam_is_p1 = (game % 2 != 0)
        
        winner = play_tournament_match(adam_is_p1)
        
        if winner == "Adam":
            adam_wins += 1
        else:
            gen70_wins += 1
            
        print(f"Game {game}/{TOTAL_GAMES} complete. Winner: {winner} | Score: Adam {adam_wins} - {gen70_wins} Gen70")
        
    total_time = time.time() - start_time
    print("\n=== TOURNAMENT COMPLETE ===")
    print(f"Total Time: {total_time / 60:.1f} minutes")
    print(f"Final Score: Adam {adam_wins} | Gen70 {gen70_wins}")
    
    if gen70_wins > adam_wins:
        print("Result: Machine Learning successfully conquered the baseline!")
    elif adam_wins > gen70_wins:
        print("Result: Adam defended his title!")
    else:
        print("Result: It's a dead tie!")

if __name__ == "__main__":
    run_tournament()