"""角色卡管理 — 確保角色在整部劇中外觀一致

每個角色有一張固定的角色卡（描述髮型、膚色、服裝等），
所有生圖 prompt 都基於角色卡組裝，避免角色長相不一致。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..utils.config import PROJECT_ROOT


@dataclass
class CharacterCard:
    name: str
    gender: str
    age_range: str  # e.g. "25-30"
    hair: str  # e.g. "黑色長直髮"
    skin_tone: str  # e.g. "白皙"
    outfit: str  # e.g. "白色襯衫，黑色西裝褲"
    body_type: str  # e.g. "纖細"
    personality: str  # e.g. "冷酷但內心溫柔"
    extra: dict = field(default_factory=dict)  # 額外特徵

    def to_prompt_desc(self, lang: str = "en") -> str:
        """轉成生圖 prompt 用的角色描述"""
        if lang == "en":
            return (
                f"{self.gender}, {self.age_range} years old, "
                f"{self.hair}, {self.skin_tone} skin, "
                f"{self.body_type} build, wearing {self.outfit}"
            )
        return (
            f"{self.gender}，{self.age_range}歲，"
            f"{self.hair}，{self.skin_tone}膚色，"
            f"{self.body_type}身材，穿著{self.outfit}"
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterCard":
        d = dict(d)  # shallow copy to avoid mutating caller's dict
        extra = d.pop("extra", {})
        # Only pass known fields; put unknown keys into extra
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        known_fields.discard("extra")
        for key in list(d.keys()):
            if key not in known_fields:
                extra[key] = d.pop(key)
        return cls(**d, extra=extra)


class CharacterManager:
    """管理一部劇的所有角色卡"""

    def __init__(self, drama_id: str):
        self.drama_id = drama_id
        self.characters: dict[str, CharacterCard] = {}
        self._save_dir = PROJECT_ROOT / "data" / "characters" / drama_id
        self._save_dir.mkdir(parents=True, exist_ok=True)

    def add(self, card: CharacterCard):
        self.characters[card.name] = card

    def get(self, name: str) -> CharacterCard | None:
        return self.characters.get(name)

    def all_cards(self) -> list[CharacterCard]:
        return list(self.characters.values())

    def get_prompt_desc(self, name: str, lang: str = "en") -> str:
        """取得角色的生圖描述"""
        card = self.get(name)
        if not card:
            return f"unknown character: {name}"
        return card.to_prompt_desc(lang=lang)

    def save(self):
        """存角色卡到 JSON"""
        data = {name: card.to_dict() for name, card in self.characters.items()}
        path = self._save_dir / "characters.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        """從 JSON 載入角色卡"""
        path = self._save_dir / "characters.json"
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.characters = {
            name: CharacterCard.from_dict(d) for name, d in data.items()
        }
