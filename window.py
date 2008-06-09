import logging
import time

import pygtk
pygtk.require('2.0')
import gtk
from gtk import gdk
import gobject
import pango

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
        self.label.set_markup(self.markup("Snippet: " + self.snippet))
        if self.valid_snippet:
            try:
                self.desclabel.set_text(self.config.get('snippets',
                    self.snippet + 'desc'))
            except ConfigParser.NoOptionError:
                self.desclabel.set_text("")
        else:
            self.desclabel.set_text("")

    def markup(self, text):
        """Marks up the text with the configured font and color depending on
        whether there is a match or not."""
        if self.valid_snippet:
            color = self.config.get('appearance', 'validcolor')
        else:
            color = self.config.get('appearance', 'invalidcolor')
        return '<span font_family="%s" size="%s" color="%s">%s</span>' % (
                self.config.get('appearance', 'font'),
                self.config.getint('appearance', 'size') * 1024,
                color,text)

    def close_window(self):
        gtk.gdk.keyboard_ungrab()
        self.window.hide()
        gtk.main_quit()

