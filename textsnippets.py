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
import pango

import sys, time

# Local imports
import config

# TODO
#  - Reuse the same notify window each time (don't destroy it, just hide)
#  - Fix the focus issue on repeated views (hopefully solved by the reuse
#       window fix)
#  - Fix config reloading
#  - Add a description to the shortcut which is displayed when you type it
#       E.g.: nc - 'Check nagios config'

class TextSnippets:

    def __init__(self, hotkey, snippets):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.grab_key(hotkey)
        self.hotkey = hotkey
        self.snippets = snippets
        self.typer = KeyboardTyper()
        self.notifywindow = NotifyWindow(self.snippets)

    def grab_key(self, key):
        if type(key) == int:
            keycode = key
        else:
            keysym = XK.string_to_keysym(key)
            if keysym == 0:
                print "Error, unknown key: %s" % key
            keycode = self.disp.keysym_to_keycode(keysym)
        ec = error.CatchError(error.BadAccess)
        self.root.grab_key(keycode,
            X.AnyModifier, 1, X.GrabModeAsync, X.GrabModeAsync, onerror=ec)
        self.disp.sync()
        if ec.get_error():
            print "Unable to set hotkey. Perhaps it is already in use."
            print "Exiting..."
            sys.exit(1)

    def event_loop(self):
        while 1:
            event = self.root.display.next_event()
            if event.type == X.KeyPress:
                if event.detail == self.hotkey:
                    self.handle_hotkey()

    def handle_hotkey(self):
        print "Hotkey pressed"
        snippetword = self.notifywindow.main()
        if snippetword != "":
            try:
                snippet = self.snippets[snippetword]
            except KeyError:
                print "Invalid snippet: snippetword"
                return
            if snippet == 'snippet:quit':
                sys.exit(0)
            elif snippet == 'snippet:reload':
                print "Reloading..."
                reload(config)
            else:
                time.sleep(config.delay)
                self.typer.type(snippet)

class NotifyWindow:
    def __init__(self, snippets):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(0)
        self.window.set_focus_on_map(True)
        self.window.set_decorated(False)
        self.label = gtk.Label("")
        self.window.connect("key_press_event", self.key_press_event)
        self.window.add(self.label)
        self.label.show()
        self.snippets = snippets
        self.snippet = ""
        self.valid_snippet = False
        self.update_label()

    def main(self):
        self.window.show()
        self.window.present()
        self.window.set_keep_above(True)
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        gtk.main()
        return self.snippet

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def key_press_event(self, widget, data=None):
        if data.keyval == gtk.keysyms.Return:
            if self.snippets.has_key(self.snippet):
                self.window.hide()
                gtk.main_quit()
            else:
                print "Invalid snippet"
        elif data.keyval == gtk.keysyms.BackSpace:
            self.snippet = self.snippet[:-1]
        elif data.keyval == gtk.keysyms.Escape:
            self.snippet = ""
            self.window.hide()
            gtk.main_quit()
        elif data.string != '':
            self.snippet = self.snippet + data.string
        self.valid_snippet = self.snippets.has_key(self.snippet)
        self.update_label()

    def update_label(self):
        self.label.set_text("Snippet: " + self.snippet)
        self.set_label_font()

    def set_label_font(self):
        attrs = pango.AttrList()
        attrs.insert(pango.AttrFamily("Bitstream Vera Sans", 0, 65535))
        attrs.insert(pango.AttrSize(20000, 0, 65535))
        if self.valid_snippet:
            attrs.insert(pango.AttrForeground(0,32768,0,0,65535))
        self.label.set_attributes(attrs)


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
        ts = TextSnippets(config.hotkey, config.snippets)
        ts.event_loop()
    except KeyboardInterrupt:
        print "Exiting..."
        sys.exit(0)
