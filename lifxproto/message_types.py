from collections import namedtuple

from hachoir.field import FieldSet, Enum, String, Float32
from hachoir.field import UInt64, UInt32, UInt16, Int16, UInt8, NullBits, Bytes, RawBytes

from .message_converters import enumConverter, labelConverter


PAYLOAD_CLASSES = []
EMPTY_REQUEST_PAYLOADS = []


def empty_request_type(typename, name, typeid):
    typ = namedtuple(typename, 'name typeid direction'.split())
    obj = typ(name, typeid, 'send')
    EMPTY_REQUEST_PAYLOADS.append(obj)
    return obj


GetService      = empty_request_type('GetService', 'get_service', 2)
GetHostInfo     = empty_request_type('GetHostInfo', 'get_host_info', 12)
GetHostFirmware = empty_request_type('GetHostFirmware', 'get_host_firmware', 14)
GetWifiInfo     = empty_request_type('GetWifiInfo', 'get_wifi_info', 16)
GetWifiFirmware = empty_request_type('GetWifiFirmware', 'get_wifi_firmware', 18)
GetPower        = empty_request_type('GetPower', 'get_power', 18)
GetLabel        = empty_request_type('GetLabel', 'get_label', 23)
GetVersion      = empty_request_type('GetVersion', 'get_version', 32)
GetInfo         = empty_request_type('GetInfo', 'get_info', 34)
Acknowledgement = empty_request_type('Acknowledgement', 'acknowledgement', 45)
GetLocation     = empty_request_type('GetLocation', 'get_location', 48)
GetGroup        = empty_request_type('GetGroup', 'get_group', 51)
LightGet        = empty_request_type('LightGet', 'light_get', 101)
LightGetPower   = empty_request_type('LightGetPower', 'light_get_power', 116)
LightGetInfrared = empty_request_type('LightGetInfrared', 'light_get_infrared', 120)
MultiZoneGetColorZones = empty_request_type('MultiZoneGetColorZones', 'multi_zone_get_color_zones', 502)


def payload(typeid, name, request=False):
    def wrapper(klass):
        klass.typeid = typeid
        klass.name = name
        klass.direction = 'send' if request else 'recv'
        PAYLOAD_CLASSES.append(klass)
        return klass
    return wrapper


class GUIDField(RawBytes):
    def __init__(self, parent, name):
        super().__init__(parent, name, 16, "GUID value")


class Label(String):
    def __init__(self, parent, name):
        super().__init__(parent, name, 32, charset='ASCII', strip='\0', truncate='\0')


Label = labelConverter(Label)


@payload(3, 'state_service')
class StateService(FieldSet):
    def createFields(self):
        yield UInt8(self, 'service')
        yield UInt32(self, 'port')


@payload(13, 'state_host_info')
class StateHostInfo(FieldSet):
    def createFields(self):
        yield Float32(self, "signal")
        yield UInt32(self, "tx")
        yield UInt32(self, "rx")
        yield UInt16(self, "reserved[]")


@payload(15, 'state_host_firmware')
class StateHostFirmware(FieldSet):
    def createFields(self):
        yield UInt64(self, "build")
        yield NullBits(self, "reserved[]", 64)
        yield UInt32(self, "version")


@payload(17, 'state_wifi_info')
class StateWifiInfo(FieldSet):
    def createFields(self):
        yield Float32(self, "signal")
        yield UInt32(self, "tx")
        yield UInt32(self, "rx")
        yield UInt16(self, "reserved[]")


@payload(19, 'state_wifi_firmware')
class StateWifiFirmware(FieldSet):
    def createFields(self):
        yield UInt64(self, "build")
        yield UInt64(self, "reserved[]")
        yield UInt32(self, "version")


@payload(21, 'set_power', request=True)
class SetPower(FieldSet):
    def createFields(self):
        yield UInt16(self, "level")


@payload(22, 'state_power')
class StatePower(FieldSet):
    def createFields(self):
        yield UInt16(self, "level")


@payload(24, 'set_label')
class SetLabel(FieldSet):
    def createFields(self):
        yield Label(self, "label")


@payload(25, 'state_label')
class StateLabel(FieldSet):
    def createFields(self):
        yield Label(self, "label")


@payload(33, 'state_version')
class StateVersion(FieldSet):
    def createFields(self):
        yield UInt32(self, 'vendor')
        yield UInt32(self, 'product')
        yield UInt32(self, 'version')


@payload(35, 'state_info')
class StateInfo(FieldSet):
    def createFields(self):
        yield UInt64(self, "time")
        yield UInt64(self, "uptime")
        yield UInt64(self, "downtime")


@payload(50, 'state_location')
class StateLocation(FieldSet):
    def createFields(self):
        yield GUIDField(self, "location")
        yield Label(self, "label")
        yield UInt64(self, "updated_at")


@payload(53, 'state_group')
class StateGroup(FieldSet):
    def createFields(self):
        yield GUIDField(self, 'group')
        yield Label(self, "label")
        yield UInt64(self, "updated_at")


@payload(58, 'echo_request', request=True)
class EchoRequest(FieldSet):
    def createFields(self):
        yield Bytes(self, "blob", 64)


@payload(59, 'echo_response')
class EchoResponse(FieldSet):
    def createFields(self):
        yield Bytes(self, "blob", 64)


class HSBK(FieldSet):
    def createFields(self):
        yield UInt16(self, "hue")
        yield UInt16(self, "saturation")
        yield UInt16(self, "brightness")
        yield UInt16(self, "kelvin")


@payload(102, 'light_set_color', request=True)
class LightSetColor(FieldSet):
    def createFields(self):
        yield UInt8(self, "reserved[]")
        yield HSBK(self, "color")
        yield UInt32(self, "duration")


@payload(103, 'light_set_waveform', request=True)
class LightSetWaveform(FieldSet):
    WAVEFORMS = {
        0: 'saw',
        1: 'sine',
        2: 'half_sine',
        3: 'triangle',
        4: 'pulse'
    }

    def createFields(self):
        yield UInt8(self, "reserved[]")
        yield UInt8(self, "transient")
        yield HSBK(self, "color")
        yield UInt32(self, "period")
        yield Float32(self, "cycles")
        yield Int16(self, "skew_ratio")
        yield enumConverter(Enum(UInt8(self, "waveform"), self.WAVEFORMS))


@payload(107, 'light_state')
class LightState(FieldSet):
    def createFields(self):
        yield HSBK(self, "color")
        yield Int16(self, "reserved[]")
        yield UInt16(self, "power")
        yield Label(self, "label")
        yield UInt64(self, "reserved[]")


@payload(117, 'light_set_power')
class LightSetPower(FieldSet):
    def createFields(self):
        yield UInt16(self, "level")
        yield UInt32(self, "duration")


@payload(118, 'light_state_power')
class LightStatePower(FieldSet):
    def createFields(self):
        yield UInt16(self, "level")


#
# TODO:
#
#   LightStateInfrared: 121,
#   MultiZoneStateZone: 503,
#   ... maybe more ...
#


def valid_type_ids():
    typeids = [obj.typeid for obj in EMPTY_REQUEST_PAYLOADS]
    typeids.extend([kls.typeid for kls in PAYLOAD_CLASSES])
    return typeids


def type_ids_by_name():
    lookup = {obj.name: obj.typeid for obj in EMPTY_REQUEST_PAYLOADS}
    lookup.update({kls.name: kls.typeid for kls in PAYLOAD_CLASSES})
    return lookup


VALID_TYPE_IDS = valid_type_ids()
TYPE_IDS_BY_NAME = type_ids_by_name()
EMPTY_REQUEST_PAYLOADS_IDS = [obj.typeid for obj in EMPTY_REQUEST_PAYLOADS]


__all__ = [t.__class__.__name__ for t in EMPTY_REQUEST_PAYLOADS]
__all__ = __all__ + [kls.__name__ for kls in PAYLOAD_CLASSES]
