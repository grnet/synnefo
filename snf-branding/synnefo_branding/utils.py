from synnefo_branding import settings

def get_branding_dict():
	dct = {}
	for key in dir(settings):
		if key == key.upper():
			dct[key.lower()] = getattr(settings, key)
	return dct

def brand_message(msg, **extra_args):
	params = get_branding_dict()
	params.update(extra_args)
	return msg % params
