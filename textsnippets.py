#!/usr/bin/env python

# System imports
from Xlib.display import Display
from Xlib import error
from Xlib import X
from Xlib import XK
from Xlib.ext import xtest

import pygtk
pygtk.require('2.0')
import gtk
from gtk import gdk
import gobject
import pango

import logging

import getopt, os, sys, time

# Local imports
#import config
import ConfigParser

class TextSnippets:

    def __init__(self):
        self.get_options()
        self.init_logger()
        self.load_config()
        self.typer = KeyboardTyper()
        self.hotkey = Hotkey(self.config, self.handle_hotkey,
                hotkey = self.config.get('general', 'hotkey'),
                modifiers = self.config.get('general', 'modifiers').lower())
        self.notifywindow = NotifyWindow(self.config)

    def init_logger(self):
        if self.options['debug']:
            level=logging.DEBUG
        else:
            level=logging.INFO
        logging.basicConfig(level=level,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')

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
            opts, args = getopt.getopt(sys.argv[1:], "d", ['debug'])
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
        self.hotkey.event_loop()

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
                files = config.read([os.path.expanduser('~/.textsnippetsrc')])
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

class Hotkey:
    def __init__(self, config, handler, hotkey, modifiers):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.handler = handler
        self.config = config
        self.grab_key(hotkey, modifiers)

    def grab_key(self, hotkey, modifiers):
        if modifiers == 'none':
            logging.debug("Setting modifier keys to Any")
            modmask = X.AnyModifier
        else:
            modmasks = {
                'ctrl':     X.ControlMask,
                'control':  X.ControlMask,
                'c':        X.ControlMask,
                'shift':    X.ShiftMask,
                's':        X.ShiftMask,
                'alt':      X.Mod1Mask,
                'a':        X.Mod1Mask,
                'meta':     X.Mod1Mask,
                'm':        X.Mod1Mask,
                'super':    X.Mod4Mask,
                'win':      X.Mod4Mask,
                'w':        X.Mod4Mask,
                'windows':  X.Mod4Mask,
                'mod1':     X.Mod1Mask,
                'mod2':     X.Mod2Mask,
                'mod3':     X.Mod3Mask,
                'mod4':     X.Mod4Mask,
                'mod5':     X.Mod5Mask
            }
            modmask = 0
            modlist = modifiers.split('+')
            logging.debug("Modifiers are: %s" % ', '.join(modlist))
            for mod in modlist:
                try:
                    modmask |= modmasks[mod]
                except KeyError:
                    logging.error('Invalid modifier key: %s. Ignoring this key'
                            % mod)
            logging.debug("Modmask is: %s" % modmask)
        # If we have a number, then take it as a keycode, otherwise, treat it
        # as a key name
        try:
            keycode = int(hotkey)
            logging.debug("Hotkey is a keycode: %s" % keycode)
        except ValueError:
            logging.debug("Hotkey is a keyname: %s" % hotkey)
            keysym = XK.string_to_keysym(hotkey)
            if keysym == 0:
                logging.error("unknown key: %s" % hotkey)
            keycode = self.disp.keysym_to_keycode(keysym)
        ec = error.CatchError(error.BadAccess)
        self.root.grab_key(keycode, modmask, 1, X.GrabModeAsync,
                X.GrabModeAsync, onerror=ec)
        self.disp.sync()
        if ec.get_error():
            logging.error("Unable to set hotkey. Perhaps it is already in use.")
            logging.info("Exiting...")
            sys.exit(1)
        else:
            logging.debug("Successfully set hotkey")
            self.keycode = keycode

    def event_loop(self):
        while 1:
            event = self.root.display.next_event()
            if event.type == X.KeyPress:
                if event.detail == self.keycode:
                    self.handler()
                else:
                    logging.debug("Key pressed: %s" % event.detail)

class NotifyWindow:
    def __init__(self, config):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_SPLASHSCREEN)
        self.window.set_border_width(0)
        self.window.set_decorated(False)
        self.box = gtk.VBox()
        self.label = gtk.Label("")
        self.box.add(self.label)
        self.desclabel = gtk.Label("")
        self.box.add(self.desclabel)
        self.window.add(self.box)
        self.box.show()
        self.label.show()
        self.desclabel.show()
        self.window.connect("key_press_event", self.key_press_event)
        self.config = config

    def main(self):
        self.snippet = ""
        self.valid_snippet = False
        self.update_label()
        # Shrink the window to be the width of the text
        self.window.resize(1,1)
        self.window.show()
        self.window.present()
        self.window.set_keep_above(True)
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        for i in xrange(20):
            val = gtk.gdk.keyboard_grab(self.window.window)
            if val == gtk.gdk.GRAB_SUCCESS:
                break
            time.sleep(0.1)
        gtk.main()
        return self.snippet

    def delete_event(self, widget, event, data=None):
        return False

    def key_press_event(self, widget, data=None):
        if data.keyval == gtk.keysyms.Return:
            if self.config.has_option('snippets', self.snippet):
                self.close_window()
            else:
                logging.warning("Invalid snippet")
        elif data.keyval == gtk.keysyms.BackSpace:
            self.snippet = self.snippet[:-1]
        elif data.keyval == gtk.keysyms.Escape:
            self.snippet = ""
            self.close_window()
        elif data.string != '':
            self.snippet = self.snippet + data.string
        self.valid_snippet = self.config.has_option('snippets', self.snippet)
        self.update_label()

    def destroy(self, widget, data=None):
        gtk.gdk.keyboard_ungrab()
        gtk.main_quit()

    def update_label(self):
        self.label.set_text("Snippet: " + self.snippet)
        if self.valid_snippet:
            try:
                self.desclabel.set_text(self.config.get('snippets',
                    self.snippet + 'desc'))
            except ConfigParser.NoOptionError:
                self.desclabel.set_text("")
        else:
            self.desclabel.set_text("")
        self.set_label_font()

    def set_label_font(self):
        attrs = pango.AttrList()
        attrs.insert(pango.AttrFamily("Bitstream Vera Sans", 0, 65535))
        attrs.insert(pango.AttrSize(20000, 0, 65535))
        if self.valid_snippet:
            attrs.insert(pango.AttrForeground(0,32768,0,0,65535))
        self.label.set_attributes(attrs)

    def close_window(self):
        gtk.gdk.keyboard_ungrab()
        self.window.hide()
        gtk.main_quit()

class KeyboardTyper:
    def __init__(self):
        self.disp = Display()
        self.keysym_to_modifier_map = {}
        self.keysym_to_keycode_map = {}
        self.key_modifiers = (None, "Shift_L", "ISO_Level3_Shift", None, None,
                None)
        self.load_keycodes()

    def str_to_keycode(self, str):
        if str is None:
            return None
        keysym = XK.string_to_keysym(str)
        keycode = self.disp.keysym_to_keycode(keysym)
        return keycode

    def type(self, text):
        for char in text:
            keysym = ord(char)
            keycode = self.keysym_to_keycode_map.get(keysym, None)
            if keycode is None:
                keycode = self.disp.keysym_to_keycode(keysym)
            wrap_key = self.keysym_to_modifier_map.get(keysym, None)
            #print char, keysym, keycode, wrap_key
            if wrap_key is not None:
                xtest.fake_input(self.disp, X.KeyPress, wrap_key)
            xtest.fake_input(self.disp, X.KeyPress, keycode)
            xtest.fake_input(self.disp, X.KeyRelease, keycode)
            if wrap_key is not None:
                xtest.fake_input(self.disp, X.KeyRelease, wrap_key)
            self.disp.sync()

    def load_keycodes(self):
        d = self.disp
        ksmm = self.keysym_to_modifier_map
        kskc = self.keysym_to_keycode_map

        min_keycode = d.display.info.min_keycode
        max_keycode = d.display.info.max_keycode
        count = max_keycode + 1 - min_keycode
        keysyms = d.get_keyboard_mapping(min_keycode, count)

        for keycode_index in xrange(0,count):
            curr = keysyms[keycode_index]
            for wrap_key_index in xrange(0, len(curr)):
                str = XK.keysym_to_string(curr[wrap_key_index])
                if str is not None:
                    #keysym = XK.string_to_keysym(str)
                    keysym = curr[wrap_key_index]
                    keycode = keycode_index + min_keycode
                    if not ksmm.has_key(keysym):
                        ksmm[keysym] = self.str_to_keycode(
                            self.key_modifiers[wrap_key_index])
                        kskc[keysym] = keycode

if __name__ == '__main__':
    try:
        ts = TextSnippets()
        ts.start()
    except KeyboardInterrupt:
        logging.info("Exiting...")
        sys.exit(0)
