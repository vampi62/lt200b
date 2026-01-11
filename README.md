# lt200b

The Dymo LetraTag 200B is a Bluetooth label printer that comes with an iOS and Android app. The app only allows you to print text using a couple of installed fonts. This script implements the BLE protocol and allows you to print any image from your computer.

## Usage

Use the MAC address printed on the back of the printer. Since the printer uses pixels that are twice as high as they are wide, the aspect ratio of the image is automatically adjusted.

```
python print.py --address aa:bb:cc:dd:ee:ff --image hello.png
python print.py --address aa:bb:cc:dd:ee:ff --text "Hello World"
```

## UI

You can also use a simple GUI to print images or text.
or replace the "address" variable in gui.py with the MAC address of your printer to start the graphical interface without having to enter it each time.

```
python gui.py --address aa:bb:cc:dd:ee:ff
```

![GUI Screenshot](gui.png)

