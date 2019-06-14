import setuptools

setuptools.setup(
    name="coraxml_utils",
    version="0.1.0",
    description="Utils for CorA-XML files",
    packages=setuptools.find_packages(),
    install_requires=[
        'lxml',
        'regex',
        'lark-parser'
    ],
)
