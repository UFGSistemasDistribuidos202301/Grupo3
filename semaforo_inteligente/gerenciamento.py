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

        self.__topic_semaforo = "semaforo_temporizadores"

        self.__topic_radar = "dados_trafego"
        self.__log_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ),))+'/logs.log'

         # Dicionário para armazenar o tempo aberto de cada semáforo (inicializado como 0)
        self.__signal_open_time = {1: timedelta(seconds=10), 2: timedelta(seconds=10), 3: timedelta(seconds=10), 4: timedelta(seconds=10)}
        
        # inicia os semáforos ímpares como abertos
        self.__semaforos_abertos = {1: True, 2: False, 3: True, 4: False}

        # dicionário para guardar o horario em que o semáforo foi aberto
        self.__horario_verde = {1: datetime.now(), 2: None, 3: datetime.now(), 4: None}

        # ficará ouvindo as mensagens MQTT relacionadas aos dados de tráfego
        thread_id = _thread.start_new_thread(self.subscribe_radar, ())

    def log(self, msg):
        """
        Esse método é usado para registrar mensagens de log
        no arquivo de log definido no construtor.
        Ele grava a data/hora atual e a mensagem passada como
        argumento no arquivo de log.
        """
        string = '{} - {}'.format(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), msg)
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
        total_cars = 0;
        now = datetime.now()
        
        for v in self.__velocities[street-1]:
            date_obj = datetime.strptime(v["time"], '%Y-%m-%d %H:%M:%S')
            if(date_obj > (now - timedelta(minutes=5))):
                sum += int(v["mean velocity"])
                total_cars += int(v["cars"])

        if total_cars > 0:
            return round(sum/len(self.__velocities[street-1]), 2)
        else:
            return 0

    def count_signal_open_time(self, semaforo_id):
        if semaforo_id in self.__semaforos_abertos and self.__semaforos_abertos[semaforo_id]:
            current_time = datetime.now()
            signal_open_time = current_time - self.__signal_open_time[semaforo_id]
            return signal_open_time.total_seconds()
        else:
            return 0  # Retorna 0 se o sinal não estiver aberto
    
    def adjust_signal_timing(self, semaforo_id, additional_time):
        """
        Esse método corrige o tempo em que o semáforo
        ficará aberto. Não permite que um semáforo fique
        mais de 120s (2 minutos) aberto.
        """
        if semaforo_id in self.__semaforos_abertos:
            if additional_time and self.__semaforos_abertos[semaforo_id]:
                current_open_time = self.__signal_open_time[semaforo_id]
                new_open_time = current_open_time + timedelta(seconds=additional_time)
                
                if new_open_time.total_seconds() <= 120:
                    self.__signal_open_time[semaforo_id] = new_open_time
                    self.log("Adjusting Signal Timing for 'Semaforo {}': New Open Time = {} seconds".format(semaforo_id, new_open_time.total_seconds()))

                    print("Adjusting Signal Timing for 'Semaforo {}': New Open Time = {} seconds".format(semaforo_id, new_open_time.total_seconds()))
                
                    if semaforo_id == 1:
                        self.__client.publish(self.__topic_semaforo, json.dumps(f'Adjust open time to {new_open_time.total_seconds()}s'))
                else:
                    self.log("Maximum Green Time Exceeded for 'Semaforo {}'. No further adjustment.".format(semaforo_id))
            else:
                self.log("Invalid Additional Time or 'Semaforo {}' is not open. No adjustment.".format(semaforo_id))
        else:
            self.log("Invalid ID: {}. No adjustment.".format(semaforo_id))

    def count_signal_open_time(self, semaforo_id):
        """
        Esse método verifica se semaforo_id é um id
        válido e, caso positivo, verifica se está verde
        retornando o tempo em segundos em que permanece
        aberto.
        """
        if semaforo_id in self.__semaforos_abertos and self.__semaforos_abertos[semaforo_id]:
            return self.__signal_open_time[semaforo_id].total_seconds()
        else:
            return 0

    def on_message_radar(self, client, userdata, message):
        decoded_message = json.loads(message.payload.decode())
        street = decoded_message["street"]

        # controle do tempo em que um semáforo ficar aberto
        # e fecha/abre novos semáforos caso possível

        for semaforo, horario in self.__horario_verde.items():
            if self.__semaforos_abertos[semaforo]:
                time_passed = (datetime.now() - horario).seconds

                if time_passed > self.__signal_open_time[semaforo].seconds:
                    peer_id = ((semaforo + 1) % 4) + 1

                    peer_closed = self.__signal_open_time[peer_id].seconds > \
                                  self.__signal_open_time[semaforo].seconds

                    if peer_closed:
                        opening = datetime.now()

                        for sem_id in [1, 2, 3, 4]:
                            if sem_id in [semaforo, peer_id]:
                                self.__semaforos_abertos[sem_id] = False
                                self.__horario_verde[sem_id] = None
                            else:
                                self.__semaforos_abertos[sem_id] = True
                                self.__horario_verde[sem_id] = opening
                        
                        self.log(f"Semaphors with ID {semaforo} and {peer_id} turned into red.")
                        self.log(f"Semaphors with ID {(semaforo % 4) + 1} and {(peer_id % 4) + 1} turned into green.")

                        print(f"Semaphors with ID {semaforo} and {peer_id} turned into red.")
                        print(f"Semaphors with ID {(semaforo % 4) + 1} and {(peer_id % 4) + 1} turned into green.")
                        break

        try:
            if len(self.__velocities[street - 1]) == 10:
                self.__velocities[street - 1].pop(0)

            self.__velocities[street - 1].append(decoded_message)
            media = self.media(street)
            self.log("Street: {}, Velocity: {}".format(street, media))

            # Implementação do Volume de Tráfego e Densidade de Tráfego
            if media <= 30 and self.__semaforos_abertos[street]:  
                self.log("High Traffic Volume on Street {}".format(street))
                print("High Traffic Volume on Street {}".format(street))
                
                # o tempo será corrigido para tentar subir a velocidade média
                # da via para 30 km/h
                increased_open_time = round((30 / media) * self.__signal_open_time[street].seconds)
                self.adjust_signal_timing(street, increased_open_time)
            elif media >= 50 and self.__semaforos_abertos[street]:
                decrease_open_time = round((50 / media) * self.__signal_open_time[street].seconds)
                self.adjust_signal_timing(street, decrease_open_time)

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