import sublime
import sublime_plugin
import subprocess
import os
import re
import time

# the xmake plugin
class XmakePlugin(object):

	# initializer
	def __init__(self):

		# init xmake
		self.xmake = None

		# init panels
		self.panels = {}

		# init default target
		self.target = "default"

		# init current project directory
		self.projectdir = None

		# init build output level
		self.build_output_level = "warning"

		# load options
		self.options = {}
		self.options_changed = True
		self.load_options()
		
		# update status
		self.update_status()

	# get xmake program
	def get_xmake(self):

		# for windows? return xmake directly
		if sublime.platform() == "windows":
			self.xmake = "xmake"

		# attempt to get xmake program
		if not self.xmake:
			programs = ["xmake", os.path.join(os.getenv("HOME"), ".local/bin/xmake"), "/usr/local/bin/xmake", "/usr/bin/xmake"]
			for program in programs:
				if program == "xmake" or os.path.isfile(program):
					result = subprocess.Popen(program + " --version", stdout = subprocess.PIPE, shell = True).communicate()
					if result and len(result[0]) > 0:
						self.xmake = program
						break
		
		# ok?
		return self.xmake

	# print message to console
	def console_print(self, host, prefix, output):

		if host and prefix:
			host = host + "[" + prefix + "]: "
		elif host and not prefix:
			host = host + ": "
		elif not host and prefix:
			host = os.path.basename(prefix) + ": "

		output = "[xmake]: " + host + output.replace("\n", "\n[rsync-ssh] "+ host)
		print(output)

	# show the console window
	def console_show(self):

		# get window
		window = sublime.active_window()

		# show console
		window.run_command("show_panel", {"panel": "console", "toggle": False})

	# get the project directory
	def get_projectdir(self, tips = True):

		# get window
		window = sublime.active_window()

		# get folders
		folders = window.folders()
		if not folders or len(folders) == 0:
			for win in sublime.windows():
				for folder in win.folders():
					if not folders:
						folders = []
					folders.append(folder)

		# check
		if not folders or len(folders) == 0:
			if tips:
				self.console_print("", "", "Unable to initialize settings, you must have a .sublime-project file.")
				self.console_print("", "", "Please use 'Project -> Save Project As...' first.")
				self.console_show(window)
			return None

		# get the first folder path with xmake.lua
		projectdir = None
		for folder in folders:

			# get folder directory
			if folder == ".":
				folder = os.path.basename(os.path.dirname(window.project_file_name()))
			if os.path.isfile(os.path.join(folder, "xmake.lua")):
				projectdir = folder
				break

			# find xmake.lua
			found = False
			for parent, dirnames, filenames in os.walk(folder):
				if not found:
					for filename in filenames:
						if filename == "xmake.lua":
							found = True
						break
			if found:
				projectdir = folder
				break

		# show error tips if not found
		if not projectdir and tips:
			self.console_print("", "", "Unable to find xmake.lua in the project folder, you must have a xmake.lua file.")
			self.console_show(window)

		# ok?
		return projectdir

	# get output panel
	def output_panel(self, name):

		# get window
		window = sublime.active_window()

		# init key
		key = "output." + name

		# attempt to get the output panel
		panel = self.panels[key]
		if panel:
			return panel

		# new a output panel
		panel = window.create_output_panel(name)
		panel.set_name(key)

		# save this panel
		self.panels[key] = panel

		# ok
		return panel

	# clean output panel
	def clean_output_panel(self, name):
		self.panels["output." + name] = None

	# run command
	def run_command(self, command, taskname = None):

		# get project directory
		projectdir = plugin.get_projectdir(False)
		if projectdir == None:
			return

		# get window
		window = sublime.active_window()

	    # create output panel
		panel = self.output_panel('xmake')

		# show output panel
		window.run_command("show_panel", {"panel": "output.xmake"})

		# start to output
		panel.set_read_only(False)

		# start time
		startime = time.clock()

		# run it
		process = subprocess.Popen(command, stdout = subprocess.PIPE, shell = True, cwd = projectdir, bufsize = 0)
		if process:
			process.stdout.flush()
			for line in iter(process.stdout.readline, b''):
				panel.run_command('append', {'characters': line.decode('utf-8'), "force": True, "scroll_to_end": True})
				process.stdout.flush()
			process.communicate()

		# end time
		endime = time.clock()

		# show result
		result = "%sFinished, %0.2f seconds!\n" %(taskname + " " if taskname else "", endime - startime)
		panel.run_command('append', {'characters': result, "force": True, "scroll_to_end": True})

		# stop to output
		panel.set_read_only(True)

	# load options
	def load_options(self):

		# get window
		window = sublime.active_window()

		# get project directory
		projectdir = self.get_projectdir(False)
		if projectdir == None:
			return

		# get cache config
		cache = None
		config = subprocess.Popen(self.get_xmake() + """ l -c 'import("core.project.config"); config.load(); print("$(plat) $(arch) $(mode)")'""", stdout = subprocess.PIPE, cwd = projectdir, shell = True).communicate()
		if config and len(config) != 0:
			cache = config[0].strip().decode('utf-8').split(' ')

		# get platform
		plat = cache[0] if cache != None and len(cache) > 0 else None
		if plat != None and len(plat) > 0:
			self.options["plat"] = plat
		else:
			self.options["plat"] = {"osx": "macosx", "linux": "linux", "windows": "windows"}[sublime.platform()]

		# get architecture
		arch = cache[1] if cache != None and len(cache) > 1 else None
		if arch != None and len(arch) > 0:
			self.options["arch"] = arch
		else:
			self.options["arch"] = sublime.arch() if sublime.platform() == "windows" else {"x86": "i386", "x64": "x86_64"}[sublime.arch()]
 
		# get architecture
		mode = cache[2] if cache != None and len(cache) > 2 else None
		if mode != None and len(mode) > 0:
			self.options["mode"] = mode
		else:
			self.options["mode"] = "release"

	# get option
	def get_option(self, name):
		return self.options.get(name)

	# set option
	def set_option(self, name, value):

		# this option has been changed?
		if self.options.get(name) != value:
			self.options[name] = value
			self.mark_options_changed(True)
			self.update_status()

	# get target
	def get_target(self):
		return self.target

	# set target
	def set_target(self, name):
		if self.target != name:
			self.target = name
			self.update_status()

	# get build output level
	def get_build_output_level(self):
		return self.build_output_level

	# set build output level
	def set_build_output_level(self, level):
		self.build_output_level = level

	# update status 
	def update_status(self):

		# get window
		window = sublime.active_window()

		# get view
		view = window.active_view()
		if not view:
			return

		# get project directory
		projectdir = self.get_projectdir(False)
		if projectdir == None:
			return

		# project changed? update options and status
		if projectdir and self.projectdir != projectdir:
			self.projectdir = projectdir
			self.load_options()

		# update the plugin name
		view.set_status("xmake_statusitem_1", "xmake: " + os.path.basename(projectdir))

		# update the platform 
		view.set_status("xmake_statusitem_2", self.options["plat"])

		# update the architecture 
		view.set_status("xmake_statusitem_3", self.options["arch"])

		# update the mode 
		view.set_status("xmake_statusitem_4", self.options["mode"])

		# update the target 
		view.set_status("xmake_statusitem_5", self.target)

	# mark options changed
	def mark_options_changed(self, changed):
		self.options_changed = changed

	# update config
	def update_config(self):

		# options have been changed?
		if self.options_changed:

			# make command
			command = self.get_xmake() + " f -p %s -a %s -m %s" %(self.get_option("plat"), self.get_option("arch"), self.get_option("mode"))
			
			# configure project
			plugin.run_command(command, "Configure")

			# reload options
			plugin.load_options()

			# update status
			plugin.update_status()

			# clear changed mark
			self.options_changed = False

# define plugin
global plugin
plugin = XmakePlugin()

# plugin loaded
def plugin_loaded():
	plugin.update_status()

# clean configure 
class XmakeCleanConfigureCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")
        
		# configure project
		plugin.run_command(plugin.get_xmake() + " f -c", "Clean Configure")

		# reload options
		plugin.load_options()

		# update status
		plugin.update_status()

		# clear options changed
		plugin.mark_options_changed(False)

# configure project
class XmakeConfigureCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")
        
        # update config
		plugin.update_config()

# build target
class XmakeBuildCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")
        
        # update config
		plugin.update_config()

		# add build level to command     
		targetname = plugin.get_target()     
		buildlevel = plugin.get_build_output_level()
		command = plugin.get_xmake()
		if targetname and targetname != "default":
			command += " build";
		if buildlevel == "verbose":
			command += " -v";
		elif buildlevel == "warning":
			command += " -w";
		elif buildlevel == "debug":
			command += " -v --backtrace";

		# add build target to command
		if targetname and targetname != "default":
			command += " " + targetname;
		elif targetname == "all":
			command += " -a";

		# build target
		plugin.run_command(command, "Build")

# rebuild target
class XmakeRebuildCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")
        
        # update config
		plugin.update_config()

		# add build level to command     
		targetname = plugin.get_target()     
		buildlevel = plugin.get_build_output_level()
		command = plugin.get_xmake() + " -r"  
		if buildlevel == "verbose":
			command += " -v";
		elif buildlevel == "warning":
			command += " -w";
		elif buildlevel == "debug":
			command += " -v --backtrace";

		# add build target to command
		if targetname and targetname != "default":
			command += " " + targetname;
		elif targetname == "all":
			command += " -a";

		# rebuild target
		plugin.run_command(command, "Rebuild")
        
# run target
class XmakeRunCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")
        
        # update config
		plugin.update_config()

		# make command
		command = plugin.get_xmake() + " r"   
		targetname = plugin.get_target() 
		if targetname and targetname != "default":
			command += " " + targetname;
		elif targetname == "all":
			command += " -a";

		# run target
		plugin.run_command(command, "Run")

# clean files
class XmakeCleanCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")

		# update config
		plugin.update_config()

		# make command
		command = plugin.get_xmake() + " c"
		targetname = plugin.get_target()   
		if targetname and targetname != "default":
			command += " " + targetname;

		# clean files
		plugin.run_command(command, "Clean")

# package files
class XmakePackageCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = plugin.get_projectdir()
		if projectdir == None:
			return

		# clean output panel first
		plugin.clean_output_panel("xmake")

		# update config
		plugin.update_config()

		# make command
		command = plugin.get_xmake() + " p"
		targetname = plugin.get_target()   
		if targetname and targetname != "default":
			command += " " + targetname;
		elif targetname == "all":
			command += " -a"

		# clean files
		plugin.run_command(command, "Package")

# set target platform
class XmakeSetTargetPlatCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# show quick panel
		self.plats = ["linux", "macosx", "windows", "android", "iphoneos", "watchos", "mingw", "cross"]
		self.view.window().show_quick_panel(self.plats, self._on_select)

	# on select
	def _on_select(self, idx):

		# selected
		if idx > -1:

			# get the selected platform
			plat = self.plats[idx]
			if plat:
				plugin.set_option("plat", plat)

				# update architecture
				arch = None
				host = {"osx": "macosx", "linux": "linux", "windows": "windows"}[sublime.platform()]
				if plat == host:
					arch = sublime.arch() if sublime.platform() == "windows" else {"x86": "i386", "x64": "x86_64"}[sublime.arch()]
				else:
					arch = {"windows": "x86", "macosx": "x86_64", "linux": "x86_64", "mingw": "x86_64", "iphoneos": "arm64", "watchos": "armv7k", "android": "armv7-a"}[plat]
				if arch:
					plugin.set_option("arch", arch)

# set target architecture
class XmakeSetTargetArchCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# init archs
		self.archs = {}
		self.archs["windows"] = ["x86", "x64"]
		self.archs["macosx"] = ["i386", "x86_64"]
		self.archs["iphoneos"] = ["armv7", "armv7s", "arm64", "i386", "x86_64"]
		self.archs["watchos"] = ["armv7k", "i386"]
		self.archs["android"] = ["armv5te", "armv6", "armv7-a", "armv8-a", "arm64-v8a"]
		self.archs["linux"] = self.archs["macosx"]
		self.archs["mingw"] = self.archs["macosx"]

		# get the current platform
		plat = plugin.get_option("plat")
		
		# show quick panel
		self.view.window().show_quick_panel(self.archs[plat], self._on_select)

	# on select
	def _on_select(self, idx):

		# selected
		if idx > -1:

			# get the current platform
			plat = plugin.get_option("plat")
			
			# get the selected architecture
			arch = self.archs[plat][idx]
			if arch:
				plugin.set_option("arch", arch)

# set build mode
class XmakeSetBuildModeCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# show quick panel
		self.modes = ["debug", "release"]
		self.view.window().show_quick_panel(self.modes, self._on_select)

	# on select
	def _on_select(self, idx):

		# selected
		if idx > -1:

			# get the selected mode
			mode = self.modes[idx]
			if mode:
				plugin.set_option("mode", mode)

# set default target
class XmakeSetDefaultTargetCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# get project directory
		projectdir = plugin.get_projectdir(False)
		if projectdir == None:
			return

		# get targets
		self.targets = ["all", "default"]
		targets = subprocess.Popen(plugin.get_xmake() + """ l -c 'import("core.project.config"); import("core.project.project"); config.load(); for name, _ in pairs((project.targets())) do print(name) end'""", stdout = subprocess.PIPE, cwd = projectdir, shell = True).communicate()
		if targets:
			for target in targets[0].strip().decode('utf-8').split('\n'):
				self.targets.append(target)

		# show quick panel
		self.view.window().show_quick_panel(self.targets, self._on_select)

	# on select
	def _on_select(self, idx):

		# selected
		if idx > -1:

			# get the selected target
			target = self.targets[idx]
			if target:
				plugin.set_target(target)

# set build output level
class XmakeSetBuildOutputLevelCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# get levels
		self.levels = ["normal", "verbose", "warning", "debug"]

		# show quick panel
		self.view.window().show_quick_panel(self.levels, self._on_select)
 
	# on select
	def _on_select(self, idx):

		# selected
		if idx > -1:

			# get the selected level
			level = self.levels[idx]
			if level:
				plugin.set_build_output_level(level)

# the event listener
class XmakeListener(sublime_plugin.EventListener):

	# on activated
	def on_activated_async(self, view):

		# update status
		plugin.update_status()

	# on load
	def on_load_async(self, view):

		# update status
		plugin.update_status()

	# on post text command
	def on_post_text_command(self, view, command_name, args):

		# double click?
		if command_name == 'drag_select' and 'by' in args.keys() and args['by'] == 'words':
			self.__on_double_click_command(view, args)

	# on double click command
	def __on_double_click_command(self, view, args):

		# only for the panel: output.xmake
		if view.name() != "output.xmake":
			return

		# get the selected position
		sel = view.sel()[0]
		if sel.end() - sel.begin() <= 0:
			return

		# get the selected line
		selected_line = view.substr(view.line(sel)).split('\n')[0].rstrip()

		# get file, line and message
		file = None
		line = None
		kind = None
		message = None
		if sublime.platform() == "windows":
			matches = re.findall(r'(.*?)\\(([0-9]*)\\): (.*?) .*?: (.*)', selected_line)
			if matches and len(matches[0]) == 4:
				file = matches[0][0]
				line = matches[0][1]
				kind = matches[0][2]
				message = matches[0][3]
		else:
			matches = re.findall(r'^(error: )?(.*?):([0-9]*):([0-9]*): (.*?): (.*)$', selected_line)
			if matches and len(matches[0]) == 6:
				file = matches[0][1]
				line = matches[0][2]
				kind = matches[0][4]
				message = matches[0][5]

		# goto the error and warning position
		if file and line and message and os.path.isfile(file):

			# get the project directory
			projectdir = plugin.get_projectdir()
			if projectdir == None:
				return

			# get absolute file path
			if not os.path.isabs(file):
				file = os.path.abspath(os.path.join(projectdir, file))

			# goto the file view
			window = sublime.active_window()
			fileview = window.open_file("%s:%s:0"%(file, line), sublime.ENCODED_POSITION)
			if fileview:
				# TODO
				line = int(line)
				region = fileview.line(fileview.text_point(line - 1 if line > 0 else 0, 0))
				fileview.add_regions("highlighted_lines", [region], 'error', 'dot', sublime.DRAW_OUTLINED)
				fileview.show(region)
				window.focus_view(fileview)

