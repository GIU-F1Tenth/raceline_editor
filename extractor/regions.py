from dataclasses import dataclass, field
from typing import ClassVar

from extractor import Region


@dataclass
class ConstantSpeedMultiplierRegion(Region):
    REGION_TYPE: ClassVar[str] = "Constant Speed Multiplier"

    multiplier: float = 1.0

    def to_dict(self):
        return {
            "type": self.REGION_TYPE,
            "name": self.name,
            "start": self.start_index,
            "end": self.end_index,
            "multiplier": float(self.multiplier),
        }

    @staticmethod
    def from_dict(data):
        return ConstantSpeedMultiplierRegion(
            start_index=int(data["start"]),
            end_index=int(data["end"]),
            multiplier=float(data.get("multiplier", 1.0)),
            name=str(data.get("name", "")),
        )


@dataclass
class OvertakingAllowedRegion(Region):
    REGION_TYPE: ClassVar[str] = "Overtaking Allowed"

    can_overtake: bool = field(default=True, kw_only=True)

    def to_dict(self):
        return {
            "type": self.REGION_TYPE,
            "name": self.name,
            "start": self.start_index,
            "end": self.end_index,
            "can_overtake": bool(self.can_overtake),
        }

    @staticmethod
    def from_dict(data):
        return OvertakingAllowedRegion(
            start_index=int(data["start"]),
            end_index=int(data["end"]),
            name=str(data.get("name", "")),
            can_overtake=bool(data.get("can_overtake", True)),
        )


@dataclass
class CurvatureRegion(Region):
    REGION_TYPE: ClassVar[str] = "Curvature Region"

    is_curved: bool = field(default=True, kw_only=True)

    def to_dict(self):
        return {
            "type": self.REGION_TYPE,
            "name": self.name,
            "start": self.start_index,
            "end": self.end_index,
            "is_curved": bool(self.is_curved),
        }

    @staticmethod
    def from_dict(data):
        return CurvatureRegion(
            start_index=int(data["start"]),
            end_index=int(data["end"]),
            name=str(data.get("name", "")),
            is_curved=bool(data.get("is_curved", True)),
        )


REGION_TYPES = {
    ConstantSpeedMultiplierRegion.REGION_TYPE: ConstantSpeedMultiplierRegion,
    OvertakingAllowedRegion.REGION_TYPE: OvertakingAllowedRegion,
    CurvatureRegion.REGION_TYPE: CurvatureRegion,
}
