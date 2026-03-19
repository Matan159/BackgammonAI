import pygame
from actions import validate_single_move

class InputHandler:
    def __init__(self):
        self.dragging_piece = None 
        
    def get_point_at_pixels(self, x, y, renderer):
        # Bear-Off trays on the right edge
        if x > renderer.width - 60:
            if y < renderer.height / 2:
                return 25  # Top right: Human (Player 1) bears off
            else:
                return 0   # Bottom right: Adam (Player -1) bears off
                
        if not renderer.board_rect.collidepoint(x, y):
            return None
            
        usable_x = x - renderer.board_rect.left
        
        # Define the exact pixel boundaries of the middle bar
        bar_left = (renderer.board_rect.width / 2) - (renderer.bar_width / 2)
        bar_right = (renderer.board_rect.width / 2) + (renderer.bar_width / 2)
        
        if bar_left <= usable_x <= bar_right:
            return 25 if y < (renderer.height / 2) else 0 
            
        if usable_x > bar_right:
            usable_x -= renderer.bar_width
            
        visual_index = int(usable_x // renderer.point_width)
        visual_index = min(visual_index, 11)
            
        is_top = y < (renderer.height / 2)
        
        if is_top:
            return visual_index + 13
        else:
            return 12 - visual_index

    # --- FIX: turn_history added to the arguments here ---
    def handle_event(self, event, game_state, renderer, available_dice, turn_history=None):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            clicked_point = self.get_point_at_pixels(x, y, renderer)
            
            if clicked_point is not None and game_state.board[clicked_point] != 0:
                player = 1 if game_state.board[clicked_point] > 0 else -1
                
                if player == game_state.current_turn:
                    bar_idx = 0 if player == 1 else 25
                    
                    if game_state.board[bar_idx] != 0 and clicked_point != bar_idx:
                        print("You must move your captured pieces off the bar first!")
                        return 
                    
                    game_state.board[clicked_point] -= player
                    self.dragging_piece = {
                        'from_index': clicked_point,
                        'player': player,
                        'x': x,
                        'y': y
                    }
                
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_piece:
                self.dragging_piece['x'], self.dragging_piece['y'] = event.pos
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_piece:
                x, y = event.pos
                drop_point = self.get_point_at_pixels(x, y, renderer)
                original_point = self.dragging_piece['from_index']
                player = self.dragging_piece['player']
                
                game_state.board[original_point] += player
                
                is_valid = False
                
                if drop_point is not None and available_dice:
                    is_valid, new_board, new_dice, used_die = validate_single_move(
                        game_state, original_point, drop_point, available_dice
                    )
                
                if is_valid:
                    # Save a snapshot to the undo stack
                    if turn_history is not None:
                        turn_history.append((list(game_state.board), list(available_dice)))
                        
                    game_state.board = new_board
                    available_dice.clear()
                    available_dice.extend(new_dice)
                    print(f"Valid Move! Used die: {used_die}. Remaining dice: {available_dice}")
                
                self.dragging_piece = None