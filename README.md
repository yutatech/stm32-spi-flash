# stm32-spi-flash

This project is a firmware uploader for STM32, utilizing the Raspberry Pi’s SPI bus for communication.

## How to install

```sh
pip install git+https://github.com/yutatech/stm32-spi-flash
```

## Usage

1. Boot target STM32 from bootloader

2. Run command

```sh
spiflash binarly.bin
spiflash elf.elf
spiflash --spi-bus 0 --spi-cs 0 --spi-speed 4000000 binary.bin
```

## Debug

```sh
cd stm32-spi-flash
python3 -m spiflash.spiflash
```

## Enabling SPI Bus

Edit `/boot/firmware/config.txt`

Please see `/boot/firmware/README` for details.

## References

- [AN4286 - SPI protocol used in the STM32 bootloader](https://www.st.com/resource/en/application_note/an4286-spi-protocol-used-in-the-stm32-bootloader-stmicroelectronics.pdf)
- [AN2606 - STM32 microcontroller system memory boot mode](https://www.st.com/content/ccc/resource/technical/document/application_note/b9/9b/16/3a/12/1e/40/0c/CD00167594.pdf/files/CD00167594.pdf/jcr:content/translations/en.CD00167594.pdf)