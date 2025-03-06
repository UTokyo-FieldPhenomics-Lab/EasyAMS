import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

with open('easyams/__init__.py', encoding='utf-8') as fid:
    for line in fid:
        if line.startswith('__version__'):
            VERSION = line.strip().split()[-1][1:-1]
            break

def parse_requirements_file(filename):
    with open(filename, encoding='utf-8') as fid:
        requires = [line.strip() for line in fid.readlines() if line]

    return requires

INSTALL_REQUIRES = parse_requirements_file('requirements/inference.txt')
# The `requirements/extras.txt` file is explicitely omitted because
# it contains requirements that do not have wheels uploaded to pip
# for the platforms we wish to support.
extras_require = {
    dep: parse_requirements_file('requirements/' + dep + '.txt')
    for dep in ['train'] #['docs', 'test', 'build']
}


setup(
    name="easyams",  # 包名
    version=VERSION,  # 版本号
    author="Haozhou Wang",  # 作者
    author_email="howcanoewang@gmail.com",  # 作者邮箱
    description="Easy Agisoft MetaShape (EasyAMS) Plugin with extended functions for smart agriculture.",  # 简短描述
    long_description=long_description,
    long_description_content_type="text/markdown",  # 长描述的格式
    url="https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS",  # 项目主页
    packages=find_packages(),  # 自动发现包
    install_requires=INSTALL_REQUIRES,
    classifiers=[  # 分类信息
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Processing",
        "Topic :: Environment :: Plugins",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires=">=3.8, <4",  # Python 版本要求
    project_urls={
        # 'Documentation': 'https://easyams.readthedocs.io/en/latest/',
        'Source': 'https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS',
        'Tracker': 'https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/issues',
        'forum': 'https://github.com/UTokyo-FieldPhenomics-Lab/EasyAMS/discussions'
    },
)