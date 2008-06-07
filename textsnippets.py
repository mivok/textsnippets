#!/usr/bin/env python

# System imports
import logging

import getopt, os, sys, time

# Local imports
import ConfigParser
from keyboard import KeyboardTyper, Hotkey
from window import NotifyWindow

class TextSnippets:

    def __init__(self):
        self.get_options()
        self.init_logger()
        self.load_config()
        self.typer = KeyboardTyper()
        self.hotkey = Hotkey(self.config, self.handle_hotkey)
        self.notifywindow = NotifyWindow(self.config)

    def init_logger(self):
        if self.options['debug']:
            level=logging.DEBUG
        else:
            level=logging.INFO
        logging.basicConfig(level=level,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
        logging.info("Textsnippets Starting...")
        logging.debug("Debugging mode on")

    def load_config(self):
        self.config = ConfigParser.SafeConfigParser()
        try:
            self.config.readfp(open(sys.path[0] + "/defaults"))
            logging.debug("Loaded default configuration")
        except IOError:
            logging.error("Unable to load default configuraiton. The program"
                    " may not work correctly.")

        if self.options['conffile']:
            filelist = self.options['conffile']
        else:
            filelist = ['/etc/textsnippetsrc',
                    os.path.expanduser('~/.textsnippetsrc')]
        files = self.config.read(filelist)
        logging.debug("Loaded config files: %s" % ', '.join(files))

    def get_options(self):
        self.options = {
            'debug': False,
            'conffile': None
        }
        try:
            opts, args = getopt.getopt(sys.argv[1:], "dc:",
                    ['debug', 'conffile='])
        except getopt.GetoptError, e:
            print str(e)
            print "Usage: %s [-d|--debug] [-c configfile|--config=filename]" % (
                    sys.argv[0])
            sys.exit(2)

        for o, a in opts:
            if o == '-d' or o == '--debug':
                self.options['debug'] = True
            elif o == '-c' or o == '--config':
                self.options['conffile'] = a
            else:
                print "Unhandled option: %s" % o
                sys.exit(1)

    def start(self):
        if self.hotkey.grab_key(hotkey = self.config.get('general', 'hotkey'),
                modifiers = self.config.get('general', 'modifiers').lower()):
            logging.debug("Successfully set hotkey")
            self.hotkey.event_loop()
        else:
            logging.critical("Unable to set hotkey. "
                    "Perhaps it is already in use?")
            logging.info("Exiting")
            sys.exit(1)

    def handle_hotkey(self):
        logging.debug("Hotkey pressed")
        snippetword = self.notifywindow.main()
        if snippetword != "":
            try:
                snippet = self.config.get('snippets', snippetword)
            except ConfigParser.NoOptionError:
                logging.warning("Invalid snippet: snippetword")
                return
            if snippet == 'snippet:quit':
                sys.exit(0)
            elif snippet == 'snippet:reload':
                logging.info("Reloading user configuration")
                conffile = self.options['conffile'] or os.path.expanduser(
                        '~/.textsnippetsrc')
                files = self.config.read([conffile])
                logging.debug("Reloaded config files: %s" % ', '.join(files))
            else:
                try:
                    delay = self.config.getfloat('general', 'delay')
                    time.sleep(delay)
                    logging.debug("Delaying for %ss" % delay)
                except ValueError:
                    logging.warning("Delay %ss not valid. Defaulting to 0.1s"
                            % config.get('general', 'delay'))
                    time.sleep(0.1)
                except ConfigParser.NoOptionError:
                    logging.warning("Delay value not set, defaulting to 0.1s")
                    time.sleep(0.1)
                self.typer.type(snippet)

if __name__ == '__main__':
    try:
        ts = TextSnippets()
        ts.start()
    except KeyboardInterrupt:
        logging.info("Exiting...")
        sys.exit(0)
