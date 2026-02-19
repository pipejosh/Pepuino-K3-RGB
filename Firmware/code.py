import board
import time
import usb_hid
import neopixel
import rotaryio

from digitalio import DigitalInOut, Direction, Pull
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# =========================
# CONFIG
# =========================
NUM_LEDS = 3
LONG_PRESS_TIME = 2.0
PRESS_DECAY = 2.5
ROTATION_DECAY = 3.0
SWEEP_SPEED = 1
ROTATION_INTENSITY_SCALE = 1.5
BTN_PRESS_DECAY = 1.0  # per-button white glow decay

# =========================
# HID
# =========================
kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)

# =========================
# BUTTONS
# =========================
btn_left = DigitalInOut(board.D9)
btn_center = DigitalInOut(board.D0)
btn_right = DigitalInOut(board.D7)

for b in (btn_left, btn_center, btn_right):
    b.direction = Direction.INPUT
    b.pull = Pull.UP

# =========================
# ENCODER
# =========================
encoder = rotaryio.IncrementalEncoder(board.D1, board.D2)
encoder_btn = DigitalInOut(board.D3)
encoder_btn.direction = Direction.INPUT
encoder_btn.pull = Pull.UP

encoder_last_btn = encoder_btn.value
press_start_time = 0
long_press_triggered = False
last_encoder_position = encoder.position

# =========================
# NEOPIXELS
# =========================
pixels = neopixel.NeoPixel(board.D10, NUM_LEDS, brightness=1.0, auto_write=False)

# =========================
# STATE
# =========================
profile = 0  # 0 = OSU, 1 = GD
wave_pos = 0.0
wave_dir = 1
press_energy = 0.0

# Per-button white glow
btn_left_energy = 0.0
btn_center_energy = 0.0
btn_right_energy = 0.0

rotation_energy = 0.0
sweep_pos = 1.0  # fractional position
rotation_direction = 1  # 1 = volume up, -1 = volume down

# =========================
# HELPERS
# =========================
def hsv_to_rgb(h, s, v):
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

# =========================
# BASE ANIMATIONS
# =========================
def osu_wave(dt):
    global wave_pos, wave_dir
    wave_pos += wave_dir * 2.5 * dt
    if wave_pos > 2: wave_dir = -1
    if wave_pos < 0: wave_dir = 1
    colors = []
    for i in range(NUM_LEDS):
        distance = abs(i - wave_pos)
        brightness = max(0, 1 - distance)
        r = 140 * brightness
        g = 0
        b = 220 * brightness
        colors.append((r, g, b))
    return colors

def gd_wave(dt):
    global wave_pos
    wave_pos += 0.5 * dt
    colors = []
    for i in range(NUM_LEDS):
        hue = (wave_pos + i * 0.25) % 1.0
        r, g, b = hsv_to_rgb(hue, 1, 1)
        colors.append((r*255, g*255, b*255))
    return colors

# =========================
# MAIN LOOP
# =========================
last_time = time.monotonic()

while True:
    now = time.monotonic()
    dt = now - last_time
    last_time = now

    # ---------------------
    # ENCODER ROTATION (INVERTED)
    # ---------------------
    current_pos = encoder.position
    delta = current_pos - last_encoder_position
    if delta != 0:
        rotation_direction = 1 if delta > 0 else -1
        rotation_energy += abs(delta) * ROTATION_INTENSITY_SCALE
        rotation_energy = min(rotation_energy, 3.0)

        # volume control inverted
        if delta > 0:
            cc.send(ConsumerControlCode.VOLUME_DECREMENT)  # CW lowers volume
            sweep_pos -= SWEEP_SPEED * abs(delta)
            if sweep_pos < 0:
                sweep_pos += NUM_LEDS
        else:
            cc.send(ConsumerControlCode.VOLUME_INCREMENT)  # CCW raises volume
            sweep_pos += SWEEP_SPEED * abs(delta)
            if sweep_pos >= NUM_LEDS:
                sweep_pos -= NUM_LEDS

    last_encoder_position = current_pos
    rotation_energy -= ROTATION_DECAY * dt
    if rotation_energy < 0: rotation_energy = 0

    # ---------------------
    # ENCODER BUTTON
    # ---------------------
    current_btn = encoder_btn.value
    if not current_btn and encoder_last_btn:
        press_start_time = now
        long_press_triggered = False
        press_energy = 1.0
    if not current_btn:
        if not long_press_triggered and (now - press_start_time >= LONG_PRESS_TIME):
            profile = 1 - profile
            long_press_triggered = True
            press_energy = 1.5
    if current_btn and not encoder_last_btn:
        if (now - press_start_time) < LONG_PRESS_TIME:
            cc.send(ConsumerControlCode.PLAY_PAUSE)
    encoder_last_btn = current_btn

    press_energy -= PRESS_DECAY * dt
    if press_energy < 0: press_energy = 0

    # ---------------------
    # BUTTON MAPPING + PER-BUTTON WHITE GLOW
    # ---------------------
    if profile == 0:  # OSU
        if not btn_left.value:
            kbd.press(Keycode.ESCAPE)
            btn_left_energy = 1.0
        else:
            kbd.release(Keycode.ESCAPE)
        if not btn_center.value:
            kbd.press(Keycode.Z)
            btn_center_energy = 1.0
        else:
            kbd.release(Keycode.Z)
        if not btn_right.value:
            kbd.press(Keycode.X)
            btn_right_energy = 1.0
        else:
            kbd.release(Keycode.X)
    else:  # GD
        if not btn_left.value:
            kbd.press(Keycode.SPACE)
            btn_left_energy = 1.0
        else:
            kbd.release(Keycode.SPACE)
        if not btn_center.value:
            kbd.press(Keycode.UP_ARROW)
            btn_center_energy = 1.0
        else:
            kbd.release(Keycode.UP_ARROW)
        if not btn_right.value:
            kbd.press(Keycode.DOWN_ARROW)
            btn_right_energy = 1.0
        else:
            kbd.release(Keycode.DOWN_ARROW)

    # decay per-button energies
    btn_left_energy -= BTN_PRESS_DECAY * dt
    btn_center_energy -= BTN_PRESS_DECAY * dt
    btn_right_energy -= BTN_PRESS_DECAY * dt
    btn_left_energy = max(0, btn_left_energy)
    btn_center_energy = max(0, btn_center_energy)
    btn_right_energy = max(0, btn_right_energy)

    # ---------------------
    # BASE COLORS + OVERLAYS
    # ---------------------
    base = osu_wave(dt) if profile == 0 else gd_wave(dt)
    final = []

    for i in range(NUM_LEDS):
        r, g, b = base[i]

        # rotation sweep overlay
        if rotation_energy > 0:
            dist = abs(i - sweep_pos)
            dist = min(dist, NUM_LEDS - dist)
            sweep_brightness = max(0, 1 - dist) * rotation_energy
            r += 255 * sweep_brightness
            g += 255 * sweep_brightness
            b += 255 * sweep_brightness

        # encoder press overlay
        if press_energy > 0:
            r += 255 * press_energy
            g += 255 * press_energy
            b += 255 * press_energy

        # per-button white glow
        if i == 0:
            r += 100 * btn_left_energy
            g += 100 * btn_left_energy
            b += 100 * btn_left_energy
        elif i == 1:
            r += 100 * btn_center_energy
            g += 100 * btn_center_energy
            b += 100 * btn_center_energy
        elif i == 2:
            r += 100 * btn_right_energy
            g += 100 * btn_right_energy
            b += 100 * btn_right_energy

        final.append((min(255,int(r)), min(255,int(g)), min(255,int(b))))

    # update LEDs
    for i in range(NUM_LEDS):
        pixels[i] = final[i]
    pixels.show()
