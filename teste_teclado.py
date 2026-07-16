import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

LINHAS = [5, 6, 13, 19]
COLUNAS = [26, 16, 20, 21]

TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

for l in LINHAS:
    GPIO.setup(l, GPIO.OUT)
    GPIO.output(l, GPIO.HIGH)

for c in COLUNAS:
    GPIO.setup(c, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def ler_teclado():
    for i, linha_pin in enumerate(LINHAS):
        GPIO.output(linha_pin, GPIO.LOW) # Ativa linha
        for j, col_pin in enumerate(COLUNAS):
            if GPIO.input(col_pin) == GPIO.LOW: # Tecla pressionada detetada
                while GPIO.input(col_pin) == GPIO.LOW: 
                    time.sleep(0.01) # Debounce simples
                GPIO.output(linha_pin, GPIO.HIGH)
                return TECLAS[i][j]
        GPIO.output(linha_pin, GPIO.HIGH) # Desativa linha
    return None

try:
    print("Aguardando teclas...")
    while True:
        tecla = ler_teclado()
        if tecla:
            print(f"Tecla pressionada: {tecla}")
        time.sleep(0.1)
finally:
    GPIO.cleanup()
