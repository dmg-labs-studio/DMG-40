Directly upload those files to the Raspberry Pi Pico 2W after flashing Micropython in BOOTSEL mode.
Note: it makes sense to set a request_timeout for each request to ensure that the script doesn't time out and gets stuck when the API is not responding.
Please adjust the config file as needed:
Required:
- Your wifi-name
- You wifi-password

Optional (if you want another transit API):
- please find the documentation of your target transit network and adjust the query_VAG_API() function in LED_MATRIX.py according to your needs.

