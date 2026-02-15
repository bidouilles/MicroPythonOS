# Building & Flashing MicroPythonOS from macOS

A step-by-step guide to build MicroPythonOS firmware and flash it to a Waveshare ESP32-S3 board.

## What you need

- A Mac with macOS
- A Waveshare ESP32-S3-Touch-LCD board (LCD-2 or LCD-2.8)
- A USB-C data cable (not a charge-only cable!)

## 1. Install tools

Open Terminal and run these commands one by one.

### Xcode command line tools (compiler, git, etc.)

```bash
xcode-select --install
```

A popup will appear. Click "Install" and wait for it to finish.

### Homebrew packages

If you don't have Homebrew yet, install it first:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install build tools:

```bash
brew install cmake ninja python3 coreutils
```

> `coreutils` is needed because the build scripts use GNU `readlink -f`, which
> the built-in macOS `readlink` does not support.

### Python packages

```bash
pip3 install esptool mpremote
```

Verify everything is installed:

```bash
cmake --version
ninja --version
python3 --version
esptool.py version
mpremote version
```

All five commands should print a version number without errors.

## 2. Get the source code

```bash
cd /path/to/your/workspace
git clone <MicroPythonOS-repo-url> MicroPythonOS
cd MicroPythonOS
```

Then pull in all the submodules (this downloads the MicroPython source, LVGL,
ESP-IDF, and other dependencies):

```bash
git submodule update --init --recursive
```

This takes a while the first time. Go get a coffee.

## 3. Build the firmware

```bash
./scripts/build_mpos.sh esp32s3
```

What this does behind the scenes:

1. Patches ESP-IDF component manifests
2. Freezes all Python libraries and built-in apps into the firmware binary
3. Compiles MicroPython + LVGL + drivers for ESP32-S3 with 16MB flash and OTA support

The first build takes **10-20 minutes**. Later builds are faster because only
changed files are recompiled.

When it finishes, the firmware binary is at:

```
lvgl_micropython/build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin
```

## 4. Connect the board

1. Plug the board into your Mac with a USB-C data cable.
2. Check that it shows up:

```bash
ls /dev/cu.usb*
```

You should see something like:

```
/dev/cu.usbmodem14101
```

> **Nothing shows up?**
> - Try a different USB cable (many cables are charge-only).
> - Try a different USB port.
> - Open **System Information** > **USB** and check if the device appears.

## 5. Put the board in flash mode

This is only needed if the board doesn't respond to esptool (some boards
auto-enter flash mode, others don't).

1. **Hold** the BOOT button
2. **Press and release** the RESET button
3. **Release** the BOOT button

The board is now in download mode and ready to receive firmware.

## 6. Erase the flash (first time only)

This wipes the entire flash memory for a clean start. You only need to do this
once, or when switching between different firmware projects.

```bash
esptool.py --chip esp32s3 --port /dev/cu.usbmodem14101 erase_flash
```

Replace `/dev/cu.usbmodem14101` with your actual port from step 4.

## 7. Flash the firmware

### Option A: Use the project's flash script

```bash
./scripts/flash_over_usb.sh
```

This auto-detects the firmware binary and flashes it.

### Option B: Manual command (more control)

```bash
esptool.py --chip esp32s3 \
  --port /dev/cu.usbmodem14101 \
  --before default_reset --after hard_reset \
  write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m \
  0 lvgl_micropython/build/lvgl_micropy_ESP32_GENERIC_S3-SPIRAM_OCT-16.bin
```

After flashing, **press the RESET button** on the board.

## 8. Upload the filesystem

The build in step 3 already baked the core libraries into the firmware. But to
install apps and data files, run:

```bash
./scripts/install.sh
```

This uses `mpremote` to copy `lib/`, `apps/`, and `data/` to the board's
internal storage.

To install just one app:

```bash
./scripts/install.sh com.micropythonos.about
```

## 9. Connect to the REPL

The REPL (Read-Eval-Print Loop) lets you type Python commands directly on the
board.

```bash
mpremote repl
```

You should see the MicroPython prompt:

```
>>>
```

Try it out:

```python
>>> import machine
>>> machine.freq()
240000000
```

**Keyboard shortcuts inside the REPL:**

| Keys | Action |
|------|--------|
| `Ctrl-C` | Interrupt running code |
| `Ctrl-D` | Soft reset the board |
| `Ctrl-X` | Exit mpremote |

## 10. Quick iteration (no rebuild needed)

When you're editing Python files (drivers, board configs, apps), you don't need
to rebuild the entire firmware. Just copy files directly to the board:

```bash
# Copy a single file
mpremote cp path/to/myfile.py :/lib/myfile.py

# Reset the board to pick up changes
mpremote reset
```

**Example** -- updating the LCD-2.8 board file and touch driver:

```bash
mpremote cp internal_filesystem/lib/mpos/board/waveshare_esp32_s3_touch_lcd_28.py \
  :/lib/mpos/board/waveshare_esp32_s3_touch_lcd_28.py

mpremote cp internal_filesystem/lib/drivers/indev/cst328.py \
  :/lib/drivers/indev/cst328.py

mpremote cp internal_filesystem/lib/mpos/main.py \
  :/lib/mpos/main.py

mpremote reset
```

**Example** -- run a test script without copying it to the board:

```bash
mpremote run my_test_script.py
```

## Troubleshooting

### "Port not found" or "No serial port detected"

- Check that your USB cable is a **data** cable.
- Put the board in flash mode (step 5).
- Try `ls /dev/cu.usb*` to find the correct port name.

### "readlink: illegal option -- f"

The build scripts require GNU coreutils. Install with:

```bash
brew install coreutils
```

Then either add to your PATH:

```bash
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
```

Or add that line to your `~/.zshrc` so it persists.

### Build fails with submodule errors

```bash
git submodule update --init --recursive
```

### "Permission denied" on serial port

```bash
sudo chmod 666 /dev/cu.usbmodem14101
```

### Board boots but display is white / touch doesn't work

- Check that the correct board file is loaded. Connect to REPL (`mpremote repl`)
  and look at the boot log -- it should say which board was detected.
- For touch issues, try different `startup_rotation` values in the board file:
  `_0`, `_90`, `_180`, `_270`.

### esptool.py "command not found"

```bash
pip3 install esptool
```

Or use the one installed by ESP-IDF:

```bash
ls ~/.espressif/python_env/*/bin/esptool.py
```

## Quick reference

| Task | Command |
|------|---------|
| Build firmware | `./scripts/build_mpos.sh esp32s3` |
| Flash firmware | `./scripts/flash_over_usb.sh` |
| Install filesystem | `./scripts/install.sh` |
| Connect to REPL | `mpremote repl` |
| Copy file to board | `mpremote cp local.py :/remote.py` |
| Run script on board | `mpremote run script.py` |
| List files on board | `mpremote ls :/` |
| Soft reset board | `mpremote reset` |
