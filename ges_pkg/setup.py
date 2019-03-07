import setuptools

setuptools.setup(
    name='guardian-ecosystem-simulator',
    version='0.1',
    scripts=['ges'] ,
    author="Alex Bennett",
    author_email="abennett@elexausa.com",
    description="Guardian IoT ecosystem simulator",
    long_description="Guardian Ecosystem Simulator enables simulation of experimental IoT devices.",
    url="https://github.com/elexausa/guardian-ecosystem-simulator",
    packages=setuptools.find_packages(),
    install_requires=[
        'Click==7.0',
        'dataclasses==0.6',
        'simpy==3.0.11',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
 )
