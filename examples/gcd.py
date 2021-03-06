# Example of instantiating a wasm module and calling an export on it

from wasmtime import Store, Module, Instance

store = Store()
module = Module.from_file(store, './examples/gcd.wat')
instance = Instance(module, [])
gcd = instance.get_export("gcd").func()

print("gcd(6, 27) = %d" % gcd.call(6, 27))
