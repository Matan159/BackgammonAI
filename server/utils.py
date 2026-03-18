from models import GameState
from actions import init_game, roll_dice, get_legal_moves, check_winner
from heuristicsBU import get_best_move, get_expected_value

def print_state(state: GameState):
    b = state.board
    turn_text = "Your turn" if state.current_turn == 1 else "Computer's turn"
    print(f"\n--- {turn_text} ---")
    print(f"P1 Bar: {b[25]}  |  P-1 Bar: {b[0]}")
    print("Top: " + " | ".join(f"{i:02d}: {b[i]:2d}" for i in range(13, 25)))
    print(
        "Bot: " + " | ".join(f"{i:02d}: {b[i]:2d}" for i in range(12, 0, -1)))
    print(f"P1 Off: {b[26]}  |  P-1 Off: {b[27]}\n")


def human_turn(state: GameState, dice: list[int]) -> GameState:
    moves = get_legal_moves(state, dice)
    
    if not moves:
        print("\nNo legal moves available. Skipping turn.")
        return GameState(board=state.board, current_turn=-state.current_turn)

    if len(moves) == 1:
        print("\nOnly 1 legal move available. Auto-playing...")
        print_state(moves[0])
        return GameState(board=moves[0].board, current_turn=-state.current_turn)

    print("\nEvaluating your options...")
    for i, move in enumerate(moves):
        # Calculate the exact same Expectiminimax score the AI sees
        score = get_expected_value(move)
        print(f"\n[{i}] Option (Expected Value: {score:.2f}):")
        print_state(move)

    choice = -1
    while choice not in range(len(moves)):
        try:
            choice = int(input(f"\nSelect move (0-{len(moves)-1}): "))
        except ValueError:
            pass

    return GameState(board=moves[choice].board, current_turn=-state.current_turn)


def run_game():
    state = init_game()
    human_player = 1
    
    starter = "You" if state.current_turn == 1 else "The Computer"
    print(f"\n" + "="*40)
    print(f" GAME START! {starter} will move first.")
    print("="*40 + "\n")

    while True:
        winner = check_winner(state)
        if winner:
            print(f"\nPlayer {winner} wins!")
            break

        dice = roll_dice()
        print_state(state)
        print(f"Dice: {dice}")

        if state.current_turn == human_player:
            state = human_turn(state, dice)
        else:
            print("\nComputer is thinking...")
            best_move, evaluated_moves = get_best_move(state, dice)
            
            if not evaluated_moves:
                print("No legal moves available. Skipping turn.")
                state = GameState(board=state.board, current_turn=-state.current_turn)
                continue
                
            print(f"\n--- Computer evaluated {len(evaluated_moves)} possible moves ---")
            for i, (score, move) in enumerate(evaluated_moves):
                print(f"\n[Computer Option {i}] Expected Value: {score:.2f}")
                print_state(move)
                
            print(f"\n=> Computer chose Option 0 with score {evaluated_moves[0][0]:.2f}")
            state = GameState(board=best_move.board, current_turn=-state.current_turn)


if __name__ == "__main__":
    run_game()