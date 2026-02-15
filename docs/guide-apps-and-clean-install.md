# Apps & Clean Install Guide

How to install apps, create custom apps, and do a clean fresh install on your board.

## Installing apps

### Install all apps and system files

```bash
./scripts/install.sh
```

This copies `lib/`, `builtin/`, `apps/`, and `data/` from `internal_filesystem/`
to the board over USB. It takes a few minutes.

### Install a single app

```bash
./scripts/install.sh com.micropythonos.helloworld
```

This copies just that app directory to `/apps/` on the board. Much faster for
iterating on one app.

### Install a single file manually

```bash
mpremote cp internal_filesystem/apps/com.micropythonos.helloworld/assets/hello.py \
  :/apps/com.micropythonos.helloworld/assets/hello.py

mpremote reset
```

## Available apps

Apps live in `internal_filesystem/apps/`:

| App | Description |
|-----|-------------|
| `com.micropythonos.helloworld` | Minimal example app |
| `com.micropythonos.draw` | Drawing canvas |
| `com.micropythonos.camera` | Camera viewer |
| `com.micropythonos.confetti` | Confetti animation |
| `com.micropythonos.connect4` | Connect 4 game |
| `com.micropythonos.imageview` | Image viewer |
| `com.micropythonos.imu` | IMU sensor display |
| `com.micropythonos.musicplayer` | Music player |
| `com.micropythonos.playtune` | Speaker test with tones |
| `com.micropythonos.showbattery` | Battery status |
| `com.micropythonos.showfonts` | Font browser |
| `com.micropythonos.soundrecorder` | Sound recorder |
| `com.quasikili.quasibird` | Flappy bird clone |
| `com.quasikili.quasicalculator` | Calculator |
| `com.quasikili.quasinametag` | Name tag display |

System apps (in `internal_filesystem/builtin/apps/`) are installed automatically
and include the launcher, settings, app store, Wi-Fi manager, about screen, and
OS updater.

## Creating a custom app

### App directory structure

```
internal_filesystem/apps/com.yourname.myapp/
  META-INF/
    MANIFEST.JSON       # App metadata (required)
  assets/
    main.py             # Your app code (entrypoint)
  res/
    mipmap-mdpi/
      icon_64x64.png    # App icon for the launcher (64x64 PNG)
```

### MANIFEST.JSON

```json
{
  "name": "My App",
  "publisher": "Your Name",
  "short_description": "What it does",
  "long_description": "Longer description.",
  "fullname": "com.yourname.myapp",
  "version": "0.0.1",
  "category": "tools",
  "activities": [
    {
      "entrypoint": "assets/main.py",
      "classname": "MyApp",
      "intent_filters": [
        {
          "action": "main",
          "category": "launcher"
        }
      ]
    }
  ]
}
```

Key fields:

- **fullname**: Reverse-domain app ID. Must match the directory name.
- **entrypoint**: Path to the Python file (relative to the app directory).
- **classname**: The `Activity` subclass to instantiate.
- **intent_filters**: `"action": "main"` + `"category": "launcher"` makes the
  app appear in the launcher.

### Minimal app code (assets/main.py)

```python
from mpos import Activity

class MyApp(Activity):

    def onCreate(self):
        screen = lv.obj()

        label = lv.label(screen)
        label.set_text("Hello from MyApp!")
        label.center()

        self.setContentView(screen)
```

Your Activity subclass gets an LVGL display context. Use `lv.*` to build your UI
and call `self.setContentView(screen)` to show it.

### Deploy and test

```bash
# Copy to board
mpremote cp -r internal_filesystem/apps/com.yourname.myapp :/apps/

# Reboot to see it in the launcher
mpremote reset
```

Or use the install script:

```bash
./scripts/install.sh com.yourname.myapp
```

### Quick iteration

For fast development, skip copying the whole app -- just push the changed file
and reset:

```bash
mpremote cp internal_filesystem/apps/com.yourname.myapp/assets/main.py \
  :/apps/com.yourname.myapp/assets/main.py

mpremote reset
```

## Board-specific installation

Not all boards have the same peripherals. Use `--board` to install only the apps
that work on your hardware:

```bash
./scripts/install.sh --board waveshare_esp32_s3_touch_lcd_28
```

This installs all system files (`lib/`, `builtin/`, `data/`) but only the user
apps that are compatible with the board. Apps that require missing hardware
(camera, microphone, SD card, etc.) are excluded.

Supported boards:

| Board | Flag value |
|-------|-----------|
| Waveshare ESP32-S3-Touch-LCD-2.8 | `waveshare_esp32_s3_touch_lcd_28` |

Without `--board`, all apps are installed (original behavior).

## Clean fresh install (wipe everything)

After flashing new firmware with `./scripts/flash_over_usb.sh`, old apps and
data may still be on the board because the flash script only writes the firmware
partition -- it does not erase the filesystem partition where apps are stored.

To get a completely clean board:

### Option 1: Erase flash before flashing (recommended)

This wipes **everything** -- firmware, filesystem, Wi-Fi credentials, all apps:

```bash
# Step 1: Erase the entire flash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem14101 erase_flash

# Step 2: Flash firmware
./scripts/flash_over_usb.sh

# Step 3: Reinstall all files
./scripts/install.sh
```

Replace `/dev/cu.usbmodem14101` with your actual port (`ls /dev/cu.usb*`).

If the board doesn't respond, put it in flash mode first: hold BOOT, press
RESET, release BOOT.

### Option 2: Erase flash using the flash script

Pass `--erase-all` to the flash script to erase and flash in one step:

```bash
./scripts/flash_over_usb.sh --erase-all
```

Then reinstall:

```bash
./scripts/install.sh
```

### Option 3: Delete apps manually (no reflash needed)

If you just want to remove leftover apps without reflashing:

```bash
# Connect to REPL
mpremote repl
```

Then in the REPL:

```python
>>> import os
>>> os.listdir('/apps')
['com.micropythonos.helloworld', 'com.old.unwanted.app', ...]

>>> def rmrf(path):
...     try:
...         for f in os.listdir(path):
...             fp = path + '/' + f
...             try:
...                 os.listdir(fp)
...                 rmrf(fp)
...             except:
...                 os.remove(fp)
...         os.rmdir(path)
...     except:
...         os.remove(path)
...
>>> rmrf('/apps/com.old.unwanted.app')
```

Or wipe all apps and reinstall:

```python
>>> for app in os.listdir('/apps'):
...     rmrf('/apps/' + app)
```

Then exit REPL (`Ctrl-X`) and reinstall:

```bash
./scripts/install.sh
```

## Quick reference

| Task | Command |
|------|---------|
| Install everything | `./scripts/install.sh` |
| Install for specific board | `./scripts/install.sh --board waveshare_esp32_s3_touch_lcd_28` |
| Install one app | `./scripts/install.sh com.micropythonos.helloworld` |
| Erase flash + reflash | `esptool.py ... erase_flash` then `flash_over_usb.sh` then `install.sh` |
| Erase + flash (one step) | `./scripts/flash_over_usb.sh --erase-all` then `install.sh` |
| List apps on board | `mpremote ls :/apps/` |
| Remove one app | Delete via REPL (see above) |
| Push file to board | `mpremote cp local.py :/remote.py` |
| Reboot board | `mpremote reset` |
