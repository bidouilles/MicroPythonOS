import math
from mpos import Activity, SensorManager

# Display dimensions (Waveshare ESP32-S3-Touch-LCD-2.8)
DISP_W = 240
DISP_H = 320

# Bubble level area
LEVEL_SIZE = 200       # diameter of the level circle
LEVEL_R = LEVEL_SIZE // 2
DOT_R = 12             # bubble dot radius
MAX_ANGLE = 45.0       # degrees at which the dot hits the edge


class Tilt(Activity):

    _accel_sensor = None
    _timer = None

    # LVGL objects
    _canvas_obj = None
    _dot = None
    _crosshair_h = None
    _crosshair_v = None
    _pitch_label = None
    _roll_label = None
    _raw_label = None

    def onCreate(self):
        screen = lv.obj()
        screen.set_style_pad_all(0, 0)
        screen.set_style_bg_color(lv.color_hex(0x000000), 0)

        # Title
        title = lv.label(screen)
        title.set_text("Angular Deflection")
        title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        title.align(lv.ALIGN.TOP_MID, 0, 6)

        # Level container - centered circle area
        cx = DISP_W // 2
        cy = 130

        # Outer ring
        ring = lv.obj(screen)
        ring.set_size(LEVEL_SIZE + 4, LEVEL_SIZE + 4)
        ring.align(lv.ALIGN.TOP_MID, 0, cy - LEVEL_R - 2)
        ring.set_style_radius(lv.RADIUS_CIRCLE, 0)
        ring.set_style_bg_color(lv.color_hex(0x1A1A2E), 0)
        ring.set_style_border_color(lv.color_hex(0x4444AA), 0)
        ring.set_style_border_width(2, 0)
        ring.set_style_pad_all(0, 0)
        ring.remove_flag(lv.obj.FLAG.SCROLLABLE)

        # Crosshairs
        self._crosshair_h = lv.line(ring)
        self._crosshair_h.set_style_line_color(lv.color_hex(0x333366), 0)
        self._crosshair_h.set_style_line_width(1, 0)
        pts_h = [{'x': 0, 'y': LEVEL_R}, {'x': LEVEL_SIZE, 'y': LEVEL_R}]
        self._crosshair_h.set_points(pts_h, 2)

        self._crosshair_v = lv.line(ring)
        self._crosshair_v.set_style_line_color(lv.color_hex(0x333366), 0)
        self._crosshair_v.set_style_line_width(1, 0)
        pts_v = [{'x': LEVEL_R, 'y': 0}, {'x': LEVEL_R, 'y': LEVEL_SIZE}]
        self._crosshair_v.set_points(pts_v, 2)

        # Center mark
        center_dot = lv.obj(ring)
        center_dot.set_size(6, 6)
        center_dot.set_style_radius(lv.RADIUS_CIRCLE, 0)
        center_dot.set_style_bg_color(lv.color_hex(0x666699), 0)
        center_dot.set_style_border_width(0, 0)
        center_dot.align(lv.ALIGN.CENTER, 0, 0)

        # Bubble dot
        self._dot = lv.obj(ring)
        self._dot.set_size(DOT_R * 2, DOT_R * 2)
        self._dot.set_style_radius(lv.RADIUS_CIRCLE, 0)
        self._dot.set_style_bg_color(lv.color_hex(0x00FF88), 0)
        self._dot.set_style_bg_opa(200, 0)
        self._dot.set_style_border_color(lv.color_hex(0x00CC66), 0)
        self._dot.set_style_border_width(2, 0)
        self._dot.align(lv.ALIGN.CENTER, 0, 0)

        # Angle readouts below the level
        info_y = cy + LEVEL_R + 12

        self._pitch_label = lv.label(screen)
        self._pitch_label.set_text("Pitch:  0.0")
        self._pitch_label.set_style_text_color(lv.color_hex(0x00FF88), 0)
        self._pitch_label.set_style_text_font(lv.font_montserrat_20, 0)
        self._pitch_label.align(lv.ALIGN.TOP_MID, 0, info_y)

        self._roll_label = lv.label(screen)
        self._roll_label.set_text("Roll:   0.0")
        self._roll_label.set_style_text_color(lv.color_hex(0x00FF88), 0)
        self._roll_label.set_style_text_font(lv.font_montserrat_20, 0)
        self._roll_label.align(lv.ALIGN.TOP_MID, 0, info_y + 28)

        self._raw_label = lv.label(screen)
        self._raw_label.set_text("X: 0.00  Y: 0.00  Z: 0.00")
        self._raw_label.set_style_text_color(lv.color_hex(0x888888), 0)
        self._raw_label.align(lv.ALIGN.TOP_MID, 0, info_y + 62)

        # Init sensor
        try:
            if SensorManager.is_available():
                self._accel_sensor = SensorManager.get_default_sensor(
                    SensorManager.TYPE_ACCELEROMETER)
            if not self._accel_sensor:
                self._raw_label.set_text("No accelerometer found")
        except Exception as e:
            self._raw_label.set_text(f"Sensor error: {e}")

        self.setContentView(screen)

    def onStart(self, screen):
        self._timer = lv.timer_create(self._update, 50, None)

    def onStop(self, screen):
        if self._timer:
            self._timer.delete()
            self._timer = None

    def _update(self, timer):
        if not self._accel_sensor:
            return

        data = SensorManager.read_sensor(self._accel_sensor)
        if not data:
            return

        ax, ay, az = data  # m/s^2

        # Convert to G
        gx = ax / 9.80665
        gy = ay / 9.80665
        gz = az / 9.80665

        # Compute pitch and roll from accelerometer (degrees)
        # pitch = rotation around X axis, roll = rotation around Y axis
        pitch = math.atan2(gy, math.sqrt(gx * gx + gz * gz)) * 180.0 / math.pi
        roll = math.atan2(-gx, math.sqrt(gy * gy + gz * gz)) * 180.0 / math.pi

        # Map angles to pixel offset (clamp to circle)
        max_offset = LEVEL_R - DOT_R
        dx = int(-roll / MAX_ANGLE * max_offset)
        dy = int(-pitch / MAX_ANGLE * max_offset)

        # Clamp to circle boundary
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > max_offset:
            scale = max_offset / dist
            dx = int(dx * scale)
            dy = int(dy * scale)

        self._dot.align(lv.ALIGN.CENTER, dx, dy)

        # Color: green when level, yellow/red when tilted
        total_tilt = math.sqrt(pitch * pitch + roll * roll)
        if total_tilt < 3.0:
            color = 0x00FF88  # green - level
        elif total_tilt < 15.0:
            color = 0xFFCC00  # yellow - moderate tilt
        else:
            color = 0xFF4444  # red - steep tilt
        self._dot.set_style_bg_color(lv.color_hex(color), 0)

        # Update labels
        self._pitch_label.set_text(f"Pitch: {pitch:+6.1f}")
        self._roll_label.set_text(f"Roll:  {roll:+6.1f}")
        self._raw_label.set_text(f"X:{gx:+.2f}  Y:{gy:+.2f}  Z:{gz:+.2f}")
