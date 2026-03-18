from pydantic import BaseModel


class GameState(BaseModel):
    # Array of length 28: [P1_Bar, Spot_1 ... Spot_24, P2_Bar, P1_Off, P2_Off]
    board: list[int]
    current_turn: int  # 1 for Player, -1 for Opponent
