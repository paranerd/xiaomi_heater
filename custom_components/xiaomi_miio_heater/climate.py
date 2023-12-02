"""Climate support for Xiaomi Smart Heater."""
from functools import partial
import logging
from typing import Any

from miio import DeviceException
from miio.miot_device import DeviceStatus, MiotDevice
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUCCESS = ["ok"]
CONF_MODEL = "model"
SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE)

DEVICE_ID = ""

TEMP_PRECISION = 1
MIN_TEMP = 18
MIN_TEMP_ZB1 = 16
MAX_TEMP = 28

MODEL_HEATER_ZA1 = "zhimi.heater.zb1"
MODEL_HEATER_ZA2 = "zhimi.heater.za2"
MODEL_HEATER_ZB1 = "zhimi.heater.za1"
MODEL_HEATER_MC2 = "zhimi.heater.mc2"
MODEL_HEATER_MC2A = "zhimi.heater.mc2a"

ATTR_DURATION = "duration"

SERVICE_SET_DELAY_OFF = "climate_set_delay_off"

SERVICE_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_id})

SERVICE_SCHEMA_DELAY_OFF = SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_DURATION): cv.positive_int}
)

SERVICES = {
    SERVICE_SET_DELAY_OFF: {
        "method": "async_set_delay_off",
        "schema": SERVICE_SCHEMA_DELAY_OFF,
    },
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate device."""

    data = hass.data[DOMAIN][config_entry.entry_id]

    devices = []

    #device = Device(data[CONF_HOST], data["token"])
    unique_id = "{}-{}".format(data[CONF_MODEL], data["mac"])

    if data[CONF_MODEL] in [
        MODEL_HEATER_MC2,
        MODEL_HEATER_MC2A
    ]:
        heater = HeaterMC2(data[CONF_HOST], data[CONF_TOKEN], model=data[CONF_MODEL])
        miHeater = XiaomiHeater(heater, data[CONF_NAME], data[CONF_MODEL], unique_id, hass)
    elif data[CONF_MODEL] == MODEL_HEATER_ZA1:
        heater = HeaterZA1(data[CONF_HOST], data[CONF_TOKEN], model=data[CONF_MODEL])
        miHeater = XiaomiHeater(heater, data[CONF_NAME], data[CONF_MODEL], unique_id, hass)
    elif data[CONF_MODEL] in [MODEL_HEATER_ZA2, MODEL_HEATER_ZB1]:
        heater = HeaterZA2(data[CONF_HOST], data[CONF_TOKEN], model=data[CONF_MODEL])
        miHeater = XiaomiHeater(heater, data[CONF_NAME], data[CONF_MODEL], unique_id, hass)
    else:
        _LOGGER.error(
            "Unsupported device found! Please create an issue at "
            "https://github.com/paranerd/xiaomi_heater/issues "
            "and provide the following data: %s",
            data[CONF_MODEL],
        )
        return False

    devices.append(miHeater)

    async_add_entities(devices, update_before_add=True)

    async def async_service_handler(entity, service_call):
        """Map services to methods on XiaomiFan."""
        service = SERVICES.get(service_call.service)
        params = {
            key: value for key, value in service_call.data.items() if key != ATTR_ENTITY_ID
        }

        if hasattr(entity, service["method"]):
            await getattr(entity, service["method"])(**params)

    platform = entity_platform.async_get_current_platform()

    for name, service in SERVICES.items():
      schema = service.get(
            "schema", SERVICE_SCHEMA
      )

      platform.async_register_entity_service(
          name,
          schema,
          async_service_handler,
      )

class XiaomiHeater(ClimateEntity):
    """Representation of a Xiaomi Heater device."""

    def __init__(self, device, name, model, unique_id, _hass) -> None:
        """Initialize the heater."""
        self._device = device
        self._name = name
        self._model = model
        self._state = None
        self._attr_unique_id = unique_id
        #self.getAttrData()

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def device(self):
        """Return the model of the device."""
        return self._model

    @property
    def hvac_mode(self) -> HVACMode:
        """Return HVAC mode."""
        return HVAC_MODE_HEAT if self._state["power"] else HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes."""
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]


    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @property
    def precision(self) -> float:
        """Return the unit of measurement which this thermostat uses."""
        return TEMP_PRECISION

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._state["target_temperature"]

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self._state["current_temperature"]

    @property
    def current_humidity(self) -> int:
        """Return the current humidity."""
        return self._state["humidity"]

    @property
    def target_temperature_step(self) -> float:
        """Return the supported step of target temperature."""
        return 1

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a miio device command handling error messages."""
        try:
            result = await self.hass.async_add_job(partial(func, *args, **kwargs))

            _LOGGER.debug("Response received from miio device: %s", result)

            return result == SUCCESS
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    @property
    def extra_state_attributes(self) -> (dict[str, Any] | None):
        """Return state."""
        return self._state

    @property
    def is_on(self) -> bool:
        """Return true if heater is on."""
        return self._state["power"]

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self._device.min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return MAX_TEMP

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.warning("Setting temperature: %s", temperature)
        if temperature is None:
            _LOGGER.error("Wrong temperature: %s", temperature)
            return

        await self._try_command(
            "Setting temperature of the miio device failed.",
            self._device.set_temperature,
            int(temperature),
        )

    async def async_set_delay_off(self, **kwargs: Any) -> None:
        """Set delay off duration."""
        duration = kwargs.get(ATTR_DURATION)
        if duration is None:
            _LOGGER.error("Invalid duration: %s", duration)
            return

        _LOGGER.info("Setting delay duration to %s", duration)

        await self._try_command(
            "Setting delay off duration of the miio device failed.",
            self._device.set_delay_off,
            int(duration),
        )

    async def async_turn_on(self) -> None:
        """Turn the device on."""
        self._device.turn_on()

    async def async_turn_off(self) -> None:
        """Turn the device off."""
        self._device.turn_off()

    async def async_update(self) -> None:
        """Retrieve latest state."""
        try:
            state = await self.hass.async_add_job(self._device.status)

            self._state = {
                "power": state.power,
                "current_temperature": state.current_temperature,
                "target_temperature": state.target_temperature,
                "humidity": state.humidity
            }

        except DeviceException as ex:
            _LOGGER.exception("Caught update exception %s", ex)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set operation mode."""
        if hvac_mode in [HVAC_MODE_HEAT, HVAC_MODE_COOL]:
            await self.async_turn_on()
        elif hvac_mode  == HVAC_MODE_OFF:
            await self.async_turn_off()
        else:
            _LOGGER.error("Unrecognized operation mode: %s", hvac_mode)

class HeaterStatus(DeviceStatus):
    """Container for status reports for Heater."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Populate data."""
        self.data = data

    @property
    def power(self) -> bool:
        """Return if device is turned on."""
        return self.data["power"]

    @property
    def target_temperature(self) -> bool:
        """Return target temperature."""
        return self.data["target_temperature"]

    @property
    def current_temperature(self) -> bool:
        """Return current temperature."""
        return self.data["current_temperature"]

    @property
    def humidity(self) -> bool:
        """Return current humidity."""
        return self.data["humidity"] if "humidity" in self.data else 0

class Heater(MiotDevice):
    """Representation of a generic Xiaomi Heater."""

    def __init__(
        self,
        ip: str,
        token: str,
        start_id: int,
        debug: int,
        lazy_discover: bool,
        model: str,
    ) -> None:
        """Initialize a generic Xiaomi Heater."""
        super().__init__(ip, token, start_id, debug, lazy_discover, model=model)

    def status(self):
        """Retrieve properties."""
        return HeaterStatus(
            {
                prop["did"]: prop["value"] if prop["code"] == 0 else None
                for prop in self.get_properties_for_mapping()
            }
        )

    def turn_on(self):
        """Power on."""
        return self.set_property("power", True)

    def turn_off(self):
        """Power off."""
        return self.set_property("power", False)

    def set_temperature(self, temperature: int):
        """Set temperature."""
        if temperature is None:
            _LOGGER.error("Invalid temperature: %s", temperature)
            return

        return self.set_property("target_temperature", temperature)

    def set_delay_off(self, duration: int):
        """Set delay off duration."""
        return self.set_property("countdown", int(duration))

    @property
    def min_temp(self) -> float:
        """Get minimum temperature."""
        return MIN_TEMP

class HeaterZA1(Heater):
    """Representation of a Xiaomi Heater ZA1."""

    mapping = {
        # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:heater:0000A01A:zhimi-za1:1
        "power": {"siid": 2, "piid": 1},
        "target_temperature": {"siid": 2,"piid": 2},
        "current_temperature": {"siid":3,"piid":1},
        "humidity": {"siid":3,"piid":2},
        "countdown": {"siid": 6, "piid": 1},
    }

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        model: str = None,
    ) -> None:
        """Initialize a Xiaomi Heater ZA1 device."""
        super().__init__(ip, token, start_id, debug, lazy_discover, model=model)

    @property
    def min_temp(self) -> float:
        """Get minimum temperature."""
        return MIN_TEMP_ZB1

class HeaterZA2(Heater):
    """Representation of a Xiaomi Heater ZA2 and ZB1."""

    mapping = {
        # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:heater:0000A01A:zhimi-za2:1
        # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:heater:0000A01A:zhimi-zb1:1
        "power": {"siid": 2, "piid": 2},
        "target_temperature": {"siid":2,"piid":6},
        "current_temperature": {"siid":5,"piid":8},
        "humidity": {"siid":5,"piid":7},
        "countdown": {"siid": 4, "piid": 1},
    }

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        model: str = None,
    ) -> None:
        """Initialize a Xiaomi Heater ZA2 device."""
        super().__init__(ip, token, start_id, debug, lazy_discover, model=model)

    @property
    def min_temp(self) -> float:
        """Get minimum temperature."""
        return MIN_TEMP_ZB1

class HeaterMC2(Heater):
    """Representation of a Xiaomi Heater MC2(a)."""

    mapping = {
        # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:heater:0000A01A:zhimi-mc2:1
        # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:heater:0000A01A:zhimi-mc2a:1
        "power": {"siid": 2, "piid": 1},
        "target_temperature": {"siid": 2,"piid": 5},
        "current_temperature": {"siid": 4,"piid": 7},
        "countdown": {"siid": 3, "piid": 1},
    }

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        model: str = None,
    ) -> None:
        """Initialize a Xiaomi Heater MC2 device."""
        super().__init__(ip, token, start_id, debug, lazy_discover, model=model)
