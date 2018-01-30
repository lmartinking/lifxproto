Lifx Proto
==========

**Experimental, In Development!**

Python implementation of the Lifx LAN Protocol, using Hachoir3.

Currently it can only build, and serialise/deserialise packets.

The majority of the protocol message types are already implemented.

## Usage

Firstly, familiarise yourself with the [Lifx Lan Protocol](https://lan.developer.lifx.com/).

Use the `Message` class to easily create and edit packets.

```$python
import lifxproto.message as msg

m = msg.Message.build(msg.GetService)

buff = m.bytes()
```

To parse a response:

```$python
data, (addr, port) = sock.revfrom(1024) # get UDP packet data

m = msg.Message.from_bytes(data)

# Access packet fields using attributes
print(m.source)
print(m.sequence)
```

## Under The Hood

Have a look at `DeviceFrameParser` in `lifxproto/message.py` to
see how simple it is compared to using `struct` and `bitstring` manually.

The bulk of message types are implemented in `lifxproto/message_types.py`

There is currently the basics of a "converter" protocol, which allows
friendly conversion between values used on the API side (`Message`) and what
is demanded by the protocol fields as defined within the internals (`DeviceFrame`)
and the message `FieldSet` based types.

## Licence

LGPLv3. See `LICENSE` and `COPYING.LESSER`.

Copyright (c) 2018 Lucas Martin-King.

Other parts of this software (eg: Hachoir3) are covered by other licences.
