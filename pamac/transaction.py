#! /usr/bin/python
# -*-coding:utf-8-*-

from gi.repository import Gtk, GObject

import pyalpm
import traceback
import dbus
from dbus.mainloop.glib import DBusGMainLoop

from pamac import config

interface = Gtk.Builder()
interface.add_from_file('/usr/share/pamac/gui/dialogs.glade')

ErrorDialog = interface.get_object('ErrorDialog')
WarningDialog = interface.get_object('WarningDialog')
ProgressWindow = interface.get_object('ProgressWindow')
progress_bar = interface.get_object('progressbar2')
progress_label = interface.get_object('progresslabel2')
action_icon = interface.get_object('action_icon')
ProgressCancelButton = interface.get_object('ProgressCancelButton')

t_lock = False
do_syncfirst = False
list_first = []
to_remove = []
to_add = []
to_update = []
handle = None

def get_handle():
	global handle
	handle = config.pacman_conf.initialize_alpm()

DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
proxy = bus.get_object('org.manjaro.pamac','/org/manjaro/pamac', introspect=False)
Refresh = proxy.get_dbus_method('Refresh','org.manjaro.pamac')
Init = proxy.get_dbus_method('Init','org.manjaro.pamac')
Sysupgrade = proxy.get_dbus_method('Sysupgrade','org.manjaro.pamac')
Remove = proxy.get_dbus_method('Remove','org.manjaro.pamac')
Add = proxy.get_dbus_method('Add','org.manjaro.pamac')
Prepare = proxy.get_dbus_method('Prepare','org.manjaro.pamac')
To_Remove = proxy.get_dbus_method('To_Remove','org.manjaro.pamac')
To_Add = proxy.get_dbus_method('To_Add','org.manjaro.pamac')
Commit = proxy.get_dbus_method('Commit','org.manjaro.pamac')
Release = proxy.get_dbus_method('Release','org.manjaro.pamac')
StopDaemon = proxy.get_dbus_method('StopDaemon','org.manjaro.pamac')

def action_signal_handler(action):
	progress_label.set_text(action)
	#~ if 'Downloading' in action:
		#~ print('cancel enabled')
		#~ ProgressCancelButton.set_visible(True)
	#~ else:
	ProgressCancelButton.set_visible(False)
		#~ print('cancel disabled')

def icon_signal_handler(icon):
	action_icon.set_from_file(icon)

def target_signal_handler(target):
	progress_bar.set_text(target)

def percent_signal_handler(percent):
	if percent == '0':
		progress_bar.pulse()
	else:
		progress_bar.set_fraction(float(percent))

bus.add_signal_receiver(action_signal_handler, dbus_interface = "org.manjaro.pamac", signal_name = "EmitAction")
bus.add_signal_receiver(icon_signal_handler, dbus_interface = "org.manjaro.pamac", signal_name = "EmitIcon")
bus.add_signal_receiver(target_signal_handler, dbus_interface = "org.manjaro.pamac", signal_name = "EmitTarget")
bus.add_signal_receiver(percent_signal_handler, dbus_interface = "org.manjaro.pamac", signal_name = "EmitPercent")

def init_transaction(**options):
	"Transaction initialization"
	global t_lock
	error = Init(dbus.Dictionary(options, signature='sb'))
	if not error:
		t_lock = True
		return True
	else:
		ErrorDialog.format_secondary_text(error)
		response = ErrorDialog.run()
		if response:
			ErrorDialog.hide()
		return False

def check_conflicts():
	global to_add
	global to_remove
	to_check = []
	warning = ''
	for pkgname in to_add:
		for repo in handle.get_syncdbs():
			pkg = repo.get_pkg(pkgname)
			if pkg:
				to_check.append(pkg)
				break
	for target in to_check:
		if target.replaces:
			for name in target.replaces:
				pkg = handle.get_localdb().get_pkg(name)
				if pkg:
					if not pkg.name in to_remove:
						to_remove.append(pkg.name)
						if warning:
							warning = warning+'\n'
						warning = warning+pkg.name+' will be replaced by '+target.name
		if target.conflicts:
			for name in target.conflicts:
				pkg = handle.get_localdb().get_pkg(name)
				if pkg:
					if not pkg.name in to_remove:
						to_remove.append(pkg.name)
		for installed_pkg in handle.get_localdb().pkgcache:
			if installed_pkg.conflicts:
				for name in installed_pkg.conflicts:
					if name == target.name:
						if not name in to_remove:
							to_remove.append(installed_pkg.name)
	if warning:
		WarningDialog.format_secondary_text(warning)
		response = WarningDialog.run()
		if response:
			WarningDialog.hide()

def get_to_remove():
	global to_remove
	to_remove = To_Remove()

def get_to_add():
	global to_add
	to_add = To_Add()

def do_refresh():
	"""Sync databases like pacman -Sy"""
	global t_lock
	ProgressWindow.show_all()
	print('show')
	if t_lock is False:
		t_lock = True
		ProgressWindow.show_all()
		error = Refresh(timeout = 2000*1000)
		if error:
			ErrorDialog.format_secondary_text(error)
			response = ErrorDialog.run()
			if response:
				ErrorDialog.hide()
			Release()
		ProgressWindow.hide()
		print('hide')
		t_lock = False

def get_updates():
	"""Return a list of package objects in local db which can be updated"""
	global do_syncfirst
	global list_first
	get_handle()
	if config.syncfirst:
		for name in config.syncfirst:
			pkg = handle.get_localdb().get_pkg(name)
			candidate = pyalpm.sync_newversion(pkg, handle.get_syncdbs())
			if candidate:
				list_first.append(candidate)
		if list_first:
			do_syncfirst = True
			return list_first
	result = []
	installed_pkglist = handle.get_localdb().pkgcache
	for pkg in installed_pkglist:
		candidate = pyalpm.sync_newversion(pkg, handle.get_syncdbs())
		if candidate:
			result.append(candidate)
	return result

def get_new_version_available(pkgname):
	for repo in handle.get_syncdbs():
		pkg = repo.get_pkg(pkgname)
		if pkg is not None:
			return pkg.version
			break