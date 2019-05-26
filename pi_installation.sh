#!/usr/bin/env bash
#beefore running this:
#sudo -raspi-config:
    # change pass 1
    #
#git clone https://github.com/JulianKimmig/photobooth.git
#sh photobooth/pi_installation.sh

echo 'deb [trusted=yes] http://dl.bintray.com/yoursunny/PiZero stretch-backports main' | sudo tee  /etc/apt/sources.list.d/bintray-yoursunny-PiZero.list
sudo apt update -y
sudo apt upgrade -y

sudo apt-get install --no-install-recommends xserver-xorg x11-xserver-utils xinit openbox chromium-browser -y

sudo apt-get install python3 python3-pip python3-opencv git libcblas-dev libhdf5-dev libhdf5-serial-dev libatlas-base-dev libjasper-dev libqtgui4 libqt4-test gphoto2 libzbar0 libgstreamer1.0-0 xserver-xorg-legacy -y
alias python=python3
alias pip=pip3
cd photobooth
pip3 install -r requirements.txt



echo -e "xset s off\n xset s noblank\n xset -dpms\n setxkbmap -option terminate:ctrl_alt_bksp\n\n sed -i 's/\"exited_cleanly\":false/\"exited_cleanly\":true/' ~/.config/chromium/'Local State'\n sed -i 's/\"exited_cleanly\":false/\"exited_cleanly\":true/; s/\"exit_type\":\"[^\"]\+\"/\"exit_type\":\"Normal\"/' ~/.config/chromium/Default/Preferences\n chromium-browser --disable-infobars --kiosk 'http://localhost:8000/'\n" | sudo tee /etc/xdg/openbox/autostart
echo -e "if [[ -z \$DISPLAY ]] && [[ \$(tty) = /dev/tty1 ]]; then\n cd ~/photobooth\n sleep 5\n git pull\n python3 ~/photobooth/manage.py runserver 0.0.0.0:8000&\n sleep 5\n ~/start_screen.sh&\nfi" > ~/.bash_profile
echo -e "while [ \$(nc -w 1 localhost 8000 </dev/null; echo \$?) -gt 0 ];do\n echo 'wait for server to start'\n sleep 2\n done\n startx -- -nocursor" > ~/start_screen.sh
chmod +x ~/start_screen.sh

sudo usermod -a -G tty pi

echo -e "start_x=1\ngpu_mem=512\ndisable_camera_led=1" | sudo tee -a /boot/config.txt

#printer
sudo apt-get install cups -y
sudo usermod -a -G lpadmin pi

sudo apt-get install python3-cups -y