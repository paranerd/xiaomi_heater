# Xiaomi Mi Smart Heater

This is a custom component for home assistant to integrate the Xiaomi Mi Smart Fan.

Based on the foundation of [Rytilahti](https://github.com/rytilahti/python-miio) - Huge Thank You!

## Supported Devices

| Name | Model |
| ----------------------- | ---------------------- |
| Smartmi Smart Heater 1S | zhimi.heater.za1 |
| Smartmi Smart Heater | zhimi.heater.za2 |
| Smartmi Smart Convector Heater 1S | zhimi.heater.zb1 |
| Mi Smart Space Heater S 2020 | zhimi.heater.mc2 |
| Mi Smart Space Heater S | zhimi.heater.mc2a |

## Features

- Power (on, off)
- Target temperature
- Delay off countdown
- Attributes
    - Humidity (zhimi.heater.za1 and zhimi.heater za2 only)
    - Current temperature
    - Target temperature

## Prerequisites

Please follow the instructions on [Retrieving the Access Token](https://www.home-assistant.io/integrations/xiaomi_miio/#xiaomi-cloud-tokens-extractor) to get the API token to use in setup.

## Install

You can install it manually by copying the `custom_component/` folder to your Home Assistant configuration folder.

## Setup

1. Go to "Settings" -> "Devices & Services" -> "Add Integration"
1. Search for "Xiaomi Mi Smart Heater"
1. Enter the following details:
    - Host: IP of your device
    - Name: Friendly name of the device in Home Assistant
    - Token: The API token you got earlier
1. Submit

## Troubleshooting

### Home Assistant cannot connect to the device

Make sure that Home Assistant and the Xiaomi device are in the same subnet. Otherwise Xiaomi will block communication.
