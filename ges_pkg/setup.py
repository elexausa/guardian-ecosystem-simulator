import setuptools

setuptools.setup(
    name='guardian-ecosystem-simulator',
    version='0.5',
    scripts=['gesd'] ,
    author="Alex Bennett",
    author_email="abennett@elexausa.com",
    description="Guardian IoT ecosystem simulator",
    long_description="Guardian Ecosystem Simulator provides toolset and \
            workspace for the research and development of various connected \
            (IoT-oriented) devices. Also includes daemon process that can be \
            configured by implemeter to run at startup server-side. Consider \
            `systemd` if this functionality is desired.",
    url="https://github.com/elexausa/guardian-ecosystem-simulator",
    packages=setuptools.find_packages(),
    install_requires=[
        'dataclasses==0.6',
        'simpy==3.0.11'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
 )
