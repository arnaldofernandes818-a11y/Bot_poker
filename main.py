import asyncio
import pandas as pd
import numpy as np
from quotexpy import Quotex
import os
from aiohttp import web

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
        # 🟢 RUTAS DE ENTORNO PARA RENDER
        chrome_path = os.environ.get("GOOGLE_CHROME_BIN")
        driver_path = os.environ.get("CHROMEDRIVER_PATH")
        
        # 🟢 ARGUMENTOS PARA NAVEGADOR EN LA NUBE
        chrome_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--headless",
            "--disable-gpu",
            "--window-size=1920,1080"
        ]
        
        self.api = Quotex(
            email=EMAIL, 
            password=PASS,
            chrome_bin=chrome_path,
            executable_path=driver_path,
            args=chrome_args
        )
        self.estado_martingala = 0
        self.monto_actual = MONTO_BASE
        self.en_operacion = False
        
    async def conectar(self):
        print("Intentando conectar a Quotex con configuración de nube...")
        try:
            check, message = await self.api.connect()
            if check:
                self.api.change_balance("PRACTICE") 
                print(f"--- CONECTADO CON ÉXITO: {EMAIL} ---")
                return True
            
            # 📸 INVESTIGACIÓN SI FALLA
            print(f"Error de conexión: {message}")
            try:
                if hasattr(self.api, 'driver') and self.api.driver:
                    self.api.driver.save_screenshot("captura_error.png")
                    print("📸 Se ha intentado guardar 'captura_error.png' para depuración.")
            except Exception as e_snap:
                print(f"No se pudo tomar la captura: {e_snap}")
                
            return False
        except Exception as e:
            print(f"Error crítico al conectar: {e}")
            return False

    async def obtener_datos(self, activo):
        try:
            velas = await self.api.get_candles(activo, 300) 
            df = pd.DataFrame(velas)
            if df.empty: return None, None
            
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
        except:
            return None, None

    async def analizar(self, activo):
        ha, ema = await self.obtener_datos(activo)
        if ha is None or ema is None: return None
        
        try:
            v = ha.iloc[-1]
            e = ema.iloc[-1]
            e_ant = ema.iloc[-5] 
            inclinacion = e - e_ant

            if v['close'] > v['open'] and (v['open'] - v['low']) == 0 and v['close'] > e:
                if inclinacion > 0.00005: return "CALL"
            if v['close'] < v['open'] and (v['high'] - v['close']) == 0 and v['close'] < e:
                if inclinacion < -0.00005: return "PUT"
        except:
            pass
        return None

    async def ejecutar(self):
        # Servidor para que Render no cierre el bot
        async def handle(request): return web.Response(text="LacerBot Is Alive")
        app = web.Application()
        app.router.add_get('/', handle)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 10000))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()

        if not await self.conectar():
            print("No se pudo iniciar el bot por error de conexión.")
            return
        
        print("Bot en marcha. Buscando señales...")
        while True:
            if not self.en_operacion:
                try:
                    activos = await self.api.get_all_asset_payout()
                    for activo, payout in activos.items():
                        if (payout * 100) >= PAYOUT_MINIMO:
                            senal = await self.analizar(activo)
                            if senal:
                                print(f"\n--- SEÑAL EN {activo} ({int(payout*100)}%) ---")
                                id_op = await self.api.buy(self.monto_actual, activo, senal, EXPIRACION_MINUTOS)
                                if id_op:
                                    self.en_operacion = True
                                    await asyncio.sleep(EXPIRACION_MINUTOS * 60)
                                    gano = await self.api.check_win(id_op)
                                    self.gestionar_resultado(gano)
                                    break
                except Exception as e:
                    print(f"Error en bucle: {e}")
            await asyncio.sleep(20)

    def gestionar_resultado(self, gano):
        self.en_operacion = False
        if gano:
            print(">>> GANADA")
            self.monto_actual = MONTO_BASE
            self.estado_martingala = 0
        else:
            if self.estado_martingala < MAX_CICLOS_MG:
                self.estado_martingala += 1
                self.monto_actual *= MULTIPLICADOR_MG
                print(f">>> PERDIDA. MG {self.estado_martingala}")
            else:
                self.monto_actual = MONTO_BASE
                self.estado_martingala = 0

if __name__ == "__main__":
    asyncio.run(LacerBotQuotex().ejecutar())
