import json
import inspect
from .enums import DeviceType, OperateCode, BaseEnum


# DTO class
class Telegram:
    def __init__(self, device_address:(int,int)=None):
        self.source_address = None
        self.source_device_type = DeviceType.PyBusPro
        self.operate_code:OperateCode = None
        self.target_address = device_address
        self._payload = None
        self.crc = None

    def __str__(self):
        """Return object as readable string."""
        _dict = vars(self)

        def _enum_encoder(obj):
            if isinstance(obj, BaseEnum):
                return obj.name
            try:
                return obj.__dict__
            except AttributeError:
                return str(obj)

        return json.JSONEncoder(default=_enum_encoder).encode(_dict)

    def __eq__(self, other):
        """Equal operator."""
        return self.__dict__ == other.__dict__
    
    @property
    def payload(self):
        # 这个属性只读，只能设置一次
        if self._payload is not None:
            return self._payload

        self._payload = []
        member_dict = vars(self)
        # 遍历成员及其值
        for member, value in member_dict.items():
            if member.startswith("_") and member != "_payload":
                self._payload.append(value)
        return self._payload
    
    @payload.setter
    def payload(self, new_value):
        self._payload = new_value

    def toControl(self):        
        if self.operate_code is None:
            return self

        # 根据操作类型找出属于哪个Control类
        control = None
        class_name = f"{self.operate_code.name}Data"
        # 获取当前模块中定义的所有对象        
        objects = globals().values() 
        classes = [obj for obj in objects if inspect.isclass(obj)]        
        for clas in classes:
            if clas.__name__ == class_name:
                control = clas(self.target_address)
                break        
        
        if control:
            # 字段赋值
            control.source_address = self.source_address
            control.source_device_type = self.source_device_type
            control._payload = self._payload
            control.crc = self.crc
            # payload字段赋值
            index = 0
            member_dict = vars(control)
            for member in member_dict.keys():
                if member.startswith("_") and member != "_payload":
                    member_dict[member] = control._payload[index]
                    index += 1
        
        return control if control else self

class ReadStatusOfChannelsData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadStatusOfChannels
class ReadStatusOfChannelsResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadStatusOfChannelsResponse
        self._channel_count = 0
    def get_status(self, channel):
        return self._payload[channel] if channel < self._channel_count else None

class SingleChannelControlData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.SingleChannelControl
        self._channel_number = None
        self._channel_status = None
        self._running_time_minutes = None
        self._running_time_seconds = None
class SingleChannelControlResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.SingleChannelControlResponse
        self._channel_number = None
        self._success = None
        self._channel_status = None

class ReadStatusOfUniversalSwitchData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadStatusOfUniversalSwitch
        self._switch_number = None
class ReadStatusOfUniversalSwitchResponseData(Telegram):
    # 这个按我的理解好像不太对，应该是跟ReadStatusOfChannelsResponseData结构差不多
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadStatusOfUniversalSwitchResponse
        self._switch_number = None
        self._switch_status = None

class UniversalSwitchControlData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.UniversalSwitchControl
        self._switch_number = None
        self._switch_status = None
class UniversalSwitchControlResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.UniversalSwitchControlResponse
        self._switch_number = None
        self._switch_status = None

class SceneControlData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.SceneControl
        self._area_number = None
        self._scene_number = None
class SceneControlResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.SceneControlResponse
        
class ReadSensorStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadSensorStatus
class ReadSensorStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadSensorStatusResponse
        self._success = None
        self._current_temperature = None
        self._brightness_high = None
        self._brightness_low = None
        self._motion_sensor = None
        self._sonic = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None

class ReadSensorsInOneStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadSensorsInOneStatus
class ReadSensorsInOneStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadSensorsInOneStatusResponse
        self._bit_0 = None
        self._current_temperature = None
        self._bit_2 = None
        self._bit_3 = None
        self._bit_4 = None
        self._bit_5 = None
        self._bit_6 = None
        self._motion_sensor = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None

class ReadDryContactStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadDryContactStatus
        self._switch_number = None
class ReadDryContactStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadDryContactStatusResponse
        self._bit_0 = None
        self._switch_number = None
        self._switch_status = None

class BroadcastSensorStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.BroadcastSensorStatusResponse
        self._current_temperature = None
        self._brightness_high = None
        self._brightness_low = None
        self._motion_sensor = None
        self._sonic = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None
class BroadcastSensorStatusAutoResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.BroadcastSensorStatusAutoResponse
        self._current_temperature = None
        self._brightness_high = None
        self._brightness_low = None
        self._motion_sensor = None
        self._sonic = None
        self._dry_contact_1_status = None
        self._dry_contact_2_status = None
class BroadcastTemperatureResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.BroadcastTemperatureResponse
        self._bit_0 = None
        self._current_temperature = None
class BroadcastStatusOfUniversalSwitchData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.BroadcastStatusOfUniversalSwitch
        self._switch_count = None
    def get_switch_status(self, number):
        return self._payload[number] if number<self._switch_count else None

class ControlFloorHeatingStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ControlFloorHeatingStatus
        self._temperature_type = None # 0 = C, 1 = F
        self._status = None # 0 = OFF, 1 = ON
        self._mode = None # 1 = Normal, 2 = Day , 3 = Night, 4 = Away, 5 = Timer
        self._normal_temperature = None
        self._day_temperature = None
        self._night_temperature = None
        self._away_temperature = None
class ControlFloorHeatingStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ControlFloorHeatingStatusResponse
        self._success = None
        self._temperature_type = None # 0 = C, 1 = F
        self._status = None # 0 = OFF, 1 = ON
        self._mode = None # 1 = Normal, 2 = Day , 3 = Night, 4 = Away, 5 = Timer
        self._normal_temperature = None
        self._day_temperature = None
        self._night_temperature = None
        self._away_temperature = None
        self._Timer = None # 0 = Day, 1 = Night

class ReadFloorHeatingStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadFloorHeatingStatus
class ReadFloorHeatingStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadFloorHeatingStatusResponse
        self._temperature_type = None # 0 = C, 1 = F
        self._current_temperature = None
        self._status = None # 0 = OFF, 1 = ON
        self._mode = None # 1 = Normal, 2 = Day , 3 = Night, 4 = Away, 5 = Timer
        self._normal_temperature = None
        self._day_temperature = None
        self._night_temperature = None
        self._away_temperature = None

class ReadAirConditionStatusData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadAirConditionStatus
        self._ac_number = None
class ReadAirConditionStatusResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ReadAirConditionStatusResponse
        self._ac_number = None
        self._temperature_type = None # 0-C, 1-F
        self._current_temperature = None
        self._cool_temperature = None
        self._heat_temperature = None
        self._auto_temperature = None
        self._dry_temperature = None
        self._bit_7 = None
        self._status = None # 0-OFF, 1-ON
        self._mode = None # 0-COOL, 1-Heat, 2-FAN, 3-Auto, 4-Dry
        self._fan = None # 0-Auto, 1-High, 2-Medium, 3-Low
        self._temperature = None # 不清楚指定的是什么温度
        self._bit_12 = None # 都是00

class ControlAirConditionData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ControlAirCondition
        self._ac_number = None
        self._temperature_type = None
        self._current_temperature = None
        self._cool_temperature = None
        self._heat_temperature = None
        self._auto_temperature = None
        self._dry_temperature = None
        self._bit_7 = 48 # 十六进制30
        self._status = None
        self._mode = None
        self._fan = None
        self._bit_11 = 0
        self._bit_12 = 0
class ControlAirConditionResponseData(Telegram):
    def __init__(self, device_address):
        super().__init__(device_address)
        self.operate_code = OperateCode.ControlAirConditionResponse
        self._ac_number = None
        self._temperature_type = None
        self._current_temperature = None
        self._cool_temperature = None
        self._heat_temperature = None
        self._auto_temperature = None
        self._dry_temperature = None
        self._bit_7 = None
        self._status = None
        self._mode = None
        self._fan = None
        self._bit_11 = None
        self._bit_12 = None
