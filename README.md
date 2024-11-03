# PyEngine

Have you ever considered making a game without making boilerplate code?

No? Well now you have a game engine that does it

It has a UI like any other game engine.

# Requirements

This game engine requires these libraries:
```
pip install pygame-ce
pip install lupa
pip install pyqt5
```

- **Pygame**
   - game rendering

- **PyQt5**
   - ui rendering

- **Lupa**
   - lua runtime

# UI

It has THE game screen and properties menu with a object viewer.

# Script

It uses Lua for scripts

`self` is a built in class for Lua, giving you the power of editing attributes

For example
```lua
self.pos[0] = 10 -- pos is a list of 2 values, x and y
self.pos[1] = 10

--"""
--Every single attribute in the properties bar is a legal attribute to modify
--"""
```
