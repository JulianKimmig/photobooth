sudo apt update
sudo apt upgrade

# python, pip
sudo apt-get install python3 -y
sudo apt-get install python3-pip -y
sudo apt-get install git -y
alias python=python3

git clone https://github.com/JulianKimmig/photobooth.git

cd photobooth

pip3 install -r requirements.txt

sudo apt install openbox obconf obmenu midori -y
sudo apt-get --no-install-recommends install xserver-xorg xserver-xorg-video-fbdev xinit pciutils xinput xfonts-100dpi xfonts-75dpi xfonts-scalable -y
mkdir -p ~/.config/openbox && cp /etc/xdg/openbox/* ~/.config/openbox

nano ~/.config/openbox/autostart
sleep 5s && midori  --inactivity-reset=120 -e Fullscreen "http://localhost:8000"

echo "/usr/bin/openbox-session">~/.xsession
nano ~/.bash_profile
#add
#if [[ -z $DISPLAY ]] && [[ $(tty) = /dev/tty1 ]]; then
#python3 ~/photobooth/manage.py runserver &
#startx -- -nocursor
#fi
sudo raspi-config
   # 3 boot-oprtion
   # autologin to textconsole


sudo apt install gphoto2 -y
