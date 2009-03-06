from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

class CustomConfigParser(SafeConfigParser):
    """A version of SafeConfigParser with methods that return default values
    if the options do not exist."""

    def getdefault(self, section, option, default=None):
        """A version of ConfigParser.get that returns a default if the option
        does not exist."""
        try:
            val = SafeConfigParser.get(self, section, option)
        except (NoSectionError, NoOptionError):
            val = default
        return val

    def getfloatdefault(self, section, option, default=None):
        """A version of ConfigParser.getint that returns a default if the
        option does not exist."""
        try:
            val = SafeConfigParser.getint(self, section, option)
        except (NoSectionError, NoOptionError):
            val = default
        return val

    def getfloatdefault(self, section, option, default=None):
        """A version of ConfigParser.getfloat that returns a default if the
        option does not exist."""
        try:
            val = SafeConfigParser.getfloat(self, section, option)
        except (NoSectionError, NoOptionError):
            val = default
        return val

    def getbooleandefault(self, section, option, default=None):
        """A version of ConfigParser.getboolean that returns a default if the
        option does not exist."""
        try:
            val = SafeConfigParser.getboolean(self, section, option)
        except (NoSectionError, NoOptionError):
            val = default
        return val
