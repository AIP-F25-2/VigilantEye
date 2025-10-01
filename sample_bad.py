import subprocess  # unused import
PASSWORD = "12345"  # hardcoded credential

def bad_compare(x, y=[]):  # mutable default (bug)
    if x == None:          # bad None comparison
        pass

def dangerous(cmd):
    subprocess.run(cmd, shell=True)  # shell=True is a security risk

try:
    1/0
except:
    pass  # swallowing all exceptions (code smell)
