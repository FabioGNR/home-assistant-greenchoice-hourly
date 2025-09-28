# Greenchoice Energy Consumption importer

[![GitHub Release][releases-shield]][releases-link]
[![License][license-shield]][license-link]

## Description

This custom integration for [Home Assistant](https://www.home-assistant.io/) will periodically import historical consumption data from Greenchoice.
The data can then be used in the energy dashboard.

- Electricity consumption (low/high/total)
- Electricity cost (total)
- Gas consumption (low/high/total)
- Gas cost (total)

It assumes hourly data is available and imports it as such.

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FabioGNR&repository=home-assistant-greenchoice-hourly)

## Setup

After installing the integration, go to Configuration > Integrations, click the + button at the bottom right, and search for "Greenchoice" to add an account.

## Usage

By default the integration attempts to import the last 3 weeks when first added. Twice a day it will check for new data and import automatically.

## Services

- TODO: implement custom import service to allow importing specific periods
- TODO: implement import service to force update of last few days
- TODO: implement service to delete all statistics added by this integration

# Thanks to

Integration [homeassistant-greenchoice](https://github.com/barisdemirdelen/homeassistant-greenchoice) for inspiration and authentication code.

[releases-shield]: https://img.shields.io/github/release/FabioGNR/home-assistant-greenchoice-hourly.svg
[releases-link]: https://github.com/FabioGNR/home-assistant-greenchoice-hourly/releases
[license-shield]: https://img.shields.io/github/license/FabioGNR/home-assistant-greenchoice-hourly?color=brightgreen
[license-link]: https://github.com/FabioGNR/home-assistant-greenchoice-hourly/blob/master/LICENSE
