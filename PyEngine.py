import sys
import ast
import pygame
import asyncio
from lupa import LuaRuntime
from PyQt5.QtWidgets import (
	QApplication,
	QMainWindow,
	QVBoxLayout,
	QHBoxLayout,
	QWidget,
	QFrame,
	QMenu,
	QListWidget,
	QDialog,
	QFormLayout,
	QLineEdit,
	QPushButton,
	QMessageBox,
	QTextEdit,
	QProgressBar
)
from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QImage, QPainter, QCursor

class GameObject:
	def __init__(self, pos, size, color, shape='square',font_size=32, script="", parent=None, font_text="New Text"):
		self.pos = list(pos)
		self.size = list(size)
		self.color = color
		self.shape = shape
		self.radius = size[0]//2
		self.parent = parent
		self.console = parent.console
		self.font_size = font_size
		self.text = font_text
		self.font = None

		self.script = script
		self.selected = False  # Initialize selected state
		self.lua = LuaRuntime(unpack_returned_tuples=True)

	def execute_script(self):
		# Set up Lua script environment
		self.lua_globals = self.lua.globals()
		
		# Create a Lua table called 'self' and assign attributes
		lua_self = self.lua.table()
		for attr, value in self.__dict__.items():
			if attr not in ("selected", "script", "console", "lua", "parent", "font"):
				lua_self[attr] = list(value) if isinstance(value, tuple) else value

		# Set the Lua 'self' table
		self.lua_globals['self'] = lua_self

		# Execute the Lua script
		try:
			lua_func = self.lua.execute(self.script)
		except Exception as e:
			self.console.append_text(repr(e))
			QMessageBox.critical(None, f"Error Occured!", "Error has occured, view console for more info", QMessageBox.NoButton)
			self.parent.toggle_play_state(quiet_mode=True)
			return

		for attr, value in self.lua_globals['self'].items():
			setattr(self, attr, value)

		if lua_func:
			lua_func()


	def copy(self):
		return GameObject(self.pos, self.size, color=self.color, shape=self.shape, script=self.script, parent=self.parent, font_size=self.font_size, font_text=self.text)
	def __repr__(self):
		if self.shape:
			return self.shape

	def set(self, token_name, value):
		for i, token in enumerate(self.tokens):
			if token_name == token:
				self.tokens[i] = value

	def hex_to_rgb(self, hex_color):
		hex_color = hex_color.lstrip('#')
		return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

	def draw(self, screen):
		self.font = pygame.font.SysFont("Arial", self.font_size)
		if type(self.color) == str:
			self.color = self.hex_to_rgb(self.color)
		# Draw the shape
		if self.shape == 'square':
			pygame.draw.rect(screen, self.color, (*self.pos, *self.size))
		elif self.shape == 'circle':
			pygame.draw.circle(screen, self.color, (self.pos[0]+self.radius, self.pos[1]+self.radius), self.radius)
		elif self.shape == 'text':
			font = self.font.render(str(self.text),True, self.color, None)
			screen.blit(font, self.pos)
		# Draw border if sellected
		if self.selected:
			border_color = (255, 255, 0)  # Yellow border
			if self.shape == 'square':
				pygame.draw.rect(screen, border_color, (*self.pos, *self.size), 3)  # Border thickness of 3
			elif self.shape == 'circle':
				pygame.draw.circle(screen, border_color, (self.pos[0] + self.radius, self.pos[1] + self.radius), self.radius + 3, 3)  # Border thickness of 3
			elif self.shape == 'text':
				font = self.font.render(str(self.text), True, self.color, border_color)
				screen.blit(font, self.pos)
class Game(QWidget):
	def __init__(self, properties_frame, console):
		super().__init__()
		self.setFixedSize(500, 480)
		self.property_frame = properties_frame
		pygame.init()
		self.screen = pygame.Surface((500, 480))
		self.clock = pygame.time.Clock()
		self.console = console
		
		self.objects = []
		self.selected_objects = []  # List to hold selected objects
		self.is_playing = False

		self.BG = (255,255,255)
		
		self.timer = QTimer(self)
		self.timer.timeout.connect(self.update_game)
		self.timer.start(16)

		self.context_menu = QMenu(self)
		self.context_menu.addAction("New Object", self.show_new_object_menu)
		self.play = self.context_menu.addAction("Play Game", self.toggle_play_state)

		self.clipboard=None

		self.last_mouse_pos = None  # Variable to store the last mouse position

	def update_game(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit()
		
		self.screen.fill(self.BG)
		
		for obj in self.objects:
			obj.draw(self.screen)
		
		self.update()

	def paintEvent(self, event):
		q_image = pygame.image.tostring(self.screen, 'RGBA')
		image = QImage(q_image, 500, 480, QImage.Format_RGBA8888)
		
		painter = QPainter(self)
		painter.drawImage(0, 0, image)

	def contextMenuEvent(self, event):
		self.context_menu.clear()
		if self.clipboard:
			self.context_menu.addAction("Paste", self.paste)
		if self.selected_objects:
			# Context menu for when objects are selected
			self.context_menu.addAction("Destroy", self.destroy_selected_objects)
			self.context_menu.addAction("Copy", self.copy_selected_objects)
		else:
			# Default context menu when no objects are selected
			
			self.context_menu.addAction("New Object", self.show_new_object_menu)
			self.play = self.context_menu.addAction({True: "Stop Game", False:"Play Game"}[self.is_playing], self.toggle_play_state)
		
		self.context_menu.exec_(event.globalPos())

	def copy_selected_objects(self):
		self.clipboard = [obj.copy() for obj in self.selected_objects]

	def paste(self):
		for obj in self.selected_objects:
			obj.selected = False
		for obj in self.clipboard:
			obj.pos[0] += 5
			obj.pos[1] += 5

			self.objects.append(obj)
			obj.selected = True

		self.selected_objects = self.clipboard
		self.clipboard = None

	def destroy_selected_objects(self):
		# Remove selected objects from the game
		for obj in self.selected_objects:
			self.objects.remove(obj)
		self.selected_objects.clear()
		self.console.append_text("Destroyed selected objects")
		self.update_properties_display(selected_object=None)

	def show_new_object_menu(self):
		shape_menu = QMenu("Select Object", self)
		shape_menu.addAction("Square", self.add_square)
		shape_menu.addAction("Circle", self.add_circle)
		shape_menu.addAction("Text", self.add_text)
		shape_menu.exec_(QCursor.pos())

	def add_square(self):
		self.add_shape('square')

	def add_circle(self):
		self.add_shape('circle')
	def add_text(self):
		self.add_shape('text')

	def add_shape(self, shape):
		if self.is_playing:
			self.console.append_text("Unable to add shape in (Playing mode)")
			return

		self.console.append_text(f"Added shape: {shape}")
		global_pos = QCursor.pos()
		local_pos = self.mapFromGlobal(global_pos)

		x = local_pos.x() - 25
		y = local_pos.y() - 25
		
		if shape == 'square':
			self.objects.append(GameObject((x, y), (50, 50), color=(0,0,255), shape='square', parent=self))
		elif shape == 'circle':
			self.objects.append(GameObject((local_pos.x(), local_pos.y()), (50, 50), color=(0,255,0), shape='circle', parent=self))
		elif shape == 'text':
			self.objects.append(GameObject((local_pos.x(), local_pos.y()), (100, 25), color=(0,255,0), shape='text', parent=self))

	def toggle_play_state(self, quiet_mode=False):
		if not self.is_playing:
			if not quiet_mode:
				self.current_state = [obj.copy() for obj in self.objects]
				for obj in self.objects:
					obj.execute_script()
		else:
			self.objects = self.current_state
		self.is_playing = not self.is_playing
		playing = {True: "Stop Game", False:"Play Game"}[self.is_playing]
		self.play.setText(playing)
		if not quiet_mode:
			self.console.append_text(f"Play Mode is set to: ({self.is_playing})")
		for obj in self.selected_objects:
			obj.selected = False
		self.selected_objects = []
		self.update_game()
		self.update_properties_display(selected_object=None)

	def update_properties_display(self, selected_object):
		self.property_frame.list_widget.clear()

		if selected_object:
			self.property_frame.list_widget.addItem(f"Property: {selected_object}")
			self.property_frame.list_widget.addItem(f"   Position: {selected_object.pos}")
			if selected_object.shape == "circle":
				self.property_frame.list_widget.addItem(f"   Radius: {selected_object.radius}")
			else:
				self.property_frame.list_widget.addItem(f"   Size: {selected_object.size}")
				
			if selected_object.shape == "text":
				self.property_frame.list_widget.addItem(f"   Font Size: {selected_object.font_size}")
				self.property_frame.list_widget.addItem(f"   Text: {selected_object.text}")
			
			self.property_frame.list_widget.addItem(f"   Color: {self.rgb_to_hex(selected_object.color)}")
			self.property_frame.list_widget.addItem(f"   Shape: {selected_object.shape}")
			self.property_frame.list_widget.addItem(f"   Script: ...")

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			if not self.is_playing:
				clicked_on_object = False
				for obj in self.objects:
					if self.is_mouse_on_object(event.pos(), obj):
						clicked_on_object = True
						if event.modifiers() & Qt.ShiftModifier:
							# Add to selection if Shift is held
							if obj in self.selected_objects:
								obj.selected = False
								self.selected_objects.remove(obj)
							else:
								obj.selected = True
								self.selected_objects.append(obj)
							continue
						else:
							# Single selection without Shift
							for selected_obj in self.selected_objects:
								selected_obj.selected = False
							self.selected_objects = [obj]
							obj.selected = True
							continue
						break
				
				if not clicked_on_object:
					# Deselect all objects if background is clicked
					for selected_obj in self.selected_objects:
						selected_obj.selected = False
					self.selected_objects.clear()
					self.update_properties_display(None)

				for obj in self.selected_objects:
					self.update_properties_display(obj)

			# Store the last mouse position on mouse press
			self.last_mouse_pos = event.pos()

	def rgb_to_hex(self, rgb):
		return "#{:02x}{:02x}{:02x}".format(*rgb)

	def hex_to_rgb(self, hex_color):
		hex_color = hex_color.lstrip('#')
		return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

				

	def mouseMoveEvent(self, event):
		if not self.is_playing and self.last_mouse_pos and self.selected_objects:
			# Calculate mouse movement delta
			dx = event.x() - self.last_mouse_pos.x()
			dy = event.y() - self.last_mouse_pos.y()

			# Move all selected objects based on mouse movement
			for obj in self.selected_objects:
				obj.pos = (obj.pos[0] + dx, obj.pos[1] + dy)

				self.update_properties_display(obj)

			# Update last mouse position
			self.last_mouse_pos = event.pos()

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.LeftButton:
			if self.selected_objects:
				for obj in self.selected_objects:
					obj.selected = True
			# Reset last mouse position
			self.last_mouse_pos = None

	def is_mouse_on_object(self, mouse_pos, obj):
		x, y = obj.pos
		w, h = obj.size
		return x <= mouse_pos.x() <= x + w and y <= mouse_pos.y() <= y + h

class PropertiesFrame(QFrame):
	def __init__(self):
		super().__init__()
		self.setFixedWidth(200)
		self.setStyleSheet("background-color: lightgray;")

		self.script_editor = ScriptEditor(self)
		
		self.layout = QVBoxLayout(self)
		self.list_widget = QListWidget(self)
		self.layout.addWidget(self.list_widget)
		self.setLayout(self.layout)
		
		self.list_widget.itemDoubleClicked.connect(self.edit_property)

	def edit_script(self):
		if self.script_editor.isVisible():
			self.game.console.append_text("Unable to edit script, since there is already one running.")
			return
		self.script_editor.edit_script(self.game.selected_objects[0])
		self.script_editor.show()

	def edit_property(self, item):
		if not self.game.selected_objects:
			self.game.console.append_text("Unable to edit properties in (Playing mode)")
			return
		# Extract property name and value from the item text
		property_text = item.text().split(": ")
		property_name = property_text[0].strip()
		if property_name == "Script":
			self.edit_script()
			return
		if property_name == "Property":
			return
		try:
			current_value = str(list(ast.literal_eval(property_text[1])))
		except:
			current_value = property_text[1]



		# Create a dialog for editing
		dialog = QDialog(self)
		dialog.setWindowTitle(f"Edit Property: {property_name}")
		dialog.setGeometry(0,0, 300, 100)
		dialog_layout = QFormLayout(dialog)

		# Create a QLineEdit for editing

		edit_input = QLineEdit(current_value)

		inputs = {property_name: edit_input}

		if property_name in ["Position", "Size"]:
			val1, val2 = ast.literal_eval(current_value)
			edit_input = QLineEdit(str(val1))
			edit_input2 = QLineEdit(str(val2))
			dialog_layout.addRow(property_name + " 1", edit_input)
			dialog_layout.addRow(property_name + " 2", edit_input2)

			inputs[property_name] = [edit_input, edit_input2]

		else:
			dialog_layout.addRow(property_name, edit_input)

		save_button = QPushButton("Save")
		save_button.clicked.connect(lambda: self.save_property(property_name, inputs, dialog))
		dialog_layout.addWidget(save_button)

		dialog.exec_()

	def set_game(self, game):
		self.game = game

	def save_property(self, property_name, inputs, dialog):
		# Update the property based on its name
		selected_items = self.list_widget.selectedItems()
		if selected_items:
			selected_object = self.game.selected_objects[0]
			if property_name == 'Position':
				try:
					pos = (ast.literal_eval(inputs[property_name][0].text()), ast.literal_eval(inputs[property_name][1].text()))
					selected_object.pos = list(pos)
				except ValueError:
					dialog.accept()
					QMessageBox.warning(self, "Input Error", "Please enter a valid position.")
					return
			elif property_name == 'Size':
				try:
					size = (ast.literal_eval(inputs[property_name][0].text()), ast.literal_eval(inputs[property_name][1].text()))
					selected_object.size = size
				except ValueError as e:
					dialog.accept()
					QMessageBox.warning(self, "Input Error", "Please enter a valid size.")
					return
			elif property_name == 'Color':
				selected_object.color = self.game.hex_to_rgb(inputs[property_name].text())
			elif property_name == 'Font Size':
				try:
					selected_object.font_size = int(inputs[property_name].text())
				except:
					QMessageBox.warning(self, "Input Error", "Please enter a valid size.")
				
			elif property_name == 'Text':
				selected_object.text = str(inputs[property_name].text())
			elif property_name == 'Shape':
				if inputs[property_name].text() not in ["circle", "square"]:
					dialog.accept()
					QMessageBox.warning(self, f"Expected: (circle/square) Got {inputs[property_name].text()}", "Please enter a valid shape")
					return
				selected_object.shape = inputs[property_name].text()

			self.game.update_properties_display(self.game.selected_objects[0])
			dialog.accept()

class ScriptEditor(QDialog):
	def __init__(self, parent):
		super().__init__()
		self.setWindowTitle("Script Editor")
		self.setFixedSize(400, 300)

		self.script_editor = QTextEdit(self)

		#self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
		
		layout = QVBoxLayout(self)
		layout.addWidget(self.script_editor)
		self.setLayout(layout)

		self.parent = parent

	def edit_script(self, obj):
		self.script_editor.setText(obj.script)

	def closeEvent(self, event):
		self.first_selected = self.parent.game.selected_objects[0]
		self.first_selected.script = self.script_editor.toPlainText()

class ConsoleDialog(QDialog):
	def __init__(self, MainWindow):
		super().__init__()
		self.MainWindow = MainWindow
		self.setWindowTitle("Console")
		self.setFixedSize(400, 300)
		
		# Add a QTextEdit widget to display console messages
		self.console_output = QTextEdit(self)
		self.console_output.setReadOnly(True)

		self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
		
		layout = QVBoxLayout(self)
		layout.addWidget(self.console_output)
		self.setLayout(layout)

	def closeEvent(self, event):
		# Handle the close event to perform actions when console is closed
		self.MainWindow.toggle_console_action.setText("Show Console")
		super().closeEvent(event)

	def append_text(self, text):
		# Append new text to the console
		self.console_output.append(text)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("PyEngine")

		self.setGeometry(100, 100, 800, 600)
		
		# Initialize the console dialog
		self.console_dialog = ConsoleDialog(self)
		
		# Add menu bar with an option to toggle the console
		self.menu_bar = self.menuBar()
		self.view_menu = self.menu_bar.addMenu("View")
		
		# Add an action to toggle the console visibility
		self.toggle_console_action = self.view_menu.addAction("Show Console")
		self.toggle_console_action.triggered.connect(self.toggle_console)

		frame = QFrame(self)
		frame.setStyleSheet("background-color: lightgray;")
		
		layout = QHBoxLayout(frame)
		
		self.properties_frame = PropertiesFrame()
		self.game = Game(self.properties_frame, self.console_dialog)
		
		layout.addWidget(self.game)
		self.properties_frame.set_game(self.game)
		layout.addWidget(self.properties_frame)
		
		frame.setLayout(layout)
		self.setCentralWidget(frame)

	def toggle_console(self):
		# Toggle the console window visibility
		if self.console_dialog.isVisible():
			self.console_dialog.hide()
			self.toggle_console_action.setText("Show Console")
		else:
			self.console_dialog.show()
			self.toggle_console_action.setText("Hide Console")

if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())