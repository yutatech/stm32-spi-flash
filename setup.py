from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext

setup(
    name="spiflash",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "spiflash=spiflash.spiflash:main",  # `spiflash` コマンドで実行
        ],
    },
    package_data={
        'spiflash': ['devices.yml'],
    },
    author="Yuta Fujiyama",
    author_email="yuta.technology@gmail.com",
    description="This project is a firmware uploader for STM32, utilizing the Raspberry Pi's SPI bus for communication.",
    url="https://github.com/yutatech/stm32-spi-flash",
    install_requires=[
        "spidev",
        "pyelftools",
        "pyyaml",
        "tqdm",
    ],
    python_requires='>=3.7',
    ext_modules=[Extension('lib_gpio', sources=['spiflash/lib_gpio.c'])],
    cmdclass={'build_ext': build_ext},
)
