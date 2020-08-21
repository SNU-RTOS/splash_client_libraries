import base64

ros_primitive_types = ['bool', 'byte', 'char', 'int8', 'uint8', 'int16',
                       'uint16', 'int32', 'uint32', 'int64', 'uint64',
                       'float32', 'float64', 'string']
ros_time_types = ['time', 'duration']
ros_header_types = ['Header', 'std_msgs/Header', 'roslib/Header']

def convert_ros_message_to_dictionary(message):
    """
    Takes in a ROS message and returns a Python dictionary.
    Example:
        ros_message = std_msgs.msg.String(data="Hello, Robot")
        dict_message = convert_ros_message_to_dictionary(ros_message)
    """
    dictionary = {}
    message_fields = message.get_fields_and_field_types().items()
    for field_name, field_type in message_fields:
        field_value = getattr(message, field_name)
        dictionary[field_name] = _convert_from_ros_type(field_type, field_value)

    return dictionary

def _convert_from_ros_type(field_type, field_value):
    if field_type in ros_primitive_types:
        field_value = field_value
    elif field_type in ros_time_types:
        field_value = _convert_from_ros_time(field_type, field_value)
    elif _is_ros_binary_type(field_type):
        field_value = _convert_from_ros_binary(field_type, field_value)
    elif _is_field_type_a_primitive_array(field_type):
        field_value = list(field_value)
    elif _is_field_type_an_array(field_type):
        field_value = _convert_from_ros_array(field_type, field_value)
    else:
        field_value = convert_ros_message_to_dictionary(field_value)

    return field_value

def _convert_from_ros_time(field_type, field_value):
    field_value = {
        'secs'  : field_value.secs,
        'nsecs' : field_value.nsecs
    }
    return field_value

def _convert_from_ros_binary(field_type, field_value):
    field_value = base64.standard_b64encode(field_value).decode('utf-8')
    return field_value

def _convert_from_ros_array(field_type, field_value):
    # use index to raise ValueError if '[' not present
    list_type = field_type[:field_type.index('[')]
    return [_convert_from_ros_type(list_type, value) for value in field_value]

def _is_ros_binary_type(field_type):
    """ Checks if the field is a binary array one, fixed size or not
    """
    return field_type.startswith('uint8[') or field_type.startswith('char[')

def _is_field_type_an_array(field_type):
    return field_type.find('[') >= 0

def _is_field_type_a_primitive_array(field_type):
    bracket_index = field_type.find('[')
    if bracket_index < 0:
        return False
    else:
        list_type = field_type[:bracket_index]
        return list_type in ros_primitive_types