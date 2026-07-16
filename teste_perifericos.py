import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Mapeamento de Pinos
TRIG_PIN = 14    # Pino que envia o pulso ultrassónico (Saída)
ECHO_PIN = 15    # Pino que recebe o retorno (Entrada - Requer Divisor de Tensão)
BUZZER_PIN = 12  # Buzzer
TRINCO_PIN = 23  # Relé do Trinco

# Configuração dos Pinos
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(TRINCO_PIN, GPIO.OUT)

# Garante que o gatilho comece desligado
GPIO.output(TRIG_PIN, GPIO.LOW)
time.sleep(2) # Tempo para o sensor estabilizar

def medir_distancia():
    """Envia um pulso ultrassónico e calcula a distância em cm."""
    # 1. Envia um pulso de 10 microssegundos no pino Trigger
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001) # 10us
    GPIO.output(TRIG_PIN, GPIO.LOW)
    
    # 2. Mede o tempo de início do sinal de Echo (quando vai para HIGH)
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        inicio_pulso = time.time()
        
    # 3. Mede o tempo de fim do sinal de Echo (quando volta para LOW)
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        fim_pulso = time.time()
        
    # 4. Calcula a duração total do pulso
    duracao_pulso = fim_pulso - inicio_pulso
    
    # 5. Calcula a distância baseada na velocidade do som (34300 cm/s)
    # Dividido por 2 porque a onda vai e volta
    distancia = (duracao_pulso * 34300) / 2
    
    return round(distancia, 2)

def bipar(tempo):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(tempo)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

try:
    print("Testando Sensor Ultrassónico na Fechadura...")
    bipar(0.1)
    
    ultimo_estado_aberta = False

    while True:
        distancia = medir_distancia()
        print(f"Distância medida: {distancia} cm")
        
        # DEFINIÇÃO DO LIMIAR: Se a distância for maior que 10 cm, a porta abriu
        if distancia > 10.0:
            if not ultimo_estado_aberta:
                print("ALERTA: Porta aberta! (Distância > 10cm)")
                bipar(0.1) # Dá um bipe rápido de aviso
                ultimo_estado_aberta = True
        else:
            if ultimo_estado_aberta:
                print("Porta fechada/trancada.")
                ultimo_estado_aberta = False
                
        time.sleep(0.5) # Faz uma leitura a cada 500 milissegundos

except KeyboardInterrupt:
    print("\nEncerrando...")
finally:
    GPIO.cleanup()
    print("GPIO limpo e seguro.")
