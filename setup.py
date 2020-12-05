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
        "dev": ["sqlalchemy-stubs>=0.3", "black>=20.7", "flake8>=s.8.4", "pylint>=2.6.0"],
        "full": [
            "toml>=0.10.2",
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
    packages=["timesheet"],
    entry_points={"console_scripts": ["timesheet = timesheet:main", "clock = timesheet:clock"]},
)
