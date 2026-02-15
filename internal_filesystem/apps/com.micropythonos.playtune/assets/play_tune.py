import math
import struct
import time
from machine import Pin, I2S
from mpos import Activity

# I2S pins for PCM5101 DAC on Waveshare ESP32-S3-Touch-LCD-2.8
I2S_SCK = 48   # BCLK
I2S_WS = 38    # LRCK
I2S_SD = 47    # DOUT

SAMPLE_RATE = 22050
AMPLITUDE = 16000  # ~50% of int16 max

# Note frequencies (Hz)
NOTES = {
    'C4': 262, 'D4': 294, 'E4': 330, 'F4': 349, 'G4': 392, 'A4': 440, 'B4': 494,
    'C5': 523, 'D5': 587, 'E5': 659, 'F5': 698, 'G5': 784, 'A5': 880, 'B5': 988,
    'C6': 1047,
}

MELODIES = {
    'Scale': [
        ('C4',200),('D4',200),('E4',200),('F4',200),
        ('G4',200),('A4',200),('B4',200),('C5',400),
    ],
    'Twinkle': [
        ('C4',300),('C4',300),('G4',300),('G4',300),
        ('A4',300),('A4',300),('G4',600),(None,100),
        ('F4',300),('F4',300),('E4',300),('E4',300),
        ('D4',300),('D4',300),('C4',600),
    ],
    'Ode to Joy': [
        ('E4',300),('E4',300),('F4',300),('G4',300),
        ('G4',300),('F4',300),('E4',300),('D4',300),
        ('C4',300),('C4',300),('D4',300),('E4',300),
        ('E4',450),('D4',150),('D4',600),
    ],
    'Beep Test': [
        ('A4',500),(None,200),('A5',500),(None,200),
        ('C5',300),('E5',300),('G5',300),('C6',500),
    ],
}


def _gen_tone(freq, duration_ms, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
    """Generate a 16-bit mono sine wave buffer for a tone."""
    num_samples = sample_rate * duration_ms // 1000
    buf = bytearray(num_samples * 2)  # 16-bit = 2 bytes per sample
    two_pi_f = 2.0 * math.pi * freq / sample_rate
    for i in range(num_samples):
        sample = int(amplitude * math.sin(two_pi_f * i))
        struct.pack_into('<h', buf, i * 2, sample)
    return buf


def _gen_silence(duration_ms, sample_rate=SAMPLE_RATE):
    """Generate a silent buffer."""
    num_samples = sample_rate * duration_ms // 1000
    return bytearray(num_samples * 2)


class PlayTune(Activity):

    _i2s = None
    _playing = False
    _status_label = None

    def onCreate(self):
        screen = lv.obj()
        screen.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        screen.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        screen.set_style_pad_row(8, 0)
        screen.set_style_pad_all(12, 0)

        title = lv.label(screen)
        title.set_text("Speaker Test")
        title.set_style_text_font(lv.font_montserrat_20, 0)

        for name in MELODIES:
            btn = lv.button(screen)
            btn.set_width(lv.pct(90))
            label = lv.label(btn)
            label.set_text(name)
            label.center()
            btn.add_event_cb(lambda e, n=name: self._play_melody(n), lv.EVENT.CLICKED, None)

        # Single-note frequency slider
        freq_cont = lv.obj(screen)
        freq_cont.set_width(lv.pct(90))
        freq_cont.set_height(lv.SIZE_CONTENT)
        freq_cont.set_style_pad_all(8, 0)
        freq_cont.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        freq_cont.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

        self._freq_label = lv.label(freq_cont)
        self._freq_label.set_text("440 Hz")

        slider = lv.slider(freq_cont)
        slider.set_width(lv.pct(90))
        slider.set_range(100, 2000)
        slider.set_value(440, False)
        slider.add_event_cb(self._freq_changed, lv.EVENT.VALUE_CHANGED, None)

        beep_btn = lv.button(freq_cont)
        beep_btn.set_width(lv.pct(60))
        label = lv.label(beep_btn)
        label.set_text("Beep!")
        label.center()
        beep_btn.add_event_cb(self._beep_freq, lv.EVENT.CLICKED, None)
        self._slider = slider

        self._status_label = lv.label(screen)
        self._status_label.set_text("Tap a melody or Beep!")

        self.setContentView(screen)

    def _init_i2s(self):
        """Initialize I2S for PCM5101 DAC."""
        if self._i2s:
            return
        self._i2s = I2S(
            0,
            sck=Pin(I2S_SCK, Pin.OUT),
            ws=Pin(I2S_WS, Pin.OUT),
            sd=Pin(I2S_SD, Pin.OUT),
            mode=I2S.TX,
            bits=16,
            format=I2S.MONO,
            rate=SAMPLE_RATE,
            ibuf=8000,
        )

    def _deinit_i2s(self):
        if self._i2s:
            self._i2s.deinit()
            self._i2s = None

    def _play_buf(self, buf):
        """Write audio buffer to I2S."""
        self._init_i2s()
        self._i2s.write(buf)

    def _freq_changed(self, event):
        freq = self._slider.get_value()
        self._freq_label.set_text(f"{freq} Hz")

    def _beep_freq(self, event):
        freq = self._slider.get_value()
        self._status_label.set_text(f"Beep {freq} Hz")
        buf = _gen_tone(freq, 300)
        self._play_buf(buf)
        self._status_label.set_text(f"Done - {freq} Hz")

    def _play_melody(self, name):
        if self._playing:
            return
        self._playing = True
        self._status_label.set_text(f"Playing {name}...")
        self._init_i2s()
        melody = MELODIES[name]
        for note, dur in melody:
            if not self._playing:
                break
            if note is None:
                buf = _gen_silence(dur)
            else:
                buf = _gen_tone(NOTES[note], dur)
            self._i2s.write(buf)
        self._playing = False
        self._status_label.set_text("Done")

    def onPause(self):
        self._playing = False
        self._deinit_i2s()
