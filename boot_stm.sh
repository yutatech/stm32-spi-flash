echo 6 | sudo tee /sys/class/gpio/export
echo out | sudo tee /sys/class/gpio/gpio6/direction
echo 1 | sudo tee /sys/class/gpio/gpio6/value

./reset_stm.sh
sleep 2
echo 0 | sudo tee /sys/class/gpio/gpio6/value
echo 6 | sudo tee /sys/class/gpio/unexport
