from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .game_logic import GameState, Phase, PlayerColor, apply_place, apply_slide, legal_slide_squares

ACTION_SPACE_SIZE = 45  # 36 place actions + 9 slide actions
FEATURE_COLUMNS = [
    *(f"board_{i}" for i in range(36)),
    "current_player_is_b",
    "phase_placement",
    "phase_placement_slide",
    "phase_movement",
    "hole_square_index",
    "blocked_slide_square_index",
]


def _legal_place_targets(state: GameState) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for sq in range(9):
        if sq == state.holeSquareIndex:
            continue
        for sl in range(4):
            if state.board[sq][sl] is None:
                out.append((sq, sl))
    return out


def extract_features(state: GameState) -> list[float]:
    board_features: list[float] = []
    for square in state.board:
        for slot in square:
            if slot == PlayerColor.R.value:
                board_features.append(1.0)
            elif slot == PlayerColor.B.value:
                board_features.append(-1.0)
            else:
                board_features.append(0.0)

    current_player_is_b = 1.0 if state.currentPlayer == PlayerColor.B else 0.0
    phase_placement = 1.0 if state.phase == Phase.placement else 0.0
    phase_placement_slide = 1.0 if state.phase == Phase.placementSlide else 0.0
    phase_movement = 1.0 if state.phase == Phase.movement else 0.0
    hole_square_index = float(state.holeSquareIndex)
    blocked_slide_square_index = float(state.blockedSlideSquareIndex) if state.blockedSlideSquareIndex is not None else -1.0

    return [
        *board_features,
        current_player_is_b,
        phase_placement,
        phase_placement_slide,
        phase_movement,
        hole_square_index,
        blocked_slide_square_index,
    ]


def encode_place_action(square_index: int, slot_index: int) -> int:
    return square_index * 4 + slot_index


def decode_place_action(action_id: int) -> tuple[int, int]:
    return action_id // 4, action_id % 4


def encode_slide_action(square_index: int) -> int:
    return 36 + square_index


def decode_slide_action(action_id: int) -> int:
    return action_id - 36


@dataclass
class AIPlayer:
    model_path: Path
    _model: Optional[object] = None
    _tf: Optional[object] = None

    @classmethod
    def default(cls) -> "AIPlayer":
        model_dir = Path(__file__).resolve().parent / "models"
        return cls(model_path=model_dir / "ai_player.keras")

    def is_ready(self) -> bool:
        return self.model_path.exists()

    def _ensure_tf(self) -> object:
        if self._tf is None:
            import tensorflow as tf  # type: ignore[import-not-found]

            self._tf = tf
        return self._tf

    def _build_model(self, input_dim: int, output_dim: int) -> object:
        tf = self._ensure_tf()
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(input_dim,)),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dense(64, activation="relu"),
                tf.keras.layers.Dense(output_dim, activation="softmax"),
            ]
        )
        model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        return model

    def _load_or_create_model(self, *, create_if_missing: bool) -> object:
        tf = self._ensure_tf()
        if self._model is not None:
            return self._model
        if self.model_path.exists():
            self._model = tf.keras.models.load_model(self.model_path)
        elif create_if_missing:
            self._model = self._build_model(len(FEATURE_COLUMNS), ACTION_SPACE_SIZE)
        else:
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        return self._model

    def train_from_csv(
        self,
        csv_path: str | Path,
        *,
        epochs: int = 30,
        batch_size: int = 32,
    ) -> None:
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Training CSV not found at {csv_path}")

        features: list[list[float]] = []
        labels: list[int] = []
        with csv_path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("CSV must include a header row")
            required = list(FEATURE_COLUMNS) + ["action_id"]
            missing = [col for col in required if col not in reader.fieldnames]
            if missing:
                raise ValueError(f"CSV missing columns: {', '.join(missing)}")

            for row in reader:
                features.append([float(row[col]) for col in FEATURE_COLUMNS])
                labels.append(int(row["action_id"]))

        tf = self._ensure_tf()
        model = self._load_or_create_model(create_if_missing=True)
        x_tensor = tf.convert_to_tensor(features, dtype=tf.float32)
        y_tensor = tf.convert_to_tensor(labels, dtype=tf.int32)

        model.fit(x_tensor, y_tensor, epochs=epochs, batch_size=batch_size, verbose=0)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(self.model_path)

    def _predict_action_scores(self, state: GameState) -> Optional[list[float]]:
        if not self.is_ready():
            return None
        tf = self._ensure_tf()
        model = self._load_or_create_model(create_if_missing=False)
        features = extract_features(state)
        scores = model.predict(tf.convert_to_tensor([features], dtype=tf.float32), verbose=0)[0]
        return [float(x) for x in scores]

    def _choose_action_id(
        self,
        action_ids: list[int],
        scores: list[float],
        *,
        rng: Optional[random.Random] = None,
    ) -> Optional[int]:
        if not action_ids:
            return None
        masked_scores = {action_id: scores[action_id] for action_id in action_ids}
        if rng is None:
            return max(masked_scores.items(), key=lambda item: item[1])[0]

        total = sum(masked_scores.values())
        if total <= 0:
            return rng.choice(action_ids)
        threshold = rng.random() * total
        cumulative = 0.0
        for action_id, score in masked_scores.items():
            cumulative += score
            if cumulative >= threshold:
                return action_id
        return action_ids[-1]

    def take_turn(self, state: GameState, *, rng: Optional[random.Random] = None) -> bool:
        if state.winner is not None or state.drawReason is not None:
            return False
        if state.currentPlayer != PlayerColor.B:
            return False

        scores = self._predict_action_scores(state)
        if scores is None:
            return False

        if state.phase == Phase.placement:
            place_actions = [encode_place_action(sq, sl) for sq, sl in _legal_place_targets(state)]
            action_id = self._choose_action_id(place_actions, scores, rng=rng)
            if action_id is None:
                return False
            square_index, slot_index = decode_place_action(action_id)
            apply_place(state, squareIndex=square_index, slotIndex=slot_index, player=PlayerColor.B)

        if state.currentPlayer != PlayerColor.B:
            return True

        if state.phase in (Phase.placementSlide, Phase.movement):
            slide_actions = [encode_slide_action(sq) for sq in legal_slide_squares(state)]
            action_id = self._choose_action_id(slide_actions, scores, rng=rng)
            if action_id is None:
                return True
            square_index = decode_slide_action(action_id)
            apply_slide(state, squareIndex=square_index, player=PlayerColor.B)

        return True
