import time
import threading
import RPi.GPIO as GPIO
from rpi_lcd import LCD

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pinos do Teclado Matricial 4x4
LINHAS = [5, 6, 13, 19]
COLUNAS = [26, 16, 20, 21]

# Pinos dos Atuadores e Sensores
BUZZER_PIN = 12
TRINCO_PIN = 23
SENSOR_PORTA_PIN = 22

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

# Inicialização do LCD via I2C (Endereço padrão 0x27)
try:
    lcd = LCD(address=0x27, bus=1)
except Exception as e:
    print(f"Erro ao inicializar LCD: {e}. Verifique as ligações I2C.")
    lcd = None

# Configura linhas como saídas (inicialmente em nível ALTO)
for l in LINHAS:
    GPIO.setup(l, GPIO.OUT)
    GPIO.output(l, GPIO.HIGH)

# Configura colunas como entradas com resistor de Pull-Up interno
for c in COLUNAS:
    GPIO.setup(c, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Configura periféricos
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(TRINCO_PIN, GPIO.OUT)
GPIO.setup(SENSOR_PORTA_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Garante estados iniciais seguros (Trinco trancado, Buzzer desligado)
GPIO.output(TRINCO_PIN, GPIO.LOW)
GPIO.output(BUZZER_PIN, GPIO.LOW)

def bipar(duracao, repeticoes=1, intervalo=0.1):
    """Gera bipes de feedback sonoro de forma síncrona."""
    for _ in range(repeticoes):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(duracao)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if repeticoes > 1:
            time.sleep(intervalo)

def atualizar_display(linha1, linha2=""):
    """Escreve mensagens de forma segura no LCD."""
    if lcd:
        try:
            lcd.clear()
            lcd.text(linha1[:16], 1)
            lcd.text(linha2[:16], 2)
        except Exception as e:
            print(f"Erro no display: {e}")
    print(f"[LCD] L1: '{linha1}' | L2: '{linha2}'")

def monitorar_porta_callback(canal):
    """Interrupção física: Trata a abertura/fecho da porta em tempo real."""
    time.sleep(0.05) # Debounce do sensor magnético / switch
    if GPIO.input(SENSOR_PORTA_PIN) == GPIO.HIGH:
        atualizar_display("ALERTA!", "Porta Aberta!")
        bipar(0.2, 3, 0.1) # Alerta sonoro rápido
    else:
        atualizar_display("Porta Fechada", "Digite a Senha:")

# Configura a interrupção física por mudança de estado (borda de subida/descida)
GPIO.add_event_detect(SENSOR_PORTA_PIN, GPIO.BOTH, callback=monitorar_porta_callback, bouncetime=400)

def ler_teclado():
    """Varre o teclado matricial e retorna a tecla pressionada com debounce."""
    for i, linha_pin in enumerate(LINHAS):
        GPIO.output(linha_pin, GPIO.LOW)  # Ativa a linha atual colocando em nível lógico baixo
        for j, col_pin in enumerate(COLUNAS):
            if GPIO.input(col_pin) == GPIO.LOW:  # Tecla pressionada detetada
                # Aguarda a tecla ser solta para evitar leituras duplicadas (Bounce)
                while GPIO.input(col_pin) == GPIO.LOW:
                    time.sleep(0.01)
                GPIO.output(linha_pin, GPIO.HIGH)
                return TECLAS[i][j]
        GPIO.output(linha_pin, GPIO.HIGH)  # Desativa a linha antes de passar à próxima
    return None

def fluxo_fechadura():
    senha_inserida = ""
    atualizar_display("Fechadura RPi 3", "Digite a Senha:")

    while True:
        # Se a porta estiver aberta, aguarda que seja fechada para aceitar senha
        if GPIO.input(SENSOR_PORTA_PIN) == GPIO.HIGH:
            time.sleep(0.5)
            continue

        tecla = ler_teclado()
        
        if tecla:
            # Caso o utilizador queira limpar a digitação atual
            if tecla == "*":
                senha_inserida = ""
                bipar(0.05)
                atualizar_display("Digite a Senha:", "")
                continue
            
            # Submete a senha imediatamente ao carregar em '#'
            elif tecla == "#":
                if len(senha_inserida) > 0:
                    validar_senha(senha_inserida)
                senha_inserida = ""
                continue
            
            # Adiciona o dígito à senha se não exceder o limite de 4
            if len(senha_inserida) < 4:
                senha_inserida += tecla
                bipar(0.05)  # Feedback tátil do clique
                # Mostra asteriscos correspondentes no LCD
                atualizar_display("Digite a Senha:", "*" * len(senha_inserida))
                
            # Validação automática ao atingir 4 dígitos
            if len(senha_inserida) == 4:
                time.sleep(0.2) # Pequena pausa para o utilizador ver o quarto asterisco
                validar_senha(senha_inserida)
                senha_inserida = ""

        time.sleep(0.1)  # Evita sobrecarga de processamento na CPU

def validar_senha(senha):
    """Valida se a senha está correta e aciona o respetivo comportamento de hardware."""
    if senha == SENHA_CORRETA:
        atualizar_display("Acesso Permitido", "Porta Destrancada")
        GPIO.output(TRINCO_PIN, GPIO.HIGH)  # Liberta o trinco solenoide/relé
        
        # Bipe longo de sucesso
        bipar(0.8)
        
        # Mantém a porta destrancada pelo tempo estipulado
        time.sleep(tempo_bloqueio_trinco)
        
        # Tranca novamente a porta
        GPIO.output(TRINCO_PIN, GPIO.LOW)
        atualizar_display("Porta Trancada", "Digite a Senha:")
    else:
        atualizar_display("Senha Incorreta", "Tente Novamente")
        # Sequência sonora de erro (3 bipes rápidos)
        bipar(0.15, 3, 0.08)
        time.sleep(1.5)
        atualizar_display("Digite a Senha:", "")

if __name__ == "__main__":
    try:
        fluxo_fechadura()
    except KeyboardInterrupt:
        print("\nPrograma encerrado pelo utilizador.")
    finally:
        # Garante a limpeza de todos os pinos de GPIO ao sair do programa
        GPIO.output(TRINCO_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        if lcd:
            try:
                lcd.clear()
            except:
                pass
        GPIO.cleanup()
        print("GPIO limpo e seguro.")
