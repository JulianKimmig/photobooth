sudo apt update
sudo apt upgrade

#libs
echo 'deb [trusted=yes] http://dl.bintray.com/yoursunny/PiZero stretch-backports main' | sudo tee  /etc/apt/sources.list.d/bintray-yoursunny-PiZero.list
sudo apt update
sudo apt install python3-opencv

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
cd  ~/photobooth
git pull
#python3 ~/photobooth/manage.py runserver &
#startx -- -nocursor
#fi
sudo raspi-config
   # 3 boot-oprtion
   # autologin to textconsole


sudo apt install gphoto2 -y
