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
    def __init__(self, semaforos_abertos):
        self.__id = 2
        self.__topic = 'dados_trafego'
        self.__client = mqtt.Client()

        self.__semaforos_abertos = semaforos_abertos  # Recebe o estado dos semáforos

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
    
    def adjust_data_on_signal_close(self):
        self.__num_cars = min(self.__num_cars + 10, 100)  # Limita a 100 carros
        self.__velocity = max(self.__velocity - 10, 0)  # Diminui a velocidade até 0        

    def publish_vel(self):
        num_cars = 10
        while True:
            if self.__semaforos_abertos[self.__id]:
                if num_cars > 0:
                    num_cars -= 1  # Simula a saída de um carro da via
                    velocity = random.uniform(20.0, 80.0)  # Velocidade aleatória para carros em movimento
                else:
                    velocity = 0  # Sem carros na via, velocidade é 0
            else:
                if num_cars < 100:
                    num_cars += 1  # Simula a entrada de um carro na via
                velocity = 0  # Sinal fechado, velocidade é 0
            
            msg = {"street": self.__id, "velocity": velocity, "cars": num_cars, "time": str(datetime.now())}
            self.log(msg)
            self.__client.publish(self.__topic, json.dumps(msg))
            time.sleep(2)

if __name__ == '__main__':
    try:
        semaforos_abertos = {1: True, 2: False, 3: True, 4: False}
        radar = Radar(semaforos_abertos)
        
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            radar.loop_stop()
            pass 
    except (KeyboardInterrupt, SystemExit):
        pass    