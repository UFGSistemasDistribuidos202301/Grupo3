#Libraries
from datetime import datetime, date, timedelta
#import RPi.GPIO as GPIO
import time, os, json, _thread, yaml
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe

try:
    import asyncio
except ImportError:
    import trollius as asyncio

class Controle(object):
    def __init__(self):
        self.__client = mqtt.Client()
        self.__client.connect(host="localhost", port=1883)
        self.__client.loop_start()
        self.__velocities = list()
        self.__velocities.append(list())
        self.__velocities.append(list())
        self.__velocities.append(list())
        self.__velocities.append(list())

        self.__topic_radar = "dados_trafego"
        self.__log_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ),))+'/logs.log'

        _thread.start_new_thread(self.subscribe_radar, ())

    def log(self, msg):
        string = '{} - {}'.format(str(datetime.now()), msg)
        os.system(f"echo '{string}' >> {self.__log_file}")
    
    def loop_stop(self):
        try:
            self.__client.loop_stop()
        except:
            pass
    
    def media(self, street):
        sum = 0
        now = datetime.now()
        
        for v in self.__velocities[street-1]:
            date_obj = datetime.strptime(v["time"], '%Y-%m-%d %H:%M:%S.%f')
            if(date_obj > (now - timedelta(minutes=5))):
                sum+=int(v["velocity"])

        return sum/len(self.__velocities[street-1])

    def on_message_radar(self, client, userdata, message):
        decoded_message = json.loads(message.payload.decode())
        street = decoded_message["street"]
        try:
            if(len(self.__velocities[street-1])==10):
                self.__velocities[street-1].pop(0)
            
            self.__velocities[street-1].append(decoded_message)
            media = self.media(street)
            self.log("Street: {}, Velocity: {}".format(street, media))
        except Exception as e:
            print(e)

    
    def subscribe_radar(self):
        subscribe.callback(self.on_message_radar, self.__topic_radar)


if __name__ == '__main__':
    try:
        controle = Controle()
        
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            controle.loop_stop()
 
        # Reset by pressing CTRL + C
    except (KeyboardInterrupt, SystemExit):
        pass