import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

SENSOR_PIN = 22 # Chave fim de curso (Pull-Up)
BUZZER_PIN = 12 # Buzzer
TRINCO_PIN = 23 # Relé do Trinco

GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(TRINCO_PIN, GPIO.OUT)

def bipar(tempo):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(tempo)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

def monitorar_porta(canal):
    if GPIO.input(SENSOR_PIN) == GPIO.HIGH:
        print("ALERTA: Porta aberta!")
    else:
        print("Porta fechada/trancada.")

# Configuração de interrupção física por mudança de estado
GPIO.add_event_detect(SENSOR_PIN, GPIO.BOTH, callback=monitorar_porta, bouncetime=300)

try:
    print("Testando periféricos. Aproxime/afaste o sensor...")
    bipar(0.1)
    while True:
        time.sleep(1)
finally:
    GPIO.cleanup()
