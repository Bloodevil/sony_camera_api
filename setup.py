import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

here = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(here, 'README.md')).read()

version = '0.1.1'

install_requires = [
]

setup(name='sony-camera-api',
    version = version,
    description = "Sony Camera Remote API for python",
    author='Yeaji Shin',
    author_email='yeahjishin@gmail.com',
    url='https://github.com/Bloodevil/sony_camera_api',
    download_url='https://github.com/Bloodevil/sony_camera_api/tarball/0.1',
    license='MIT',
    install_requires=install_requires,
    py_modules=["sony_camera_api",
    ],
    keywords=['sony', 'camera', 'remote', 'api'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        # topic
        # environment ...
        'Programming Language :: Python :: 2',
        # add python 3
    ],
)
