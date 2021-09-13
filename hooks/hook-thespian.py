from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []

for mod in collect_submodules('thespian'):
    if not mod.startswith('thespian.test'):
        hiddenimports.append(mod)
