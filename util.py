import os

def empty_dir(dir):
    for (name, type, *_) in os.ilistdir(dir):
        full_path = f'{dir}/{name}'
        if type == 0x8000:
            os.remove(full_path)
            continue

        empty_dir(full_path)
        os.rmdir(full_path)

def singleton(f):
    running = False
    
    def call(*args, **kwargs):
        nonlocal running
        
        if running:
            return
    
        running = True
        f(*args, **kwargs)
        running = False
    
    return call