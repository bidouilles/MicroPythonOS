mydir=$(readlink -f "$0")
mydir=$(dirname "$mydir")

pkill -f "python.*mpremote"

# Parse arguments
appname=""
board=""
while [ $# -gt 0 ]; do
	case "$1" in
		--board)
			board="$2"
			shift 2
			;;
		*)
			appname="$1"
			shift
			;;
	esac
done

# Board-specific app lists. Only user apps (from apps/) are filtered;
# lib/, builtin/, and data/ are always installed in full.
get_board_apps() {
	case "$1" in
		waveshare_esp32_s3_touch_lcd_28)
			echo "com.micropythonos.helloworld"
			echo "com.micropythonos.confetti"
			echo "com.micropythonos.connect4"
			echo "com.micropythonos.draw"
			echo "com.micropythonos.imu"
			echo "com.micropythonos.musicplayer"
			echo "com.micropythonos.playtune"
			echo "com.micropythonos.showbattery"
			echo "com.micropythonos.showfonts"
			echo "com.micropythonos.tilt"
			echo "com.quasikili.quasibird"
			echo "com.quasikili.quasicalculator"
			echo "com.quasikili.quasinametag"
			;;
		*)
			echo "Unknown board: $1" >&2
			exit 1
			;;
	esac
}

echo "This script will install the important files from internal_filesystem/ on the device using mpremote.py"
echo
echo "Usage: $0 [appname] [--board <board_name>]"
echo "Example: $0"
echo "Example: $0 com.micropythonos.about"
echo "Example: $0 --board waveshare_esp32_s3_touch_lcd_28"

mpremote=$(readlink -f "$mydir/../lvgl_micropython/lib/micropython/tools/mpremote/mpremote.py")

pushd "$mydir"/../internal_filesystem/

# Maybe also do: import mpos ; mpos.TaskManager.stop()
echo "Disabling wifi because it writes to REPL from time to time when doing disconnect/reconnect for ADC2..."
$mpremote exec "import mpos ; mpos.net.wifi_service.WifiService.disconnect()"
sleep 2

if [ ! -z "$appname" ]; then
	echo "Installing one app: $appname"
	appdir="apps/$appname"
        target="apps/"
	if [ ! -d "$appdir" ]; then
		echo "$appdir doesn't exist so taking the builtin/"
		appdir="builtin/apps/$appname/"
                target="builtin/apps/"
		if [ ! -d "$appdir" ]; then
			echo "$appdir also doesn't exist, exiting..."
			exit 1
		fi
	fi
        $mpremote mkdir "/apps"
        #$mpremote mkdir "/builtin" # dont do this because it breaks the mount!
        #$mpremote mkdir "/builtin/apps"
	if test -L "$appdir"; then
		$mpremote fs mkdir :/"$appdir"
		$mpremote fs cp -r "$appdir"/* :/"$appdir"/
	else
		$mpremote fs cp -r "$appdir" :/"$target"
	fi
	echo "start_app(\"/$appdir\")"
	$mpremote
	popd
	exit
fi

# boot.py is not copied because it can't be overridden anyway

# The issue is that this brings all the .git folders with it:
#$mpremote fs cp -r apps :/

$mpremote fs cp -r lib :/


#echo "Unmounting builtin/ so that it can be customized..." # not sure this is necessary
#$mpremote exec "import os ; os.umount('/builtin')"
$mpremote fs cp -r builtin :/

#$mpremote fs cp -r data :/
#$mpremote fs cp -r data/images :/data/

$mpremote fs mkdir :/data
$mpremote fs mkdir :/data/com.micropythonos.system.wifiservice
$mpremote fs cp ../internal_filesystem_excluded/data/com.micropythonos.system.wifiservice/config.json :/data/com.micropythonos.system.wifiservice/

$mpremote fs mkdir :/apps

if [ ! -z "$board" ]; then
	echo "Installing apps for board: $board"
	for app in $(get_board_apps "$board"); do
		appdir="apps/$app"
		if [ ! -d "$appdir" ] && [ ! -L "$appdir" ]; then
			echo "Warning: $appdir not found, skipping..."
			continue
		fi
		echo "Installing $app"
		if test -L "$appdir"; then
			$mpremote fs mkdir :/"$appdir"
			$mpremote fs cp -r "$appdir"/* :/"$appdir"/
		else
			$mpremote fs cp -r "$appdir" :/apps/
		fi
	done
else
	$mpremote fs cp -r apps/com.micropythonos.* :/apps/
	find apps/ -maxdepth 1 -type l | while read symlink; do
		if echo $symlink | grep quasiboats; then
			echo "Skipping $symlink because it's needlessly big..."
			continue
		fi
		echo "Handling symlink $symlink"
		$mpremote fs mkdir :/"$symlink"
		$mpremote fs cp -r "$symlink"/* :/"$symlink"/

	done
fi

popd

# Install test infrastructure (for running ondevice tests)
echo "Installing test infrastructure..."
$mpremote fs mkdir :/tests
$mpremote fs mkdir :/tests/screenshots

if [ ! -z "$appname" ]; then
	echo "Not resetting so the installed app can be used immediately."
	$mpremote reset
fi
