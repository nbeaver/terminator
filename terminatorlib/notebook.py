#!/usr/bin/python
# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""notebook.py - classes for the notebook widget"""

import gobject
import gtk

from newterminator import Terminator
from config import Config
from factory import Factory
from container import Container
from editablelabel import EditableLabel
from translation import _
from util import err

class Notebook(Container, gtk.Notebook):
    """Class implementing a gtk.Notebook container"""
    window = None

    def __init__(self, window):
        """Class initialiser"""
        if isinstance(window.get_child(), gtk.Notebook):
            err('There is already a Notebook at the top of this window')
            raise(ValueError)

        Container.__init__(self)
        gtk.Notebook.__init__(self)
        self.terminator = Terminator()
        self.window = window
        gobject.type_register(Notebook)
        self.register_signals(Notebook)
        self.configure()

        child = window.get_child()
        window.remove(child)
        window.add(self)
        self.newtab(child)

        label = TabLabel(self.window.get_title(), self)
        self.set_tab_label(child, label)
        self.set_tab_label_packing(child, not self.config['scroll_tabbar'],
                                   not self.config['scroll_tabbar'],
                                   gtk.PACK_START)

        self.show_all()

    def configure(self):
        """Apply widget-wide settings"""
        # FIXME: Should all of our widgets have this?
        #self.connect('page-reordered', self.on_page_reordered)
        self.set_property('homogeneous', not self.config['scroll_tabbar'])
        self.set_scrollable(self.config['scroll_tabbar'])

        pos = getattr(gtk, 'POS_%s' % self.config['tab_position'].upper())
        self.set_tab_pos(pos)
        self.set_show_tabs(not self.config['hide_tabbar'])

    def split_axis(self, widget, vertical=True, sibling=None):
        """Default axis splitter. This should be implemented by subclasses"""
        page_num = self.page_num(widget)
        if page_num == -1:
            err('Notebook::split_axis: %s not found in Notebook' % widget)
            return

        self.remove_page(page_num)

        maker = Factory()
        if vertical:
            container = maker.make('vpaned')
        else:
            container = maker.make('hpaned')

        if not sibling:
            sibling = maker.make('terminal')
        self.terminator.register_terminal(sibling)
        sibling.spawn_child()

        self.insert_page(container, None, page_num)
        self.show_all()

        container.add(widget)
        container.add(sibling)
        self.set_current_page(page_num)

        self.show_all()

    def add(self, widget):
        """Add a widget to the container"""
        raise NotImplementedError('add')

    def remove(self, widget):
        """Remove a widget from the container"""
        page_num = self.page_num(widget)
        if page_num == -1:
            err('Notebook::remove: %s not found in Notebook' % widget)
            return(False)
        self.remove_page(page_num)
        return(True)

    def newtab(self, widget=None):
        """Add a new tab, optionally supplying a child widget"""
        if not widget:
            maker = Factory()
            widget = maker.make('terminal')
            self.terminator.register_terminal(widget)
            widget.spawn_child()

        signals = {'close-term': self.wrapcloseterm,
                   #'title-change': self.title.set_title,
                   'split-horiz': self.split_horiz,
                   'split-vert': self.split_vert,
                   'unzoom': self.unzoom}

        maker = Factory()
        if maker.isinstance(widget, 'Terminal'):
            for signal in signals:
                self.connect_child(widget, signal, signals[signal])

        self.set_tab_reorderable(widget, True)
        label = TabLabel(self.window.get_title(), self)

        label.show_all()
        widget.show_all()

        self.set_tab_label(widget, label)
        self.set_tab_label_packing(widget, not self.config['scroll_tabbar'],
                                   not self.config['scroll_tabbar'],
                                   gtk.PACK_START)


        self.append_page(widget, None)
        self.set_current_page(-1)
        widget.grab_focus()

    def wrapcloseterm(self, widget):
        """A child terminal has closed"""
        if self.closeterm(widget):
            if self.get_n_pages() == 1:
                child = self.get_nth_page(0)
                self.remove_page(0)
                parent = self.get_parent()
                parent.remove(self)
                parent.add(child)
                del(self)

    def resizeterm(self, widget, keyname):
        """Handle a keyboard event requesting a terminal resize"""
        raise NotImplementedError('resizeterm')

    def zoom(self, widget, fontscale = False):
        """Zoom a terminal"""
        raise NotImplementedError('zoom')

    def unzoom(self, widget):
        """Unzoom a terminal"""
        raise NotImplementedError('unzoom')

class TabLabel(gtk.HBox):
    """Class implementing a label widget for Notebook tabs"""
    notebook = None
    terminator = None
    config = None
    label = None
    icon = None
    button = None

    def __init__(self, title, notebook):
        """Class initialiser"""
        gtk.HBox.__init__(self)
        self.notebook = notebook
        self.terminator = Terminator()
        self.config = Config()

        self.label = EditableLabel(title)
        self.update_angle()

        self.pack_start(self.label, True, True)

        self.update_button()
        self.show_all()

    def update_button(self):
        """Update the state of our close button"""
        if not self.config['close_button_on_tab']:
            if self.button:
                self.button.remove(self.icon)
                self.remove(self.button)
                del(self.button)
                del(self.icon)
                self.button = None
                self.icon = None
            return

        if not self.button:
            self.button = gtk.Button()
        if not self.icon:
            self.icon = gtk.Image()
            self.icon.set_from_stock(gtk.STOCK_CLOSE,
                                     gtk.ICON_SIZE_MENU)

        self.button.set_relief(gtk.RELIEF_NONE)
        self.button.set_focus_on_click(False)
        # FIXME: Why on earth are we doing this twice?
        self.button.set_relief(gtk.RELIEF_NONE)
        self.button.add(self.icon)
        self.button.connect('clicked', self.on_close)
        self.button.set_name('terminator-tab-close-button')
        self.button.connect('style-set', self.on_style_set)
        if hasattr(self.button, 'set_tooltip_text'):
            self.button.set_tooltip_text(_('Close Tab'))
        self.pack_start(self.button, False, False)
        self.show_all()

    def update_angle(self):
        """Update the angle of a label"""
        position = self.notebook.get_tab_pos()
        if position == gtk.POS_LEFT:
            self.label.set_angle(90)
        elif position == gtk.POS_RIGHT:
            self.label.set_angle(270)
        else:
            self.label.set_angle(0)

    def on_style_set(self, widget, prevstyle):
        """Style changed, recalculate icon size"""
        x, y = gtk.icon_size_lookup_for_settings(self.button.get_settings(),
                                                 gtk.ICON_SIZE_MENU)
        self.button.set_size_request(x + 2, y + 2)

    def on_close(self, widget):
        """The close button has been clicked. Destroy the tab"""
        pass
# vim: set expandtab ts=4 sw=4:
