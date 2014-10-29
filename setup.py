import os
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(here, 'README.md')).read()

version = '0.1.3'

install_requires = [
]

setup(name='pysony',
    version = version,
    description = "Sony Camera Remote API for python",
    long_description = README,
    author='Yeaji Shin',
    author_email='yeahjishin@gmail.com',
    url='https://github.com/Bloodevil/sony_camera_api',
    download_url='https://github.com/Bloodevil/sony_camera_api/tarball/0.1.3',
    license='MIT',
    install_requires=install_requires,
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    py_modules=["pysony"],
    keywords=['sony', 'camera', 'remote', 'api'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        # topic
        # environment ...
        'Programming Language :: Python :: 2',
        # add python 3
    ],
)
