from setuptools import setup, find_packages

setup(
    name="spiflash",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "spiflash=spiflash.spiflash:main",  # `spiflash` コマンドで実行
        ],
    },
    author="Yuta Fujiyama",
    author_email="yuta.technology@gmail.com",
    description="This project is a firmware uploader for STM32, utilizing the Raspberry Pi's SPI bus for communication.",
    url="https://github.com/yutatech/stm32-spi-flash",
)
