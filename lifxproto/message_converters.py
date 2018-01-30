#
# Handy things to help conversion to and from the more raw field values...
#


def converter(field, to_value, from_value):
    field.toValue = to_value      # user value to field value
    field.fromValue = from_value  # field value to user value
    return field


def labelConverter(field):
    def toLabelValue(label):
        label = label.encode('utf-8')
        if len(label) > 32:
            label = label[0:32]
        return label

    def fromLabelValue(value):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        return value

    return converter(field, toLabelValue, fromLabelValue)


def enumConverter(field):
    def fromValue(value):
        return field.getEnum()[value]

    def toValue(value):
        return {v: k for k, v in field.getEnum().items()}[value]

    return converter(field, toValue, fromValue)
