
def copy_class_attrs(source, target):
    source_dict = vars(source)
    target_dict = vars(target)
    source_attrs = [k for k in source_dict.keys() if k.startswith("_")]
    target_attrs = [k for k in target_dict.keys() if k.startswith("_")]

    for target_attr in target_attrs:
        if target_attr in source_attrs:
            if source_dict[target_attr] is not None:
                target_dict[target_attr] = source_dict[target_attr]
