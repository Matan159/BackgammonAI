import random
from typing import Optional
from models import GameState

def init_game(starting_player: Optional[int] = None) -> GameState:
    board = [0] * 28

    # Player 1 (positive)
    board[1], board[12], board[17], board[19] = 2, 5, 3, 5
    # Player 2 (negative)
    board[24], board[13], board[8], board[6] = -2, -5, -3, -5

    if starting_player is None:
        starting_player = random.choice([1, -1])

    return GameState(board=board, current_turn=starting_player)


def roll_dice() -> list[int]:
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return [d1, d1, d1, d1] if d1 == d2 else [d1, d2]

def can_bear_off(board: list[int], p: int) -> bool:
    # Home board check + ensures no pieces are stuck on the bar
    if p == 1:
        return not any(board[i] > 0 for i in range(0, 19)) and board[25] <= 0
    else:
        return not any(board[i] < 0 for i in range(7, 26)) and board[0] >= 0


def get_legal_moves(state: GameState, dice: list[int]) -> list[GameState]:
    single_moves = get_single_moves(state, dice)
    if not single_moves:
        return []
        
    all_combinations = get_move_combinations(single_moves)
    
    # 1. Backgammon rule: Must play the maximum number of dice possible
    min_rem_len = min(len(rem) for _, rem in all_combinations)
    valid_combos = [(st, rem) for st, rem in all_combinations if len(rem) == min_rem_len]
    
    # 2. Backgammon rule: If only one die can be played, you MUST play the higher number
    if min_rem_len > 0:
        # The smaller the sum of remaining dice, the larger the die that was played
        min_rem_sum = min(sum(rem) for _, rem in valid_combos)
        valid_combos = [(st, rem) for st, rem in valid_combos if sum(rem) == min_rem_sum]
        
    unique_boards = set()
    best_moves = []
    for st, _ in valid_combos:
        board_tuple = tuple(st.board)
        if board_tuple not in unique_boards:
            unique_boards.add(board_tuple)
            best_moves.append(st)
            
    return best_moves

def get_single_moves(state: GameState, dice: list[int]) -> list[tuple[GameState, list[int]]]:
    moves_list = []
    p = state.current_turn
    bar_idx = 0 if p == 1 else 25
    
    points_to_check = [bar_idx] if state.board[bar_idx] * p > 0 else range(1, 25)
    bearing_off = can_bear_off(state.board, p)

    for i in points_to_check:
        if state.board[i] * p > 0:
            for die in set(dice):
                target = i + (die * p)
                
                # 1. Normal Move
                if 1 <= target <= 24:
                    if state.board[target] * p >= -1:
                        new_board = list(state.board)
                        new_board[i] -= p
                        
                        if new_board[target] * p == -1: 
                            new_board[target] = p
                            opponent_bar = 25 if p == 1 else 0
                            new_board[opponent_bar] -= p
                        else:
                            new_board[target] += p
                            
                        new_dice = list(dice)
                        new_dice.remove(die)
                        moves_list.append((GameState(board=new_board, current_turn=p), new_dice))
                        
                # 2. Bearing Off
                elif bearing_off:
                    is_exact = (target == 25 if p == 1 else target == 0)
                    valid = is_exact
                    
                    if not valid:
                        # Allow overshoot only if there are no pieces behind it
                        if p == 1 and target > 25:
                            valid = not any(state.board[k] > 0 for k in range(19, i))
                        elif p == -1 and target < 0:
                            valid = not any(state.board[k] < 0 for k in range(i + 1, 7))
                            
                    if valid:
                        new_board = list(state.board)
                        new_board[i] -= p
                        off_idx = 26 if p == 1 else 27
                        new_board[off_idx] += p
                        
                        new_dice = list(dice)
                        new_dice.remove(die)
                        moves_list.append((GameState(board=new_board, current_turn=p), new_dice))
                        
    return moves_list

def get_move_combinations(moves_list: list[tuple[GameState, list[int]]]) -> list[tuple[GameState, list[int]]]:
    final_turns = []
    for state, remaining_dice in moves_list:
        if not remaining_dice:
            final_turns.append((state, []))
        else:
            next_moves = get_single_moves(state, remaining_dice)
            if not next_moves:
                final_turns.append((state, remaining_dice))
            else:
                final_turns.extend(get_move_combinations(next_moves))
    return final_turns

def apply_move(state: GameState, move: GameState) -> GameState:
    # In this simplified version, we assume the move is already validated
    return GameState(board=move.board, current_turn=-state.current_turn)


def check_winner(state: GameState) -> Optional[int]:
    if state.board[26] == 15:  # Player 1 wins
        return 1
    elif state.board[27] == -15:  # Player 2 wins
        return -1
    return None

def select_move_randomly(state: GameState, dice: list[int]) -> Optional[GameState]:
    legal_moves = get_legal_moves(state, dice)
    return random.choice(legal_moves) if legal_moves else None
