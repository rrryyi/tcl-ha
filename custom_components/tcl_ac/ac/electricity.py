"""TCL 空调电量统计传感器"""
import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .. import DOMAIN
from ..core.config import DeviceFilterConfig
from ..core.device import TclDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_electricity_sensors(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """为空调设备创建电量统计传感器"""
    entities = []
    for device in hass.data[DOMAIN]["devices"]:
        if DeviceFilterConfig.is_skip(hass, entry, device.id):
            continue
        has_climate_attrs = any(
            attr.key in ("powerSwitch", "workMode", "targetTemperature") for attr in device.attributes
        )
        if has_climate_attrs:
            entities.append(TclElectricitySensor(device))

    if entities:
        async_add_entities(entities)


class TclElectricitySensor(SensorEntity):
    """电量统计传感器"""

    _attr_should_poll = True
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, device: TclDevice):
        self._device = device
        self._client = device.client
        self._attr_unique_id = '{}.{}_electricity_summary'.format(DOMAIN, device.id).lower()
        self._attr_name = f"{device.name} 电量统计"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id.lower())},
            name=device.name,
            manufacturer='TCL',
            model=device.product_key
        )
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._last_update = None

    async def async_update(self) -> None:
        now = datetime.now()
        if self._last_update and (now - self._last_update) < timedelta(hours=24):
            return
        self._last_update = now

        try:
            # timeType: 1=周, 2=月, 3=年
            data = await self._client.get_electricity_summary(self._device.id, self._device.product_key, 1)
            if not data or not data.get('ecoDetails'):
                self._attr_native_value = None
                self._attr_extra_state_attributes = {'status': 'no data'}
                return

            # ecoDetails 是数组，取最后一个元素作为当前周期
            eco_details = data['ecoDetails']
            current = eco_details[-1] if eco_details else {}

            # 主值：当前周期总电量
            electricity = current.get('electricity')
            if electricity is not None:
                try:
                    self._attr_native_value = float(electricity)
                except (ValueError, TypeError):
                    self._attr_native_value = None
            else:
                self._attr_native_value = None

            # 属性：只存精简摘要，避免超过 HA 的 16384 字节限制
            attrs = {}
            if current.get('electricityBill') is not None:
                attrs['electricity_bill'] = current['electricityBill']
            if current.get('ecoHours') is not None:
                attrs['eco_hours'] = current['ecoHours']
            if current.get('runningHours') is not None:
                attrs['running_hours'] = current['runningHours']
            if current.get('carbonEmission') is not None:
                attrs['carbon_emission_kg'] = current['carbonEmission']
            if current.get('runningHoursPerDay') is not None:
                attrs['running_hours_per_day'] = current['runningHoursPerDay']
            if current.get('electricityPerDay') is not None:
                attrs['electricity_per_day'] = current['electricityPerDay']

            # 历史周期摘要（只存电量和费用，不存 dataList）
            history = []
            for item in eco_details[:-1]:
                history.append({
                    'electricity': item.get('electricity'),
                    'electricity_bill': item.get('electricityBill'),
                    'running_hours': item.get('runningHours'),
                    'eco_hours': item.get('ecoHours'),
                })
            if history:
                attrs['history'] = history

            attrs['time_type'] = 'weekly'
            self._attr_extra_state_attributes = attrs

        except Exception as e:
            _LOGGER.error(
                "Error fetching electricity summary for device %s: %s",
                self._device.id, e
            )
            self._attr_native_value = None
            self._attr_extra_state_attributes = {'error': str(e)}
