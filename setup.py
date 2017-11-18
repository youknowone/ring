from __future__ import with_statement

from setuptools import setup
import sys


def get_version():
    with open('ring/version.txt') as f:
        return f.read().strip()


tests_require = [
    'pytest>=3.0.2', 'pytest-cov', 'pytest-lazy-fixture', 'mock', 'patch',
    'pymemcache',
    'redis', 'requests',
]
docs_require = [
    'sphinx',
]

dev_require = tests_require + docs_require

try:
    import __pypy__  # noqa
except ImportError:
    tests_require.extend([
        'pylibmc',
    ])

if sys.version_info[0] == 2:
    tests_require.extend([
        'python-memcached',
    ])
else:
    tests_require.extend([
        'python3-memcached',
    ])

if (3, 3) <= sys.version_info[:2] <= (3, 4):
    tests_require.extend([
        'asyncio',
    ])

if sys.version_info >= (3, 3):
    if sys.version_info < (3, 5):
        tests_require.append('pytest-asyncio==0.5.0')
    else:
        tests_require.append('pytest-asyncio')
    tests_require.extend([
        'aiomcache',
        'aioredis>=1.0.0',
    ])


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='ring',
    version=get_version(),
    description='The ultimate cache with built-in memcache & redis + asyncio support.',
    long_description=get_readme(),
    author='Jeong YunWon',
    author_email='ring@youknowone.org',
    url='https://github.com/youknowone/ring',
    packages=(
        'ring',
    ),
    install_requires=[
        'prettyexc>=0.6.0',
        'callable>=0.1.2',
    ],
    tests_require=tests_require + ['tox', 'tox-pyenv'],
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
        'dev': dev_require,
    },
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
        'Programming Language :: Python :: 3.6',
    ],
)  # noqa
