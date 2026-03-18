from models import GameState
from actions import check_winner, get_legal_moves
from functools import lru_cache

# 21 unique dice rolls and their mathematical probabilities
DICE_PROBS = [([i, i, i, i], 1/36) for i in range(1, 7)] + \
             [([i, j], 2/36) for i in range(1, 7) for j in range(i + 1, 7)]

# --- Continuous Strategy Weight Profiles ---

STRATEGY_SAFE = {
    'off': 25, 'cap': -50, 'pos': 0.5, 
    'util': 1.0, 'prime_pure': 3.5, 'flex_safety': 1.5, 'free': 3.0
}

STRATEGY_AGGRESSIVE = {
    'off': 25, 'cap': -40, 'pos': 0.5, 
    'util': 1.5, 'prime_pure': 5.0, 'flex_safety': 0.5, 'free': 0.5
}

STRATEGY_RACE = {
    'off': 40, 'pip': -1.5, 'outside': -10, 'spread': 2
}

# --- Heuristic Tuning Constants ---

WIN_SCORE = 10000.0 # Score for winning positions

# Checker Utilization
UTIL_PRIME_ZONE_WEIGHT = 2.0   # Points 4-8
UTIL_MID_ZONE_WEIGHT = 1.0     # Points 9-18
UTIL_DEAD_ZONE_WEIGHT = -0.5   # Points 1-3
UTIL_STACK_PENALTY = -0.8      # Penalty per checker stacked beyond 2

# Primes & Purity
PRIME_EXPONENT = 1.5
PRIME_BLOCKING_MULT = 2.0
PRIME_NON_BLOCKING_MULT = 1.0
PURITY_GAP_PENALTY = 1.5       # Penalty for gaps inside the prime zone

# Flexibility & Safety
FLEX_BASE_WEIGHT = 1.0
FLEX_CLOSENESS_FACTOR = 0.5    # Multiplier for how closely packed occupied points are
SAFETY_DIRECT_THREAT_PENALTY = 10   # Opponent is 1-6 spots away
SAFETY_INDIRECT_THREAT_PENALTY = 1.0 # Opponent is 7-11 spots away
SAFETY_SAFE_BLOT_PENALTY = 0.2       # Unprotected but not actively threatened

# ----------------------------------

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between 'a' and 'b' using parameter 't' (0.0 to 1.0)."""
    return a + (b - a) * t

@lru_cache(maxsize=None)
def get_dynamic_weights(player_pips: int, opp_pips: int) -> dict:
    """Calculates exact, blended weights based on the pip difference."""
    diff = player_pips - opp_pips
    
    # Clamp the difference to a specific range: -20 (ahead) to +20 (behind)
    MAX_DIFF = 20.0
    clamped_diff = max(-MAX_DIFF, min(MAX_DIFF, float(diff)))
    
    # Normalize to a 0.0 to 1.0 scale
    t = (clamped_diff + MAX_DIFF) / (2 * MAX_DIFF)
    
    # Generate the interpolated weights dynamically
    dynamic_weights = {}
    for key in STRATEGY_SAFE:
        dynamic_weights[key] = lerp(STRATEGY_SAFE[key], STRATEGY_AGGRESSIVE[key], t)
        
    return dynamic_weights

def get_captured(board: list[int], p: int) -> int:
    return abs(board[0 if p == 1 else 25])

def get_beared_off(board: list[int], p: int) -> int:
    return abs(board[26 if p == 1 else 27])

def get_position_score(board: list[int], p: int) -> float:
    score = 0
    for i in range(1, 25):
        if board[i] * p > 0:
            progress = i if p == 1 else (25 - i)
            score += progress * abs(board[i])
    return score

def get_outside_checkers(board: list[int], p: int) -> int:
    """Counts how many checkers are left outside the home board."""
    count = 0
    if p == 1:
        for i in range(0, 19):
            if board[i] > 0:
                count += board[i]
    else:
        for i in range(7, 26):
            if board[i] < 0:
                count += abs(board[i])
    return count

def get_home_spread(board: list[int], p: int) -> int:
    """Rewards having checkers distributed across multiple home board points."""
    count = 0
    if p == 1:
        for i in range(19, 25):
            if board[i] > 0:
                count += 1
    else:
        for i in range(1, 7):
            if board[i] < 0:
                count += 1
    return count

def get_contact_scores(board: list[int], player_turn: int) -> tuple[float, float]:
    """
    Single-pass master function. Calculates all contact-game heuristics 
    for BOTH players in exactly one loop through the board.
    Returns: (player_score_raw, opponent_score_raw)
    """
    util = [0.0, 0.0]
    pos = [0.0, 0.0]
    current_chain = [0, 0]
    prime_score = [0.0, 0.0]
    made_points = [[], []]
    occupied_points = [[], []]
    blots = [[], []]
    back_points = [[], []]

    # --- THE SINGLE LOOP ---
    for i in range(1, 26):
        p1_val = board[i] if i <= 24 else 0
        p2_val = -board[i] if i <= 24 else 0
        
        for idx, (count, p, rel_point) in enumerate([(p1_val, 1, i), (p2_val, -1, 25 - i)]):
            if count > 0:
                pos[idx] += rel_point * count
                
                effective_checkers = min(count, 2)
                stacked_checkers = max(0, count - 2)
                if 4 <= rel_point <= 8:
                    util[idx] += effective_checkers * UTIL_PRIME_ZONE_WEIGHT
                elif 9 <= rel_point <= 18:
                    util[idx] += effective_checkers * UTIL_MID_ZONE_WEIGHT
                elif rel_point <= 3:
                    util[idx] += count * UTIL_DEAD_ZONE_WEIGHT
                util[idx] += stacked_checkers * UTIL_STACK_PENALTY
                
                if count >= 2:
                    current_chain[idx] += 1
                    made_points[idx].append(rel_point)
                
                occupied_points[idx].append(rel_point)
                if count == 1:
                    blots[idx].append(i)
                    
                if rel_point >= 19:
                    back_points[idx].append(rel_point)
            
            if count < 2 or i == 25:
                if current_chain[idx] >= 2:
                    is_blocking = False
                    if p == 1:
                        chain_end = i - 1
                        is_blocking = min(board[chain_end:25], default=0) < 0 or board[25] < 0
                    else:
                        chain_start = i - current_chain[idx]
                        is_blocking = max(board[1 : max(1, chain_start)], default=0) > 0 or board[0] > 0
                    
                    prime_score[idx] += (current_chain[idx] ** PRIME_EXPONENT) * (PRIME_BLOCKING_MULT if is_blocking else PRIME_NON_BLOCKING_MULT)
                current_chain[idx] = 0

    # --- POST-LOOP CALCULATIONS ---
    pure_score = [0.0, 0.0]
    flex_score = [0.0, 0.0]
    safety_penalty = [0.0, 0.0]
    free_score = [0.0, 0.0]
    
    for idx, p in enumerate([1, -1]):
        prime_zone = [pt for pt in made_points[idx] if 3 <= pt <= 9]
        if len(prime_zone) >= 2:
            prime_zone.sort()
            for pt in range(prime_zone[0] + 1, prime_zone[-1]):
                if pt not in prime_zone:
                    pure_score[idx] -= PURITY_GAP_PENALTY
                    
        if occupied_points[idx]:
            span = max(occupied_points[idx]) - min(occupied_points[idx])
            closeness = (24 - span) * FLEX_CLOSENESS_FACTOR
            flex_score[idx] = len(occupied_points[idx]) * closeness * FLEX_BASE_WEIGHT
            
        if not back_points[idx]:
            free_score[idx] = 5.0
        else:
            for pt in back_points[idx]:
                free_score[idx] += (25 - pt) * 0.5
            if len(set(back_points[idx])) > 1:
                free_score[idx] += 2.0
                
        for b_idx in blots[idx]:
            is_direct = False
            is_indirect = False
            if p == 1:
                if min(board[b_idx + 1 : min(b_idx + 7, 25)], default=0) < 0: is_direct = True
                elif min(board[min(b_idx + 7, 25) : min(b_idx + 12, 25)], default=0) < 0: is_indirect = True
                if board[25] < 0:
                    dist = 25 - b_idx
                    if dist <= 6: is_direct = True
                    elif 7 <= dist <= 11: is_indirect = True
            else:
                if max(board[max(1, b_idx - 6) : b_idx], default=0) > 0: is_direct = True
                elif max(board[max(1, b_idx - 11) : max(1, b_idx - 6)], default=0) > 0: is_indirect = True
                if board[0] > 0:
                    if b_idx <= 6: is_direct = True
                    elif 7 <= b_idx <= 11: is_indirect = True
            
            if is_direct: safety_penalty[idx] += SAFETY_DIRECT_THREAT_PENALTY
            elif is_indirect: safety_penalty[idx] += SAFETY_INDIRECT_THREAT_PENALTY
            else: safety_penalty[idx] += SAFETY_SAFE_BLOT_PENALTY
            
    p1_stats = {
        'pos': pos[0], 'util': util[0], 'prime_pure': prime_score[0] + pure_score[0], 
        'flex_safety': flex_score[0] - safety_penalty[0], 'free': free_score[0]
    }
    p2_stats = {
        'pos': pos[1], 'util': util[1], 'prime_pure': prime_score[1] + pure_score[1], 
        'flex_safety': flex_score[1] - safety_penalty[1], 'free': free_score[1]
    }
    
    return (p1_stats, p2_stats) if player_turn == 1 else (p2_stats, p1_stats)

def evaluate_state(state: GameState) -> float:
    winner = check_winner(state)
    if winner == state.current_turn:
        return WIN_SCORE
    elif winner is not None: 
        return -WIN_SCORE

    return _evaluate_board_tuple(tuple(state.board), state.current_turn)
    
@lru_cache(maxsize=200000)
def _evaluate_board_tuple(board_tuple: tuple, p: int) -> float:
    board = list(board_tuple) 
    
    player_pips = get_pip_count(board, p)
    opp_pips = get_pip_count(board, -p)

    if is_pure_race(board):
        w = STRATEGY_RACE
        player_score = (w['off'] * get_beared_off(board, p) + 
                        w['pip'] * player_pips + 
                        w['outside'] * get_outside_checkers(board, p) +
                        w['spread'] * get_home_spread(board, p)) 
        
        opp_score = (w['off'] * get_beared_off(board, -p) + 
                     w['pip'] * opp_pips + 
                     w['outside'] * get_outside_checkers(board, -p) +
                     w['spread'] * get_home_spread(board, -p))
                     
        return player_score - opp_score
    else:
        player_stats, opp_stats = get_contact_scores(board, p)
        
        w_player = get_dynamic_weights(player_pips, opp_pips)
        player_score = (w_player['off'] * get_beared_off(board, p) + 
                        w_player['cap'] * get_captured(board, p) + 
                        w_player['pos'] * player_stats['pos'] + 
                        w_player['util'] * player_stats['util'] +
                        w_player['prime_pure'] * player_stats['prime_pure'] +
                        w_player['flex_safety'] * player_stats['flex_safety'] +
                        w_player['free'] * player_stats['free'])
        
        w_opp = get_dynamic_weights(opp_pips, player_pips) 
        opp_score = (w_opp['off'] * get_beared_off(board, -p) + 
                     w_opp['cap'] * get_captured(board, -p) + 
                     w_opp['pos'] * opp_stats['pos'] + 
                     w_opp['util'] * opp_stats['util'] +
                     w_opp['prime_pure'] * opp_stats['prime_pure'] +
                     w_opp['flex_safety'] * opp_stats['flex_safety'] +
                     w_opp['free'] * opp_stats['free'])
        
        return player_score - opp_score

def is_pure_race(board: list[int]) -> bool:
    p1_min = 26
    for i in range(0, 25):
        if board[i] > 0:
            p1_min = i
            break
            
    p2_max = -1
    for i in range(25, 0, -1):
        if board[i] < 0:
            p2_max = i
            break
            
    return p1_min > p2_max

def get_pip_count(board: list[int], p: int) -> int:
    total_pips = 0
    if p == 1:
        for i in range(0, 25):
            if board[i] > 0:
                total_pips += board[i] * (25 - i)
    else:
        for i in range(1, 26):
            if board[i] < 0:
                total_pips += abs(board[i]) * i
    return total_pips

def get_expected_value(move: GameState) -> float:
    """Calculates the fast, 1-ply Expectiminimax value of a single board state."""
    opp_state = GameState(board=move.board, current_turn=-move.current_turn)
    expected_value = 0
    
    # Chance Node: Average all possible opponent dice rolls
    for roll, prob in DICE_PROBS:
        opp_moves = get_legal_moves(opp_state, roll)
        
        if not opp_moves:
            # If opponent is blocked, evaluate from our perspective
            expected_value += prob * evaluate_state(move)
            continue
        
        # MIN Node: Opponent picks their best move
        best_opp_score = float('-inf')
        for opp_move in opp_moves:
            score = evaluate_state(opp_move)
            if score > best_opp_score:
                best_opp_score = score
                
        # Convert opponent's gain into our loss
        expected_value += prob * (-best_opp_score)
        
    return expected_value

def get_best_move(state: GameState, dice: list[int]) -> tuple[GameState, list[tuple[float, GameState]]]:
    """
    Evaluates all legal moves silently using a 1-ply search. 
    Returns: (best_move, list_of_all_evaluated_moves) for frontend processing.
    """
    possible_moves = get_legal_moves(state, dice)
    if not possible_moves:
        return state, [] # No legal moves available
        
    evaluated_moves = []
    for move in possible_moves:
        ev = get_expected_value(move)
        evaluated_moves.append((ev, move))
        
    # Sort descending so the highest expected value is index 0
    evaluated_moves.sort(key=lambda x: x[0], reverse=True)
    
    return evaluated_moves[0][1], evaluated_moves