# Grupo3

### Install mosquitto
###### sudo apt update 
###### sudo apt install -y mosquitto
###### sudo systemctl start mosquitto
###### sudo apt install -y mosquitto-clients

### Install Paho-MQTT
###### pip install paho-mqtt

### Run Radar
##### Radar desempenha o papel do sensor implantado na via. Ele é responsável por coletar informações e enviar a velocidade do veículo para o tópico "dados_tragefo". A quantidade de aplicações Radar.py é equivalente à quantidade de vias pertencentes a um único cruzamento. Cada Radar possui um ID único. Para execução de cada RadarX.py, onde 'X' corresponde ao ID do radar:

###### cd semaforo_inteligente/Radar
###### python3 radarX.py

### Run Gerenciamento
##### A aplicação de gerecniamento é responsável por receber as informações enviados por cada radar e, a partir dos dados coletados, realizar um controle do fluxo de veículos no cruzamento

###### python3 gerenciamento.py
