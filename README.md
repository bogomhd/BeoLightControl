# BeoLightControl

A simple program which allow you to control Philips Hue bulbs with a BeoRemote One BT connected to a Bang & Olufsen product. It was made using my spare time and comes with absolutely no warranty.

Should be compatible Bang & Olufsen devices:
BeoPlay M3, M5, A6, A9, Beosound 1, 2, 35, Stage, Core, Shape, Edge, Beovision Eclipse, Beovision Harmony

I use this program with a raspberry pi. But it could be used with any linux machine.

## Installation: 

### Install Raspbian 
Follow instructions on: https://www.raspberrypi.org/downloads/

(You might need to enable SSH and VLC if remote access is needed)

### Install pip3 and packages
```
sudo apt install python3-pip
sudo pip3 install zeroconf requests pyyaml
```
(Other packages might be needed depending on the OS default)


## Usage

### Start the program
1. Open directory in terminal
2. Enter './BeoLightControl.py'
3. Follow the steps presented until you reach the "What do you want to do?" menu.
4. Enter '1' for "Select Light or Group" and follow the setup process.
5. When back in the "What do you want to do?" menu enter '2' and start the lisnter.

Now the program is listning for light events from your Bang & Olufsen product. Give it a go with the remote connected to the product.

### Remote guide:
1. Press list on the remote and navigate to the "Light" entry
2. Press "Select" when "Light" entry is selected
3. Now it says light in the display. 
4. Use select to turn on/off the configured light.
5. Use up/down navigation keys to increase/decrease brightness

NB: The Philips Hue system is not that fast! So if do key presses fast the bridge will buffer those requests and execute them when it can!

If you ever need to reconnect the Phileps Hue Bridge with the app. Just delete the BeoLightControl.yaml file. Then you will be taken through the Philips Hue Bridge configuration again.






