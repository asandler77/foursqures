from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CreateGameIn(BaseModel):
    piecesPerPlayer: int = Field(default=8, ge=1, le=18)


class CreateGameOut(BaseModel):
    gameId: str
    playerToken: str
    state: dict


class GameStateOut(BaseModel):
    state: dict


class MoveIn(BaseModel):
    action: Literal["place", "slide"]
    squareIndex: int = Field(ge=0, le=8)
    slotIndex: Optional[int] = Field(default=None, ge=0, le=3)
    slideSquareIndex: Optional[int] = Field(default=None, ge=0, le=8)
    playerToken: str

    @model_validator(mode="after")
    def validate(self) -> "MoveIn":
        if self.action == "place":
            if self.slotIndex is None:
                raise ValueError("slotIndex is required for place")
            # slideSquareIndex is optional: if provided, server will place then slide in same request
        else:
            if self.slotIndex is not None:
                raise ValueError("slotIndex must be omitted for slide")
            if self.slideSquareIndex is not None:
                raise ValueError("slideSquareIndex must be omitted for slide")
        return self


class RestartIn(BaseModel):
    playerToken: str

