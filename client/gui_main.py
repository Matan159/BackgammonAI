import pygame
import sys
import os
import random 
import copy 

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
server_dir = os.path.join(parent_dir, "server")
sys.path.append(server_dir)

from actions import init_game, roll_dice, get_legal_moves 
from heuristics import get_best_move
from renderer import Renderer
from input_handler import InputHandler

ADAM_DNA = (
    40.0, -50.0, 0.5, 1.0, 3.5, 1.5, 3.0, 
    40.0, -40.0, 0.5, 1.5, 5.0, 0.5, 0.5, 
    40.0, -1.5, -10.0, 2.0, 2.0, 1.0, -0.5, -0.8, 
    1.5, 2.0, 1.0, 1.5, 1.0, 0.5, 15.0, 1.0, 0.2
)

GEN150SWISS_DNA = (37.43753781382364, -47.765830142695386, 0.3747430920532817, 1.3382554236291975, 3.6133831731925743, 1.5319756954712047, 1.66156654842285, 40.95355108891252, -39.42628439543213, 0, 2.1394699179247234, 5.880416444147361, 0.7391095990249441, 0.29437310194315636, 39.64942923896567, -1.5599547313901485, -10.0, 1.791496701182991, 2.0, 0, -0.6087619474760084, -0.8049597225550622, 0.8000865077479294, 2.0, 1.4132407561394085, 0.3412313221860206, 0, 1.6314553496938662, 15.542179970828627, 1.0, 0)

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

# --- All UI Buttons ---
BUTTON_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 125, WINDOW_HEIGHT // 2 - 30, 250, 60)
CANCEL_BUTTON_RECT = pygame.Rect(20, WINDOW_HEIGHT - 60, 120, 40)
PLAY_BUTTON_RECT = pygame.Rect(WINDOW_WIDTH - 140, WINDOW_HEIGHT - 60, 120, 40)
LOBBY_BUTTON_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 125, WINDOW_HEIGHT // 2 + 80, 250, 60)
OK_BUTTON_RECT = pygame.Rect(WINDOW_WIDTH // 2 - 75, WINDOW_HEIGHT // 2 + 30, 150, 50)

def frontend_check_winner(game_state):
    p1_active = sum(game_state.board[i] for i in range(0, 25) if game_state.board[i] > 0)
    p2_active = sum(abs(game_state.board[i]) for i in range(1, 26) if game_state.board[i] < 0)
    if p1_active == 0: return 1
    if p2_active == 0: return -1
    return 0

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("AI Backgammon - Match Mode")
    clock = pygame.time.Clock()
    
    renderer = Renderer(width=WINDOW_WIDTH, height=WINDOW_HEIGHT, style="wood")
    input_handler = InputHandler()
    
    # --- MATCH VARIABLES ---
    human_score = 0
    adam_score = 0
    last_winner = 0
    
    game_state = init_game()
    available_dice = []
    visual_dice = []
    turn_history = [] 
    
    ui_state = "MATCH_LOBBY" # Start in the lobby, not on the board!
    anim_timer = 0
    is_first_turn = True
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        # 1. Check for Winner (Only if we are actually playing a game)
        if ui_state not in ["MATCH_LOBBY", "GAME_OVER_POPUP"]:
            winner = frontend_check_winner(game_state)
            if winner in [1, -1]:
                if winner == 1: human_score += 1
                else: adam_score += 1
                last_winner = winner
                ui_state = "GAME_OVER_POPUP"
            
        # 2. Process Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                
                # Lobby: Start Game
                if ui_state == "MATCH_LOBBY" and LOBBY_BUTTON_RECT.collidepoint(mouse_pos):
                    # WIPE EVERYTHING CLEAN FOR A NEW GAME
                    game_state = init_game()
                    available_dice = []
                    visual_dice = []
                    turn_history = []
                    is_first_turn = True
                    ui_state = "START"
                    
                # Popup: OK Button
                elif ui_state == "GAME_OVER_POPUP" and OK_BUTTON_RECT.collidepoint(mouse_pos):
                    ui_state = "MATCH_LOBBY"
                
                # Main Center Button
                elif BUTTON_RECT.collidepoint(mouse_pos):
                    if ui_state == "START":
                        ui_state = "START_ROLL"
                        anim_timer = 90
                    elif ui_state == "HUMAN_ROLL":
                        ui_state = "ANIMATING_ROLL"
                        anim_timer = 90 
                
                # Corner Buttons
                elif ui_state == "PLAYING" and game_state.current_turn == 1:
                    if turn_history and CANCEL_BUTTON_RECT.collidepoint(mouse_pos):
                        last_board, last_dice = turn_history.pop()
                        game_state.board = list(last_board)
                        available_dice.clear()
                        available_dice.extend(last_dice)
                        input_handler.dragging_piece = None 
                        
                    safe_state = copy.deepcopy(game_state)
                    human_can_end = not available_dice or not get_legal_moves(safe_state.board, safe_state.current_turn, list(available_dice))
                    
                    if human_can_end and PLAY_BUTTON_RECT.collidepoint(mouse_pos):
                        game_state.current_turn = -1
                        is_first_turn = False
                        ui_state = "AI_ROLL"
                        anim_timer = 90
                        turn_history.clear() 
            
            # Drag and Drop
            if ui_state == "PLAYING" and game_state.current_turn == 1:
                input_handler.handle_event(event, game_state, renderer, available_dice, turn_history)
                
        # 3. STATE LOGIC
        if ui_state == "START_ROLL":
            visual_dice = [random.randint(1, 6), random.randint(1, 6)]
            anim_timer -= 1
            if anim_timer <= 0:
                while visual_dice[0] == visual_dice[1]:
                    visual_dice = [random.randint(1, 6), random.randint(1, 6)]
                game_state.current_turn = 1 if visual_dice[0] > visual_dice[1] else -1
                if game_state.current_turn == 1:
                    ui_state = "HUMAN_ROLL"
                else:
                    ui_state = "AI_ROLL"
                    anim_timer = 120 
                visual_dice = []
                
        elif ui_state in ["ANIMATING_ROLL", "AI_ROLL"]:
            visual_dice = [random.randint(1, 6), random.randint(1, 6)]
            anim_timer -= 1
            if anim_timer <= 0:
                available_dice = roll_dice()
                visual_dice = available_dice
                ui_state = "PLAYING"
                
        elif ui_state == "PLAYING" and game_state.current_turn == -1:
            if not available_dice:
                game_state.current_turn = 1
                is_first_turn = False
                ui_state = "HUMAN_ROLL"
            else:
                # 1. Calculate the legal moves exactly once
                possible_moves = get_legal_moves(game_state.board, game_state.current_turn, list(available_dice))
                
                # 2. Check if Adam is blocked
                if not possible_moves:
                    ui_state = "NO_MOVES"
                    anim_timer = 120
                else:
                    # 3. Pass the calculated moves into get_best_move (no longer takes dice directly!)
                    best_state, _ = get_best_move(game_state, possible_moves, weights=ADAM_DNA)
                    game_state = best_state
                    available_dice = []

        elif ui_state == "NO_MOVES":
            visual_dice = available_dice 
            anim_timer -= 1
            if anim_timer <= 0:
                available_dice = [] 
                ui_state = "PLAYING"
                
        # 4. RENDERING LAYER
        if ui_state == "MATCH_LOBBY":
            # Draw the Lobby Screen
            renderer.draw_match_lobby(screen, human_score, adam_score)
            renderer.draw_button(screen, "Start Game", LOBBY_BUTTON_RECT, LOBBY_BUTTON_RECT.collidepoint(mouse_pos))
        else:
            # Draw the Game Board
            renderer.render_frame(screen, game_state, input_handler, visual_dice)
            
            # Draw UI Overlays on top of the board
            is_main_hovered = BUTTON_RECT.collidepoint(mouse_pos)
            status_msg = ""
            
            if ui_state == "GAME_OVER_POPUP":
                renderer.draw_game_over_popup(screen, last_winner)
                renderer.draw_button(screen, "OK", OK_BUTTON_RECT, OK_BUTTON_RECT.collidepoint(mouse_pos))
            else:
                if ui_state == "START":
                    renderer.draw_button(screen, "Roll Who Starts", BUTTON_RECT, is_main_hovered)
                elif ui_state == "HUMAN_ROLL":
                    renderer.draw_button(screen, "Roll Dice", BUTTON_RECT, is_main_hovered)
                    status_msg = "You won the starting roll!" if is_first_turn else "Your turn to roll."
                elif ui_state == "AI_ROLL":
                    status_msg = "Adam won the starting roll!" if is_first_turn else "Adam's turn to roll."
                elif ui_state == "ANIMATING_ROLL":
                    status_msg = "Rolling..."
                elif ui_state == "PLAYING":
                    if game_state.current_turn == 1:
                        safe_state = copy.deepcopy(game_state)
                        human_can_end = not available_dice or not get_legal_moves(game_state.board, game_state.current_turn, list(available_dice))
                        
                        if not available_dice: status_msg = "Moves finished. Click 'Play' to end turn."
                        elif human_can_end: status_msg = "No legal moves remain! Click 'Play' to skip."
                        else: status_msg = "Your turn: Make your moves."
                            
                        if turn_history: renderer.draw_button(screen, "Cancel", CANCEL_BUTTON_RECT, CANCEL_BUTTON_RECT.collidepoint(mouse_pos))
                        if human_can_end: renderer.draw_button(screen, "Play", PLAY_BUTTON_RECT, PLAY_BUTTON_RECT.collidepoint(mouse_pos))
                    else:
                        status_msg = "Adam is playing..."
                elif ui_state == "NO_MOVES":
                    status_msg = "Adam has no possible moves! Turn skipped."

                renderer.draw_status_message(screen, status_msg)
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()