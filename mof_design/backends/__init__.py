"""Backend adapters emit proposals; task validation and delivery are shared."""
def create(engine, task, request, runtime):
    if engine=='egmof':
        from .egmof import EGMOFBackend
        return EGMOFBackend(task,request,runtime)
    if engine=='mofflow2_linker':
        from .mofflow2 import LinkerBackend
        return LinkerBackend(task,request,runtime)
    raise ValueError('unsupported backend')
