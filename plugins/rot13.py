def rot13(self, input):
    """Encrypt a string using the ROT13 cipher"""
    if not input.args:
        raise self.BadInputError()

    self.say("\x02ROT13'd:\x02 %s" % input.args.encode("rot13"))

rot13.rule = ["rot13"]
rot13.usage = [("Encrypt a string using the ROT13 cipher", "$pcmd <string>")]

