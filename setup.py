#!/usr/bin/env python
from setuptools import setup, find_packages

VERSION = '0.2.1'

entry_points = {
	'console_scripts': [
		'nti_render_content = nti.deploymenttools.content.render:main',
		'nti_release_content = nti.deploymenttools.content.release_content:main',
		'nti_build_content_catalog = nti.deploymenttools.content.build_catalog:main',
		'nti_gc_content_catalog = nti.deploymenttools.content.gc_catalog:main',
		'nti_update_library = nti.deploymenttools.content.update_library:main',
		'nti_remote_render = nti.deploymenttools.content.remote_render:main',
	]
}

setup(
	name = 'nti.deploymenttools.content',
	version = VERSION,
	keywords = 'deployment tools',
	author = 'Sean Jones',
	author_email = 'sean.jones@nextthought.com',
	description = 'NextThought Platform Deployment Tools',
	long_description = 'Dataserver README',
	classifiers=[
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers :: Education",
		"Operating System :: OS Independent",
		"Programming Language :: Python :: 2.7",
		"Framework :: Pylons :: ZODB :: Pyramid",
		"Internet :: WWW/HTTP",
		"Natural Language :: English",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
	],
	install_requires = [
		'setuptools',
		'boto',
		'nti.contentrendering',
	],
	packages = find_packages( 'src' ),
	package_dir = {'': 'src'},
	package_data = {'nti': [ 'deploymenttools/content/default_sharing.json' ]},
	include_package_data = True,
	namespace_packages=['nti', 'nti.deploymenttools'],
	zip_safe = False,
	entry_points = entry_points
	)
