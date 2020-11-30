from setuptools import setup

setup(
    name="timesheet",
    version="v1.0.0",
    install_requires=[
        "sqlalchemy>=1.3",
        "click>=7.1",
    ],
    python_requires=">=3.9",
    extras_require={
        "dev": [
            "sqlalchemy-stubs>=0.3",
            "black>=20.7",
        ],
        "full": [
            "toml",
            "PyYAML>=5.3",
        ],
    },
    packages=["timesheet"],
    entry_points={
        "console_scripts": [
            "timesheet = timesheet:main",
            "clock = timesheet:clock",
        ]
    },
)
