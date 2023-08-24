#Libraries
from datetime import datetime
import random
import json
import time
import os
import paho.mqtt.client as mqtt

try:
    import asyncio
except ImportError:
    import trollius as asyncio

class Radar(object):
    def __init__(self):
        self.__id = 2
        self.__topic = 'dados_trafego'
        self.__client = mqtt.Client()

        self.__client.connect(host='localhost', port=1883)
        self.__client.loop_start()
        self.__log_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ),))+'/logs.log'
        self.publish_vel()

    def log(self, msg):
        string = '{} - {}'.format(str(datetime.now()), msg)
        os.system(f"echo '{string}' >> {self.__log_file}")
    
    def loop_stop(self):
        try:
            self.__client.loop_stop()
        except:
            pass    
    
    def publish_vel(self):
        while(True):
            num_cars = round(random.gauss(mu = 50, sigma = 20))
            num_cars = num_cars if num_cars > 1 else 1

            traffic_factor = (-1) * ((num_cars - 50) * 2) / 5
            
            velocity = round(random.gauss(mu = 40 + traffic_factor, sigma = 15), 2)
            velocity =  velocity if velocity > 5 else 5

            msg = {"street": self.__id, "cars": num_cars, "mean velocity": velocity, "time": str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
            self.log(msg)
            print(msg)

            self.__client.publish(self.__topic, json.dumps(msg))
            time.sleep(2)

if __name__ == '__main__':
    try:
        radar = Radar()
        
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            radar.loop_stop()
            pass 
    except (KeyboardInterrupt, SystemExit):
        pass    