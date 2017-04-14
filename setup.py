from __future__ import with_statement

from setuptools import setup
import sys

tests_require = [
    'pytest>=3.0.2', 'pytest-cov', 'mock', 'patch',
    'pymemcache',
    'redis', 'requests',
]

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

if sys.version_info[:2] == (3, 3):
    tests_require.extend([
        'asyncio',
    ])

if sys.version_info >= (3, 3):
    tests_require.extend([
        'pytest-asyncio',
        'aiomcache',
        'aioredis',
    ])


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='ring',
    version='0.2.5',
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
    ],
    tests_require=tests_require + ['tox', 'tox-pyenv'],
    extras_require={
        'tests': tests_require,
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
