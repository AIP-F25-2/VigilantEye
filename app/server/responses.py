from flask import jsonify
def ok(**data): return jsonify({"ok": True, **data})
def err(msg, code=400): return jsonify({"ok": False, "error": msg}), code
