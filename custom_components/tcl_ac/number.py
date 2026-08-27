import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import TclAttribute
from .core.device import TclDevice
from .entity import TclAbstractEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.NUMBER,
        lambda device, attribute: TclNumber(device, attribute)
    )


class TclNumber(TclAbstractEntity, NumberEntity):

    def __init__(self, device: TclDevice, attribute: TclAttribute):
        super().__init__(device, attribute)

    def _update_value(self):
        if self._attribute.key in self._attributes_data:
            self._attr_native_value = self._attributes_data[self._attribute.key]

    def set_native_value(self, value: float) -> None:
        self._send_command({
            self._attribute.key: value
        })
