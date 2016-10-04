from __future__ import with_statement

from setuptools import setup


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='ring',
    version='0.1.0',
    description='Generic cache decorator with built-in memcache & redis support.',
    long_description=get_readme(),
    author='Jeong YunWon',
    author_email='ring@youknowone.org',
    url='https://github.com/youknowone/ring',
    packages=(
        'ring',
    ),
    install_requires=[
        'prettyexc>=0.6.0',
    ],
    tests_require=[
        'pytest', 'tox', 'mock', 'patch',
        'pymemcache',
        'redis',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
