from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Region(ABC):
    start_index: int
    end_index: int
    name: str = field(default="", kw_only=True)

    def __post_init__(self):
        start_index = min(self.start_index, self.end_index)
        end_index = max(self.start_index, self.end_index)
        self.start_index = start_index
        self.end_index = end_index

    def covers_index(self, point_index):
        return self.start_index <= point_index <= self.end_index

    @staticmethod
    @abstractmethod
    def from_dict(cls, data):
        raise NotImplementedError

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError
