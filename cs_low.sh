echo 25 | sudo tee /sys/class/gpio/export
echo out | sudo tee /sys/class/gpio/gpio25/direction
echo 0 | sudo tee /sys/class/gpio/gpio25/value
