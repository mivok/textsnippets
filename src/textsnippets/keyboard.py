import logging

from Xlib.display import Display
from Xlib import error
from Xlib import X
from Xlib import XK
from Xlib.ext import xtest

class Hotkey:
    def __init__(self, config, handler):
        self.disp = Display()
        self.root = self.disp.screen().root
        self.root.change_attributes(event_mask = X.KeyPressMask)
        self.handler = handler
        self.config = config

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
            if modifiers:
                modlist = modifiers.split('+')
                logging.debug("Modifiers are: %s" % ', '.join(modlist))
                for mod in modlist:
                    try:
                        modmask |= modmasks[mod]
                    except KeyError:
                        logging.error(
                            'Invalid modifier key: %s. Ignoring this key'
                            % mod)
                logging.debug("Modmask is: %s" % modmask)
            else:
                logging.debug("No modifiers specified")
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
            return False
        else:
            self.keycode = keycode
            return keycode

    def event_loop(self):
        """Loop until a hotkey is pressed. This will block until the hotkey is
        pressed. Use event_callback instead if you want a non-blocking
        implementation that does a single check to see if a key has been
        pressed."""
        while 1:
            self._process_event(self.root.display.next_event())

    def event_callback(self):
        """Checks to see if any events are waiting (i.e. if the hotkey was
        pressed. If so, then process it, otherwise do nothing and return."""
        if self.root.display.pending_events() > 0:
            self._process_event(self.root.display.next_event())
        return True

    def _process_event(self, event):
        """Processes a hotkey event"""
        if event.type == X.KeyPress:
            if event.detail == self.keycode:
                self.handler()
            else:
                logging.debug("Key pressed: %s" % event.detail)

class KeyboardTyper:
    def __init__(self):
        self.disp = Display()
        self.keysym_to_modifier_map = {}
        self.keysym_to_keycode_map = {}
        self.key_modifiers = (None, "Shift_L", "ISO_Level3_Shift", None, None,
                None)
        self._load_keycodes()

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

    def _load_keycodes(self):
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
                    if not keysym in ksmm:
                        ksmm[keysym] = self._str_to_keycode(
                            self.key_modifiers[wrap_key_index])
                        kskc[keysym] = keycode

    def _str_to_keycode(self, str):
        if str is None:
            return None
        keysym = XK.string_to_keysym(str)
        keycode = self.disp.keysym_to_keycode(keysym)
        return keycode
