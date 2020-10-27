from setuptools import setup

setup(
    name="timesheet",
    version="v23",
    install_requires=[
        "sqlalchemy~=1.3",
        "click~=7.1",
    ],
    extras_require={
        "dev": [
            "sqlalchemy-stubs==0.3",
            "mypy==0.790",
        ]
    },
    packages=["timesheet"],
    entry_points={
        "console_scripts": ["timesheet = timesheet:main", "clock = timesheet:clock"]
    },
)
