# svk-mac
Pythonscript to register mac-addresses to Svenskakyrkan-pda or check if they're registered

## Usage
```
svk-mac.py -h -f <find economic unit IDs> -u <username> -p <password> -e <economic unit ID to log in with, get IDs with -f> -m <mac-address> -n <name> -t <LAPTOP/PHONE/TABLET/OTHER> /
-i/--ifile <list-of-mac-adresses.txt> --check <checks if MAC in -m exists> --
```

list-of-mac-adresses.txt tab-separated with
> MAC Name  DeviceType
### Example:
```
11:12:13:14:15:16	123Test	LAPTOP
11:12:13:14:15:17	456Test	PHONE
11:12:13:14:15:18	789Test	TABLET
11:12:13:14:15:19	101Test	OTHER
```

## Requirements
Python modules, add with pip install <module>:
* requests
* beutifulsoup4

## Download
  Download dist/svk-mac/svk-mac.7z, extract and run svk-mac.exe, built on win 10 x64 with pyinstaller.
