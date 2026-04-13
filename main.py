import time
import pandas as pd
import numpy as np
from quotexpy import Quotex

# --- CONFIGURACIÓN DE ACCESO ---
EMAIL = "Andresfernandes818@gmail.com"
PASS = "Ar28436519@"

# --- PARÁMETROS ESTRATÉGICOS ---
MONTO_BASE = 1.0
MULTIPLICADOR_MG = 2.1
EXPIRACION_MINUTOS = 10
MAX_CICLOS_MG = 2
PERIODO_EMA = 200
PAYOUT_MINIMO = 90 

class LacerBotQuotex:
    def __init__(self):
        self.api = Quotex(email=EMAIL, password=PASS)
        self.estado_martingala = 0
        self.monto_actual = MONTO_BASE
        self.en_operacion = False
        
    def conectar(self):
        check, message = self.api.connect()
        if check:
            self.api.change_balance("PRACTICE") 
            print(f"--- CONECTADO (REAL/OTC Habilitado): {EMAIL} ---")
            return True
        return False

    def obtener_datos(self, activo):
        velas = self.api.get_candles(activo, 300) 
        df = pd.DataFrame(velas)
        ha_df = pd.DataFrame(index=df.index, columns=['open', 'high', 'low', 'close'])
        ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        for i in range(len(df)):
            if i == 0:
                ha_df.iloc[i, 0] = (df.iloc[0]['open'] + df.iloc[0]['close']) / 2
            else:
                ha_df.iloc[i, 0] = (ha_df.iloc[i-1][0] + ha_df.iloc[i-1][3]) / 2
        ha_df['high'] = df[['high', 'open', 'close']].max(axis=1)
        ha_df['low'] = df[['low', 'open', 'close']].min(axis=1)
        ema = df['close'].ewm(span=PERIODO_EMA, adjust=False).mean()
        return ha_df, ema

    def analizar(self, activo):
        try:
            ha, ema = self.obtener_datos(activo)
            v = ha.iloc[-1]
            e = ema.iloc[-1]
            e_ant = ema.iloc[-5] # Revisa 5 velas atrás para ver la fuerza del inicio
            
            cuerpo = abs(v['close'] - v['open'])
            mecha_sup = v['high'] - max(v['open'], v['close'])
            mecha_inf = min(v['open'], v['close']) - v['low']
            
            # FILTRO DE INCLINACIÓN (Movimiento empezando con fuerza)
            inclinacion = e - e_ant

            # COMPRA: Inclinación positiva clara + Heikin Ashi perfecta
            if v['close'] > v['open'] and mecha_inf == 0 and v['close'] > e:
                if inclinacion > 0.00005: # Filtro más exigente para asegurar tendencia
                    return "CALL"

            # VENTA: Inclinación negativa clara + Heikin Ashi perfecta
            if v['close'] < v['open'] and mecha_sup == 0 and v['close'] < e:
                if inclinacion < -0.00005:
                    return "PUT"
        except:
            return None
        return None

    def ejecutar(self):
        if not self.conectar(): return
        while True:
            if not self.en_operacion:
                activos = self.api.get_all_asset_payout()
                for activo, payout in activos.items():
                    # Ahora escanea TODOS los pares con pago >= 90%
                    if (payout * 100) >= PAYOUT_MINIMO:
                        senal = self.analizar(activo)
                        if senal:
                            print(f"\n--- ENTRADA CONFIRMADA EN {activo} ({int(payout*100)}%) ---")
                            id_op = self.api.buy(self.monto_actual, activo, senal, EXPIRACION_MINUTOS)
                            if id_op:
                                self.en_operacion = True
                                time.sleep(EXPIRACION_MINUTOS * 60)
                                self.gestionar_resultado(self.api.check_win(id_op))
                                break
            time.sleep(15)

    def gestionar_resultado(self, gano):
        self.en_operacion = False
        if gano:
            self.monto_actual = MONTO_BASE
            self.estado_martingala = 0
        else:
            if self.estado_martingala < MAX_CICLOS_MG:
                self.estado_martingala += 1
                self.monto_actual *= MULTIPLICADOR_MG
            else:
                self.monto_actual = MONTO_BASE
                self.estado_martingala = 0

if __name__ == "__main__":
    LacerBotQuotex().ejecutar()
