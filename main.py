import time
import pandas as pd
import numpy as np
# Se ajusta la importación para máxima compatibilidad con el entorno Render
from pocketoptionapi.stable_api import PocketOption 

# --- CONFIGURACIÓN DE ACCESO ---
EMAIL = "Andresfernandes818@gmail.com"
PASS = "Ar28436519@"

# --- PARÁMETROS ESTRATÉGICOS ---
MONTO_BASE = 2.0
MULTIPLICADOR_MG = 2.1
EXPIRACION_MINUTOS = 10
MAX_CICLOS_MG = 2
PERIODO_EMA = 200
PARES_OTC = ["EURUSD_otc", "GBPUSD_otc", "USDCHF_otc", "AUDUSD_otc", "NZDUSD_otc"]

class LacerBotOTC:
    def __init__(self):
        self.api = PocketOption(EMAIL, PASS)
        self.estado_martingala = 0
        self.monto_actual = MONTO_BASE
        self.en_operacion = False
        self.conectado = False
        
    def conectar(self):
        check, message = self.api.connect()
        if check:
            self.api.change_balance("PRACTICE") # Modo DEMO
            self.conectado = True
            print(f"--- CONECTADO CON ÉXITO: {EMAIL} ---")
            print(f"SALDO DEMO ACTUAL: ${self.api.get_balance()}")
        else:
            print(f"Error de conexión: {message}")

    def obtener_heikin_ashi(self, activo):
        # Obtener últimas 30 velas de 5 min (300 seg)
        velas = self.api.get_candles(activo, 300, 30) 
        df = pd.DataFrame(velas)
        
        # Transformación a Heikin Ashi
        ha_df = pd.DataFrame(index=df.index, columns=['open', 'high', 'low', 'close'])
        ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        
        for i in range(len(df)):
            if i == 0:
                ha_df.iloc[i, ha_df.columns.get_loc('open')] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
            else:
                ha_df.iloc[i, ha_df.columns.get_loc('open')] = (ha_df.iloc[i-1]['open'] + ha_df.iloc[i-1]['close']) / 2
        
        ha_df['high'] = df[['high', 'open', 'close']].max(axis=1)
        ha_df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        # EMA 200
        df['ema_200'] = df['close'].ewm(span=PERIODO_EMA, adjust=False).mean()
        return ha_df, df['ema_200']

    def analizar_par(self, activo):
        try:
            ha, ema = self.obtener_heikin_ashi(activo)
            v = ha.iloc[-1] # Vela actual
            e = ema.iloc[-1] # EMA 200 actual
            e_ant = ema.iloc[-2] # EMA anterior
            
            cuerpo = abs(v['close'] - v['open'])
            mecha_sup = v['high'] - max(v['open'], v['close'])
            mecha_inf = min(v['open'], v['close']) - v['low']
            
            # Filtros de Inteligencia
            inclinacion = e - e_ant
            
            # LÓGICA DE COMPRA (CALL)
            if v['close'] > v['open'] and mecha_inf == 0 and v['close'] > e:
                if inclinacion > 0.00001 and not (mecha_sup > cuerpo * 1.5):
                    return "CALL"
                    
            # LÓGICA DE VENTA (PUT)
            if v['close'] < v['open'] and mecha_sup == 0 and v['close'] < e:
                if inclinacion < -0.00001 and not (mecha_inf > cuerpo * 1.5):
                    return "PUT"
        except Exception:
            return None
                
        return None

    def bucle_cazador(self):
        self.conectar()
        while True:
            if not self.en_operacion:
                for activo in PARES_OTC:
                    # Logs simplificados para el panel de Render
                    print(f"Escaneando {activo}...")
                    senal = self.analizar_par(activo)
                    
                    if senal:
                        print(f"\n--- SEÑAL DETECTADA EN {activo}: {senal} ---")
                        id_op = self.api.buy(self.monto_actual, activo, senal, EXPIRACION_MINUTOS)
                        if id_op:
                            self.en_operacion = True
                            print(f"Operación abierta: ${self.monto_actual}. Esperando 10 min...")
                            time.sleep(EXPIRACION_MINUTOS * 60)
                            resultado, beneficio = self.api.check_win(id_op)
                            self.gestionar_resultado(resultado > 0)
                            break 
            
            time.sleep(15) # Pausa entre escaneos para evitar saturación

    def gestionar_resultado(self, gano):
        self.en_operacion = False
        if gano:
            print(">>> RESULTADO: ¡GANADA! Volviendo a base.")
            self.estado_martingala = 0
            self.monto_actual = MONTO_BASE
        else:
            if self.estado_martingala < MAX_CICLOS_MG:
                self.estado_martingala += 1
                self.monto_actual *= MULTIPLICADOR_MG
                print(f">>> RESULTADO: PERDIDA. G{self.estado_martingala} por ${self.monto_actual}")
            else:
                print(">>> RESULTADO: CICLO FALLIDO. Reiniciando a base.")
                self.estado_martingala = 0
                self.monto_actual = MONTO_BASE

# --- LANZAMIENTO ---
if __name__ == "__main__":
    bot = LacerBotOTC()
    bot.bucle_cazador()
            
