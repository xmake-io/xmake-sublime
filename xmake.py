import sublime
import sublime_plugin
import subprocess
import os
import re
import time

# print message to console
def console_print(host, prefix, output):

	if host and prefix:
		host = host + "[" + prefix + "]: "
	elif host and not prefix:
		host = host + ": "
	elif not host and prefix:
		host = os.path.basename(prefix) + ": "

	output = "[xmake]: " + host + output.replace("\n", "\n[rsync-ssh] "+ host)
	print(output)

# show the console window
def console_show(window = sublime.active_window()):
	window.run_command("show_panel", {"panel": "console", "toggle": False})

# get the project directory
def get_projectdir(view):

	# get the project data	
	project_data = view.window().project_data()
	if project_data == None:
		console_print("", "", "Unable to initialize settings, you must have a .sublime-project file.")
		console_print("", "", "Please use 'Project -> Save Project As...' first.")
		console_show(view.window())
		return None

	# get the first folder path with xmake.lua
	for folder in project_data.get("folders"):

		# get folder directory
		folderdir = folder.get("path")
		if folderdir == ".":
			folderdir = os.path.basename(os.path.dirname(view.window().project_file_name()))
		if os.path.isfile(os.path.join(folderdir, "xmake.lua")):
			return folderdir

		# find xmake.lua
		found = False
		for parent, dirnames, filenames in os.walk(folderdir):
			if not found:
				for filename in filenames:
					if filename == "xmake.lua":
						found = True
					break
		if found:
			return folderdir

	# show error tips
	console_print("", "", "Unable to find xmake.lua in the project folder, you must have a xmake.lua file.")
	console_show(view.window())

	# xmake.lua not found!
	return None

# run command
def run_command(self, command, taskname = None):

    # create output panel
	panel = self.view.window().create_output_panel('xmake')

	# show output panel
	self.view.window().run_command("show_panel", {"panel": "output.xmake"})

	# start to output
	panel.set_read_only(False)

	# start time
	startime = time.clock()

    # run it
	process = subprocess.Popen(command, stdout = subprocess.PIPE, shell = True, bufsize = 0)
	if process:
		process.stdout.flush()
		for line in iter(process.stdout.readline, b''):
			panel.run_command('append', {'characters': line.decode('utf-8'), "force": True, "scroll_to_end": True})
			process.stdout.flush()
		process.communicate()

	# end time
	endime = time.clock()

	# show result
	result = "%sFinished, %0.2f seconds!" %(taskname + " " if taskname else "", endime - startime)
	panel.run_command('append', {'characters': result, "force": True, "scroll_to_end": True})

	# stop to output
	panel.set_read_only(True)

# clean configure 
class XmakeCleanConfigureCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)
        
		# configure project
		run_command(self, "xmake config -c", "Clean Configure")

# configure project
class XmakeConfigureCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)
        
		# configure project
		run_command(self, "xmake config", "Configure")

# build target
class XmakeBuildCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)

		# build target
		run_command(self, "xmake", "Build")

# rebuild target
class XmakeRebuildCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)

		# rebuild target
		run_command(self, "xmake -r", "Rebuild")
        
# run target
class XmakeRunCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)
        
		# run target
		run_command(self, "xmake run", "Run")

# clean files
class XmakeCleanCommand(sublime_plugin.TextCommand):

	# run command
	def run(self, edit):

		# run async
		sublime.set_timeout_async(self.__run_async, 0)

	# async run command
	def __run_async(self):

		# get the project directory
		projectdir = get_projectdir(self.view)
		if projectdir == None:
			return

		# enter the project directory
		os.chdir(projectdir)
        
		# clean files
		run_command(self, "xmake clean", "Clean")

# the event listener
class XmakeListener(sublime_plugin.EventListener):

	# post text command
	def on_post_text_command(self, view, command_name, args):

		# double click?
		if command_name == 'drag_select' and 'by' in args.keys() and args['by'] == 'words':
			self.__on_double_click_command(view, args)

	# on double click command
	def __on_double_click_command(self, view, args):
		
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
		matches = re.findall(r'^(error: )?(.*?):([0-9]*):([0-9]*): (.*?): (.*)$', selected_line)
		if matches and len(matches[0]) == 6:
			file = matches[0][1]
			line = matches[0][2]
			kind = matches[0][4]
			message = matches[0][5]

		# goto the error and warning position
		if file and line and message and os.path.isfile(file):

			# get the project directory
			projectdir = get_projectdir(view)
			if projectdir == None:
				return

			# get absolute file path
			if not os.path.isabs(file):
				file = os.path.abspath(os.path.join(projectdir, file))

			# goto the file view
			window = sublime.active_window()
			fileview = window.open_file("%s:%s:0"%(file, line), sublime.ENCODED_POSITION)
			if fileview:
				line = int(line)
				region = fileview.full_line(fileview.text_point(line - 1 if line > 0 else 0, 0))
				fileview.add_regions("highlighted_lines", [region], 'error', 'dot', sublime.DRAW_OUTLINED)
				fileview.show(region)
				window.focus_view(fileview)

