import time
from rpi_lcd import LCD

# Inicializa o LCD no endereço I2C padrão (geralmente 0x27 ou 0x3f)
lcd = LCD(address=0x27, bus=1)

try:
    print("Iniciando teste do display LCD...")
    lcd.clear()
    lcd.text("Fechadura RPi 3", 1)
    lcd.text("Aguardando...", 2)
    time.sleep(3)
    
    lcd.clear()
    lcd.text("Senha Correta!", 1)
    lcd.text("Porta Destravada", 2)
    time.sleep(3)

finally:
    lcd.clear()
