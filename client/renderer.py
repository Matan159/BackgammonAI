import pygame

PALETTES = {
    "wood": {
        "bg": (133, 94, 66),
        "point_light": (210, 180, 140),
        "point_dark": (101, 67, 33),
        "bar": (80, 50, 20),
        "border": (60, 30, 10),
        "p1_checker": (245, 245, 220), # Ivory White
        "p2_checker": (30, 30, 30)     # Ebony Black
    },
    "modern": {
        "bg": (240, 240, 240), "point_light": (200, 200, 200), "point_dark": (50, 50, 50),
        "bar": (100, 100, 100), "border": (30, 30, 30),
        "p1_checker": (255, 255, 255), "p2_checker": (0, 0, 0)
    },
    "casino": {
        "bg": (34, 139, 34), "point_light": (245, 245, 220), "point_dark": (139, 0, 0), 
        "bar": (20, 80, 20), "border": (101, 67, 33),
        "p1_checker": (255, 255, 255), "p2_checker": (20, 20, 20)
    }
}

class Renderer:
    def __init__(self, width=1000, height=700, style="wood"):
        self.width = width
        self.height = height
        self.colors = PALETTES[style]
        self.board_rect = pygame.Rect(50, 50, width - 100, height - 100)
        self.bar_width = 50
        
        # Calculate sizing for the points and checkers
        usable_width = self.board_rect.width - self.bar_width
        self.point_width = usable_width // 12
        self.point_height = self.board_rect.height * 0.42 
        self.checker_radius = int((self.point_width / 2) * 0.8)

        # Initialize font for dice
        pygame.font.init()
        self.font = pygame.font.SysFont(None, 36)
        
    def draw_background(self, screen):
        screen.fill(self.colors["border"])
        pygame.draw.rect(screen, self.colors["bg"], self.board_rect)
        
        bar_x = self.width // 2 - self.bar_width // 2
        bar_rect = pygame.Rect(bar_x, 50, self.bar_width, self.height - 100)
        pygame.draw.rect(screen, self.colors["bar"], bar_rect)

    def draw_points(self, screen):
        for i in range(12):
            x_offset = self.board_rect.left + (i * self.point_width)
            if i >= 6:
                x_offset += self.bar_width
                
            c1 = self.colors["point_dark"] if i % 2 == 0 else self.colors["point_light"]
            c2 = self.colors["point_light"] if i % 2 == 0 else self.colors["point_dark"]
            
            bottom_points = [(x_offset, self.board_rect.bottom), (x_offset + self.point_width, self.board_rect.bottom), (x_offset + self.point_width / 2, self.board_rect.bottom - self.point_height)]
            pygame.draw.polygon(screen, c1, bottom_points)
            
            top_points = [(x_offset, self.board_rect.top), (x_offset + self.point_width, self.board_rect.top), (x_offset + self.point_width / 2, self.board_rect.top + self.point_height)]
            pygame.draw.polygon(screen, c2, top_points)

    def draw_checkers(self, screen, game_state):
        if not game_state: return

        # Loop from 0 to 25 to explicitly include the bars!
        for i in range(0, 26):
            count = game_state.board[i]
            if count == 0: continue

            player = 1 if count > 0 else -1
            if i == 0 and player == -1: continue # Adam's off-board pieces
            if i == 25 and player == 1: continue # Human's off-board pieces
            num_checkers = abs(count)
            color = self.colors["p1_checker"] if player == 1 else self.colors["p2_checker"]
            
            # The text on the 5th checker should contrast with the checker color
            text_color = (0, 0, 0) if player == 1 else (255, 255, 255) 

            # Calculate base X and Y coordinates
            if i == 0 or i == 25:
                # IT'S ON THE BAR
                x_offset = self.width // 2
                is_top = (i == 25) 
            elif i <= 12:
                # BOTTOM TRIANGLES
                visual_index = 12 - i
                is_top = False
                x_offset = self.board_rect.left + (visual_index * self.point_width) + (self.point_width // 2)
                if visual_index >= 6: x_offset += self.bar_width
            else:
                # TOP TRIANGLES
                visual_index = i - 13
                is_top = True
                x_offset = self.board_rect.left + (visual_index * self.point_width) + (self.point_width // 2)
                if visual_index >= 6: x_offset += self.bar_width

            # --- NEW: Cap visual stacking at 5 ---
            draw_count = min(num_checkers, 5)

            for j in range(draw_count):
                y_offset = self.checker_radius * 2 * j
                
                if is_top:
                    y = self.board_rect.top + self.checker_radius + y_offset
                    if i == 25: y += 50 # Bump down slightly on the bar
                else:
                    y = self.board_rect.bottom - self.checker_radius - y_offset
                    if i == 0: y -= 50 # Bump up slightly on the bar

                # Draw the checker
                pygame.draw.circle(screen, color, (int(x_offset), int(y)), self.checker_radius)
                pygame.draw.circle(screen, (0, 0, 0), (int(x_offset), int(y)), self.checker_radius, 2)

                # --- NEW: Draw numerical count on the 5th piece ---
                if j == 4 and num_checkers > 5:
                    text_surf = self.font.render(str(num_checkers), True, text_color)
                    text_rect = text_surf.get_rect(center=(int(x_offset), int(y)))
                    screen.blit(text_surf, text_rect)


    def draw_dragged_piece(self, screen, input_handler):
        if input_handler.dragging_piece:
            piece = input_handler.dragging_piece
            color = self.colors["p1_checker"] if piece['player'] == 1 else self.colors["p2_checker"]
            
            # Draw the piece exactly at the mouse coordinates
            pygame.draw.circle(screen, color, (piece['x'], piece['y']), self.checker_radius)
            pygame.draw.circle(screen, (0, 0, 0), (piece['x'], piece['y']), self.checker_radius, 2)
    
    def draw_dice(self, screen, dice):
        if not dice: return
        
        start_y = self.height - 35 
        
        total_width = (len(dice) * 50) - 10 
        
        # Calculate the exact center of the screen, then back up by half the total width
        start_x = (self.width // 2) - (total_width // 2) + 20 
        
        for i, val in enumerate(dice):
            die_rect = pygame.Rect(0, 0, 40, 40)
            die_rect.center = (start_x + (i * 50), start_y)
            
            pygame.draw.rect(screen, (255, 255, 255), die_rect, border_radius=5)
            pygame.draw.rect(screen, (0, 0, 0), die_rect, 2, border_radius=5)
            
            text = self.font.render(str(val), True, (0, 0, 0))
            text_rect = text.get_rect(center=die_rect.center)
            screen.blit(text, text_rect)


    def draw_button(self, screen, text, rect, is_hovered):
        # Change color slightly if the mouse is hovering over it
        color = (180, 130, 80) if is_hovered else (133, 94, 66)
        
        # Draw the main button and a darker border
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (60, 30, 10), rect, 3, border_radius=10)
        
        # Draw the text perfectly centered
        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

    def draw_status_message(self, screen, text):
        if not text: return
        
        # Draw a clear white text message centered at the very top of the window
        text_surf = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(self.width // 2, 25))
        screen.blit(text_surf, text_rect)

    def draw_bear_off_zones(self, screen, game_state):
        # P1 active: indices 1-24, plus index 0 (Bar). Ignore 25!
        p1_active = sum(game_state.board[i] for i in range(0, 25) if game_state.board[i] > 0)
        
        # P2 active: indices 1-24, plus index 25 (Bar). Ignore 0!
        p2_active = sum(abs(game_state.board[i]) for i in range(1, 26) if game_state.board[i] < 0)
        
        p1_off = 15 - p1_active
        p2_off = 15 - p2_active

        tray_width = 45
        tray_height = 200
        
        p1_tray = pygame.Rect(self.width - tray_width - 10, self.board_rect.top, tray_width, tray_height)
        p2_tray = pygame.Rect(self.width - tray_width - 10, self.board_rect.bottom - tray_height, tray_width, tray_height)

        pygame.draw.rect(screen, self.colors["bar"], p2_tray, border_radius=5)
        pygame.draw.rect(screen, self.colors["bar"], p1_tray, border_radius=5)
        pygame.draw.rect(screen, self.colors["border"], p2_tray, 2, border_radius=5)
        pygame.draw.rect(screen, self.colors["border"], p1_tray, 2, border_radius=5)
        
        # Draw the scores
        text1 = self.font.render(str(p1_off), True, (255, 255, 255))
        screen.blit(text1, text1.get_rect(center=p1_tray.center))

        text2 = self.font.render(str(p2_off), True, (255, 255, 255))
        screen.blit(text2, text2.get_rect(center=p2_tray.center))

    def draw_match_lobby(self, screen, human_score, adam_score):
        # Fill screen with a solid dark wood color
        screen.fill((40, 20, 10)) 
        
        # Draw Title
        title_font = pygame.font.SysFont(None, 80)
        title_surf = title_font.render("Backgammon Match", True, (255, 255, 255))
        screen.blit(title_surf, title_surf.get_rect(center=(self.width // 2, self.height // 2 - 150)))
        
        # Draw Score
        score_font = pygame.font.SysFont(None, 120)
        if human_score == adam_score:
            score_text = f"Tied at {human_score} - {adam_score}"
        else:
            score_text = f"You {human_score} - {adam_score} Adam"
            
        score_surf = score_font.render(score_text, True, (255, 215, 0))
        screen.blit(score_surf, score_surf.get_rect(center=(self.width // 2, self.height // 2 - 20)))

    def draw_game_over_popup(self, screen, winner):
        # Darken the board behind the popup
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Draw the popup box
        popup_rect = pygame.Rect(self.width // 2 - 200, self.height // 2 - 120, 400, 240)
        pygame.draw.rect(screen, self.colors["bar"], popup_rect, border_radius=15)
        pygame.draw.rect(screen, self.colors["border"], popup_rect, 4, border_radius=15)
        
        # Draw the winner text
        font = pygame.font.SysFont(None, 70)
        text = "You Won!" if winner == 1 else "Adam Won!"
        color = (255, 215, 0) if winner == 1 else (255, 100, 100)
        text_surf = font.render(text, True, color)
        screen.blit(text_surf, text_surf.get_rect(center=(self.width // 2, self.height // 2 - 30)))

    def render_frame(self, screen, game_state, input_handler, available_dice): 
        self.draw_background(screen)
        self.draw_points(screen)
        self.draw_checkers(screen, game_state)
        self.draw_bear_off_zones(screen, game_state)
        self.draw_dice(screen, available_dice)
        self.draw_dragged_piece(screen, input_handler)