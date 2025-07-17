#!/bin/bash

ID_VENDOR="04b4"
ID_PRODUCT="00f5"

bus_dev=$(lsusb | grep "$ID_VENDOR:$ID_PRODUCT" | awk '{print $2 "/" $4}' | sed 's/://')
if [ -n "$bus_dev" ]; then
  echo "Found at /dev/bus/usb/$bus_dev"
  ln -sf "/dev/bus/usb/$bus_dev" /dev/evk4
else
  echo "Device not found"
fi

exec "$@"