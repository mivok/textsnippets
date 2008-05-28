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

import sys, time

# Local imports
#import config
import ConfigParser

class TextSnippets:

    def __init__(self, config):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.config = config
        self.grab_key()
        self.typer = KeyboardTyper()
        self.notifywindow = NotifyWindow(self.config)

    def grab_key(self):
        key = self.config.get('general', 'hotkey')
        # If we have a number, then take it as a keycode, otherwise, treat it
        # as a key name
        try:
            keycode = int(key)
            logging.debug("Hotkey is a keycode: %s" % keycode)
        except ValueError:
            logging.debug("Hotkey is a keyname: %s" % key)
            keysym = XK.string_to_keysym(key)
            if keysym == 0:
                logging.error("unknown key: %s" % key)
            keycode = self.disp.keysym_to_keycode(keysym)
        ec = error.CatchError(error.BadAccess)
        self.root.grab_key(keycode,
            X.AnyModifier, 1, X.GrabModeAsync, X.GrabModeAsync, onerror=ec)
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
                    self.handle_hotkey()
                else:
                    logging.debug("Key pressed: %s" % event.detail)

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
                logging.info("Reloading...")
                #reload(config)
                logging.debug("Not implemented")
            else:
                try:
                    time.sleep(float(config.get('general', 'delay')))
                except ValueError:
                    logging.warning("Delay %ss not valid. Defaulting to 0.1s"
                            % config.get('general', 'delay'))
                    time.sleep(0.1)
                except ConfigParser.NoOptionError:
                    logging.warning("Delay value not set, defaulting to 0.1s")
                    time.sleep(0.1)
                self.typer.type(snippet)

class NotifyWindow:
    def __init__(self, config):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(0)
        self.window.set_focus_on_map(True)
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
        logging.basicConfig(level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s')
        config = ConfigParser.SafeConfigParser()
        config.read(['defaults', '/etc/textsnippetsrc',
            '~/.textsnippetsrc'])
        ts = TextSnippets(config)
        ts.event_loop()
    except KeyboardInterrupt:
        logging.info("Exiting...")
        sys.exit(0)
