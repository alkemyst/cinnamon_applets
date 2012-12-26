#!/usr/bin/env python
#-*- coding:utf-8 -*-

__program_name__ = 'settings.py'
__author__ = 'Simon Wiles'
__email__ = 'simonjwiles@gmail.com'
__copyright__ = 'Copyright 2012, Simon Wiles'
__license__ = 'GPL http://www.gnu.org/licenses/gpl.txt'
__date__ = '2012-12'

import codecs
import os
import subprocess
from gi.repository import Gtk, GLib  # pylint: disable-msg=E0611

# prefer simplejson if available (it's faster), and fallback to json
#  (included in the standard library for Python >= 2.6) if not.
try:
    import simplejson as json
except ImportError:
    import json

APPLET_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA = json.load(codecs.open(
                       os.path.join(APPLET_DIR, 'metadata.json'), 'r', 'utf8'))
SETTINGS = None

# i18n
from gettext import gettext as _
#import gettext
#gettext.install('cinnamon', '/usr/share/cinnamon/locale')


def get_settings(schema_name):
    """ Get settings values from corresponding schema file """

    from gi.repository import Gio # pylint: disable-msg=E0611

    # Try to get schema from local installation directory
    schemas_dir = os.path.join(APPLET_DIR, 'schemas')
    if os.path.isfile(os.path.join(schemas_dir, 'gschemas.compiled')):
        schema_source = Gio.SettingsSchemaSource.new_from_directory(
                    schemas_dir, Gio.SettingsSchemaSource.get_default(), False)
        schema = schema_source.lookup(schema_name, False)
        return Gio.Settings.new_full(schema, None, None)
    else:
        # Schema is installed system-wide
        return Gio.Settings.new(schema_name)


def get_timezones():

    timezones_tab = '/usr/share/zoneinfo/zone.tab'
    if not os.path.exists(timezones_tab):
        timezones_tab = '/usr/share/lib/zoneinfo/tab/zone_sun.tab'

    if not os.path.exists(timezones_tab):
        return []

    timezones = subprocess.check_output(
                        ['/usr/bin/awk', '!/#/ {print $3}', timezones_tab])

    return sorted(timezones.strip('\n').split('\n'))


class SettingsWindow(Gtk.Window):
    """ Build settings panel window """

    def __init__(self):
        Gtk.Window.__init__(self, title=METADATA['name'])

        self.set_size_request(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect('delete-event', self._exit_application)
        self.connect('destroy', self._exit_application)

        frame = Gtk.Box(
             orientation=Gtk.Orientation.VERTICAL, border_width=10, spacing=10)

        hbox = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, border_width=0, spacing=10)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
                            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.liststore_worldclocks = Gtk.ListStore(str, str)

        for item in SETTINGS.get_value('worldclocks'):
            self.liststore_worldclocks.append(item.split('|'))

        self.treeview = Gtk.TreeView(model=self.liststore_worldclocks)

        # Labels column
        cellrenderertext = Gtk.CellRendererText()
        cellrenderertext.set_property('editable', True)
        cellrenderertext.connect('edited', self._on_label_edited)
        col = Gtk.TreeViewColumn('Display Name', cellrenderertext, text=0)
        col.set_property('resizable', True)
        col.set_expand(True)
        self.treeview.append_column(col)

        # Timezones column
        timezones = get_timezones()

        cellrendererautocomplete = CellRendererAutoComplete(
                              timezones, match_anywhere=True, force_match=True)
        cellrendererautocomplete.set_property('editable', True)
        cellrendererautocomplete.connect('edited', self._on_tz_edited)
        col = Gtk.TreeViewColumn('Timezone', cellrendererautocomplete, text=1)
        col.set_expand(True)
        self.treeview.append_column(col)

        # Allow enable drag and drop of rows including row move
        self.treeview.set_reorderable(True)

        scrolled_window.add(self.treeview)
        self.treeview.show()

        # right-hand buttons
        hbox.pack_start(scrolled_window, True, True, 0)
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 0, 0)
        vbox = Gtk.VBox()

        buttons = (
            ('top', Gtk.STOCK_GOTO_TOP),
            ('up', Gtk.STOCK_GO_UP),
            ('down', Gtk.STOCK_GO_DOWN),
            ('bottom', Gtk.STOCK_GOTO_BOTTOM),
        )

        for button in buttons:
            img = Gtk.Image()
            img.set_from_stock(button[1], Gtk.IconSize.BUTTON)
            btn = Gtk.Button(image=img)
            btn.connect('clicked', self._reorder, button[0])
            vbox.pack_start(btn, False, False, 0)

        align.add(vbox)
        hbox.pack_end(align, False, False, 0)

        frame.pack_start(hbox, True, True, 0)

        # time format for World Clocks
        time_format = SETTINGS.get_string('time-format')
        hbox = Gtk.HBox()
        label = Gtk.Label(_('Time format for World Clocks'))
        self.entry_timeformat = Gtk.Entry()
        hbox.pack_start(label, False, False, 5)
        hbox.add(self.entry_timeformat)
        self.entry_timeformat.set_text(time_format)
        frame.pack_start(hbox, False, False, 0)

        # bottom buttons
        box_buttons = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, border_width=0, spacing=10)

        btn_new = Gtk.Button(stock=Gtk.STOCK_NEW)
        btn_new.connect('clicked', self._add_entry)
        box_buttons.pack_start(btn_new, False, False, 0)

        btn_remove = Gtk.Button(stock=Gtk.STOCK_REMOVE)
        btn_remove.connect('clicked', self._remove_entry)
        box_buttons.pack_start(btn_remove, False, False, 0)

        btn_close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        btn_close.connect('clicked', self._exit_application)
        box_buttons.pack_end(btn_close, False, False, 0)

        btn_clear = Gtk.Button(stock=Gtk.STOCK_CLEAR)
        btn_clear = Gtk.Button.new_from_stock(Gtk.STOCK_CLEAR)

        btn_clear.connect('clicked', self._clear_entries)
        box_buttons.pack_end(btn_clear, False, False, 0)

        frame.pack_end(box_buttons, False, False, 0)

        frame.show_all()
        self.add(frame)
        self.show_all()

    def _reorder(self, widget, action):
        tsel = self.treeview.get_selection()
        liststore, treeiter = tsel.get_selected()
        if treeiter is None:
            return
        if action == 'top':
            liststore.move_after(treeiter, None)
        if action == 'up' and liststore.get_string_from_iter(treeiter) != '0':
            liststore.move_before(treeiter, liststore.iter_previous(treeiter))
        if action == 'down' and \
           int(liststore.get_string_from_iter(treeiter)) + 1 != len(liststore):
            liststore.move_after(treeiter, liststore.iter_next(treeiter))
        if action == 'bottom':
            liststore.move_before(treeiter, None)

    def _on_label_edited(self, widget, path, new_value):
        self.liststore_worldclocks[path][0] = new_value
        return

    def _on_tz_edited(self, widget, path, new_value):
        self.liststore_worldclocks[path][1] = new_value
        return

    def _clear_entries(self, widget):
        self.liststore_worldclocks.clear()

    def _add_entry(self, widget):
        self.liststore_worldclocks.insert(
                  len(self.liststore_worldclocks), ('London', 'Europe/London'))

    def _remove_entry(self, widget):
        self.liststore_worldclocks.remove(
                               self.treeview.get_selection().get_selected()[1])

    def _save_settings(self):
        print [row[0] for row in self.liststore_worldclocks]
        SETTINGS.set_value('worldclocks', GLib.Variant('as',
                       ['|'.join(row) for row in self.liststore_worldclocks]))
        SETTINGS.set_string('time-format', self.entry_timeformat.get_text())

    def _exit_application(self, *args):
        try:
            self._save_settings()
        except:
            pass
        Gtk.main_quit()


class CellRendererAutoComplete(Gtk.CellRendererText):

    """ Text entry cell which binds a Gtk.EntryCompletion object """

    __gtype_name__ = 'CellRendererAutoComplete'

    def __init__(
            self, completion_entries, match_anywhere=False, force_match=False):

        self.completion_entries = completion_entries
        self.force_match = force_match

        self._liststore = Gtk.ListStore(str)
        for item in self.completion_entries:
            self._liststore.append((item,))

        self.completion = Gtk.EntryCompletion()
        self.completion.set_model(self._liststore)
        self.completion.set_text_column(0)

        if match_anywhere:
            def completion_match_func(completion, key, path, userdata):
                return key in self._liststore[path][0].lower()
            self.completion.set_match_func(completion_match_func, 0)

        Gtk.CellRendererText.__init__(self)

    def do_start_editing(
               self, event, treeview, path, background_area, cell_area, flags):
        if not self.get_property('editable'):
            return
        saved_text = self.get_property('text')

        entry = Gtk.Entry()
        entry.set_completion(self.completion)
        entry.set_text(saved_text)
        #entry.connect('editing-done', self.editing_done, path)
        entry.connect('focus-out-event', self.focus_out, path)

        entry.show()
        entry.grab_focus()
        return entry

    def focus_out(self, entry, event, path):
        """ to ensure that changes are saved when the dialogue is closed with
            the widget still focussed, I'm emitting 'edited' on this event
            instead of 'editing-done'. The is probably not the correct way,
            but it works very nicely :) """
        new_value = entry.get_text()
        if self.force_match and new_value not in self.completion_entries:
            return
        self.emit('edited', path, new_value)


if __name__ == "__main__":

    # Initialize and load gsettings values
    SETTINGS = get_settings(METADATA['settings-schema'])

    SettingsWindow()
    Gtk.main()
