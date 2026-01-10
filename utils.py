import json

def clean_object(obj):
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if obj[key] is None:
                del obj[key]
            else:
                obj[key] = clean_object(obj[key])
    elif isinstance(obj, list):
        obj = [clean_object(item) for item in obj if item is not None]
    return obj

def normalize_args(raw_args):
    obj = {}
    if isinstance(raw_args, dict):
        obj = raw_args
    # if it is a string, parse JSON
    elif isinstance(raw_args, str):
        raw_args = raw_args.strip()
        try:
            obj = json.loads(raw_args)
        except Exception:
            # model produced non-JSON content
            obj = {"text": raw_args}
    else:
        obj = raw_args

    return clean_object(obj)