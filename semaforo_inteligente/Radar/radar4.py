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
        self.__id = 4
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
            velocity = round(random.uniform(20.0, 80.0), 2)
            num_cars = random.randint(0, 100)
            msg = {"street": self.__id, "cars": num_cars, "mean velocity": velocity, "time": str(datetime.now())}
            self.log(msg)
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