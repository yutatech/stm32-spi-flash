#!/usr/bin/env python3
import argparse
import os
from tqdm import tqdm
from pathlib import Path
import yaml
from elftools.elf.elffile import ELFFile
from spi_flasher import SpiFlasher
from spi_dev import SpiDev, SpiBus, SpiCs


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


def get_device(device_id):
    script_dir = Path(__file__).parent
    file_path = script_dir / "devices.yml"

    with open(file_path, "r", encoding="utf-8") as file:
        devices = yaml.safe_load(file)

    for device in devices:
        if device["id"] == device_id:
            return device
    return {
        "name": "unknown",
        "id": "invalid",
        "flash_addr": 0x080000000,
        "sectors": None,
    }


def auto_erase(flasher, device, data_size):
    if device["sectors"]:
        sector_sizes = []
        for sector in device["sectors"]:
            sector_sizes += [sector["size"]] * sector["length"]

        erase_sectors = []
        for i, sector_size in enumerate(sector_sizes):
            erase_sectors.append(i)
            data_size -= sector_size
            if data_size <= 0:
                break

        print("[+] Erasing sectors...")
        if not flasher.erase_sectors(erase_sectors):
            print("[-] Failed to erase flash memory")
            return
    else:
        print("[+] Erasing entire flash areas...")
        if not flasher.erase_flash():
            print("[-] Failed to erase flash memory")
            return


def flash_bin(flasher, device, bin_path):
    with open(bin_path, "rb") as f:
        data = f.read()

    auto_erase(flasher, device, len(data))

    print("[+] Firmware writing started...")

    addr = device["flash_addr"]
    bar = tqdm(total=len(data))
    bar.set_description(f"[+] Writing {hex(len(data))} bytes")
    for i in range(0, len(data), 256):
        chunk = data[i : i + 256]
        if not flasher.write_memory(addr + i, list(chunk)):
            print(f"[-] Failed to write to addr: {addr + i}")
            return 1
        bar.update(len(chunk))
    bar.close()
    return 0


def flash_elf(flasher, device, elf_path):
    segments = parse_elf(elf_path)
    if not segments:
        print("[-] Failed to parse ELF file")
        return 1

    data_size = segments[-1][0] + len(segments[-1][1]) - segments[0][0]
    auto_erase(flasher, device, data_size)

    print("[+] Firmware writing started...")

    total_size = sum(len(data) for _, data in segments)
    bar = tqdm(total=total_size)
    bar.set_description(f"[+] Writing {hex(total_size)} bytes")
    for addr, data in segments:
        for i in range(0, len(data), 256):
            chunk = data[i : i + 256]
            if not flasher.write_memory(addr + i, list(chunk)):
                print(f"[-] Failed to write to address {hex(addr + i)}")
                return 1
            bar.update(len(chunk))
    bar.close()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="This command is a firmware uploader for STM32, utilizing the Raspberry Pi's SPI bus for communication."
    )
    parser.add_argument("firmware", help=".bin for .elf file")
    parser.add_argument(
        "--spi-bus", "-b", type=int, default=0, help="SPI Bus numbe. Default is 0"
    )
    parser.add_argument(
        "--spi-cs", "-c", type=int, default=0, help="SPI CS number. Default is 0"
    )
    parser.add_argument(
        "--spi-speed",
        "-s",
        type=int,
        default=4000000,
        help="SPI Speed. Default is 4000000",
    )

    args = parser.parse_args()

    if args.spi_bus == 0:
        spi_bus = SpiBus.SPI0
    elif args.spi_bus == 1:
        spi_bus = SpiBus.SPI1
    elif args.spi_bus == 2:
        spi_bus = SpiBus.SPI2
    elif args.spi_bus == 3:
        spi_bus = SpiBus.SPI3
    elif args.spi_bus == 4:
        spi_bus = SpiBus.SPI4
    elif args.spi_bus == 5:
        spi_bus = SpiBus.SPI5
    elif args.spi_bus == 6:
        spi_bus = SpiBus.SPI6
    else:
        print("Invalid value for -spi-bus. Expected a number between 0 and 6.")
        return 1

    if args.spi_cs == 0:
        spi_cs = SpiCs.CS0
    elif args.spi_cs == 1:
        spi_cs = SpiCs.CS1
    elif args.spi_cs == 2:
        spi_cs = SpiCs.CS2
    else:
        print("Invalid value for -spi-cs. Expected a number between 0 and 2.")
        return 1

    flasher = SpiFlasher(SpiDev(spi_bus, spi_cs, args.spi_speed))

    print("[+] Starting bootloader...")
    if not flasher.init_bootloader():
        print("[-] Failed to start bootloader")
        return 1

    print("[+] Getting protocol version...")
    version = flasher.get_version()
    if not version:
        print("[-] Failed to get protocol version")
        return 1

    if version < 0x10:
        print(f"    protocol version {hex(version)} is not guaranteed to be supported.")
    else:
        print(f"    protocol version: {hex(version)}")

    print("[+] Getting device ID...")
    device_id = flasher.get_device_id()
    if device_id:
        print(f"    Device ID: {hex(device_id)}")
        device = get_device(device_id)
        print(f"    Device Name: {device['name']}")
    else:
        print("[-] Failed to retrieve device ID.")
        return 1

    ext = os.path.splitext(args.firmware)[-1]
    if ext == ".bin":
        result = flash_bin(flasher, device, args.firmware)
    elif ext == ".elf":
        result = flash_elf(flasher, device, args.firmware)
    else:
        print("[-] firmware must be .bin or .elf.")
        return 1

    if result == 1:
        return 1

    print("[+] Run firmware...")
    if flasher.run_firmware(device["flash_addr"]):  # 最初のセグメントのアドレスで実行
        print("[+] Run firmware success")
    else:
        print("[-] Run firmware failed")

    flasher.close()


# 実行
if __name__ == "__main__":
    exit(main())
