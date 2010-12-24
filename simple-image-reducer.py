#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Simple Image Reducer - Reduce and rotate images in three-four clicks
# Copyright (C) 2010  Konstantin Korikov

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import os.path
import urllib
import urlparse
import ConfigParser

import Image
import EXIF

import gettext
_ = lambda x: gettext.ldgettext('simple-image-reducer', x)

import gtk
import gobject

version = '@VERSION@'

class MainWindow(gtk.Window):
    def __init__(self, argv):
        gtk.Window.__init__(self)

        self.cfg_filename = os.path.expanduser(
                os.path.join('~', '.config',
                    'simple-image-reducer', 'options'))
        self.cfg = ConfigParser.SafeConfigParser()
        self.cfg.add_section('last_used')
        self.cfg.set('last_used', 'resolution', '')
        self.cfg.set('last_used', 'rotate', 'exif')
        self.cfg.set('last_used', 'output_type', 'append')
        self.cfg.set('last_used', 'output_format', '')
        self.cfg.add_section('options')
        self.cfg.set('options', 'resolutions',
                '128x128,400x400,640x640,800x800,1024x1024')
        self.cfg.read(self.cfg_filename)

        self.task = None
        self.processed_count = 0

        self.connect('destroy', self.destroy)
        self.set_title(_("Simple Image Reducer"))
        self.set_icon_name('simple-image-reducer')

        vbox = gtk.VBox()
        self.add(vbox)

        table = gtk.Table(7, 3, False)
        table.set_row_spacings(5)
        table.set_col_spacings(5)
        table.set_border_width(10)
        vbox.pack_start(table, True, True)

        label = gtk.Label(_("Input Files:"))
        label.set_alignment(0, 0.5)
        table.attach(label,
                0, 2, 0, 1,
                gtk.FILL, gtk.FILL, 0, 0)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        table.attach(sw,
                0, 2, 1, 2,
                gtk.FILL | gtk.EXPAND,
                gtk.FILL | gtk.EXPAND, 0, 0)

        self.input_files = gtk.TreeView()
        self.input_files.set_tooltip_text(_("Drag image files here"))
        sw.add(self.input_files)
        self.input_files.set_size_request(-1, 200)
        self.input_files.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.input_files.set_rubber_banding(True)
        self.input_files.drag_dest_set(
                gtk.DEST_DEFAULT_ALL,
                [('text/uri-list', 0, 0)],
                gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self.input_files.connect('drag-data-received',
                self.on_input_files_drag_data_received)


        model = gtk.ListStore(gobject.TYPE_STRING)
        self.input_files.set_model(model)
        column = gtk.TreeViewColumn(_("File"),
                gtk.CellRendererText(), text=0)
        self.input_files.append_column(column)

        box = gtk.VButtonBox()
        box.set_spacing(5)
        box.set_layout(gtk.BUTTONBOX_START)
        table.attach(box,
            2, 3, 1, 2,
            gtk.FILL,  gtk.FILL, 0, 0)

        button = gtk.Button()
        button.set_tooltip_text(_("Add files..."))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
        button.add(image)
        button.connect('clicked', self.on_input_files_add_clicked)
        box.add(button)

        button = gtk.Button()
        button.set_tooltip_text(_("Remove files"))
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_BUTTON)
        button.add(image)
        button.connect('clicked', self.on_input_files_remove_clicked)
        box.add(button)

        label = gtk.Label(_("Fit to:"))
        label.set_alignment(1, 0.5)
        table.attach(label,
                0, 1, 2, 3,
                gtk.FILL, gtk.FILL, 0, 0)

        self.resolution = gtk.combo_box_new_text()
        self.resolution.set_tooltip_text(_("Select a maximum width and height"))
        self.resolution_map = [
                (None, _("No change")),
                ]
        for value in self.cfg.get('options', 'resolutions').split(','):
            text = value.strip()
            size = tuple([int(x) for x in text.split('x')])
            self.resolution_map.append((size, text))

        for size, text in self.resolution_map:
            self.resolution.append_text(text)
        self.resolution.set_active(0)

        default = self.cfg.get('last_used', 'resolution')
        if default:
            default = tuple([int(x) for x in default.split('x')])
        else:
            default = None
        for i in range(len(self.resolution_map)):
            if self.resolution_map[i][0] == default:
                self.resolution.set_active(i)

        self.resolution.connect('changed',
                lambda *args: self.update_output_files())

        table.attach(self.resolution,
            1, 2, 2, 3,
            gtk.FILL | gtk.EXPAND,  gtk.FILL,
            0, 0)

        label = gtk.Label(_("Rotate:"))
        label.set_alignment(1, 0.5)
        table.attach(label,
                0, 1, 3, 4,
                gtk.FILL, gtk.FILL, 0, 0)

        self.rotate = gtk.combo_box_new_text()
        self.rotate.set_tooltip_text(_("Select a rotation method"))
        self.rotate_map = [
                (None, _("No rotate")),
                ('270', _(u"90\u00b0 clockwise")),
                ('180', _(u"180\u00b0")),
                ('90', _(u"90\u00b0 counter-clockwise")),
                ('exif', _("According to EXIF data")),
                ]
        for method, text in self.rotate_map:
            self.rotate.append_text(text)
        self.rotate.set_active(0)

        default = self.cfg.get('last_used', 'rotate') or None
        for i in range(len(self.rotate_map)):
            if self.rotate_map[i][0] == default:
                self.rotate.set_active(i)

        table.attach(self.rotate,
            1, 2, 3, 4,
            gtk.FILL | gtk.EXPAND, gtk.FILL,
            0, 0)

        label = gtk.Label(_("Output files:"))
        label.set_alignment(1, 0)
        table.attach(label,
                0, 1, 4, 5,
                gtk.FILL, gtk.FILL, 0, 0)

        box = gtk.VBox()
        self.output_type_append = group = gtk.RadioButton(None, "")
        box.add(self.output_type_append)
        self.output_type_subdirectory = gtk.RadioButton(group, "")
        box.add(self.output_type_subdirectory)
        self.output_type_in_place = gtk.RadioButton(group,
                _("Modify images in place"))
        box.add(self.output_type_in_place)

        default = self.cfg.get('last_used', 'output_type')
        if default == 'subdirectory':
            self.output_type_subdirectory.set_active(True)
        elif default == 'in-place':
            self.output_type_in_place.set_active(True)
        else:
            self.output_type_append.set_active(True)
        self.update_output_files()

        table.attach(box,
            1, 2, 4, 5,
            gtk.FILL | gtk.EXPAND,  gtk.FILL,
            0, 0)

        label = gtk.Label(_("Output format:"))
        label.set_alignment(1, 0.5)
        table.attach(label,
                0, 1, 5, 6,
                gtk.FILL, gtk.FILL, 0, 0)

        self.output_format = gtk.combo_box_new_text()
        self.output_format_map = [
                (None, None, _("No change")),
                ('BMP', '.bmp', _("BMP")),
                ('GIF', '.gif', _("GIF")),
                ('JPEG', '.jpg', _("JPEG")),
                ('PNG', '.png', _("PNG")),
                ('PPM', '.ppm', _("PPM")),
                ('TIFF', '.tif', _("TIFF")),
                ]
        for fmt, ext, text in self.output_format_map:
            self.output_format.append_text(text)
        self.output_format.set_active(0)

        default = self.cfg.get('last_used',
                'output_format') or None
        for i in range(len(self.output_format_map)):
            if self.output_format_map[i][0] == default:
                self.output_format.set_active(i)

        table.attach(self.output_format,
            1, 2, 5, 6,
            gtk.FILL | gtk.EXPAND,  gtk.FILL,
            0, 0)

        box = gtk.HButtonBox()
        box.set_spacing(5)
        box.set_border_width(5)
        box.set_layout(gtk.BUTTONBOX_END)
        table.attach(box,
            0, 3, 6, 7,
            gtk.FILL | gtk.EXPAND,  gtk.FILL, 0, 0)

        button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect('clicked', self.destroy)
        box.add(button)

        button = gtk.Button(stock=gtk.STOCK_ABOUT)
        button.connect('clicked', self.about)
        box.add(button)

        self.execute_button = button = gtk.Button(stock=gtk.STOCK_EXECUTE)
        button.connect('clicked', self.execute)
        box.add(button)

        self.statusbar = gtk.Statusbar()
        vbox.pack_start(self.statusbar, False, False)
        self.update_status_bar()

        for uri in argv[1:]:
            self.add_input_file(uri)

        self.show_all()

    def destroy(self, *args):
        gtk.main_quit()

    def about(self, *args):
        dialog = gtk.AboutDialog()
        dialog.set_name(_("Simple Image Reducer"))
        dialog.set_version(version)
        dialog.set_comments(_("Reduce and rotate images in three-four clicks."))
        dialog.set_logo_icon_name('simple-image-reducer')
        dialog.set_copyright(_("(c) Copyright 2010 Konstantin Korikov"))
        dialog.set_license(_("""\
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
 
You should have received a copy of the GNU General Public License
along with this program; if not, see http://www.gnu.org/licenses/"""))
        dialog.set_wrap_license(True)
        dialog.set_website("http://simple-image-reducer.org.ua/")
        dialog.connect('response', lambda d, r: d.destroy())
        dialog.show()

    def add_input_file(self, path):
        if path.startswith('file://'):
            path = urllib.unquote(urlparse.urlsplit(path)[2])
        else:
            path = os.path.abspath(path)
        model = self.input_files.get_model()
        iter = model.append()
        model.set(iter, 0, path)
        self.update_status_bar()

    def on_input_files_drag_data_received(self, widget, context, x, y,
            data, info, time):
        if data.format == 8 and data.get_uris():
            for uri in data.get_uris():
                self.add_input_file(uri)
            context.finish(True, False, time)
        else:
            context.finish(False, False, time)

    def on_input_files_add_clicked(self, *args):
        fc = gtk.FileChooserDialog(
                title=_("Add File..."), parent=None,
                action=gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                    gtk.STOCK_ADD,gtk.RESPONSE_OK))
        fc.set_select_multiple(True)
        fc.set_default_response(gtk.RESPONSE_OK)
        filter = gtk.FileFilter()
        filter.set_name(_("Image Files"))
        filter.add_pattern('*.bmp')
        filter.add_pattern('*.gif')
        filter.add_pattern('*.jpeg')
        filter.add_pattern('*.jpg')
        filter.add_pattern('*.png')
        filter.add_pattern('*.tif')
        filter.add_pattern('*.tiff')
        fc.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name(_("All Files"))
        filter.add_pattern('*')
        fc.add_filter(filter)
        response = fc.run()
        if response == gtk.RESPONSE_OK:
            for uri in fc.get_filenames():
                self.add_input_file(uri)
        fc.destroy()

    def on_input_files_remove_clicked(self, *args):
        model, rows = self.input_files.get_selection().get_selected_rows()
        rows = [gtk.TreeRowReference(model, path) for path in rows]
        for row in rows:
            model.remove(model.get_iter(row.get_path()))
        self.update_status_bar()

    def get_output_suffix(self):
        size = self.resolution_map[
                self.resolution.get_active()][0]
        if size:
            return "%dx%d" % size
        return "modified"

    def get_output_type(self):
        if self.output_type_append.get_active():
            return 'append'
        if self.output_type_subdirectory.get_active():
            return 'subdirectory'
        if self.output_type_in_place.get_active():
            return 'in-place'
        
    def update_output_files(self):
        output_suffix = self.get_output_suffix()
        self.output_type_append.set_label(
                _("Append \"-%s\" to the file base name") % output_suffix)
        self.output_type_subdirectory.set_label(
                _("Save to \"%s\" subdirectory") % output_suffix)

    def update_status_bar(self):
        if self.task is not None:
            msg = _("%(current)d of %(total)d images processed") % {
                    'current': self.processed_count,
                    'total': len(self.input_files.get_model())}
        else:
            msg = _("%d images to process") % len(
                    self.input_files.get_model())
        self.statusbar.pop(0)
        self.statusbar.push(0, msg)

    def execute_task(self):
        size = self.resolution_map[
                self.resolution.get_active()][0]
        rotate_method = self.rotate_map[
                self.rotate.get_active()][0]
        output_suffix = self.get_output_suffix()
        output_type = self.get_output_type()
        format, extension = self.output_format_map[
                self.output_format.get_active()][0:2]
        errors = []

        exif_to_transpose = [
                (),
                (Image.FLIP_LEFT_RIGHT,),
                (Image.ROTATE_180),
                (Image.FLIP_TOP_BOTTOM,),
                (Image.ROTATE_90, Image.FLIP_LEFT_RIGHT),
                (Image.ROTATE_270,),
                (Image.ROTATE_270, Image.FLIP_LEFT_RIGHT),
                (Image.ROTATE_90,)]

        for (input,) in self.input_files.get_model():
            self.update_status_bar()
            base, ext = os.path.splitext(input)
            if output_type == 'append':
                output = "%s-%s%s" % (base, output_suffix, extension or ext)
            elif output_type == 'subdirectory':
                dir = os.path.join(os.path.dirname(input), output_suffix)
                output = os.path.join(dir,
                        os.path.basename(base) + (extension or ext))
                if not os.path.exists(dir):
                    os.makedirs(dir)
            else:
                output = base + (extension or ext)
            try:
                img = Image.open(input)
            except IOError:
                if os.access(input, os.R_OK):
                    errors.append(_("Cannot identify image file: %s") % input)
                else:
                    errors.append(_("Unable to open file: %s") % input)
                self.processed_count += 1
                continue
            transpose_methods = []
            if rotate_method == '90':
                transpose_methods = [Image.ROTATE_90]
            elif rotate_method == '180':
                transpose_methods = [Image.ROTATE_180]
            elif rotate_method == '270':
                transpose_methods = [Image.ROTATE_270]
            elif rotate_method == 'exif':
                if 'exif' in img.info:
                    tags = EXIF.process_file(open(input), details=False)
                    if 'Image Orientation' in tags:
                        transpose_methods = exif_to_transpose[
                                tags['Image Orientation'].values[0] - 1]
            for method in transpose_methods:
                img = img.transpose(method)
            if size:
                img.thumbnail(size, Image.ANTIALIAS)
            if format:
                fmt = format
            else:
                fmt = img.format
            options = {}
            if fmt == 'JPEG':
                options['quality'] = 90
            try:
                img.save(output, fmt, **options)
            except IOError:
                errors.append(_("Unable to open file for writing: %s") % input)
            self.processed_count += 1
            yield None
        self.update_status_bar()

        if errors:
            dialog = gtk.MessageDialog(self,
                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                    gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                    "\n".join(errors))
            dialog.run()

        if size:
            self.cfg.set('last_used', 'resolution', '%dx%d' % size)
        else:
            self.cfg.set('last_used', 'resolution', '')
        self.cfg.set('last_used', 'rotate', rotate_method or '')
        self.cfg.set('last_used', 'output_type', output_type)
        self.cfg.set('last_used', 'output_format', format or '')

        d = os.path.dirname(self.cfg_filename)
        if not os.path.exists(d):
            os.makedirs(d)
        fp = open(self.cfg_filename, 'w')
        self.cfg.write(fp)
        fp.close()

    def execute_iter(self):
        try:
            self.task.next()
        except StopIteration:
            self.task = None
            self.destroy()
            return False
        return True

    def execute(self, *args):
        if self.task is not None:
            return
        self.execute_button.set_sensitive(False)
        self.processed_count = 0
        self.task = self.execute_task()
        gobject.idle_add(self.execute_iter)

if __name__ == '__main__':
    MainWindow(sys.argv)
    gtk.main()
