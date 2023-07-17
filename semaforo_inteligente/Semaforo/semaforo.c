/*
* Includes
*/
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <MQTTClient.h>
#include <cjson/cJSON.h>
 
/*
* Defines
*/
/* Caso desejar utilizar outro broker MQTT, substitua o endereco abaixo */
#define MQTT_ADDRESS   "tcp://127.0.0.1:1883"
/* Substitua este por um ID unico em sua aplicacao */
#define CLIENTID       "mqttx_2cf766b5"  
 
/* Substitua aqui os topicos de publish e subscribe por topicos exclusivos de sua aplicacao */
#define MQTT_PUBLISH_TOPIC     "semaforo_error"
#define MQTT_SUBSCRIBE_TOPIC   "semaforo_temporizadores"
 
/*
*  Variaveis globais
*/
MQTTClient client;

/**
 * @brief Vetor de timers
 * 0 - Vermelho
 * 1 - Amarelo
 * 2 - Verde
 */
int timers[3] = {65, 5, 55};
 
/*
* Prototipos de funcao
*/
void publish(MQTTClient client, char* topic, char* payload);
int on_message(void *context, char *topicName, int topicLen, MQTTClient_message *message);
 
/*
* Implementacoes
*/
 
/* Funcao: publicacao de mensagens MQTT
 * Parametros: cleinte MQTT, topico MQTT and payload
 * Retorno: nenhum
*/
void publish(MQTTClient client, char* topic, char* payload) {
    MQTTClient_message pubmsg = MQTTClient_message_initializer;
 
    pubmsg.payload = payload;
    pubmsg.payloadlen = strlen(pubmsg.payload);
    pubmsg.qos = 2;
    pubmsg.retained = 0;
    MQTTClient_deliveryToken token;
    MQTTClient_publishMessage(client, topic, &pubmsg, &token);
    MQTTClient_waitForCompletion(client, token, 1000L);
}
 
/* Funcao: callback de mensagens MQTT recebidas e echo para o broker
 * Parametros: contexto, ponteiro para nome do topico da mensagem recebida, tamanho do nome do topico e mensagem recebida
 * Retorno : 1: sucesso (fixo / nao ha checagem de erro neste exemplo)
*/
int on_message(void *context, char *topicName, int topicLen, MQTTClient_message *message) {
    char* payload = message->payload;
 
    /* Mostra a mensagem recebida */
    printf("Mensagem recebida! \n\rTopico: %s Mensagem: %s\n", topicName, payload);
 
    /* Faz echo da mensagem recebida */
    publish(client, MQTT_PUBLISH_TOPIC, payload);
 
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}
 
int main(int argc, char *argv[]){
   int rc;
   MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
 
   /* Inicializacao do MQTT (conexao & subscribe) */
   MQTTClient_create(&client, MQTT_ADDRESS, CLIENTID, MQTTCLIENT_PERSISTENCE_NONE, NULL);
   MQTTClient_setCallbacks(client, NULL, NULL, on_message, NULL);
 
   rc = MQTTClient_connect(client, &conn_opts);
 
   if (rc != MQTTCLIENT_SUCCESS)
   {
       printf("\n\rFalha na conexao ao broker MQTT. Erro: %d\n", rc);
       exit(-1);
   }
 
   MQTTClient_subscribe(client, MQTT_SUBSCRIBE_TOPIC, 0);
 
   while(1)
   {
       /*
        * o exemplo opera por "interrupcao" no callback de recepcao de 
        * mensagens MQTT. Portanto, neste laco principal eh preciso fazer
        * nada.
        */
   }
}