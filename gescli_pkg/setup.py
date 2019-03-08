import setuptools

setuptools.setup(
    name='guardian-ecosystem-simulator-cli',
    version='0.1',
    scripts=['ges'] ,
    author="Alex Bennett",
    author_email="abennett@elexausa.com",
    description="Guardian IoT ecosystem simulator CLI",
    long_description="CLI for control of guardian-ecosystem-simulator-daemon.",
    url="https://github.com/elexausa/guardian-ecosystem-simulator",
    packages=setuptools.find_packages(),
    install_requires=[
        'Click==7.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
 )
