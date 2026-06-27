"""
Skydimo LED Daemon — direct COM4 control via Adalight protocol.
Background daemon that renders LED animations and monitors .ai_state / .stop.
"""
import os
import time
import math
import serial
import subprocess
import threading

import skydimo_config as cfg


class SkydimoAdalightDaemon:
    def __init__(self):
        self.current_state = 'idle'
        self.running = True

        subprocess.run(['taskkill', '/f', '/im', 'SkyDimo.exe'],
                       capture_output=True)
        time.sleep(1)

        self.ser = serial.Serial(cfg.PORT, cfg.BAUDRATE, timeout=1)

        self.header = b'Ada\x00\x00' + bytes([cfg.NUM_LEDS])

    def send_frame(self, led_data):
        frame = self.header + bytes(led_data)
        self.ser.write(frame)
        self.ser.flush()

    def get_effect_colors(self):
        led_data = []
        t = time.time()

        if self.current_state == 'idle':
            brightness = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(t * 1.25))
            r, g, b = 0, int(180 * brightness), int(200 * brightness)
            led_data = [r, g, b] * cfg.NUM_LEDS

        elif self.current_state == 'reasoning':
            for i in range(cfg.NUM_LEDS):
                hue = (i * 10 + int(t * 150)) % 360
                r, g, b = self.hsv_to_rgb(hue, 255, 255)
                led_data.extend([r, g, b])

        elif self.current_state == 'decision':
            brightness = 0.1 + 0.9 * (0.5 + 0.5 * math.sin(t * 4.0))
            led_data = [int(255 * brightness), 0, 0] * cfg.NUM_LEDS

        elif self.current_state == 'output':
            speed_factor = int(t * 20) % cfg.NUM_LEDS
            for i in range(cfg.NUM_LEDS):
                if (i - speed_factor) % cfg.NUM_LEDS < 5:
                    led_data.extend([0, 255, 0])
                else:
                    led_data.extend([0, 20, 0])

        elif self.current_state == 'waiting_user':
            brightness = 0.2 + 0.6 * (0.5 + 0.5 * math.sin(t * 1.6))
            sparkle_pos = int(t * 2.0) % cfg.NUM_LEDS
            for i in range(cfg.NUM_LEDS):
                r, g, b = 0, int(160 * brightness), int(190 * brightness)
                distance = min((i - sparkle_pos) % cfg.NUM_LEDS,
                               (sparkle_pos - i) % cfg.NUM_LEDS)
                if distance == 0:
                    r, g, b = 180, 255, 255
                elif distance == 1:
                    r, g, b = 60, 210, 220
                led_data.extend([r, g, b])

        elif self.current_state == 'testing':
            cycle = (t * 12) % ((cfg.NUM_LEDS - 1) * 2)
            scanner_pos = cycle if cycle < cfg.NUM_LEDS else (cfg.NUM_LEDS - 1) * 2 - cycle
            for i in range(cfg.NUM_LEDS):
                distance = abs(i - scanner_pos)
                glow = max(0, 1 - distance / 5)
                r = int(30 + 180 * glow)
                g = int(60 + 195 * glow)
                b = int(130 + 125 * glow)
                led_data.extend([r, g, b])

        elif self.current_state == 'success':
            center = (cfg.NUM_LEDS - 1) / 2
            tick = int(t * 7)
            for i in range(cfg.NUM_LEDS):
                distance = abs(i - center)
                wave = 0.5 + 0.5 * math.sin(t * 5.0 - distance * 0.6)
                sparkle = ((i * 17 + tick * 31) % 53) == 0
                r = 0
                g = 80 + int(175 * wave)
                b = 20 + int(60 * wave)
                if sparkle:
                    r, g, b = 180, 255, 120
                led_data.extend([r, g, b])

        elif self.current_state == 'error':
            cycle = t % 1.8
            brightness = 0.08
            if cycle < 0.25:
                brightness = max(brightness, math.sin(cycle / 0.25 * math.pi))
            elif 0.38 <= cycle < 0.63:
                brightness = max(brightness, math.sin((cycle - 0.38) / 0.25 * math.pi))
            led_data = [int(255 * brightness), 0, 0] * cfg.NUM_LEDS
        else:
            led_data = [0, 0, 0] * cfg.NUM_LEDS

        return led_data

    @staticmethod
    def hsv_to_rgb(h, s, v):
        h /= 60.0
        i = math.floor(h)
        f = h - i
        p = int(v * (1.0 - s / 255.0))
        q = int(v * (1.0 - s / 255.0 * f))
        t = int(v * (1.0 - s / 255.0 * (1.0 - f)))
        if i == 0: return v, t, p
        elif i == 1: return q, v, p
        elif i == 2: return p, v, t
        elif i == 3: return p, q, v
        elif i == 4: return t, p, v
        else: return v, p, q

    def file_listener(self):
        while self.running:
            if os.path.exists(cfg.STOP_FILE):
                self.running = False
                break
            if os.path.exists(cfg.STATE_FILE):
                try:
                    with open(cfg.STATE_FILE, 'r', encoding='utf-8') as f:
                        state = f.read().strip().lower()
                        if state in cfg.VALID_MODES:
                            self.current_state = state
                except Exception:
                    pass
            time.sleep(0.1)

    def run(self):
        with open(cfg.PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        listener_thread = threading.Thread(target=self.file_listener, daemon=True)
        listener_thread.start()

        print(f"Skydimo Adalight Daemon running on {cfg.PORT} ({cfg.NUM_LEDS} LEDs)")

        try:
            while self.running:
                start = time.time()
                colors = self.get_effect_colors()
                self.send_frame(colors)
                elapsed = time.time() - start
                sleep_time = max(0.025 - elapsed, 0)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.send_frame([0, 0, 0] * cfg.NUM_LEDS)
            self.ser.close()
            if os.path.exists(cfg.PID_FILE):
                os.remove(cfg.PID_FILE)
            if os.path.exists(cfg.STOP_FILE):
                try:
                    os.remove(cfg.STOP_FILE)
                except OSError:
                    pass

    def run_no_thread(self):
        """Minimal run loop without file listener thread — for testing."""
        with open(cfg.PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        print(f"Skydimo Adalight (no-thread) running on {cfg.PORT} ({cfg.NUM_LEDS} LEDs)")
        try:
            while self.running:
                if os.path.exists(cfg.STOP_FILE):
                    self.running = False
                    break
                if os.path.exists(cfg.STATE_FILE):
                    try:
                        with open(cfg.STATE_FILE, 'r', encoding='utf-8') as f:
                            state = f.read().strip().lower()
                            if state in cfg.VALID_MODES:
                                self.current_state = state
                    except Exception:
                        pass
                start = time.time()
                colors = self.get_effect_colors()
                self.send_frame(colors)
                elapsed = time.time() - start
                sleep_time = max(0.025 - elapsed, 0)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.send_frame([0, 0, 0] * cfg.NUM_LEDS)
            self.ser.close()
            if os.path.exists(cfg.PID_FILE):
                os.remove(cfg.PID_FILE)
            if os.path.exists(cfg.STOP_FILE):
                try:
                    os.remove(cfg.STOP_FILE)
                except OSError:
                    pass


if __name__ == '__main__':
    import sys
    daemon = SkydimoAdalightDaemon()
    if len(sys.argv) >= 2 and sys.argv[1] in cfg.VALID_MODES:
        daemon.current_state = sys.argv[1]
    daemon.run()
