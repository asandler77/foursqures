from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CreateGameIn(BaseModel):
    piecesPerPlayer: int = Field(default=16, ge=1, le=16)
    aiMode: Literal["random", "ai"] = Field(default="random")


class CreateGameOut(BaseModel):
    gameId: str
    playerToken: str
    state: dict
    aiMode: Literal["random", "ai"]


class GameStateOut(BaseModel):
    state: dict


class MoveIn(BaseModel):
    action: Literal["place", "slide"]
    # place: squareIndex = destination square
    # slide: squareIndex is optional (legacy formats). New client uses fromSquareIndex + toHoleSquareIndex.
    squareIndex: Optional[int] = Field(default=None, ge=0, le=8)
    slotIndex: Optional[int] = Field(default=None, ge=0, le=3)
    slideSquareIndex: Optional[int] = Field(default=None, ge=0, le=8)
    fromSquareIndex: Optional[int] = Field(default=None, ge=0, le=8)
    toHoleSquareIndex: Optional[int] = Field(default=None, ge=0, le=8)
    playerToken: str

    @model_validator(mode="after")
    def validate(self) -> "MoveIn":
        if self.action == "place":
            if self.squareIndex is None:
                raise ValueError("squareIndex is required for place")
            if self.slotIndex is None:
                raise ValueError("slotIndex is required for place")
            # slideSquareIndex is optional: if provided, server will place then slide in same request
            if self.fromSquareIndex is not None:
                raise ValueError("fromSquareIndex must be omitted for place")
            if self.toHoleSquareIndex is not None:
                raise ValueError("toHoleSquareIndex must be omitted for place")
        else:
            # slide
            if self.slotIndex is not None:
                raise ValueError("slotIndex must be omitted for slide")
            if self.slideSquareIndex is not None:
                raise ValueError("slideSquareIndex must be omitted for slide")
            # Supported slide payloads:
            # A) New client: fromSquareIndex + toHoleSquareIndex (squareIndex omitted)
            # B) Legacy: squareIndex = square being slid into hole
            # C) Legacy-alt: squareIndex = hole index + fromSquareIndex = square to slide
            if self.toHoleSquareIndex is not None and self.fromSquareIndex is None:
                raise ValueError("fromSquareIndex is required when toHoleSquareIndex is provided")
            if self.toHoleSquareIndex is None and self.fromSquareIndex is not None and self.squareIndex is None:
                raise ValueError("squareIndex (hole) is required when using fromSquareIndex without toHoleSquareIndex")
            if self.toHoleSquareIndex is None and self.fromSquareIndex is None and self.squareIndex is None:
                raise ValueError("squareIndex is required for slide (legacy) or provide fromSquareIndex+toHoleSquareIndex")
        return self


class RestartIn(BaseModel):
    playerToken: str

