from enum import Enum
import spidev
from spiflash.spi_base import SpiBase


class SpiBus(Enum):
    SPI0 = 0
    SPI1 = 1
    SPI2 = 2
    SPI3 = 3
    SPI4 = 4
    SPI5 = 5
    SPI6 = 6


class SpiCs(Enum):
    CS0 = 0
    CS1 = 1
    CS2 = 2


class SpiDev(SpiBase):
    def __init__(self, bus: SpiBus, cs: SpiCs, speed: int):
        if not isinstance(bus, SpiBus):
            raise ValueError("bus must be an instance of SpiBus Enum")
        if not isinstance(cs, SpiCs):
            raise ValueError("cs must be an instance of SpiCs Enum")

        self.spi = spidev.SpiDev()
        self.spi.open(bus.value, cs.value)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0  # Mode 0 (CPOL=0, CPHA=0)
        self.spi.no_cs = False

    def __del__(self):
        self.close()

    def send(self, data: list[int]) -> None:
        self.spi.writebytes(data)

    def receive(self, length: int) -> list[int]:
        if length <= 0:
            raise ValueError("Length must be greater than zero")
        received = self.spi.readbytes(length)
        return received

    def transfer(self, data: list[int]) -> list[int]:
        response = self.spi.xfer3(data)
        return response

    def close(self):
        self.spi.close()
