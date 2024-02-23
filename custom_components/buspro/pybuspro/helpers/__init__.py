import typing

def copy_class_attrs(source, target):
    source_dict = vars(source)
    target_dict = vars(target)
    source_attrs = [k for k in source_dict.keys() if k.startswith("_")]
    target_attrs = [k for k in target_dict.keys() if k.startswith("_")]

    for target_attr in target_attrs:
        if target_attr in source_attrs:
            if source_dict[target_attr] is not None:
                target_dict[target_attr] = source_dict[target_attr]

def parse_device_address(device_config:str):
    addrs = [int(k) for k in device_config.split('.')]

    device_address = (addrs[0], addrs[1])
    extra = addrs[2] if len(addrs)>2 else None
    return (device_address, extra)

