#!/usr/bin/env python3

import time
import struct
import spidev
from elftools.elf.elffile import ELFFile

# SPI 設定
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 4000000  # 1MHz
STM32_ACK = 0x79
STM32_NACK = 0x1F

# コマンド定義 (AN4286 準拠)
CMD_DUMMY = 0x00
CMD_INIT = 0x5A
CMD_INIT_ACK = 0xA5
CMD_GET_ID = 0x02
CMD_ERASE = 0x44
CMD_WRITE = 0x31
CMD_GO = 0x21


# STM32 に SPI 経由でファームウェアを書き込むクラス
class STM32Flasher:
    def __init__(self, spi_bus, spi_device, speed):
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0  # Mode 0 (CPOL=0, CPHA=0)

    def wait_for_ack(self):
        """ACKを待つ"""
        while True:
            self.spi.writebytes([CMD_DUMMY])
            response = self.spi.readbytes(1)[0]
            if response == STM32_ACK:
                self.spi.writebytes([STM32_ACK])
                # print('receive ack')
                return True
            elif response == STM32_NACK:
                self.spi.writebytes([STM32_ACK])
                # print('receive nack')
                return False
            time.sleep(0.1)

    def send_command(self, cmd):
        """STM32 にコマンドを送信し、ACK を待つ"""
        self.spi.xfer2([0x5A, cmd, cmd ^ 0xFF])
        return self.wait_for_ack()

    def init_bootloader(self):
        """ブートローダを起動"""
        self.spi.xfer2([CMD_INIT])
        return self.wait_for_ack()

    def get_version(self):
        """bootloader の version を取得"""
        ack = self.send_command(0x01)

        if ack:
            self.spi.readbytes(1)
            version = self.spi.readbytes(1)[0]
            self.wait_for_ack()
            return version

        return 0

    def get_id(self):
        """STM32 のデバイス ID を取得"""
        ack = self.send_command(0x02)
        if ack:
            self.spi.readbytes(1)
            response = self.spi.readbytes(3)
            id = response[1] * 0x100 + response[2]
            self.wait_for_ack()
            return id
        return 0

    def erase_flash(self):
        """フラッシュメモリを消去"""
        if not self.send_command(CMD_ERASE):
            return False
        self.spi.xfer2([0xFF, 0xFF, 0x00])  # 全消去
        return self.wait_for_ack()

    def erase_sectors(self, sectors):
        """セクターを消去"""
        if not self.send_command(CMD_ERASE):
            return False

        self.spi.xfer2([0x00, len(sectors), 0x00 ^ len(sectors)])  # 全消去
        if not self.wait_for_ack():
            return False

        data = []

        for sector in sectors:
            data.append(0)
            data.append(sector)

        checksum = data[0]
        for num in data[1:]:
            checksum ^= num

        self.spi.xfer2(list(data) + [checksum])

        return self.wait_for_ack()

    def write_memory(self, address, data):
        """指定アドレスにデータを書き込む"""
        # アドレス送信 (4バイト + XOR チェックサム)
        addr_bytes = struct.pack(">I", address)
        checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
        if not self.send_command(CMD_WRITE):
            return False
        self.spi.xfer2(list(addr_bytes) + [checksum])
        if not self.wait_for_ack():
            return False
        time.sleep(0.001)
        # データ送信
        length = len(data) - 1
        checksum = length
        for num in data:
            checksum ^= num
        self.spi.xfer3([length] + data + [checksum])
        time.sleep(0.001)
        return self.wait_for_ack()

    def run_firmware(self, address):
        """ファームウェアを実行"""
        addr_bytes = struct.pack(">I", address)
        checksum = addr_bytes[0] ^ addr_bytes[1] ^ addr_bytes[2] ^ addr_bytes[3]
        if not self.send_command(CMD_GO):
            return False
        self.spi.xfer2(list(addr_bytes) + [checksum])
        return self.wait_for_ack()

    def read_unprotct(self):
        if not self.send_command(0x92):
            print("unprotect fail")
            return False
        return self.wait_for_ack()

    def close(self):
        self.spi.close()


# ELF ファイルのパース
def parse_elf(elf_path):
    """ELF ファイルをパースし、書き込むデータを抽出"""
    with open(elf_path, "rb") as f:
        elf = ELFFile(f)
        segments = []
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":  # メモリにロードするセグメント
                addr = segment["p_paddr"]
                data = segment.data()
                segments.append((addr, data))
        return segments


# メイン処理
def main(elf_file):
    flasher = STM32Flasher(SPI_BUS, SPI_DEVICE, SPI_SPEED)

    print("[+] ブートローダを起動中...")
    if not flasher.init_bootloader():
        print("[-] ブートローダ起動失敗")
        return

    print("[+] プロトコルversionを取得...")
    version = flasher.get_version()
    print(f"    version: {hex(version)}")

    if version < 0x10:
        print("[-] サポートされていないプロトコルバージョン")
        return

    print("[+] STM32 ID を取得...")
    chip_id = flasher.get_id()
    if chip_id:
        print(f"    STM32 ID: {hex(chip_id)}")
    else:
        print("[-] ID 取得失敗")
        return

    # print("[+] フラッシュメモリを消去...")
    # if not flasher.erase_flash():
    #     print("[-] フラッシュ消去失敗")
    #     return

    print("[+] フラッシュメモリを消去...")
    if not flasher.erase_sectors([0]):
        print("[-] フラッシュ消去失敗")
        return

    print("[+] ELF ファイルをパース...")
    segments = parse_elf(elf_file)
    if not segments:
        print("[-] 書き込むセグメントが見つかりません")
        return

    print("[+] ファームウェア書き込み開始...")
    for addr, data in segments:
        print(f"    書き込み: {hex(addr)} - {hex(len(data))} バイト")
        for i in range(0, len(data), 256):
            chunk = data[i : i + 256]
            if not flasher.write_memory(addr + i, list(chunk)):
                print(f"[-] アドレス {hex(addr + i)} への書き込み失敗")
                return

    print("[+] ファームウェア実行...")
    if flasher.run_firmware(segments[0][0]):  # 最初のセグメントのアドレスで実行
        print("[+] 実行成功！")
    else:
        print("[-] 実行失敗")

    flasher.close()


# 実行
if __name__ == "__main__":
    elf_path = "/home/pi/spi-firmware-update-f401.elf"
    import subprocess

    result = subprocess.run(["sh", "./boot_stm.sh"], capture_output=True, text=True)
    time.sleep(0.1)

    main(elf_path)
