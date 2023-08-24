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

        # inicia congestionamento como falso em todas as vias
        self.__congestion_detected = {1: False, 2: False, 3: False, 4: False}

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
        total_cars = len(self.__velocities[street-1]);
        now = datetime.now()
        
        for v in self.__velocities[street-1]:
            date_obj = datetime.strptime(v["time"], '%Y-%m-%d %H:%M:%S.%f')
            if(date_obj > (now - timedelta(minutes=5))):
                sum+=int(v["velocity"])
                #total_cars += int(v["cars"])

        if total_cars > 0:
            return sum/total_cars
        else:
            return 0

    def open_signal(self, semaforo_id):
        if semaforo_id in self.__semaforos_abertos and not self.__semaforos_abertos[semaforo_id]:
            self.__semaforos_abertos[semaforo_id] = True
            self.__signal_start_time[semaforo_id] = datetime.now()  # Inicia o tempo de início
            self.log("Opening Semaforo {}".format(semaforo_id))
        else:
            self.log("Semaforo {} is already open or invalid.".format(semaforo_id))

    def close_signal(self, semaforo_id):
        if semaforo_id in self.__semaforos_abertos and self.__semaforos_abertos[semaforo_id]:
            self.__semaforos_abertos[semaforo_id] = False
            self.__signal_open_time[semaforo_id] = None
            self.__signal_start_time[semaforo_id] = None

            # Ajusta os dados do radar quando um sinal é fechado
            for radar_id in self.__radares:
                self.__radares[radar_id].adjust_data_on_signal_close()

            self.log("Closing Semaforo {}".format(semaforo_id))
        else:
            self.log("Semaforo {} is already closed or invalid.".format(semaforo_id))

    def loop_signal_management(self):
        while True:
            for semaforo_id in self.__semaforos_abertos:
                if self.__semaforos_abertos[semaforo_id]:
                    current_time = datetime.now()
                    start_time = self.__signal_start_time[semaforo_id]
                    if start_time is not None:
                        elapsed_time = current_time - start_time
                        if elapsed_time.total_seconds() >= self.__signal_open_time[semaforo_id].total_seconds():
                            self.close_signal(semaforo_id)
                            
                            # Verifica se há congestionamento na via fechada
                            if self.__congestion_detected[semaforo_id]:
                                other_semaforo_id = self.get_other_semaforo_id(semaforo_id)
                                if self.__semaforos_abertos[other_semaforo_id]:
                                    self.open_signal(semaforo_id)
                                else:
                                    self.log(f"Cannot open Semaforo {semaforo_id} due to congestion and other signal being closed.")

            time.sleep(1)  # Pausa de 1 segundo

    def adjust_signal_timing(self, semaforo_id, additional_time):
        if semaforo_id in self.__semaforos_abertos:
            if additional_time > 0 and self.__semaforos_abertos[semaforo_id]:
                current_open_time = self.__signal_open_time[semaforo_id]
                new_open_time = current_open_time + timedelta(seconds=additional_time)

                if new_open_time.total_seconds() <= 120:
                    self.__signal_open_time[semaforo_id] = new_open_time
                    self.__signal_start_time[semaforo_id] = datetime.now()  # Atualiza o tempo de início
                    self.log("Adjusting Signal Timing for Semaforo {}: New Open Time = {} seconds".format(semaforo_id, new_open_time.total_seconds()))
                else:
                    self.log("Maximum Green Time Exceeded for Semaforo {}. No further adjustment.".format(semaforo_id))
            else:
                # Verifica se há congestionamento na outra via e o sinal está fechado
                other_semaforo_id = 1 if semaforo_id == 2 else 2  # Supondo que estamos tratando dos semáforos 1 e 2
                if self.__congestion_detected[other_semaforo_id] and not self.__semaforos_abertos[other_semaforo_id]:
                    time_to_open = self.count_signal_open_time(other_semaforo_id)  # Tempo estimado para abrir o sinal da outra via
                    self.log("Semaforo {} timing adjustment due to congestion. Sinal {} will open after {} seconds when timing from Semaforo {} ends.".format(semaforo_id, other_semaforo_id, time_to_open, semaforo_id))
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
            num_cars = int(decoded_message["cars"])  # Número de carros na via

            self.log("Street: {}, Velocity: {}, Num Cars: {}".format(street, media, num_cars))

            # Se muito tráfego
            if media > 60:
                self.log("High Traffic Volume and Density on Street {}".format(street))
                increased_open_time = 10  # Valor de exemplo para aumentar o tempo
                self.adjust_signal_timing(street, increased_open_time)
            
            # Se está congestionado
            if media < 20 and not self.__congestion_detected[street]:
                self.log("Congestion Detected on Street {}".format(street))
                self.__congestion_detected[street] = True
                self.adjust_signal_timing(street, 20)  # Aumenta o tempo de sinal verde para aliviar o congestionamento
            
            # Se não está mais congestionado e o congestionamento foi detectado
            elif media >= 20 and self.__congestion_detected[street]:
                self.log("Congestion Cleared on Street {}".format(street))
                self.__congestion_detected[street] = False
                self.adjust_signal_timing(street, -20)  # Reduz o tempo de sinal verde após o congestionamento ser aliviado

            """ TRABALHOS FUTUROS
            - Sincronização de Semáforos:
                -- Implemente a sincronização de semáforos ao longo de uma rota para permitir que um veículo mantenha um fluxo contínuo de tráfego.
            - Priorização de Veículos de Emergência:
                -- Implemente um sistema que detecta veículos de emergência (ambulâncias, carros de bombeiros) através de sensores ou sistemas GPS.
            - Detecção de Pedestres:
                -- Integrar sensores para detectar pedestres nas proximidades e ajustar o tempo de sinalização para garantir a segurança dos pedestres.
            - Horário em consideração
            - Histórico em consideração (ML)
            """

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