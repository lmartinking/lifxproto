from io import BytesIO
from collections import OrderedDict

from hachoir.field import Parser
from hachoir.field import Bit, Bits, NullBits, Enum
from hachoir.core.endian import LITTLE_ENDIAN

from hachoir.field import UInt8, UInt16, UInt32, Bytes, String, Float32, FieldSet

from hachoir.stream import StringInputStream, FileInputStream, OutputStream
from hachoir.core.text_handler import textHandler
from hachoir.editor import createEditor, EditableFieldSet, EditableField

from .message_types import *

from .message_types import GUIDField

from .message_types import PAYLOAD_CLASSES, EMPTY_REQUEST_PAYLOADS
from .message_types import EMPTY_REQUEST_PAYLOADS_IDS
from .message_types import VALID_TYPE_IDS, TYPE_IDS_BY_NAME

from .message_converters import enumConverter


def formatTargetField(field):
    if field.value:
        return field.value[0:6].hex() if field.value != "" else ""


class DeviceFrameParser(Parser):
    endian = LITTLE_ENDIAN

    def createFields(self):
        yield from self.parseFrame()
        yield from self.parseFrameAddress()
        yield from self.parseProtocolHeader()
        yield from self.parsePayload()

    def parseFrame(self):
        yield UInt16(self, 'size')
        yield Bits(self, 'protocol', 12)  # 1024
        yield Bit(self, 'addressable')  # 1
        yield Bit(self, 'tagged')  # 1
        yield Bits(self, 'origin', 2)
        yield UInt32(self, 'source')

    def parseFrameAddress(self):
        yield textHandler(Bytes(self, 'target', 8), formatTargetField)  # MAC or Zeroes
        yield NullBits(self, 'reserved[]', 48)
        yield NullBits(self, 'reserved[]', 6)
        yield Bit(self, 'ack_required')
        yield Bit(self, 'res_required')
        yield UInt8(self, 'sequence')

    def parseProtocolHeader(self):
        type_names = {p.typeid: p.name for p in PAYLOAD_CLASSES}
        type_names.update({k.typeid: k.name for k in EMPTY_REQUEST_PAYLOADS})

        yield NullBits(self, 'reserved[]', 64)
        yield enumConverter(Enum(UInt16(self, 'type'), type_names))
        yield NullBits(self, 'reserved[]', 16)

    def parsePayload(self):
        type_parsers_by_id = {p.typeid: p for p in PAYLOAD_CLASSES}

        parser = type_parsers_by_id.get(self['type'].value)
        if parser:
            print("Calling:", parser.__name__)
            yield parser(self, parser.name)

        raise StopIteration()

    def walk(self):
        return walk_packet(self)


def walk_packet(target):
    data = OrderedDict()

    for field in target:
        if field.name.startswith('reserved'):
            continue

        if isinstance(field, (String, Float32)):
            data[field.name] = field.value
        elif isinstance(field, GUIDField):
            data[field.name] = field.value.hex()
        elif isinstance(field, (FieldSet, EditableFieldSet)):
            data[field.name] = walk_packet(field)
        else:
            if str(field.value) == field.display:
                data[field.name] = field.value
            else:
                data[field.name] = field.display

    return data


class Message:
    def __init__(self, packet):
        if hasattr(packet, 'proto'):
            self._proto = packet.proto
            self._packet = packet
        else:
            self._proto = packet
            walk_packet(self._proto)
            self._packet = createEditor(packet)
            self._packet.proto = self.proto

        self._payload_name = self._packet['type'].display

        if self._payload_name in self._packet:
            self._payload_field = self._packet[self._payload_name]

            payload_fields = [f.name for f in self._payload_field if not f.name.startswith("reserved")]
            self._payload_fields = tuple(payload_fields)
        else:
            self._payload_field = None
            self._payload_fields = tuple()

        header_fields = [f.name for f in self._packet if not f.name.startswith("reserved")]
        if self._payload_name in header_fields:
            header_fields.remove(self._payload_name)
        self._header_fields = tuple(header_fields)

    def header_fields(self):
        return self._header_fields

    def fields(self):
        return self._payload_fields

    def get_field(self, name):
        if self._payload_field and name in self._payload_field:
            return self._payload_field[name]

        if name in self._packet:
            return self._packet[name]

    def get_proto_field(self, name):
        if self._payload_name in self._proto:
            if name in self._proto[self._payload_name]:
                return self._proto[self._payload_name][name]

        if name in self._proto:
            return self._proto[name]

    def __getattr__(self, item):
        field = self.get_field(item)
        if field:
            proto_field = self.get_proto_field(item)
            converter = getattr(proto_field, 'fromValue', None)
            if converter:
                return converter(field.value)
            return field.value

        raise AttributeError(f"No such field: `{item}`")

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
            return

        field = self.get_field(key)
        if field:
            proto_field = self.get_proto_field(key)
            converter = getattr(proto_field, 'toValue', None)
            if converter:
                value = converter(value)
            field.value = value
            return

        print(f"Error: field {key} does not exist")

    def serialise(self):
        return serialise_packet(self._packet)

    def bytes(self):
        return self.serialise()

    @staticmethod
    def from_bytes(data):
        return Message(parse_packet(data))

    @staticmethod
    def build(*args, **kwargs):
        return Message(build_packet(*args, **kwargs))


def build_packet(typeid, target=None):
    """Build a new editable packet, based off the given Message type"""

    # Allow passing in payload classes
    if hasattr(typeid, 'typeid'):
        typeid = getattr(typeid, 'typeid')
    # Allow passing in names
    if isinstance(typeid, str):
        typeid = TYPE_IDS_BY_NAME.get(typeid)

    if typeid not in VALID_TYPE_IDS:
        raise ValueError("Unknown `typeid`!")

    def trim(pkt):
        fields = [f.name for f in pkt]
        assert fields[-1] == 'raw[]'
        del pkt['raw[]']
        pkt['size'].value = int(pkt.size / 8)  # bits!

    # Hachoir does not really support "building", so we instead
    # use a empty buffer, parse it, then convert that to an editable.

    buffer = bytes(1024)
    stream = StringInputStream(buffer)

    ro_packet = DeviceFrameParser(stream)

    packet = createEditor(ro_packet)
    packet['type'].value = typeid
    packet['protocol'].value = 1024

    if target:
        packet['target'].value = target

    packet['addressable'].value = 1
    packet['tagged'].value = (typeid == 2)

    trim(packet)

    if typeid in EMPTY_REQUEST_PAYLOADS_IDS:
        packet.proto = ro_packet
        return packet

    # Here's where the real fun begins!
    # We need to re-hydrate the packet, so that all the fields are known
    # This all feels quite dodgy, though...

    temp_data = serialise_packet(packet)
    new_ro_packet = parse_packet(temp_data + bytes(1024 - len(temp_data)))
    new_ro_packet.walk()

    new_packet = createEditor(new_ro_packet)
    new_packet.proto = new_ro_packet
    trim(new_packet)

    return new_packet


def serialise_packet(packet):
    """Serialise a packet to bytes"""

    # FUDGE: Hachoir3 has some issues with Python 3, so work
    #        around it for now!
    class MyBytesIO(BytesIO):
        def write(self, data):
            if isinstance(data, str) and len(data) == 1:
                data = bytes((ord(data),))
            super().write(data)

    outdata = MyBytesIO()
    outstream = OutputStream(outdata)
    packet.writeInto(outstream)
    return outdata.getvalue()


def parse_packet(file_or_data):
    """Parse a packet into a DeviceFrame object"""

    if isinstance(file_or_data, bytes):
        stream = StringInputStream(file_or_data)
    else:
        stream = FileInputStream(file_or_data, file_or_data)

    packet = DeviceFrameParser(stream)

    return packet
