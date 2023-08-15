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
        """
        O construtor __init__ é responsável por inicializar os
        parâmetros necessários, como a conexão MQTT,
        listas para armazenar velocidades, tópico MQTT e
        arquivo de log.
        """
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

         # Dicionário para armazenar o tempo aberto de cada semáforo (inicializado como 0)
        self.__signal_open_time = {1: timedelta(seconds=0), 2: timedelta(seconds=0), 3: timedelta(seconds=0), 4: timedelta(seconds=0)}
        
        # inicia os semáforos ímpares como abertos
        self.__semaforos_abertos = {1: True, 2: False, 3: True, 4: False}

        # ficará ouvindo as mensagens MQTT relacionadas aos dados de tráfego
        _thread.start_new_thread(self.subscribe_radar, ())

    def log(self, msg):
        """
        Esse método é usado para registrar mensagens de log
        no arquivo de log definido no construtor.
        Ele grava a data/hora atual e a mensagem passada como
        argumento no arquivo de log.
        """
        string = '{} - {}'.format(str(datetime.now()), msg)
        os.system(f"echo '{string}' >> {self.__log_file}")
    
    def loop_stop(self):
        """
        Este método para o loop MQTT do cliente.
        Ele é chamado quando o script precisa parar a conexão MQTT.
        """
        try:
            self.__client.loop_stop()
        except:
            pass
    
    def media(self, street):
        """
        Esse método calcula a média das velocidades dos
        veículos registradas nos últimos 5 minutos
        para uma determinada rua.
        """
        sum = 0
        now = datetime.now()
        
        for v in self.__velocities[street-1]:
            date_obj = datetime.strptime(v["time"], '%Y-%m-%d %H:%M:%S.%f')
            if(date_obj > (now - timedelta(minutes=5))):
                sum+=int(v["velocity"])

        return sum/len(self.__velocities[street-1])
    
    def count_signal_open_time(self, semaforo_id):
        if semaforo_id in self.__semaforos_abertos and self.__semaforos_abertos[semaforo_id]:
            current_time = datetime.now()
            signal_open_time = current_time - self.__signal_open_time[semaforo_id]
            return signal_open_time.total_seconds()
        else:
            return 0  # Retorna 0 se o sinal não estiver aberto
    
    def adjust_signal_timing(self, semaforo_id, additional_time):
        if semaforo_id in self.__semaforos_abertos:
            if additional_time > 0 and self.__semaforos_abertos[semaforo_id]:
                current_open_time = self.__signal_open_time[semaforo_id]
                new_open_time = current_open_time + timedelta(seconds=additional_time)
                
                if new_open_time.total_seconds() <= 120:
                    self.__signal_open_time[semaforo_id] = new_open_time
                    self.log("Adjusting Signal Timing for Semaforo {}: New Open Time = {} seconds".format(semaforo_id, new_open_time.total_seconds()))
                else:
                    self.log("Maximum Green Time Exceeded for Semaforo {}. No further adjustment.".format(semaforo_id))
            else:
                self.log("Invalid Additional Time or Semaforo is not open. No adjustment.")
        else:
            self.log("Invalid Semaforo ID: {}. No adjustment.".format(semaforo_id))

    def count_signal_open_time(self, semaforo_id):
        if semaforo_id in self.__semaforos_abertos and self.__semaforos_abertos[semaforo_id]:
            return self.__signal_open_time[semaforo_id].total_seconds()
        else:
            return 0

    def on_message_radar(self, client, userdata, message):
        decoded_message = json.loads(message.payload.decode())
        street = decoded_message["street"]
        try:
            if len(self.__velocities[street - 1]) == 10:
                self.__velocities[street - 1].pop(0)

            self.__velocities[street - 1].append(decoded_message)
            media = self.media(street)
            self.log("Street: {}, Velocity: {}".format(street, media))

            # Implementação do Volume de Tráfego e Densidade de Tráfego
            if media > 60:  
                self.log("High Traffic Volume on Street {}".format(street))
                increased_open_time = 10  # Valor de exemplo para aumentar o tempo
                self.adjust_signal_timing(street, increased_open_time)
                
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
