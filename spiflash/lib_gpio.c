#include <stdio.h>
#include <fcntl.h>
#include <stdint.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define GPIO_BASE 0xFE200000  // in case of Raspberry Pi 4
#define GPIO_LEN  4096        // mapping size
#define GPIO_REGS_GPFSEL0  0x00  // GPIO Function Select 0 register

void setup_gpio(int gpio_pin) {
    int mem_fd = open("/dev/gpiomem", O_RDWR | O_SYNC);
    if (mem_fd < 0) {
        perror("Failed to open /dev/gpiomem");
        return;
    }

    // Memory mapping
    void *gpio_map = mmap(NULL, GPIO_LEN, PROT_READ | PROT_WRITE, MAP_SHARED, mem_fd, GPIO_BASE);
    if (gpio_map == MAP_FAILED) {
        perror("Failed to map GPIO memory");
        close(mem_fd);
        return;
    }

    // Pointer to GPFSEL register
    uint32_t *gpfsel = (uint32_t *)(gpio_map + GPIO_REGS_GPFSEL0);

    int reg_idx = gpio_pin / 10;
    int shift = (gpio_pin % 10) * 3;

    uint32_t reg_value = gpfsel[reg_idx];
    reg_value &= ~(0b111 << shift);  // clear current bits
    reg_value |= (0b001 << shift);   // set alt mode to Output
    gpfsel[reg_idx] = reg_value;

    // cleanup
    munmap(gpio_map, GPIO_LEN);
    close(mem_fd);
}

static PyObject* gpio_reset(PyObject* self, PyObject* args) {
    int pin;
    if (!PyArg_ParseTuple(args, "i", &pin)) {
        return NULL;
    }

    setup_gpio(pin);

    return Py_BuildValue("i", 0);
}

static PyMethodDef GpioMethods[] = {
    {"gpio_reset", gpio_reset, METH_VARARGS, "Reset GPIO alt mode to Output"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef lib_gpio_module = {
    PyModuleDef_HEAD_INIT,
    "lib_gpio",  // Module name
    NULL,        // Module documentation (optional)
    -1,          // Indicates the module keeps state, -1 means it does not
    GpioMethods
};

// Module initialization function
PyMODINIT_FUNC PyInit_lib_gpio(void) {
    return PyModule_Create(&lib_gpio_module);
}