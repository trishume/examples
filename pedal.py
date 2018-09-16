from talon import tap
from talon.voice import talon
from . import state, speech_toggle, noise

prev_enabled = talon.enabled

def enable():
    if state.control_mouse:
        return

    global prev_enabled
    prev_enabled = talon.enabled
    speech_toggle.set_enabled(False)
    state.control_mouse = True
    noise.model.register()

def disable():
    global prev_enabled
    state.control_mouse = False
    speech_toggle.set_enabled(prev_enabled)
    noise.model.unregister()

def on_key(typ, e):
    # print((typ, e, e.key))
    if e.key == 'f6':
        e.block()
        if e.flags & tap.DOWN:
            enable()
        else:
            disable()

tap.register(tap.KEY | tap.HOOK, on_key)

def on_mouse(typ, e):
    # print((typ, e, e.button))
    if e.button == 4:
        e.block()
        if e.flags & tap.DOWN:
            enable()
        else:
            disable()

# tap.register(tap.MCLICK | tap.HOOK, on_mouse)
