import time
import threading
import RPi.GPIO as GPIO
from rpi_lcd import LCD

# ==============================================================================
# 1. CONFIGURAÇÕES GERAIS E MAPEAMENTO DE PINOS
# ==============================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pinos do Teclado Matricial 4x4
LINHAS = [5, 6, 13, 19]
COLUNAS = [26, 16, 20, 21]

# Pinos do Sensor Ultrassónico HC-SR04
TRIG_PIN = 14    # Envia o pulso sonoro
ECHO_PIN = 15    # Recebe o retorno (Requer divisor de tensão: 5V -> 3.3V)

# Pinos dos Atuadores
BUZZER_PIN = 12
TRINCO_PIN = 23

# Teclas mapeadas do teclado matricial
TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

# Configurações do Sistema
SENHA_CORRETA = "1234"
tempo_bloqueio_trinco = 5  # Segundos que a porta fica destrancada
LIMIAR_PORTA_ABERTA = 10.0  # Distância em cm acima da qual a porta é considerada aberta

# Variáveis de Controle Multithreading
porta_aberta = False
lcd_lock = threading.Lock()  # Evita que threads diferentes escrevam no LCD ao mesmo tempo

# Inicialização do LCD via I2C (Endereço padrão 0x27)
try:
    lcd = LCD(address=0x27, bus=1)
except Exception as e:
    print(f"Erro ao inicializar LCD: {e}. Verifique as ligações I2C.")
    lcd = None

# ==============================================================================
# 2. CONFIGURAÇÃO DE HARDWARE (GPIO)
# ==============================================================================
# Configura linhas do teclado como saídas (inicialmente em nível ALTO)
for l in LINHAS:
    GPIO.setup(l, GPIO.OUT)
    GPIO.output(l, GPIO.HIGH)

# Configura colunas do teclado como entradas com Pull-Up interno
for c in COLUNAS:
    GPIO.setup(c, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Configura pinos do Sensor Ultrassónico
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Configura periféricos
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(TRINCO_PIN, GPIO.OUT)

# Garante estados iniciais seguros
GPIO.output(TRIG_PIN, GPIO.LOW)
GPIO.output(TRINCO_PIN, GPIO.LOW)
GPIO.output(BUZZER_PIN, GPIO.LOW)

# ==============================================================================
# 3. FUNÇÕES AUXILIARES E LEITURA DO SENSOR ULTRASSÓNICO
# ==============================================================================
def medir_distancia():
    """Envia um pulso ultrassónico e calcula a distância em cm com proteção contra travamento."""
    # Envia pulso de 10 microssegundos
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)
    
    # Proteção de timeout para evitar travamento em loops infinitos caso o sensor falhe
    timeout = time.time() + 0.1
    inicio_pulso = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        inicio_pulso = time.time()
        if time.time() > timeout:
            return 999.0  # Retorna valor alto em caso de falha de leitura
            
    timeout = time.time() + 0.1
    fim_pulso = time.time()
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        fim_pulso = time.time()
        if time.time() > timeout:
            return 999.0
            
    duracao_pulso = fim_pulso - inicio_pulso
    distancia = (duracao_pulso * 34300) / 2
    return round(distancia, 2)

def bipar(duracao, repeticoes=1, intervalo=0.1):
    """Gera bipes de feedback sonoro de forma síncrona."""
    for _ in range(repeticoes):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duracao)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if repeticoes > 1:
            time.sleep(intervalo)

def atualizar_display(linha1, linha2=""):
    """Escreve mensagens de forma segura no LCD utilizando Locks de sincronização."""
    with lcd_lock:
        if lcd:
            try:
                lcd.clear()
                lcd.text(linha1[:16], 1)
                lcd.text(linha2[:16], 2)
            except Exception as e:
                print(f"Erro no display: {e}")
        print(f"[LCD] L1: '{linha1}' | L2: '{linha2}'")

# ==============================================================================
# 4. MONITORIZAÇÃO ASSÍNCRONA DA PORTA (THREAD EM SEGUNDO PLANO)
# ==============================================================================
def monitorar_porta_thread():
    """Mede a distância continuamente a cada 0.5s para detetar abertura de porta."""
    global porta_aberta
    ultimo_estado = False
    
    # Aguarda o sensor estabilizar
    time.sleep(1)
    
    while True:
        distancia = medir_distancia()
        
        # Se a distância for superior ao limiar e menor que a leitura de falha (999.0)
        esta_aberta = (distancia > LIMIAR_PORTA_ABERTA) and (distancia < 500.0)
        
        if esta_aberta != ultimo_estado:
            porta_aberta = esta_aberta
            ultimo_estado = esta_aberta
            
            if porta_aberta:
                atualizar_display("ALERTA!", "Porta Aberta!")
                bipar(0.2, 3, 0.1)
            else:
                atualizar_display("Porta Fechada", "Digite a Senha:")
                
        time.sleep(0.5)  # Frequência de atualização do sensor

# ==============================================================================
# 5. LÓGICA DE VARREDURA DO TECLADO MATRICIAL
# ==============================================================================
def ler_teclado():
    """Varre o teclado matricial e retorna a tecla pressionada com debounce."""
    for i, linha_pin in enumerate(LINHAS):
        GPIO.output(linha_pin, GPIO.LOW)
        for j, col_pin in enumerate(COLUNAS):
            if GPIO.input(col_pin) == GPIO.LOW:
                while GPIO.input(col_pin) == GPIO.LOW:
                    time.sleep(0.01)
                GPIO.output(linha_pin, GPIO.HIGH)
                return TECLAS[i][j]
        GPIO.output(linha_pin, GPIO.HIGH)
    return None

# ==============================================================================
# 6. ROTINA PRINCIPAL DE FLUXO E AUTENTICAÇÃO
# ==============================================================================
def fluxo_fechadura():
    senha_inserida = ""
    atualizar_display("Fechadura RPi 3", "Digite a Senha:")

    while True:
        # Se a porta estiver aberta no sensor ultrassónico, impede a digitação da senha
        if porta_aberta:
            time.sleep(0.2)
            continue

        tecla = ler_teclado()
        
        if tecla:
            if tecla == "*":
                senha_inserida = ""
                bipar(0.05)
                atualizar_display("Digite a Senha:", "")
                continue
            
            elif tecla == "#":
                if len(senha_inserida) > 0:
                    validar_senha(senha_inserida)
                senha_inserida = ""
                continue
            
            if len(senha_inserida) < 4:
                senha_inserida += tecla
                bipar(0.05)
                atualizar_display("Digite a Senha:", "*" * len(senha_inserida))
                
            if len(senha_inserida) == 4:
                time.sleep(0.2)
                validar_senha(senha_inserida)
                senha_inserida = ""

        time.sleep(0.1)

def validar_senha(senha):
    """Valida se a senha está correta e aciona o respetivo comportamento de hardware."""
    if senha == SENHA_CORRETA:
        atualizar_display("Acesso Permitido", "Porta Destrancada")
        GPIO.output(TRINCO_PIN, GPIO.HIGH)
        bipar(0.8)
        
        time.sleep(tempo_bloqueio_trinco)
        
        GPIO.output(TRINCO_PIN, GPIO.LOW)
        atualizar_display("Porta Trancada", "Digite a Senha:")
    else:
        atualizar_display("Senha Incorreta", "Tente Novamente")
        bipar(0.15, 3, 0.08)
        time.sleep(1.5)
        atualizar_display("Digite a Senha:", "")

# ==============================================================================
# 7. INICIALIZAÇÃO SEGURA
# ==============================================================================
if __name__ == "__main__":
    try:
        # Inicializa a Thread do sensor ultrassónico em modo Daemon (fecha junto com o programa)
        thread_sensor = threading.Thread(target=monitorar_porta_thread, daemon=True)
        thread_sensor.start()
        
        fluxo_fechadura()
        
    except KeyboardInterrupt:
        print("\nPrograma encerrado pelo utilizador.")
    finally:
        GPIO.output(TRINCO_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if lcd:
            try:
                lcd.clear()
            except:
                pass
        GPIO.cleanup()
        print("GPIO limpo e seguro.")
