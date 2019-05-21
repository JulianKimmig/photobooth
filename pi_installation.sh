#!/usr/bin/env bash

echo 'deb [trusted=yes] http://dl.bintray.com/yoursunny/PiZero stretch-backports main' | sudo tee  /etc/apt/sources.list.d/bintray-yoursunny-PiZero.list
sudo apt update -y
sudo apt upgrade -y

#libs


# python, pip
sudo apt-get install python3 python3-pip python3-opencv git -y
alias python=python3
alias pip=pip3
git clone https://github.com/JulianKimmig/photobooth.git

cd photobooth

pip3 install -r requirements.txt

sudo apt install openbox obconf obmenu midori -y
sudo apt-get --no-install-recommends install xserver-xorg xserver-xorg-video-fbdev xinit pciutils xinput xfonts-100dpi xfonts-75dpi xfonts-scalable -y
mkdir -p ~/.config/openbox && cp /etc/xdg/openbox/* ~/.config/openbox

echo "sleep 5s && midori  --inactivity-reset=300 -e Fullscreen -a 'http://localhost:8000/'" >> ~/.config/openbox/autostart

echo "/usr/bin/openbox-session">~/.xsession
echo "while [ \$(nc -w 1 localhost 8000 </dev/null; echo \$?) -gt 0 ];do echo 'wait for server to start';sleep 2;done;startx -- -nocursor" > ~/start_screen.sh

echo "if [[ -z \$DISPLAY ]] && [[ \$(tty) = /dev/tty1 ]]; then cd ~/photobooth;sleep 5; git pull; python3 ~/photobooth/manage.py runserver 0.0.0.0:8000& sleep 5;  ~/start_screen.sh& fi" > ~/.bash_profile
#sudo raspi-config
   # 3 boot-oprtion
   # autologin to textconsole


#picamera support
#sudo nano /boot/config.txt
#start_x=1             # essential
#gpu_mem=128           # at least, or maybe more if you wish
#disable_camera_led=0  # optional, if you don't want the led to glow

#dls support
sudo apt install gphoto2 -y
