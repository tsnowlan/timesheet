from setuptools import setup

setup(
    name="timesheet",
    version="v1.0.0",
    install_requires=[
        "sqlalchemy~=1.3",
        "click~=7.1",
    ],
    extras_require={
        "dev": ["sqlalchemy-stubs==0.3", "black~=20.8b1", "flake8~=3.8.4", "pylint~=2.6.0"],
        "format": ["pyyaml~=5.3.1", "toml~=0.10.2"],
    },
    packages=["timesheet"],
    entry_points={"console_scripts": ["timesheet = timesheet:main", "clock = timesheet:clock"]},
)
