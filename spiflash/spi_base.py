from abc import ABC, abstractmethod


class SpiBase(ABC):
    @abstractmethod
    def send(self, data: list[int]) -> None:
        pass

    @abstractmethod
    def receive(self, length: int) -> list[int]:
        pass

    @abstractmethod
    def transfer(self, data: list[int]) -> list[int]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass
