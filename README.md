Directly upload those files to the Raspberry Pi Pico 2W after flashing Micropython in BOOTSEL mode.
Note: it makes sense to set a request_timeout around 10 - 20s for each request to ensure that the script doesn't time out and gets stuck when the API is not responding.
Please adjust the config file as needed:
Required:
- Your wifi-name
- You wifi-password
- Clock: please set your time offset (for CEST / UTC+2 it's 7200; you can easily calculate it by multiplying the UTC offset with 3600, e.g., UTC+2 => 2*3600 = 7200 for CEST).
Optional (if you want another transit API):
- please find the documentation of your target transit network and adjust the query_VAG_API() function in LED_MATRIX.py according to your needs.
- Adjust the API information in config.json accordingly.

Special thanks to Mike Causer for providing the max7219.py driver logic for the LED matrix!
