from synnefo_branding import settings
from django.template.loader import render_to_string as django_render_to_string

def get_branding_dict(prepend=None):
	dct = {}
	for key in dir(settings):
		if key == key.upper():
			newkey = key.lower()
			if prepend:
				newkey = '%s_%s' % (prepend, newkey)
			dct[newkey.upper()] = getattr(settings, key)
	return dct

def brand_message(msg, **extra_args):
	params = get_branding_dict()
	params.update(extra_args)
	return msg % params

def render_to_string(template_name, dictionary=None, context_instance=None):
	if not dictionary:
		dictionary = {}
	newdict = get_branding_dict("BRANDING")
	newdict.update(dictionary)
	return django_render_to_string(template_name, newdict, context_instance)