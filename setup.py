import codecs
from setuptools import setup, find_packages

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

TESTS_REQUIRE = [
    'nti.testing',
    'zope.testrunner',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.deploymenttools.content',
    version=_read('version.txt').strip(),
    author='Sean Jones',
    author_email='sean.jones@nextthought.com',
    description='NextThought Platform Deployment Tools',
    long_description=(_read('README.rst') + '\n\n' + _read("CHANGES.rst")),
    license='Apache',
    keywords='deployment tools',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Development Status :: 4 - Beta",
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.deploymenttools.content",
    zip_safe=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti', 'nti.deploymenttools'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'setuptools',
        'boto',
        'nti.contentrendering',
        'six',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
        ],
    },
    entry_points=entry_points,
)
