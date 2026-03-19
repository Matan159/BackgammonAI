from models import GameState
from actions import check_winner, get_legal_moves
from functools import lru_cache

# 21 unique dice rolls and their mathematical probabilities
DICE_PROBS = [([i, i, i, i], 1/36) for i in range(1, 7)] + \
             [([i, j], 2/36) for i in range(1, 7) for j in range(i + 1, 7)]

WIN_SCORE = 10000.0 # Stays hardcoded to guarantee victory prioritizing

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

@lru_cache(maxsize=None)
def get_dynamic_weights(player_pips: int, opp_pips: int, weights: tuple) -> tuple:
    diff = player_pips - opp_pips
    MAX_DIFF = 20.0
    clamped_diff = max(-MAX_DIFF, min(MAX_DIFF, float(diff)))
    t = (clamped_diff + MAX_DIFF) / (2 * MAX_DIFF)
    
    return (
        lerp(weights[0], weights[7], t),  # off
        lerp(weights[1], weights[8], t),  # cap
        lerp(weights[2], weights[9], t),  # pos
        lerp(weights[3], weights[10], t), # util
        lerp(weights[4], weights[11], t), # prime_pure
        lerp(weights[5], weights[12], t), # flex_safety
        lerp(weights[6], weights[13], t)  # free
    )

def get_captured(board: tuple, p: int) -> int: return abs(board[0 if p == 1 else 25])
def get_beared_off(board: tuple, p: int) -> int: return abs(board[26 if p == 1 else 27])

def get_outside_checkers(board: tuple, p: int) -> int:
    count = 0
    if p == 1:
        for i in range(0, 19):
            if board[i] > 0: count += board[i]
    else:
        for i in range(7, 26):
            if board[i] < 0: count += abs(board[i])
    return count

def get_home_spread(board: tuple, p: int) -> int:
    count = 0
    if p == 1:
        for i in range(19, 25):
            if board[i] > 0: count += 1
    else:
        for i in range(1, 7):
            if board[i] < 0: count += 1
    return count

def get_contact_scores(board: tuple, player_turn: int, weights: tuple) -> tuple[tuple, tuple]:
     # Extract weights from DNA
    util_prime, util_mid, util_dead, util_stack = weights[18:22]
    prime_exp, prime_block, prime_non, pure_gap = weights[22:26]
    flex_base, flex_close, safe_dir, safe_indir, safe_blot = weights[26:31]

    util = [0.0, 0.0]
    pos = [0.0, 0.0]
    current_chain = [0, 0]
    prime_score = [0.0, 0.0]
    made_points = [[], []]
    occupied_points = [[], []]
    blots = [[], []]
    back_points = [[], []]

    for i in range(1, 26):
        p1_val = board[i] if i <= 24 else 0
        p2_val = -board[i] if i <= 24 else 0
        
        for idx, (count, p, rel_point) in enumerate([(p1_val, 1, i), (p2_val, -1, 25 - i)]):
            if count > 0:
                pos[idx] += rel_point * count
                eff = min(count, 2)
                stacked = max(0, count - 2)
                
                if 4 <= rel_point <= 8: util[idx] += eff * util_prime
                elif 9 <= rel_point <= 18: util[idx] += eff * util_mid
                elif rel_point <= 3: util[idx] += count * util_dead
                util[idx] += stacked * util_stack
                
                if count >= 2:
                    current_chain[idx] += 1
                    made_points[idx].append(rel_point)
                
                occupied_points[idx].append(rel_point)
                if count == 1: blots[idx].append(i)
                if rel_point >= 19: back_points[idx].append(rel_point)
            
            if count < 2 or i == 25:
                if current_chain[idx] >= 2:
                    is_blocking = False
                    if p == 1: is_blocking = min(board[i-1:25], default=0) < 0 or board[25] < 0
                    else: is_blocking = max(board[1:max(1, i-current_chain[idx])], default=0) > 0 or board[0] > 0
                    prime_score[idx] += (current_chain[idx] ** prime_exp) * (prime_block if is_blocking else prime_non)
                current_chain[idx] = 0

    pure_score = [0.0, 0.0]
    flex_score = [0.0, 0.0]
    safety_penalty = [0.0, 0.0]
    free_score = [0.0, 0.0]
    
    for idx, p in enumerate([1, -1]):
        prime_zone = [pt for pt in made_points[idx] if 3 <= pt <= 9]
        if len(prime_zone) >= 2:
            prime_zone.sort()
            prime_zone_set = set(prime_zone) 
            for pt in range(prime_zone[0] + 1, prime_zone[-1]):
                if pt not in prime_zone_set: pure_score[idx] -= pure_gap
                    
        if occupied_points[idx]:
            span = max(occupied_points[idx]) - min(occupied_points[idx])
            flex_score[idx] = len(occupied_points[idx]) * ((24 - span) * flex_close) * flex_base
            
        if not back_points[idx]: free_score[idx] = 5.0
        else:
            for pt in back_points[idx]: free_score[idx] += (25 - pt) * 0.5
            if len(set(back_points[idx])) > 1: free_score[idx] += 2.0
                
        for b_idx in blots[idx]:
            is_dir = is_indir = False
            if p == 1:
                if min(board[b_idx+1:min(b_idx+7, 25)], default=0) < 0: is_dir = True
                elif min(board[min(b_idx+7, 25):min(b_idx+12, 25)], default=0) < 0: is_indir = True
                if board[25] < 0:
                    d = 25 - b_idx
                    if d <= 6: is_dir = True
                    elif 7 <= d <= 11: is_indir = True
            else:
                if max(board[max(1, b_idx-6):b_idx], default=0) > 0: is_dir = True
                elif max(board[max(1, b_idx-11):max(1, b_idx-6)], default=0) > 0: is_indir = True
                if board[0] > 0:
                    if b_idx <= 6: is_dir = True
                    elif 7 <= b_idx <= 11: is_indir = True
            
            if is_dir: safety_penalty[idx] += safe_dir
            elif is_indir: safety_penalty[idx] += safe_indir
            else: safety_penalty[idx] += safe_blot
            
    # Return raw fast tuples instead of dictionaries
    p1_stats = (pos[0], util[0], prime_score[0] + pure_score[0], flex_score[0] - safety_penalty[0], free_score[0])
    p2_stats = (pos[1], util[1], prime_score[1] + pure_score[1], flex_score[1] - safety_penalty[1], free_score[1])
    return (p1_stats, p2_stats) if player_turn == 1 else (p2_stats, p1_stats)

def evaluate_state(state: GameState, weights: tuple) -> float:
    # Inline the winner check to avoid jumping out to check_winner() millions of times
    if state.board[26] == 15:
        return WIN_SCORE if state.current_turn == 1 else -WIN_SCORE
    elif state.board[27] == -15:
        return WIN_SCORE if state.current_turn == -1 else -WIN_SCORE
        
    return _evaluate_board_tuple(tuple(state.board), state.current_turn, weights)
    
@lru_cache(maxsize=None)
def _evaluate_board_tuple(board_tuple: tuple, p: int, weights: tuple) -> float:
    # No longer casting board_tuple to list() - passing it directly!
    player_pips, opp_pips = get_both_pip_counts(board_tuple, p)

    if is_pure_race(board_tuple):
        r_off, r_pip, r_out, r_spread = weights[14:18]
        p_score = (r_off * get_beared_off(board_tuple, p) + r_pip * player_pips + r_out * get_outside_checkers(board_tuple, p) + r_spread * get_home_spread(board_tuple, p)) 
        o_score = (r_off * get_beared_off(board_tuple, -p) + r_pip * opp_pips + r_out * get_outside_checkers(board_tuple, -p) + r_spread * get_home_spread(board_tuple, -p))
        return p_score - o_score
    else:
        p_stats, o_stats = get_contact_scores(board_tuple, p, weights)
        
        w_p_off, w_p_cap, w_p_pos, w_p_util, w_p_prime, w_p_flex, w_p_free = get_dynamic_weights(player_pips, opp_pips, weights)
        p_pos, p_util, p_prime, p_flex, p_free = p_stats
        
        p_score = (
            w_p_off * get_beared_off(board_tuple, p) + 
            w_p_cap * get_captured(board_tuple, p) + 
            w_p_pos * p_pos + 
            w_p_util * p_util + 
            w_p_prime * p_prime + 
            w_p_flex * p_flex + 
            w_p_free * p_free
        )
        
        w_o_off, w_o_cap, w_o_pos, w_o_util, w_o_prime, w_o_flex, w_o_free = get_dynamic_weights(opp_pips, player_pips, weights)
        o_pos, o_util, o_prime, o_flex, o_free = o_stats
        
        o_score = (
            w_o_off * get_beared_off(board_tuple, -p) + 
            w_o_cap * get_captured(board_tuple, -p) + 
            w_o_pos * o_pos + 
            w_o_util * o_util + 
            w_o_prime * o_prime + 
            w_o_flex * o_flex + 
            w_o_free * o_free
        )
        
        return p_score - o_score

def is_pure_race(board: tuple) -> bool:
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

def get_both_pip_counts(board: tuple, p: int) -> tuple[int, int]:
    # Single fused loop array traversal for both players
    p1_pips = 0
    p2_pips = 0
    for i in range(1, 25):
        val = board[i]
        if val > 0: p1_pips += val * (25 - i)
        elif val < 0: p2_pips += (-val) * i
        
    if board[0] > 0: p1_pips += board[0] * 25
    if board[25] < 0: p2_pips += (-board[25]) * 25
    
    return (p1_pips, p2_pips) if p == 1 else (p2_pips, p1_pips)

def get_expected_value(move: GameState, weights: tuple) -> float:
    expected_value = 0
    base_eval = None 
    opp_turn = -move.current_turn
    
    for roll, prob in DICE_PROBS:
        # Pass raw board and turn directly to skip GameState instantiation
        opp_moves = get_legal_moves(move.board, opp_turn, roll)
        
        if not opp_moves:
            if base_eval is None:
                base_eval = evaluate_state(move, weights)
            expected_value += prob * base_eval
            continue
        
        best_opp_score = float('-inf')
        for opp_move in opp_moves:
            score = evaluate_state(opp_move, weights)
            if score > best_opp_score: best_opp_score = score
        expected_value += prob * (-best_opp_score)
        
    return expected_value

def get_best_move(state: GameState, possible_moves: list[GameState], weights: tuple) -> tuple[GameState, list]:    
    if not possible_moves: 
        return state, []
        
    best_move = max(possible_moves, key=lambda move: get_expected_value(move, weights))
    return best_move, []