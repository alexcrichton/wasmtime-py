from ._ffi import *
from ctypes import *
from wasmtime import Store

dll.wasm_trap_new.restype = P_wasm_trap_t
dll.wasm_frame_func_index.restype = c_uint32
dll.wasmtime_frame_func_name.restype = POINTER(wasm_byte_vec_t)
dll.wasmtime_frame_module_name.restype = POINTER(wasm_byte_vec_t)


class Trap(Exception):
    # Creates a new trap in `store` with the given `message`
    def __init__(self, store, message):
        if not isinstance(store, Store):
            raise TypeError("expected a Store")
        if not isinstance(message, str):
            raise TypeError("expected a string")
        message_raw = str_to_name(message, trailing_nul=True)
        ptr = dll.wasm_trap_new(store.__ptr__, byref(message_raw))
        if not ptr:
            raise RuntimeError("failed to create trap")
        self.__ptr__ = ptr

    @classmethod
    def __from_ptr__(cls, ptr):
        if not isinstance(ptr, P_wasm_trap_t):
            raise TypeError("wrong pointer type")
        trap = cls.__new__(cls)
        trap.__ptr__ = ptr
        return trap

    # Returns the message for this trap
    def message(self):
        message = wasm_byte_vec_t()
        dll.wasm_trap_message(self.__ptr__, byref(message))
        # subtract one to chop off the trailing nul byte
        message.size -= 1
        ret = message.to_str()
        message.size += 1
        dll.wasm_byte_vec_delete(byref(message))
        return ret

    # Returns the message for this trap
    def frames(self):
        frames = FrameList()
        dll.wasm_trap_trace(self.__ptr__, byref(frames.vec))
        ret = []
        for i in range(0, frames.vec.size):
            ret.append(Frame.__from_ptr__(frames.vec.data[i], frames))
        return ret

    def __str__(self):
        frames = self.frames()
        message = self.message()
        if len(frames) > 0:
            message += "\nwasm backtrace:\n"
            for i, frame in enumerate(frames):
                module = frame.module_name() or '<unknown>'
                default_func_name = '<wasm function %d>' % frame.func_index()
                func = frame.func_name() or default_func_name
                message += "  %d: %s!%s\n" % (i, module, func)
        return message

    def __del__(self):
        if hasattr(self, '__ptr__'):
            dll.wasm_trap_delete(self.__ptr__)


class Frame(object):
    @classmethod
    def __from_ptr__(cls, ptr, owner):
        ty = cls.__new__(cls)
        if not isinstance(ptr, P_wasm_frame_t):
            raise TypeError("wrong pointer type")
        ty.__ptr__ = ptr
        ty.__owner__ = owner
        return ty

    # Returns the function index this frame corresponds to in its wasm module
    def func_index(self):
        return dll.wasm_frame_func_index(self.__ptr__)

    # Returns the name of the function this frame corresponds to
    #
    # May return `None` if no name can be inferred
    def func_name(self):
        ptr = dll.wasmtime_frame_func_name(self.__ptr__)
        if ptr:
            return ptr.contents.to_str()
        else:
            return None

    # Returns the name of the module this frame corresponds to
    #
    # May return `None` if no name can be inferred
    def module_name(self):
        ptr = dll.wasmtime_frame_module_name(self.__ptr__)
        if ptr:
            return ptr.contents.to_str()
        else:
            return None

    def __del__(self):
        if self.__owner__ is None:
            dll.wasm_frame_delete(self.__ptr__)


class FrameList(object):
    def __init__(self):
        self.vec = wasm_frame_vec_t(0, None)

    def __del__(self):
        dll.wasm_frame_vec_delete(byref(self.vec))
