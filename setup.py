from setuptools import setup

setup(
    name="pyvivado",
    packages=['pyvivado'],
    package_data={
        '': ['sh/*.sh', 'sh/*.sh.t', 'tcl/*.tcl.t', 'tcl/*.tcl', 'xdc/*.xdc'],
    },
    use_scm_version={
        "relative_to": __file__,
        "write_to": "pyvivado/version.py",
    },
    author="Ben Reynwar",
    author_email="ben@reynwar.net",
    license="MIT",
    url="https://github.com/codelucida/huRTLing",
    install_requires=[
        'redis',
    ],
    dependency_links=[
    ],
)
