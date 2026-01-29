from tomlkit.items import Table, InlineTable, AoT, Array

def toml_find_all_tables(element, path=None):
    if path is None:
        path = []

    if isinstance(element, (Table, InlineTable, dict)):
        # return if an element is dict-like
        yield (path, element)

        # recursively look for children
        for key, value in element.items():
            current_path = path + [key]

            # dict-like
            if isinstance(value, (Table, InlineTable, dict)):
                yield from toml_find_all_tables(value, current_path)
            # AoT (array of table) = [[key]]
            elif isinstance(value, AoT):
                for index, item in enumerate(value):
                    if isinstance(item, (Table, InlineTable, dict)):
                        aot_path = current_path + [index]
                        yield from toml_find_all_tables(item, aot_path)
            # list of inline tables = [ {key: value} ]
            elif isinstance(value, (Array, list)):
                # recursively look inside lists
                yield from toml_find_all_tables(value, current_path)

    elif isinstance(element, (Array, list)):
        for index, item in enumerate(element):
            # inside AoT, list of inline tables
            if isinstance(item, (Table, InlineTable, dict)):
                list_path = path + [index]
                yield from toml_find_all_tables(item, list_path)
            # nested list
            elif isinstance(item, (Array, list)):
                list_path = path + [index]
                yield from toml_find_all_tables(item, list_path)

def toml_is_primitive(value):
    if isinstance(value, (Table, InlineTable, AoT, dict)):
        return False

    if isinstance(value, (Array, list)):
        # return False if any of the items inside a list is dict-like
        for item in value:
            if isinstance(item, (Table, InlineTable, AoT, dict)):
                return False

    return True
