import time
import struct
from spi_base import SpiBase


class SpiFlasher:
    __STM32_ACK = 0x79
    __STM32_NACK = 0x1F
    __STM32_INIT_ACK = 0xA5

    __CMD_DUMMY = 0x00
    __CMD_INIT = 0x5A
    __CMD_GET_VERSION = 0x01
    __CMD_GET_ID = 0x02
    __CMD_ERASE = 0x44
    __CMD_WRITE = 0x31
    __CMD_READ_UNPROTECT = 0x92
    __CMD_GO = 0x21

    def __init__(self, spi: SpiBase):
        if not isinstance(spi, SpiBase):
            raise ValueError("Expected spi to be an instance of SpiBase")

        self.spi: SpiBase = spi

    def __wait_for_ack(self):
        """ACKを待つ"""
        while True:
            self.spi.send([self.__CMD_DUMMY])
            response = self.spi.receive(1)[0]
            if response == self.__STM32_ACK:
                self.spi.send([self.__STM32_ACK])
                # print('receive ack')
                return True
            elif response == self.__STM32_NACK:
                self.spi.send([self.__STM32_ACK])
                # print('receive nack')
                return False
            time.sleep(0.1)

    def __send_command(self, cmd):
        """STM32 にコマンドを送信し、ACK を待つ"""
        self.spi.transfer([0x5A, cmd, cmd ^ 0xFF])
        return self.__wait_for_ack()

    def init_bootloader(self):
        """ブートローダを起動"""
        while True:
            response = self.spi.transfer([self.__CMD_INIT])
            if response[0] == self.__STM32_INIT_ACK:
                break
            time.sleep(0.1)
        return self.__wait_for_ack()

    def get_version(self):
        """bootloader の version を取得"""
        ack = self.__send_command(self.__CMD_GET_VERSION)
        if ack:
            self.spi.receive(1)
            version = self.spi.receive(1)[0]
            self.__wait_for_ack()
            return version
        return None

    def get_device_id(self):
        """STM32 のデバイス ID を取得"""
        ack = self.__send_command(self.__CMD_GET_ID)
        if ack:
            self.spi.receive(1)
            response = self.spi.receive(3)
            device_id = response[1] * 0x100 + response[2]
            self.__wait_for_ack()
            return device_id
        return None

    def erase_flash(self):
        """フラッシュメモリを消去"""
        if not self.__send_command(self.__CMD_ERASE):
            return False
        self.spi.transfer([0xFF, 0xFF, 0x00])  # 全消去
        return self.__wait_for_ack()

    def erase_sectors(self, sectors):
        """セクターを消去"""
        if not self.__send_command(self.__CMD_ERASE):
            return False

        self.spi.transfer([0x00, len(sectors), 0x00 ^ len(sectors)])
        if not self.__wait_for_ack():
            return False

        data = []
        for sector in sectors:
            data.append(0)
            data.append(sector)

        checksum = data[0]
        for num in data[1:]:
            checksum ^= num

        self.spi.transfer(list(data) + [checksum])
        return self.__wait_for_ack()

    def write_memory(self, address, data):
        """指定アドレスにデータを書き込む"""
        # アドレス送信 (4バイト + XOR チェックサム)
        addr_bytes = struct.pack(">I", address)
        checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
        if not self.__send_command(self.__CMD_WRITE):
            return False
        self.spi.transfer(list(addr_bytes) + [checksum])
        if not self.__wait_for_ack():
            return False
        time.sleep(0.0001)

        length = len(data) - 1
        checksum = length
        for num in data:
            checksum ^= num
        self.spi.transfer([length] + data + [checksum])
        time.sleep(0.0001)
        return self.__wait_for_ack()

    def run_firmware(self, address):
        """ファームウェアを実行"""
        addr_bytes = struct.pack(">I", address)
        checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
        if not self.__send_command(self.__CMD_GO):
            return False
        self.spi.transfer(list(addr_bytes) + [checksum])
        return self.__wait_for_ack()

    def receive_unprotct(self):
        if not self.__send_command(self.__CMD_READ_UNPROTECT):
            return False
        return self.__wait_for_ack()

    def close(self):
        self.spi.close()
