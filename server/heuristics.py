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
def get_dynamic_weights(player_pips: int, opp_pips: int, weights: tuple) -> dict:
    diff = player_pips - opp_pips
    MAX_DIFF = 20.0
    clamped_diff = max(-MAX_DIFF, min(MAX_DIFF, float(diff)))
    t = (clamped_diff + MAX_DIFF) / (2 * MAX_DIFF)
    
    # Map DNA: indices 0-6 are Safe, 7-13 are Aggressive
    keys = ['off', 'cap', 'pos', 'util', 'prime_pure', 'flex_safety', 'free']
    dynamic_weights = {}
    for i, key in enumerate(keys):
        dynamic_weights[key] = lerp(weights[i], weights[i+7], t)
        
    return dynamic_weights

def get_captured(board: list[int], p: int) -> int: return abs(board[0 if p == 1 else 25])
def get_beared_off(board: list[int], p: int) -> int: return abs(board[26 if p == 1 else 27])

def get_position_score(board: list[int], p: int) -> float:
    score = 0
    for i in range(1, 25):
        if board[i] * p > 0:
            score += (i if p == 1 else (25 - i)) * abs(board[i])
    return score

def get_outside_checkers(board: list[int], p: int) -> int:
    count = 0
    if p == 1:
        for i in range(0, 19):
            if board[i] > 0: count += board[i]
    else:
        for i in range(7, 26):
            if board[i] < 0: count += abs(board[i])
    return count

def get_home_spread(board: list[int], p: int) -> int:
    count = 0
    if p == 1:
        for i in range(19, 25):
            if board[i] > 0: count += 1
    else:
        for i in range(1, 7):
            if board[i] < 0: count += 1
    return count

def get_contact_scores(board: list[int], player_turn: int, weights: tuple) -> tuple[float, float]:
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
            for pt in range(prime_zone[0] + 1, prime_zone[-1]):
                if pt not in prime_zone: pure_score[idx] -= pure_gap
                    
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
            
    p1_stats = {'pos': pos[0], 'util': util[0], 'prime_pure': prime_score[0] + pure_score[0], 'flex_safety': flex_score[0] - safety_penalty[0], 'free': free_score[0]}
    p2_stats = {'pos': pos[1], 'util': util[1], 'prime_pure': prime_score[1] + pure_score[1], 'flex_safety': flex_score[1] - safety_penalty[1], 'free': free_score[1]}
    return (p1_stats, p2_stats) if player_turn == 1 else (p2_stats, p1_stats)

def evaluate_state(state: GameState, weights: tuple) -> float:
    winner = check_winner(state)
    if winner == state.current_turn: return WIN_SCORE
    elif winner is not None: return -WIN_SCORE
    return _evaluate_board_tuple(tuple(state.board), state.current_turn, weights)
    
@lru_cache(maxsize=200000)
def _evaluate_board_tuple(board_tuple: tuple, p: int, weights: tuple) -> float:
    board = list(board_tuple) 
    player_pips = get_pip_count(board, p)
    opp_pips = get_pip_count(board, -p)

    if is_pure_race(board):
        r_off, r_pip, r_out, r_spread = weights[14:18]
        p_score = (r_off * get_beared_off(board, p) + r_pip * player_pips + r_out * get_outside_checkers(board, p) + r_spread * get_home_spread(board, p)) 
        o_score = (r_off * get_beared_off(board, -p) + r_pip * opp_pips + r_out * get_outside_checkers(board, -p) + r_spread * get_home_spread(board, -p))
        return p_score - o_score
    else:
        p_stats, o_stats = get_contact_scores(board, p, weights)
        w_p = get_dynamic_weights(player_pips, opp_pips, weights)
        p_score = (w_p['off'] * get_beared_off(board, p) + w_p['cap'] * get_captured(board, p) + sum(w_p[k] * p_stats[k] for k in p_stats))
        
        w_o = get_dynamic_weights(opp_pips, player_pips, weights) 
        o_score = (w_o['off'] * get_beared_off(board, -p) + w_o['cap'] * get_captured(board, -p) + sum(w_o[k] * o_stats[k] for k in o_stats))
        return p_score - o_score

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
            if board[i] > 0: total_pips += board[i] * (25 - i)
    else:
        for i in range(1, 26):
            if board[i] < 0: total_pips += abs(board[i]) * i
    return total_pips

def get_expected_value(move: GameState, weights: tuple) -> float:
    opp_state = GameState(board=move.board, current_turn=-move.current_turn)
    expected_value = 0
    
    for roll, prob in DICE_PROBS:
        opp_moves = get_legal_moves(opp_state, roll)
        if not opp_moves:
            expected_value += prob * evaluate_state(move, weights)
            continue
        
        best_opp_score = float('-inf')
        for opp_move in opp_moves:
            score = evaluate_state(opp_move, weights)
            if score > best_opp_score: best_opp_score = score
        expected_value += prob * (-best_opp_score)
        
    return expected_value

def get_best_move(state: GameState, dice: list[int], weights: tuple) -> tuple[GameState, list[tuple[float, GameState]]]:
    possible_moves = get_legal_moves(state, dice)
    if not possible_moves: return state, []
        
    evaluated_moves = []
    for move in possible_moves:
        ev = get_expected_value(move, weights)
        evaluated_moves.append((ev, move))
        
    evaluated_moves.sort(key=lambda x: x[0], reverse=True)
    return evaluated_moves[0][1], evaluated_moves