#!/usr/bin/env python

# Hotkey program, uses python-xlib

# Thoughts:
#   - grab_keyboard as well as grab_key for after the hotkey?

from Xlib.display import Display
from Xlib import X
import pygtk
pygtk.require('2.0')
import gtk

# 110 - Pause
# 117 - Menu
hotkeycode = 117

class TextSnippets:

    def __init__(self, hotkey):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.grab_key(hotkey)
        self.hotkey = hotkey

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
        # TODO - ungrab the hotkey (maybe)
        # Create a new window just to receive events
        # Receive keyboard events until we have a word or fail
        # Destroy/hide window
        # Display progress?

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

    def main(self):
        gtk.main()

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def key_press_event(self, widget, data=None):
        if data.string != '':
            result = self.keytree.check(data.string)
            if not result:
                gtk.main_quit()
            if result == True:
                self.label.set_label(self.label.get_label() + data.string)
            else:
                print result
                gtk.main_quit()

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
    #KeyTree.test()
    #ts = TextSnippets(hotkeycode)
    #ts.event_loop()
    kt = KeyTree(snippets.keys())
    nw = NotifyWindow(kt)
    nw.main()
