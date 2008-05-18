#!/usr/bin/env python

# Hotkey program, uses python-xlib

# Thoughts:
#   - grab_keyboard as well as grab_key for after the hotkey?

from Xlib.display import Display
from Xlib import X
from Xlib import XK
from Xlib.ext import xtest

import pygtk
pygtk.require('2.0')
import gtk

import time

# 110 - Pause
# 117 - Menu
# 227 - Also menu?
hotkeycode = 227

class TextSnippets:

    def __init__(self, hotkey, keytree, snippets):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.grab_key(hotkey)
        self.hotkey = hotkey
        self.keytree = keytree
        self.snippets = snippets
        self.typer = KeyboardTyper()

    def grab_key(self, keycode):
        self.root.grab_key(keycode,
                X.AnyModifier, 1, X.GrabModeAsync, X.GrabModeAsync)

    def grab_letter(self, char):
        keycode = keysym_to_keycode(ord(char))
        if keycode != 0:
            self.grab_key(keycode)
        else:
            print "Unknown keysym: %s (char %s)" % (keysym, char)

    def event_loop(self):
        while 1:
            event = self.root.display.next_event()
            if event.type == X.KeyPress:
                if event.detail == self.hotkey:
                    self.handle_hotkey()

    def handle_hotkey(self):
        print "Hotkey pressed"
        notifywindow = NotifyWindow(self.keytree)
        snippet = notifywindow.main()
        self.typer.type(self.snippets[snippet])

class NotifyWindow:
    def __init__(self, keytree):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_border_width(0)
        self.label = gtk.Label("Snippet: ")
        self.window.connect("key_press_event", self.key_press_event)
        self.window.add(self.label)
        self.label.show()
        self.window.show()
        self.keytree = keytree
        self.snippet = False

    def main(self):
        gtk.main()
        return self.snippet

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def key_press_event(self, widget, data=None):
        if data.string != '':
            result = self.keytree.check(data.string)
            if not result:
                self.window.destroy()
                gtk.main_quit()
            elif result == True:
                self.label.set_label(self.label.get_label() + data.string)
            else:
                self.snippet = result
                self.window.destroy()
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


class KeyTree:
    """A tree listing all the keys needed to be grabbed at a specific point in
    order to match all possible strings"""

    def __init__(self, words):
        self.tree = {}
        for word in words:
            curr = self.tree
            for letter in word:
                curr = curr.setdefault(letter, {})
            curr['word'] = word
        self.reset()

    def check(self, letter):
        """ Check for a word in the tree, a letter at a time, tracing the path
        of the word for each successive letter.

        Returns: True   - letter continues a word
                 False  - letter is not in the list of words
                 string - letter completes a word, returns the word"""
        try:
            self.currletter = self.currletter[letter]
        except KeyError:
            self.reset()
            return False

        try:
            word = self.currletter['word']
            self.reset()
            return word
        except KeyError:
            return True


    def reset(self):
        self.wordsofar = ""
        self.currletter = self.tree

    @staticmethod
    def test():
        """ Simple testing of the Keytree """
        kt = KeyTree(['test','hello','help','telephone'])
        testwords = ['test','teach','help','hello']

        for word in testwords:
            print "Testing word: %s" % word
            for letter in word:
                result = kt.check(letter)
                print letter, result
                if not result:
                    break
            print



snippets = {
    'test': 'Hello world',
    'hello': 'Hi there!',
    'help': 'No way'
}

if __name__ == '__main__':
    kt = KeyTree(snippets.keys())
    ts = TextSnippets(hotkeycode, kt, snippets)
    ts.event_loop()
#    kt = KeyboardTyper()
#    kt.type("Test !@#$%^&*()<>[]{};':\"|\\~`")
