import os
import setuptools

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Open version file
version_file = open(os.path.join(__location__, 'VERSION'))

# Get version number
version = version_file.read().strip()

setuptools.setup(
    name='guardian-ecosystem-simulator-cli',
    version=version,
    scripts=['ges'] ,
    author="Alex Bennett",
    author_email="abennett@elexausa.com",
    description="Guardian IoT ecosystem simulator CLI",
    long_description="CLI for control of guardian-ecosystem-simulator-daemon.",
    url="https://github.com/elexausa/guardian-ecosystem-simulator",
    packages=setuptools.find_packages(),
    install_requires=[
        'Click==7.0',
        'guardian-ecosystem-simulator'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
 )
