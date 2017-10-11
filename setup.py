#!/usr/bin/env python
from setuptools import setup, find_packages

VERSION = '1.0.0rc1'

entry_points = {
	'console_scripts': [
		'nti_backup_course = nti.deploymenttools.content.backup_course_bundle:main',
		'nti_copy_content_package = nti.deploymenttools.content.copy_content_package:main',
		'nti_copy_course = nti.deploymenttools.content.copy_course:main',
		'nti_remote_render = nti.deploymenttools.content.remote_render:main',
		'nti_render_content = nti.deploymenttools.content.render:main',
		'nti_restore_course = nti.deploymenttools.content.restore_course_bundle:main',
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
	include_package_data = True,
	namespace_packages=['nti', 'nti.deploymenttools'],
	zip_safe = False,
	entry_points = entry_points
	)
