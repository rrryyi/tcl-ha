import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import async_register_entity
from .core.attribute import TclAttribute
from .core.device import TclDevice
from .entity import TclAbstractEntity
from .helpers import get_key_by_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    await async_register_entity(
        hass,
        entry,
        async_add_entities,
        Platform.SELECT,
        lambda device, attribute: TclSelect(device, attribute)
    )


class TclSelect(TclAbstractEntity, SelectEntity):

    def __init__(self, device: TclDevice, attribute: TclAttribute):
        super().__init__(device, attribute)

        if 'value_comparison_table' not in attribute.ext.keys():
            raise ValueError('value_comparison_table must exist')

    def _update_value(self):
        if self._attribute.key in self._attributes_data:
            self._attr_current_option = self._get_value_from_comparison_table(self._attributes_data[self._attribute.key])

    def select_option(self, option: str) -> None:
        #这里需要通过option反查key
        key = get_key_by_value(self._attribute.ext.get('value_comparison_table'), option)
        # key 可能为合法的 0（如"关"、"自动"），不能用真值判断，否则该选项永远发不出去
        if key is not None:
            self._send_command({
                self._attribute.key: key
            })
        else:
            _LOGGER.warning('Device [{}] attribute [{}] option [{}] 反查 key 失败'.format(
                self._device.id, self._attribute.key, option
            ))

    def _get_value_from_comparison_table(self, value):
        value_comparison_table = self._attribute.ext.get('value_comparison_table', {})
        if str(value) not in value_comparison_table:
            _LOGGER.warning('Device [{}] attribute [{}] value [{}] not recognizable'.format(
                self._device.id, self._attribute.key, value
            ))
            return value

        return value_comparison_table.get(str(value))
