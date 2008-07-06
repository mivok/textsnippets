import ConfigParser
import logging
import time
import math

import pygtk
pygtk.require('2.0')
import gtk
from gtk import gdk
import gobject
import pango
import cairo

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
        self.window = FancyWindow(gtk.WINDOW_TOPLEVEL)
        self.window.resize(1,70)
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_SPLASHSCREEN)
        self.window.set_border_width(0)
        self.window.set_decorated(False)

        self.box = gtk.VBox()
        self.label = gtk.Label("")
        self.box.add(self.label)
        self.desclabel = gtk.Label("")
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        self.label.set_width_chars(40)
        self.desclabel.set_ellipsize(pango.ELLIPSIZE_END)
        self.desclabel.set_width_chars(40)
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
        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.window.set_keep_above(True)
        self.window.set_opacity(0.9)
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


class FancyWindow(gtk.Window):
    def __init__(self, *args):
        gtk.Window.__init__(self, *args)
        self.connect('size-allocate', self._on_size_allocate)
        self.set_decorated(False)
        self.radius = 20
        self.fixed = gtk.Fixed()
        self.fixed.show()
        gtk.Window.add(self,self.fixed)

        # Original width and height used in the resize event
        self._old_w = 0
        self._old_h = 0

        # Set the background
        self.bg = gtk.Image()
        self.bg.show()
        self.fixed.put(self.bg, 0, 0)

    def _on_size_allocate(self, win, allocation):
        w,h = allocation.width, allocation.height

        # Make sure we've really resized. This prevents an infinite loop where
        # setting the background causes another resize event to be sent
        if w == self._old_w and h == self._old_h:
            return
        else:
            self._old_w = w
            self._old_h = h

        # Set the window shape
        mask = self.get_mask(w,h)
        win.shape_combine_mask(mask, 0, 0)

        pixmap = self.get_bg(w,h)
        self.bg.set_from_pixmap(pixmap, None)

    def get_mask(self, w, h):
        bitmap = gtk.gdk.Pixmap(None, w, h, 1)
        cr = bitmap.cairo_create()

        # Clear the bitmap
        cr.set_source_rgb(0, 0, 0)
        cr.set_operator(cairo.OPERATOR_DEST_OUT)
        cr.paint()

        # Draw the rounded border
        cr.set_operator(cairo.OPERATOR_OVER)
        self.draw_border_path(w, h, cr)
        cr.fill()

        return bitmap

    def get_bg(self, w, h):
        pixmap = gtk.gdk.Pixmap(None, w, h, 24)
        cr = pixmap.cairo_create()

        # Draw the rounded border
        cr.set_operator(cairo.OPERATOR_OVER)
        self.draw_border_path(w, h, cr)

        r,g,b = 0.2, 0.3, 0.8
        pattern = cairo.LinearGradient(0,h,0,0)
        pattern.add_color_stop_rgb(0,r,g,b)
        pattern.add_color_stop_rgb(h,r*2,g*2,b*2)
        cr.set_source(pattern)
        cr.fill_preserve()

        cr.set_source_rgb(r/1.5, g/1.5, b/1.5)
        cr.set_line_width(5.0)
        cr.stroke_preserve()

        return pixmap

    def draw_border_path(self, w, h, cr):
        r = self.radius
        cr.arc(r, r, r, math.pi, 1.5 * math.pi)
        cr.arc(w-r, r, r, 1.5 * math.pi, 0)
        cr.arc(w-r, h-r, r, 0, math.pi/2)
        cr.arc(r, h-r, r, math.pi/2, math.pi)
        cr.line_to(0,r)

    def add(self, widget):
        self.fixed.put(widget, self.radius/2, self.radius/2)
