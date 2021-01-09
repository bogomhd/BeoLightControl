#!/usr/bin/python3
import yaml
import json
import requests
import time
import sys
import shutil
from os import system, path
from threading import Thread

from zeroconf import ServiceBrowser, Zeroconf
import ipaddress

import http.client
configuration_file = "BeoLightControl.yaml"
config_hue_bridge = "Hue bridge"
config_hue_token = "token"
config_product = "Beo product"
config_product_name = "name"
config_ip = "ip"

headers = {"Content-Type": "application/json"}

brightness_steps = 20

class ConnectionData:

    def __init__(self, hue_api_url_base, hue_api_url_light, hue_control_url, hue_id, beo_device_ip, beo_device_name):
        # http://192.168.195.141/api/*token*/lights/12
        # http://192.168.195.141/api/*token*/groups/1/
        self.hue_id = hue_id
        self.hue_id_url = hue_api_url_base + hue_api_url_light + "/" + hue_id

        self.hue_control_url = hue_control_url

        # http://192.168.195.141/api/*token*/lights/12/state
        # http://192.168.195.141/api/*token*/groups/1/action
        self.hue_control_url_full = hue_api_url_base + hue_api_url_light + "/" + hue_id + "/" + hue_control_url
        self.beo_notifications_url = 'http://' + beo_device_ip + ":8080/BeoNotify/Notifications?lastId="

        self.beo_device_ip = beo_device_ip
        self.beo_device_name = beo_device_name

        self.headers = {'Content-Type': 'application/json'}
        self.interrupt = False


class BeoLightControl:

    def __init__(self):
        self.connection_dict = {}
        self.conn_data = None
        self.devices_discovered = {}
        self.beo_device_ip = ""
        self.beo_device_name = ""

        self.hue_api_ip = ""
        self.hue_api_url_base = ""
        self.hue_api_url_groups = ""
        self.hue_api_url_light = ""
        self.hue_api_token = ""
        self.hue_id = ""
        self.hue_light_name = ""

        self.listner_thread = None

    def toggle_light(self):
        dump = {}
        response = requests.get(self.conn_data.hue_id_url, headers=headers)
        if response.status_code == 200:
            dump = json.loads(response.content.decode('utf-8'))
        else:
            print ("Something went wrong http status code: " + response.status_code)
            return

        current_state = bool(dump[self.conn_data.hue_control_url]['on'])
        if not current_state:
            data = '{"on":' + str(not current_state).lower() + ', "bri": 254}'
        else:
            data = '{"on":' + str(not current_state).lower() + '}'

        #print (data)
        requests.put(self.conn_data.hue_control_url_full, headers=headers, data=data)

    def change_brightness(self, event_key: str, key_press: bool):
        if key_press:
            dump = {}
            response = requests.get(self.conn_data.hue_id_url, headers=headers)
            if response.status_code == 200:
                dump = json.loads(response.content.decode('utf-8'))
            else:
                print ("Something went wrong http status code: " + response.status_code)
                return

            if event_key == "Down":
                data = '{"bri_inc":-254, "transitiontime":30}'
            else:
                if not bool(dump[self.conn_data.hue_control_url]['on']):
                    # If the light is off we turn it on and start the transistion
                    requests.put(self.conn_data.hue_control_url_full, headers=headers, data='{"on": true, "bri": 0}')
                    data = '{"bri_inc":254, "transitiontime":30}'
                else: 
                    data = '{"bri_inc":254, "transitiontime":30}'

        else:
            data = '{"bri_inc":0}'

        requests.put(self.conn_data.hue_control_url_full, headers=headers, data=data)

    def handle_event(self, event_key: str, key_press: bool):
        #print ("Light key:" + event_key + " press: " + str(key_press))
        if key_press and event_key == "Select":
            self.toggle_light()
        if event_key == "Up" or  event_key == "Down":
            self.change_brightness(event_key, key_press)

    def product_select(self, message):
        selection = 0

        _ = system('clear')
        print (message)
        product_list = {}
        for i, product in enumerate(self.devices_discovered):
            product_list[i] = {}
            product_list[i][product] = self.devices_discovered[product]

        for product in product_list:
            print (str(product) + ": " + str(product_list[product]))

        while True:
            selection = ""
            try:
                selection = int(input(""))
            except ValueError:
                pass
            if selection in product_list:
                break
            else:
                print("Invalid selection. Pick another!")

        return list(product_list[selection].keys())[0]

    def group_select(self):
        _ = system('clear')

        print ("Please select which group:")
        
        response = requests.get(self.hue_api_url_groups, headers=headers)
        if response.status_code == 200:
            dump = json.loads(response.content.decode('utf-8'))
        else:
            print ("Error talking to Hue Bridge!")
            return ""
        
        groups = {}
        for element in dump:
            groups[element] = dump[element]['name']
            print (element + ": " + dump[element]['name'])

        selection = input("")
        return selection, dump[selection]['name']

    def light_select(self):
        _= system('clear')

        print ("Please select which group:")
        
        response = requests.get(self.hue_api_url_light, headers=headers)
        if response.status_code == 200:
            dump = json.loads(response.content.decode('utf-8'))
        else:
            print ("Error talking to Hue Bridge!")
            return ""
        
        lights = {}
        for element in dump:
            lights[element] = dump[element]['name']
            print (element + ": " + dump[element]['name'])

        selection = input("")
        return selection, dump[selection]['name']

    def listner(self):
        last_id = "0"
        while True:
            try:
                #print ("notification url: " + self.conn_data.beo_notifications_url + last_id)
                r = requests.get(self.conn_data.beo_notifications_url + last_id, stream=True, timeout=20)

                for line in r.iter_lines():
                    if self.conn_data.interrupt:
                        return

                    # Skip keep-alive new lines
                    if line:
                        decoded_line = line.decode('utf-8')
                        new_event = json.loads(decoded_line)
                        if 'notification' in new_event:
                            if 'data' in new_event['notification']:
                                data = new_event['notification']['data']
                                if 'category' in data:
                                    if data['category'] == 'Light':
                                        self.handle_event(data['key'], (data['event'] == 'KeyPress'))
                            last_id = str(new_event['notification']['id'])
                time.sleep(0.05)
            except:
                last_id = "0"
                print ("Problem with connection to the product! Error: " + str(sys.exc_info()[0]) + "... retry in 5 sec.")
                time.sleep(5)
                        
    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        self.devices_discovered[str(ipaddress.IPv4Address(info.addresses[0]))] = info.get_name()

    def discover_devices(self, service):
        self.devices_discovered = {}
        zeroconf = Zeroconf()
        ServiceBrowser(zeroconf, service, self)
        try:
            print ("Updating list of devices in the network...")
            l = 50

            # Initial call to print 0% progress
            self.printProgressBar(0, l, prefix='Progress:', suffix='Complete', length=50, autosize=True)
            for i in range(0,l):
                time.sleep(0.1)
                # Update Progress Bar
                self.printProgressBar(i + 1, l, prefix='Progress:', suffix='Complete', length=50, autosize=True)
            
        finally:
            zeroconf.close()

    def select_hue_bridge(self):
        self.discover_devices("_hap._tcp.local.")
        self.hue_api_ip = self.product_select("Please select your Philps Hue Bridge:")
        print ("Hue Bridge IP: " + self.hue_api_ip)

    def select_beo_product(self):
        self.discover_devices("_beoremote._tcp.local.")
        self.beo_device_ip = self.product_select("Please select which product you want to configure:")
        self.beo_device_name = self.devices_discovered[self.beo_device_ip]

        config = {}
        with open(configuration_file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        
        config[config_product] = {config_product_name: self.beo_device_name, config_ip: self.beo_device_ip}
        with open(configuration_file, "w") as file:
            yaml.dump(config, file)

    def generate_hue_urls(self):
        self.hue_api_url_base = "http://" + self.hue_api_ip + "/api/" + self.hue_api_token + "/"
        self.hue_api_url_groups = self.hue_api_url_base + "groups"
        self.hue_api_url_light = self.hue_api_url_base + "lights"

    def load_stored_config(self):
        conf_file_exsists = path.exists(configuration_file)
        #print ("conf file exsists: " + str(conf_file_exsists))
        if conf_file_exsists:
            #Load data
            with open(configuration_file) as file:
                config = yaml.load(file, Loader=yaml.FullLoader)
                if config_ip in config[config_hue_bridge]:
                    self.hue_api_ip = config[config_hue_bridge][config_ip]
                else:
                    print ("Error with ip in config file")
                    return False

                if config_hue_token in config[config_hue_bridge]:
                    self.hue_api_token = config[config_hue_bridge][config_hue_token]
                else:
                    print ("Error with token in config file")
                    return False

                if config_product in config:
                    if config_product_name in config[config_product]:
                        self.beo_device_name = config[config_product][config_product_name]
                    
                    if config_ip in config[config_product]:
                        self.beo_device_ip = config[config_product][config_ip]
                    
        else:
            return False
        
        return True

    def setup_hue_config(self):

        self.select_hue_bridge()
        data = '{"devicetype":"BeoLightControl"}'

        button_pressed = False
        while not button_pressed:
            response = requests.post("http://" + self.hue_api_ip + "/api", headers=headers, data=data)
            if response.status_code == 200:
                dump = json.loads(response.content.decode('utf-8'))[0]
                if 'error' in dump:
                    input("Please press the button on the Philips Hue Bridge and press enter\n")
                else:
                    print ("Connected to Philips Hue Bridge successfully!")
                    self.hue_api_token = dump['success']['username']
                    time.sleep(3)
                    button_pressed = True
            else:
                print ("Error! HTTP Connection error code: " + response.status_code)
        
        if self.hue_api_token == "":
            print ("Error! No Hue token")
            return

        dict_file = {config_hue_bridge : {config_ip : self.hue_api_ip, config_hue_token : self.hue_api_token}}

        with open(configuration_file, "w") as file:
                yaml.dump(dict_file, file)
        


    def stop_lister(self):
        if self.listner_thread:
            if self.listner_thread.is_alive:
                self.conn_data.interrupt = True
                print ("Stopping listner...")
                self.listner_thread.join()

    def start(self):

        if not self.load_stored_config():
            self.setup_hue_config()

        self.generate_hue_urls()

        #print ("IP: " + self.hue_api_ip + " Token: " + self.hue_api_token)
        _= system('clear')
             
        hue_control_path = ""
        hue_api_url_light = ""


        while True:
            _= system('clear')
            print ("Current settings:\nProduct: " + self.beo_device_name + "\nLight/Group: " + self.hue_light_name)
            val = input("\nWhat do you want to do?\n1: Select product\n2: Select Light or Group\n3: Start/Stop listner\n4: Quit\n")

            if val == "1":
                _= system('clear')
                
                self.select_beo_product()                
            elif val == "2":
                _= system('clear')
                val = input("What to you want to control?\n1: Light\n2: Group\n") 

                if val == "1":
                    hue_control_path = "state"
                    hue_api_url_light = "lights"

                    self.hue_id, self.hue_light_name = self.light_select()
                else:
                    hue_control_path = "action"
                    hue_api_url_light = "groups"

                    self.hue_id, self.hue_light_name = self.group_select()

                _ = system('clear')
                    
            elif val == "3":
                _= system('clear')
                val = input("Do you want to start or stop the listner?\n1: Start\n2: Stop\n")
                if val == "1":
                    self.conn_data = ConnectionData(self.hue_api_url_base, hue_api_url_light, hue_control_path, self.hue_id, self.beo_device_ip, self.beo_device_name)
                    try:
                        self.listner_thread = Thread(target=self.listner)
                        
                    except:
                        print ("ERROR!")

                    print ("Started to listen to events from " + self.beo_device_ip)

                    self.listner_thread.start()
                    time.sleep(5)
                else:
                    self.stop_lister()
                    _= system('clear')
                    print ("Listner stopped!")
                    time.sleep(3)

            else:
                self.stop_lister()
                return        

    # Borrowed from: https://gist.github.com/greenstick/b23e475d2bfdc3a82e34eaa1f6781ee4
    def printProgressBar (self, iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', autosize = False):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            autosize    - Optional  : automatically resize the length of the progress bar to the terminal window (Bool)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        styling = '%s |%s| %s%% %s' % (prefix, fill, percent, suffix)
        if autosize:
            cols, _ = shutil.get_terminal_size(fallback = (length, 1))
            length = cols - len(styling)
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print('\r%s' % styling.replace(fill, bar), end = '\r')
        # Print New Line on Complete
        if iteration == total: 
            print()


beoLightControl = BeoLightControl()
beoLightControl.start()
