from api_list import exist_param, no_param


def gen():
    result = ''
    exist_def = """def %s(self, param=None):
    return self._cmd(method="%s", param=param)"""
    no_def = """def %s(self):
    return self._cmd(method="%s")"""

    for x in exist_param:
        result += exist_def%(x, x) + '\n\n'
    for x in no_param:
        result += no_def%(x, x) + '\n\n'

    return result

print gen()
