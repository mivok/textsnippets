import ConfigParser
import logging
import time

import pygtk
pygtk.require('2.0')
import gtk
from gtk import gdk
import gobject
import pango

class Gui:
    def __init__(self, config):
        self.config = config

    def start(self):
        gtk.main()

    def stop(self):
        gtk.main_quit()

    def add_idle_func(self, func):
        gobject.timeout_add(100, func)

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

    def main(self, callback):
        self.callback = callback
        self.snippet = ""
        self.valid_snippet = False
        self.update_label()
        self.window.resize(1,1) # Shrink the window to width of the text
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.window.set_keep_above(True)
        self.window.show()
        self.window.present()
        for i in xrange(20):
            val = gtk.gdk.keyboard_grab(self.window.window)
            if val == gtk.gdk.GRAB_SUCCESS:
                break
            time.sleep(0.1)

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
        self.window.resize(1,1) # Shrink the window to width of the text

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
        if self.callback:
            # TODO - make a generic config.get function with defaults + error
            # messages for missing and invalid values (invalid only matters on
            # getint getfloat etc.
            try:
                delay = self.config.getfloatdefault('general', 'delay', 0.1)
                logging.debug("Delay set to %ss" % delay)
                delay = int(delay * 1000)
            except ValueError:
                logging.warning("Delay %ss not valid. Defaulting to 0.1s"
                        % self.config.get('general', 'delay'))
                delay = 1000
            gobject.timeout_add(delay, self.callback, self.snippet)

